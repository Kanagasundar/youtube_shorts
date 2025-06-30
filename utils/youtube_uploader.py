import os
import logging
import pickle
import json
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
from typing import Tuple, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class YouTubeUploader:
    def __init__(self):
        self.youtube = None
        self.SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
        self.credentials_path = 'credentials.json'
        self.token_path = 'token.pickle'
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
                if credentials and credentials.expired and credentials.refresh_token:
                    logger.info("🔄 Refreshing expired OAuth2 token")
                    credentials.refresh(Request())
                else:
                    # Check for service account credentials
                    with open(self.credentials_path, 'r', encoding='utf-8') as f:
                        creds_data = json.load(f)
                    
                    if creds_data.get('type') == 'service_account':
                        logger.info("📝 Detected service account credentials")
                        from google.oauth2 import service_account
                        credentials = service_account.Credentials.from_service_account_info(
                            creds_data, scopes=self.SCOPES
                        )
                    else:
                        logger.info("📝 Detected OAuth2 installed application credentials")
                        if os.getenv('CI', 'false').lower() == 'true':
                            logger.error("❌ Cannot perform interactive OAuth2 flow in CI/CD environment")
                            logger.info("💡 For automated environments, consider using:")
                            logger.info("   1. Service account credentials")
                            logger.info("   2. Pre-generated OAuth2 token (token.pickle)")
                            logger.info("   3. Environment-based token injection")
                            raise RuntimeError("YouTube authentication failed")
                        
                        logger.info("🔐 Starting OAuth2 flow...")
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_path, self.SCOPES
                        )
                        credentials = flow.run_local_server(port=0)
                    
                    # Save the credentials for future runs
                    with open(self.token_path, 'wb') as token:
                        pickle.dump(credentials, token)
                        logger.info(f"✅ Saved OAuth2 token to {self.token_path}")

            self.youtube = build('youtube', 'v3', credentials=credentials)
            logger.info("✅ YouTube API client initialized successfully")

        except Exception as e:
            logger.error(f"❌ Authentication failed: {str(e)}")
            logger.debug("Stack trace:", exc_info=True)
            self.youtube = None
            raise RuntimeError("YouTube authentication failed")

    def upload_video(self, video_path: str, thumbnail_path: str, title: str, description: str, tags: List[str]) -> Optional[str]:
        """Upload a video to YouTube and set its thumbnail"""
        if not self.youtube:
            logger.error("❌ YouTube client not initialized")
            return None

        try:
            # Prepare video upload request
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': os.getenv('VIDEO_CATEGORY_ID', '28')
                },
                'status': {
                    'privacyStatus': os.getenv('VIDEO_PRIVACY', 'public')
                }
            }

            # Upload video
            logger.info(f"📤 Uploading video: {video_path}")
            media = MediaFileUpload(video_path)
            request = self.youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            response = request.execute()

            video_id = response['id']
            logger.info(f"✅ Video uploaded with ID: {video_id}")

            # Upload thumbnail
            logger.info(f"🖼️ Uploading thumbnail: {thumbnail_path}")
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            logger.info(f"✅ Thumbnail set for video ID: {video_id}")

            return video_id

        except Exception as e:
            logger.error(f"❌ Failed to upload video: {str(e)}")
            logger.debug("Stack trace:", exc_info=True)
            return None

def generate_video_metadata(topic: str, category: str, script: str) -> Tuple[str, str, List[str]]:
    """
    Generate metadata for the YouTube video.
    
    Args:
        topic (str): The video topic
        category (str): The video category
        script (str): The generated script
    
    Returns:
        Tuple[str, str, List[str]]: Title, description, and tags
    """
    title = f"{topic} | YouTube Shorts #{category.lower()}"
    if len(title) > 100:
        title = title[:97] + "..."
    
    description = f"""
Discover {topic.lower()} in this engaging YouTube Short! 
Category: {category}
#Shorts #{category.lower()} #{topic.replace(' ', '').lower()}
Subscribe for more exciting content!
"""
    
    tags = [
        "YouTubeShorts",
        category.lower(),
        topic.replace(' ', '').lower(),
        "shortvideo",
        "learn",
        "facts",
        "education"
    ]
    
    return title, description, tags