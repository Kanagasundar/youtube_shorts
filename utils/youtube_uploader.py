#!/usr/bin/env python3
"""
YouTube Uploader - Handles uploading videos to YouTube using the YouTube Data API
Supports both service account and OAuth2 authentication methods
"""

import os
import json
import random
import time
from datetime import datetime
import pickle
import logging
import re
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

logger = logging.getLogger(__name__)

class YouTubeUploader:
    def __init__(self, credentials_file='credentials.json', token_file='token.pickle'):
        """
        Initialize YouTube uploader
        
        Args:
            credentials_file (str): Path to Google API credentials JSON file
            token_file (str): Path to store authentication token
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.youtube = None
        self.auth_method = None
        
        # Initialize YouTube API client
        self._authenticate()
    
    def _detect_credential_type(self):
        """Detect the type of credentials (service account vs OAuth2)"""
        
        if not os.path.exists(self.credentials_file):
            logger.error(f"❌ Credentials file not found: {self.credentials_file}")
            return None
        
        try:
            with open(self.credentials_file, 'r', encoding='utf-8') as f:
                creds_data = json.load(f)
            
            if creds_data.get('type') == 'service_account':
                logger.info("📝 Detected service account credentials")
                return 'service_account'
            elif 'installed' in creds_data or creds_data.get('type') == 'installed':
                logger.info("📝 Detected OAuth2 installed application credentials")
                return 'oauth2'
            elif 'web' in creds_data:
                logger.info("📝 Detected OAuth2 web application credentials")
                return 'oauth2'
            else:
                logger.warning("⚠️ Unknown credential type, assuming OAuth2")
                return 'oauth2'
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in credentials file: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error reading credentials file: {e}")
            return None
    
    def _authenticate_service_account(self):
        """Authenticate using service account credentials"""
        
        try:
            logger.info("🔐 Authenticating with service account...")
            
            credentials = ServiceAccountCredentials.from_service_account_file(
                self.credentials_file, scopes=SCOPES
            )
            
            self.youtube = build('youtube', 'v3', credentials=credentials)
            self.auth_method = 'service_account'
            logger.info("✅ Service account authentication successful!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Service account authentication failed: {e}")
            return False
    
    def _authenticate_oauth2(self):
        """Authenticate using OAuth2 flow"""
        
        creds = None
        
        # Check if we have saved credentials
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
                logger.info("📂 Loaded existing OAuth2 token")
            except Exception as e:
                logger.warning(f"⚠️ Error loading saved credentials: {e}")
                # Delete corrupted token file
                try:
                    os.remove(self.token_file)
                    logger.info("🗑️ Removed corrupted token file")
                except:
                    pass
        
        # If there are no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("🔄 Refreshing expired OAuth2 credentials...")
                    creds.refresh(Request())
                    logger.info("✅ OAuth2 token refreshed successfully")
                except Exception as e:
                    logger.warning(f"⚠️ Error refreshing credentials: {e}")
                    creds = None
            
            if not creds:
                try:
                    logger.info("🔐 Starting OAuth2 flow...")
                    
                    # Check if running in CI/CD environment
                    if os.getenv('CI') or os.getenv('GITHUB_ACTIONS'):
                        logger.error("❌ Cannot perform interactive OAuth2 flow in CI/CD environment")
                        logger.info("💡 For automated environments, consider using:")
                        logger.info("   1. Service account credentials")
                        logger.info("   2. Pre-generated OAuth2 token (token.pickle)")
                        logger.info("   3. Environment-based token injection")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES)
                    
                    # Try local server first, fallback to console if needed
                    try:
                        creds = flow.run_local_server(port=0, open_browser=False)
                    except Exception:
                        logger.info("🖥️ Local server failed, using console flow...")
                        creds = flow.run_console()
                    
                    logger.info("✅ OAuth2 authentication successful!")
                    
                except Exception as e:
                    logger.error(f"❌ OAuth2 authentication failed: {e}")
                    return False
            
            # Save credentials for next time
            try:
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info(f"💾 OAuth2 credentials saved to: {self.token_file}")
            except Exception as e:
                logger.warning(f"⚠️ Could not save credentials: {e}")
        
        # Build YouTube API client
        try:
            self.youtube = build('youtube', 'v3', credentials=creds)
            self.auth_method = 'oauth2'
            logger.info("✅ YouTube API client initialized with OAuth2")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize YouTube API client: {e}")
            return False
    
    def _authenticate_from_env_token(self):
        """Try to authenticate using token from environment variable"""
        
        env_token = os.getenv('YOUTUBE_TOKEN_BASE64')
        if not env_token:
            return False
        
        try:
            import base64
            
            logger.info("🔐 Attempting authentication from environment token...")
            
            # Decode base64 token
            token_data = base64.b64decode(env_token)
            
            # Save to temporary file and load
            with open(self.token_file, 'wb') as f:
                f.write(token_data)
            
            return self._authenticate_oauth2()
            
        except Exception as e:
            logger.error(f"❌ Environment token authentication failed: {e}")
            return False
    
    def _authenticate(self):
        """Main authentication method - tries multiple approaches"""
        
        # Method 1: Try environment token first (for CI/CD)
        if self._authenticate_from_env_token():
            return
        
        # Method 2: Detect credential type and authenticate accordingly
        cred_type = self._detect_credential_type()
        
        if cred_type == 'service_account':
            if self._authenticate_service_account():
                return
        elif cred_type == 'oauth2':
            if self._authenticate_oauth2():
                return
        
        # Method 3: Fallback - try OAuth2 if service account failed
        if cred_type == 'service_account':
            logger.info("🔄 Service account failed, trying OAuth2 fallback...")
            if self._authenticate_oauth2():
                return
        
        logger.error("❌ All authentication methods failed")
        self.youtube = None
    
    def _clean_title(self, title):
        """Clean and validate video title"""
        if not title:
            return f"Amazing Facts - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Remove invalid characters and limit length
        title = re.sub(r'[<>:"/\\|?*]', '', title)
        title = title.strip()
        
        # YouTube title limit is 100 characters
        if len(title) > 100:
            title = title[:97] + "..."
        
        return title or f"Video - {datetime.now().strftime('%Y-%m-%d')}"
    
    def _clean_description(self, description):
        """Clean and validate video description"""
        if not description:
            return "Discover incredible facts that will blow your mind! 🤯"
        
        # YouTube description limit is 5000 characters
        if len(description) > 5000:
            description = description[:4997] + "..."
        
        return description
    
    def _clean_tags(self, tags):
        """Clean and validate video tags"""
        if not tags:
            return ['shorts', 'facts', 'amazing', 'viral', 'trending']
        
        cleaned_tags = []
        for tag in tags:
            if isinstance(tag, str):
                # Remove invalid characters and limit length
                tag = re.sub(r'[<>"]', '', tag.strip())
                if tag and len(tag) <= 30:  # YouTube tag limit
                    cleaned_tags.append(tag)
        
        # Limit to 500 characters total for all tags
        total_length = sum(len(tag) for tag in cleaned_tags)
        while total_length > 500 and cleaned_tags:
            removed_tag = cleaned_tags.pop()
            total_length -= len(removed_tag)
        
        return cleaned_tags[:50]  # YouTube allows max 50 tags
    
    def _is_shorts_video(self, video_path):
        """Check if video is in YouTube Shorts format (vertical, <= 60 seconds)"""
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return False
            
            # Get video properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            cap.release()
            
            # Calculate duration
            duration = frame_count / fps if fps > 0 else 0
            
            # Check if it's vertical and under 60 seconds
            is_vertical = height > width
            is_short_duration = duration <= 60
            
            logger.info(f"📊 Video properties: {width}x{height}, {duration:.1f}s, vertical: {is_vertical}")
            
            return is_vertical and is_short_duration
            
        except ImportError:
            logger.warning("⚠️ OpenCV not available, cannot detect Shorts format")
            return False
        except Exception as e:
            logger.warning(f"⚠️ Error detecting video format: {e}")
            return False
    
    def _resumable_upload(self, insert_request):
        """Execute resumable upload with retry logic"""
        
        response = None
        error = None
        retry = 0
        max_retries = 3
        
        while response is None:
            try:
                logger.info(f"📤 Upload attempt {retry + 1}/{max_retries + 1}")
                status, response = insert_request.next_chunk()
                
                if response is not None:
                    if 'id' in response:
                        logger.info(f"✅ Upload completed successfully")
                        return response['id']
                    else:
                        logger.error(f"❌ Upload failed: {response}")
                        return None
                        
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    logger.warning(f"⚠️ Recoverable HTTP error {e.resp.status}: {e}")
                    error = f"HTTP {e.resp.status}: {e}"
                else:
                    logger.error(f"❌ Non-recoverable HTTP error {e.resp.status}: {e}")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Unexpected error during upload: {e}")
                error = str(e)
                
            retry += 1
            if retry > max_retries:
                logger.error(f"❌ Upload failed after {max_retries + 1} attempts. Last error: {error}")
                return None
                
            # Exponential backoff
            sleep_time = (2 ** retry) + random.random()
            logger.info(f"⏳ Retrying in {sleep_time:.1f} seconds...")
            time.sleep(sleep_time)
        
        return None
    
    def _upload_thumbnail(self, video_id, thumbnail_path):
        """Upload custom thumbnail for the video"""
        
        try:
            logger.info(f"🖼️ Uploading thumbnail: {os.path.basename(thumbnail_path)}")
            
            # Validate thumbnail file
            if not os.path.exists(thumbnail_path):
                logger.error(f"❌ Thumbnail file not found: {thumbnail_path}")
                return False
            
            # Check file size (YouTube limit: 2MB)
            file_size = os.path.getsize(thumbnail_path)
            if file_size > 2 * 1024 * 1024:
                logger.error(f"❌ Thumbnail too large: {file_size / (1024*1024):.1f}MB (max 2MB)")
                return False
            
            # Upload thumbnail
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype='image/jpeg')
            ).execute()
            
            logger.info("✅ Thumbnail uploaded successfully")
            return True
            
        except HttpError as e:
            if e.resp.status == 400:
                logger.warning(f"⚠️ Thumbnail upload failed (channel may not be verified): {e}")
            else:
                logger.error(f"❌ Thumbnail upload failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Thumbnail upload error: {e}")
            return False
    
    def _verify_upload(self, video_id):
        """Verify that the video was uploaded successfully"""
        
        try:
            logger.info(f"🔍 Verifying upload for video ID: {video_id}")
            
            response = self.youtube.videos().list(
                part='status,snippet',
                id=video_id
            ).execute()
            
            if not response.get('items'):
                logger.error("❌ Video not found after upload")
                return False
            
            video = response['items'][0]
            upload_status = video['status']['uploadStatus']
            
            logger.info(f"📊 Upload status: {upload_status}")
            
            if upload_status in ['uploaded', 'processed']:
                logger.info("✅ Video upload verified successfully")
                return True
            elif upload_status == 'processing':
                logger.info("⏳ Video is still processing...")
                return True
            else:
                logger.warning(f"⚠️ Unexpected upload status: {upload_status}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Upload verification failed: {e}")
            return False
    
    def upload_video(self, video_path, thumbnail_path=None, title=None, description=None, 
                    tags=None, category_id=None, privacy_status=None):
        """
        Upload video to YouTube with enhanced error handling
        
        Args:
            video_path (str): Path to video file
            thumbnail_path (str): Path to thumbnail image
            title (str): Video title
            description (str): Video description
            tags (list): List of tags
            category_id (str): YouTube category ID
            privacy_status (str): 'public', 'private', 'unlisted'
            
        Returns:
            str: Video ID if successful, None if failed
        """
        
        if not self.youtube:
            logger.error("❌ YouTube API not authenticated")
            return None
        
        if not os.path.exists(video_path):
            logger.error(f"❌ Video file not found: {video_path}")
            return None
        
        # Get configuration from environment or use defaults
        category_id = category_id or os.getenv('VIDEO_CATEGORY_ID', '28')  # Education
        privacy_status = privacy_status or os.getenv('VIDEO_PRIVACY', 'public')
        
        # Default values
        if not title:
            title = f"Amazing Facts - {datetime.now().strftime('%Y-%m-%d')}"
        
        if not description:
            description = "Discover incredible facts that will blow your mind! 🤯"
        
        if not tags:
            tags = ['shorts', 'facts', 'amazing', 'viral', 'trending']
        
        # Validate and clean inputs
        title = self._clean_title(title)
        description = self._clean_description(description)
        tags = self._clean_tags(tags)
        
        # Prepare video metadata
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': str(category_id)
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Add shorts-specific metadata
        if self._is_shorts_video(video_path):
            logger.info("📱 Detected Shorts format video")
            # YouTube Shorts specific optimizations can be added here
        
        # Prepare media upload
        media = MediaFileUpload(
            video_path,
            chunksize=-1,
            resumable=True,
            mimetype='video/mp4'
        )
        
        try:
            logger.info(f"📤 Uploading video: {os.path.basename(video_path)}")
            logger.info(f"📝 Title: {title}")
            logger.info(f"📊 File size: {os.path.getsize(video_path) / (1024*1024):.1f} MB")
            logger.info(f"🔒 Privacy: {privacy_status}")
            logger.info(f"📂 Category: {category_id}")
            
            # Insert video
            insert_request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            video_id = self._resumable_upload(insert_request)
            
            if video_id:
                logger.info(f"✅ Video uploaded successfully! ID: {video_id}")
                
                # Upload thumbnail if provided
                if thumbnail_path and os.path.exists(thumbnail_path):
                    self._upload_thumbnail(video_id, thumbnail_path)
                
                # Verify upload
                if self._verify_upload(video_id):
                    logger.info("✅ Upload verification passed")
                else:
                    logger.warning("⚠️ Upload verification failed, but video may still be processing")
                
                return video_id
            else:
                logger.error("❌ Video upload failed")
                return None
                
        except HttpError as e:
            logger.error(f"❌ YouTube API error during upload: {e}")
            
            # Handle specific HTTP errors
            if e.resp.status == 400:
                logger.error("💡 Check your video file format and metadata")
            elif e.resp.status == 401:
                logger.error("💡 Authentication failed - check your credentials")
            elif e.resp.status == 403:
                logger.error("💡 Access forbidden - check API quotas and permissions")
            elif e.resp.status == 404:
                logger.error("💡 Resource not found - check your API configuration")
            elif e.resp.status >= 500:
                logger.error("💡 YouTube server error - try again later")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Unexpected error during upload: {e}")
            return None
    
    def get_channel_info(self):
        """Get information about the authenticated channel"""
        
        if not self.youtube:
            logger.error("❌ YouTube API not authenticated")
            return None
        
        try:
            response = self.youtube.channels().list(
                part='snippet,statistics',
                mine=True
            ).execute()
            
            if response.get('items'):
                channel = response['items'][0]
                info = {
                    'id': channel['id'],
                    'title': channel['snippet']['title'],
                    'description': channel['snippet'].get('description', ''),
                    'subscriber_count': channel['statistics'].get('subscriberCount', '0'),
                    'video_count': channel['statistics'].get('videoCount', '0'),
                    'view_count': channel['statistics'].get('viewCount', '0')
                }
                
                logger.info(f"📺 Channel: {info['title']}")
                logger.info(f"👥 Subscribers: {info['subscriber_count']}")
                logger.info(f"🎬 Videos: {info['video_count']}")
                
                return info
            else:
                logger.error("❌ No channel found for authenticated user")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting channel info: {e}")
            return None


def generate_video_metadata(topic, category, script):
    """
    Generate optimized title, description, and tags for YouTube video
    
    Args:
        topic (str): Main topic of the video
        category (str): Category of the content
        script (str): Video script content
        
    Returns:
        tuple: (title, description, tags)
    """
    
    # Generate engaging title
    title_templates = [
        f"🤯 {topic} - Mind-Blowing Facts!",
        f"Did You Know? {topic} Facts That Will Shock You!",
        f"Amazing {topic} Facts You Never Knew! #Shorts",
        f"🔥 {topic} - Incredible Facts Revealed!",
        f"Mind-Blowing {topic} Facts! #Shorts",
        f"You Won't Believe These {topic} Facts!",
    ]
    
    title = random.choice(title_templates)
    
    # Ensure title is not too long
    if len(title) > 100:
        title = f"🤯 {topic} Facts! #Shorts"
    
    # Generate comprehensive description
    description = f"""🤯 Discover amazing facts about {topic}!
    
{script[:200]}...

🔔 Subscribe for more incredible facts!
🏷️ #{category.replace(' ', '')} #Facts #Shorts #Amazing #Viral #Trending

📱 Follow us for daily mind-blowing content!

#YouTubeShorts #DidYouKnow #FactsDaily #MindBlown #Educational #Learning #Knowledge #Interesting #Surprising #Incredible
    """
    
    # Generate relevant tags
    base_tags = [
        'shorts',
        'facts',
        'amazing',
        'viral',
        'trending',
        'mindblowing',
        'didyouknow',
        'educational',
        'learning',
        'knowledge',
        'interesting',
        'surprising',
        'incredible'
    ]
    
    # Add topic-specific tags
    topic_words = topic.lower().replace('-', ' ').split()
    topic_tags = [word for word in topic_words if len(word) > 2]
    
    # Add category-specific tags
    category_words = category.lower().replace('-', ' ').split()
    category_tags = [word for word in category_words if len(word) > 2]
    
    # Combine all tags
    all_tags = base_tags + topic_tags + category_tags
    
    # Remove duplicates and limit
    tags = list(dict.fromkeys(all_tags))[:50]
    
    return title, description, tags


def main():
    """Test the YouTube uploader"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🧪 Testing YouTube Uploader...")
    
    uploader = YouTubeUploader()
    
    if uploader.youtube:
        logger.info("✅ YouTube API authenticated successfully")
        
        # Get channel info
        channel_info = uploader.get_channel_info()
        if channel_info:
            logger.info(f"📺 Connected to channel: {channel_info['title']}")
        
    else:
        logger.error("❌ YouTube API authentication failed")


if __name__ == "__main__":
    main()