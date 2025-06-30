import os
import json
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload
from typing import List, Optional, Tuple

class YouTubeUploader:
    def __init__(self):
        self.youtube = None
        self.SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
        self._authenticate()

    def _authenticate(self):
        """Authenticate with YouTube API"""
        credentials = None
        
        # Try to load existing token
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                credentials = pickle.load(token)

        # Refresh or create new credentials
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                # Load credentials from file
                if not os.path.exists('credentials.json'):
                    raise FileNotFoundError("credentials.json not found")
                
                with open('credentials.json', 'r') as f:
                    creds_data = json.load(f)
                
                if creds_data.get('type') == 'service_account':
                    # Service account flow
                    credentials = service_account.Credentials.from_service_account_info(
                        creds_data, scopes=self.SCOPES
                    )
                else:
                    # OAuth2 flow
                    if os.getenv('CI'):
                        raise RuntimeError("Interactive OAuth not supported in CI/CD")
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', self.SCOPES
                    )
                    credentials = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(credentials, token)

        self.youtube = build('youtube', 'v3', credentials=credentials)

    def upload_video(self, video_path: str, thumbnail_path: str, title: str, 
                    description: str, tags: List[str]) -> Optional[str]:
        """Upload video to YouTube with thumbnail"""
        if not self.youtube:
            return None

        try:
            # Upload video
            body = {
                'snippet': {
                    'title': title[:100],  # YouTube title limit
                    'description': description,
                    'tags': tags[:10],  # YouTube tag limit
                    'categoryId': os.getenv('VIDEO_CATEGORY_ID', '28')
                },
                'status': {
                    'privacyStatus': os.getenv('VIDEO_PRIVACY', 'public')
                }
            }

            media = MediaFileUpload(video_path, resumable=True)
            request = self.youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            response = request.execute()
            video_id = response['id']
            
            # Set thumbnail
            if os.path.exists(thumbnail_path):
                self.youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path)
                ).execute()
            
            return video_id
            
        except Exception as e:
            print(f"Upload failed: {e}")
            return None

def generate_video_metadata(topic: str, category: str) -> Tuple[str, str, List[str]]:
    """Generate video metadata"""
    title = f"{topic} | YouTube Shorts #{category.lower()}"
    if len(title) > 100:
        title = title[:97] + "..."
    
    description = f"""Discover {topic.lower()} in this engaging YouTube Short!

#Shorts #{category.lower().replace(' ', '')} #{topic.replace(' ', '').lower()}

Subscribe for more content!"""
    
    tags = [
        "YouTubeShorts",
        category.lower().replace(' ', ''),
        topic.replace(' ', '').lower(),
        "shorts",
        "viral",
        "trending"
    ]
    
    return title, description, tags