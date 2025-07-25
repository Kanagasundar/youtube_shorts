import os
import pickle
import json
import logging
from datetime import datetime
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

def generate_video_metadata(topic: str, category: str, script: str = '') -> tuple:
    """Generate metadata for the YouTube video based on topic, category, and optional script"""
    logger.info(f"📝 Generating video metadata for topic: {topic}, category: {category}")
    try:
        title = f"{topic} | {category} Short"
        if len(title) > 100:
            title = title[:97] + "..."  # YouTube title limit is 100 characters
        
        description = (
            f"Discover {topic.lower()} in this quick {category} Short! "
            f"Learn something new and exciting about {topic.lower()}. "
            "Subscribe and hit the bell for more fascinating content! "
            f"#{category.lower()} #youtubeshorts #{topic.replace(' ', '').lower()}"
        )
        if script:
            description = f"{script[:200]}... Subscribe for more! #{category.lower()} #youtubeshorts"
        if len(description) > 5000:
            description = description[:4997] + "..."  # YouTube description limit is 5000 characters
        
        tags = [
            "youtube shorts",
            category.lower(),
            topic.lower().replace(" ", ""),
            "short video",
            f"{category.lower()} facts"
        ]
        
        metadata = (title, description, tags)
        
        logger.info("✅ Video metadata generated successfully")
        return metadata
    
    except Exception as e:
        logger.error(f"❌ Failed to generate video metadata: {str(e)}")
        logger.debug("Stack trace:", exc_info=True)
        fallback_metadata = (
            topic[:100],
            f"Explore {topic} in this YouTube Short! #{category.lower()} #youtubeshorts",
            ['youtube shorts', category.lower()]
        )
        return fallback_metadata

class YouTubeUploader:
    """Handles YouTube video uploads with OAuth 2.0 authentication"""

    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    
    def __init__(self, credentials_path='credentials.json', token_path='token.pickle'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.youtube = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with YouTube API using OAuth 2.0 credentials"""
        try:
            credentials = None
            
            # Check for credentials.json
            if not os.path.exists(self.credentials_path):
                logger.error(f"❌ Credentials file not found: {self.credentials_path}")
                raise FileNotFoundError(f"Credentials file not found: {self.credentials_path}")
            
            # Load existing token if available
            if os.path.exists(self.token_path):
                logger.info(f"🔍 Loading saved OAuth 2.0 token from {self.token_path}")
                with open(self.token_path, 'rb') as token:
                    credentials = pickle.load(token)
                
                # Check if credentials are valid or can be refreshed
                if credentials and credentials.valid:
                    logger.info("✅ Valid credentials loaded from token.pickle")
                elif credentials and credentials.expired and credentials.refresh_token:
                    logger.info("🔄 Refreshing expired OAuth 2.0 token")
                    credentials.refresh(Request())
                    with open(self.token_path, 'wb') as token:
                        pickle.dump(credentials, token)
                        logger.info(f"✅ Saved refreshed OAuth 2.0 token to {self.token_path}")
                else:
                    logger.error("❌ Invalid or expired OAuth 2.0 token in token.pickle")
                    credentials = None
            
            # If no valid credentials, run OAuth 2.0 flow (not suitable for CI/CD)
            if not credentials:
                if os.getenv('CI', 'false').lower() == 'true':
                    logger.error("❌ No valid token.pickle found for CI/CD environment")
                    raise RuntimeError("Authentication requires a pre-existing token.pickle in CI/CD")
                else:
                    logger.info("🔐 Initiating OAuth 2.0 user consent flow")
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.SCOPES)
                    credentials = flow.run_local_server(port=0)
                    with open(self.token_path, 'wb') as token:
                        pickle.dump(credentials, token)
                        logger.info(f"✅ Saved new OAuth 2.0 token to {self.token_path}")
            
            self.youtube = build('youtube', 'v3', credentials=credentials)
            logger.info("✅ YouTube API client initialized successfully")
        
        except Exception as e:
            logger.error(f"❌ Authentication failed: {str(e)}")
            logger.debug("Stack trace:", exc_info=True)
            self.youtube = None
            raise RuntimeError("YouTube authentication failed")
    
    def upload_video(self, video_path: str, thumbnail_path: str, title: str, description: str, 
                    tags: list = None, category_id: str = '24', privacy_status: str = 'public', 
                    max_retries: int = 5) -> tuple:
        """Upload a video to YouTube with retry logic and thumbnail support"""
        if not self.youtube:
            logger.error("❌ YouTube client not initialized")
            return False, None
        
        if not os.path.exists(video_path):
            logger.error(f"❌ Video file not found: {video_path}")
            return False, None
        
        body = {
            'snippet': {
                'title': title[:100],  # YouTube title limit is 100 characters
                'description': description[:5000],  # YouTube description limit is 5000 characters
                'tags': tags or ['youtube shorts', 'short video'],
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=1024*1024, resumable=True)
        
        for attempt in range(max_retries):
            try:
                logger.info(f"📤 Uploading video (attempt {attempt + 1}/{max_retries})...")
                request = self.youtube.videos().insert(
                    part='snippet,status',
                    body=body,
                    media_body=media
                )
                response = request.execute()
                video_id = response.get('id')
                logger.info(f"✅ Video uploaded successfully! Video ID: {video_id}")
                
                # Save video metadata
                metadata = {
                    'video_id': video_id,
                    'title': title,
                    'description': description,
                    'upload_time': datetime.now().isoformat(),
                    'video_path': video_path,
                    'thumbnail_path': thumbnail_path
                }
                metadata_path = Path(video_path).with_suffix('.metadata.json')
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                logger.info(f"✅ Metadata saved to {metadata_path}")
                
                # Set thumbnail if provided
                if thumbnail_path and os.path.exists(thumbnail_path):
                    try:
                        logger.info(f"🖼️ Uploading thumbnail: {thumbnail_path}")
                        thumb_media = MediaFileUpload(thumbnail_path)
                        self.youtube.thumbnails().set(
                            videoId=video_id,
                            media_body=thumb_media
                        ).execute()
                        logger.info("✅ Thumbnail uploaded successfully")
                    except Exception as thumb_error:
                        logger.warning(f"⚠️ Failed to upload thumbnail: {thumb_error}")
                
                return True, video_id
            
            except Exception as e:
                logger.error(f"❌ Upload failed (attempt {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    logger.warning(f"Retrying in {2 ** attempt} seconds...")
                    time.sleep(2 ** attempt)
                else:
                    logger.error("❌ Max retries reached. Upload failed.")
                    return False, None
        
        return False, None