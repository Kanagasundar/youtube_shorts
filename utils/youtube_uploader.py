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
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

class YouTubeUploader:
    """Handles YouTube video uploads with authentication"""

    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    
    def __init__(self, credentials_path='credentials.json', token_path='token.pickle'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.youtube = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with YouTube API using token.pickle or service account"""
        try:
            # Check for pre-existing token.pickle
            credentials = None
            if os.path.exists(self.token_path):
                logger.info("🔍 Loading saved OAuth2 token from token.pickle")
                with open(self.token_path, 'rb') as token:
                    credentials = pickle.load(token)

            # If no valid credentials, try service account or refresh token
            if not credentials or not credentials.valid:
                with open(self.credentials_path, 'r', encoding='utf-8') as f:
                    creds_data = json.load(f)
                
                if creds_data.get('type') == 'service_account':
                    logger.info("📝 Detected service account credentials")
                    credentials = service_account.Credentials.from_service_account_info(
                        creds_data, scopes=self.SCOPES
                    )
                elif credentials and credentials.expired and credentials.refresh_token:
                    logger.info("🔄 Refreshing expired OAuth2 token")
                    credentials.refresh(Request())
                    # Save refreshed token
                    with open(self.token_path, 'wb') as token:
                        pickle.dump(credentials, token)
                        logger.info(f"✅ Saved refreshed OAuth2 token to {self.token_path}")
                else:
                    logger.error("❌ No valid credentials or token available")
                    logger.info("💡 For automated environments, ensure:")
                    logger.info("   1. YOUTUBE_TOKEN secret is set with a valid base64-encoded token.pickle")
                    logger.info("   2. YOUTUBE_CREDENTIALS secret contains service account credentials")
                    raise RuntimeError("YouTube authentication failed")

            self.youtube = build('youtube', 'v3', credentials=credentials)
            logger.info("✅ YouTube API client initialized successfully")

        except Exception as e:
            logger.error(f"❌ Authentication failed: {str(e)}")
            logger.debug("Stack trace:", exc_info=True)
            self.youtube = None
            raise RuntimeError("YouTube authentication failed")
    
    def generate_video_metadata(self, topic: str, category: str) -> dict:
        """Generate metadata for the YouTube video based on topic and category"""
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
            if len(description) > 5000:
                description = description[:4997] + "..."  # YouTube description limit is 5000 characters
            
            tags = [
                "youtube shorts",
                category.lower(),
                topic.lower().replace(" ", ""),
                "short video",
                f"{category.lower()} facts"
            ]
            
            metadata = {
                'title': title,
                'description': description,
                'tags': tags,
                'category_id': '24'  # Entertainment, suitable for Science Shorts
            }
            
            logger.info("✅ Video metadata generated successfully")
            return metadata
        
        except Exception as e:
            logger.error(f"❌ Failed to generate video metadata: {str(e)}")
            logger.debug("Stack trace:", exc_info=True)
            return {
                'title': topic[:100],
                'description': f"Explore {topic} in this YouTube Short! #{category.lower()} #youtubeshorts",
                'tags': ['youtube shorts', category.lower()],
                'category_id': '24'
            }
    
    def upload_video(self, video_path: str, title: str, description: str, category_id: str = '24', 
                    tags: list = None, privacy_status: str = 'public', max_retries: int = 5):
        """Upload a video to YouTube with retry logic"""
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
                    'video_path': video_path
                }
                metadata_path = Path(video_path).with_suffix('.metadata.json')
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                logger.info(f"✅ Metadata saved to {metadata_path}")
                
                return True, video_id
            
            except Exception as e:
                logger.error(f"❌ Upload failed (attempt {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    logger.warning(f"Retrying in {2 ** attempt} seconds...")
                    import time
                    time.sleep(2 ** attempt)
                else:
                    logger.error("❌ Max retries reached. Upload failed.")
                    return False, None
        
        return False, None