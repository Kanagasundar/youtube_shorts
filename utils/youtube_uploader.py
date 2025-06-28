import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

class YouTubeUploader:
    def __init__(self):
        self.youtube = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate with YouTube API using service account credentials"""
        try:
            creds = Credentials.from_service_account_file(
                os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '/tmp/credentials.json'),
                scopes=SCOPES
            )
            self.youtube = build('youtube', 'v3', credentials=creds)
            print("✅ YouTube API authentication successful")
        except Exception as e:
            print(f"❌ YouTube API authentication failed: {e}")
            self.youtube = None
    
    def upload_video(self, video_path, thumbnail_path, title, description, tags=None, category_id="22"):
        """Upload video to YouTube"""
        if not self.youtube:
            print("❌ YouTube authentication failed - skipping upload")
            return None
        
        try:
            # Prepare video metadata
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags or [],
                    'categoryId': category_id  # "22" is People & Blogs
                },
                'status': {
                    'privacyStatus': 'public',  # or 'private', 'unlisted'
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Upload video
            print(f"📤 Uploading video: {title}")
            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            
            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = self.execute_upload(request)
            
            if response and 'id' in response:
                video_id = response['id']
                print(f"✅ Video uploaded successfully! Video ID: {video_id}")
                print(f"🔗 Video URL: https://www.youtube.com/watch?v={video_id}")
                
                # Upload thumbnail
                if thumbnail_path and os.path.exists(thumbnail_path):
                    self.upload_thumbnail(video_id, thumbnail_path)
                
                return video_id
            else:
                print("❌ Video upload failed - no video ID returned")
                return None
                
        except HttpError as e:
            print(f"❌ YouTube API error: {e}")
            return None
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return None
    
    def upload_thumbnail(self, video_id, thumbnail_path):
        """Upload custom thumbnail for the video"""
        try:
            print(f"📷 Uploading thumbnail...")
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            print("✅ Thumbnail uploaded successfully!")
        except Exception as e:
            print(f"❌ Thumbnail upload failed: {e}")
    
    def execute_upload(self, request):
        """Execute the upload request with progress tracking"""
        response = None
        error = None
        retry = 0
        
        while response is None:
            try:
                print(f"Uploading file... (attempt {retry + 1})")
                status, response = request.next_chunk()
                if status:
                    print(f"Upload progress: {int(status.progress() * 100)}%")
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    # Recoverable errors
                    error = f"Recoverable error: {e}"
                    retry += 1
                    if retry > 3:
                        print(f"❌ Upload failed after 3 retries: {error}")
                        break
                else:
                    # Non-recoverable error
                    print(f"❌ Non-recoverable error: {e}")
                    break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                break
        
        return response

def generate_video_metadata(topic, category):
    """Generate title, description, and tags for the video"""
    # Create an engaging title
    title = f"🤯 {topic} - You Won't Believe This! #Shorts"
    
    # Create description
    description = f"""🔥 {topic}
    
Did you know about this incredible piece of history? 

{category} content that will blow your mind! 

Like and follow for more amazing historical facts and rare discoveries!

#Shorts #History #Facts #Viral #Amazing #Incredible #{category.replace(' ', '')}
#HistoricalFacts #RarePhotos #Vintage #TikTok #YouTube #Discover
    """.strip()
    
    # Generate tags
    tags = [
        "shorts",
        "history",
        "facts",
        "viral",
        "amazing",
        category.lower().replace(' ', ''),
        "historical facts",
        "rare photos",
        "vintage",
        "incredible",
        "documentary"
    ]
    
    return title, description, tags