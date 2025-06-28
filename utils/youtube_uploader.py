#!/usr/bin/env python3
"""
YouTube Uploader - Handles uploading videos to YouTube using the YouTube Data API
"""

import os
import json
import random
import time
from datetime import datetime
import pickle
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

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
        
        # Initialize YouTube API client
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with YouTube API"""
        
        creds = None
        
        # Check if we have saved credentials
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(f"⚠️ Error loading saved credentials: {e}")
                # Delete corrupted token file
                try:
                    os.remove(self.token_file)
                except:
                    pass
        
        # If there are no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("🔄 Refreshing expired credentials...")
                    creds.refresh(Request())
                except Exception as e:
                    print(f"⚠️ Error refreshing credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    print(f"❌ Credentials file not found: {self.credentials_file}")
                    print("💡 Please download credentials.json from Google Cloud Console")
                    print("💡 Go to: https://console.cloud.google.com/apis/credentials")
                    return
                
                try:
                    print("🔐 Starting OAuth flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0)
                    print("✅ Authentication successful!")
                except Exception as e:
                    print(f"❌ Authentication failed: {e}")
                    return
            
            # Save credentials for next time
            try:
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
                print(f"💾 Credentials saved to: {self.token_file}")
            except Exception as e:
                print(f"⚠️ Could not save credentials: {e}")
        
        # Build YouTube API client
        try:
            self.youtube = build('youtube', 'v3', credentials=creds)
            print("✅ YouTube API client initialized")
        except Exception as e:
            print(f"❌ Failed to initialize YouTube API client: {e}")
            self.youtube = None
    
    def upload_video(self, video_path, thumbnail_path=None, title=None, description=None, 
                    tags=None, category_id='22', privacy_status='public'):
        """
        Upload video to YouTube
        
        Args:
            video_path (str): Path to video file
            thumbnail_path (str): Path to thumbnail image
            title (str): Video title
            description (str): Video description
            tags (list): List of tags
            category_id (str): YouTube category ID (22 = People & Blogs)
            privacy_status (str): 'public', 'private', 'unlisted'
            
        Returns:
            str: Video ID if successful, None if failed
        """
        
        if not self.youtube:
            print("❌ YouTube API not authenticated")
            return None
        
        if not os.path.exists(video_path):
            print(f"❌ Video file not found: {video_path}")
            return None
        
        # Default values
        if not title:
            title = f"Amazing Facts - {datetime.now().strftime('%Y-%m-%d')}"
        
        if not description:
            description = "Discover incredible facts that will blow your mind! 🤯"
        
        if not tags:
            tags = ['shorts', 'facts', 'amazing', 'viral', 'trending']
        
        # Prepare video metadata
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Prepare media upload
        media = MediaFileUpload(
            video_path,
            chunksize=-1,
            resumable=True,
            mimetype='video/mp4'
        )
        
        try:
            print(f"📤 Uploading video: {os.path.basename(video_path)}")
            print(f"📝 Title: {title}")
            print(f"📊 File size: {os.path.getsize(video_path) / (1024*1024):.1f} MB")
            
            # Insert video
            insert_request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            video_id = self._resumable_upload(insert_request)
            
            if video_id:
                print(f"✅ Video uploaded successfully! ID: {video_id}")
                
                # Upload thumbnail if provided
                if thumbnail_path and os.path.exists(thumbnail_path):
                    self._upload_thumbnail(video_id, thumbnail_path)
                
                return video_id
            else:
                print("❌ Video upload failed")
                return None
                
        except HttpError as e:
            print(f"❌ HTTP Error during upload: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error during upload: {e}")
            return None
    
    def _resumable_upload(self, insert_request):
        """Handle resumable upload with progress tracking"""
        
        response = None
        error = None
        retry = 0
        
        while response is None:
            try:
                print("📤 Uploading...")
                status, response = insert_request.next_chunk()
                
                if status:
                    progress = int(status.progress() * 100)
                    print(f"📊 Upload progress: {progress}%")
                    
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    # Recoverable errors
                    error = f"HTTP {e.resp.status}: {e.content}"
                    print(f"⚠️ Recoverable error: {error}")
                else:
                    # Non-recoverable error
                    print(f"❌ Non-recoverable HTTP error: {e}")
                    raise
                    
            except Exception as e:
                error = f"Unexpected error: {e}"
                print(f"⚠️ {error}")
            
            if error is not None:
                retry += 1
                if retry > 3:
                    print("❌ Maximum retries exceeded")
                    return None
                
                max_delay = 2 ** retry
                delay = random.random() * max_delay
                print(f"⏳ Retrying in {delay:.1f} seconds... (attempt {retry}/3)")
                time.sleep(delay)
                error = None
        
        if 'id' in response:
            return response['id']
        else:
            print(f"❌ Upload failed: {response}")
            return None
    
    def _upload_thumbnail(self, video_id, thumbnail_path):
        """Upload custom thumbnail for video"""
        
        try:
            print(f"🖼️ Uploading thumbnail: {os.path.basename(thumbnail_path)}")
            
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            
            print("✅ Thumbnail uploaded successfully")
            
        except HttpError as e:
            print(f"⚠️ Thumbnail upload failed: {e}")
            if e.resp.status == 400:
                print("💡 Make sure your YouTube channel is verified to upload custom thumbnails")
        except Exception as e:
            print(f"⚠️ Thumbnail upload error: {e}")
    
    def get_channel_info(self):
        """Get information about the authenticated channel"""
        
        if not self.youtube:
            return None
        
        try:
            request = self.youtube.channels().list(
                part='snippet,statistics',
                mine=True
            )
            response = request.execute()
            
            if response['items']:
                channel = response['items'][0]
                return {
                    'title': channel['snippet']['title'],
                    'subscriber_count': channel['statistics'].get('subscriberCount', 'Hidden'),
                    'video_count': channel['statistics'].get('videoCount', '0'),
                    'view_count': channel['statistics'].get('viewCount', '0')
                }
        except Exception as e:
            print(f"⚠️ Error getting channel info: {e}")
        
        return None

def generate_video_metadata(topic, category, script=None):
    """
    Generate optimized metadata for YouTube video
    
    Args:
        topic (str): Video topic
        category (str): Video category
        script (str): Video script (optional)
        
    Returns:
        tuple: (title, description, tags)
    """
    
    # Generate engaging title
    title_templates = [
        f"{topic} #shorts",
        f"🤯 {topic}",
        f"This Will Blow Your Mind: {topic}",
        f"You Won't Believe: {topic}",
        f"SHOCKING: {topic}",
        f"Mind-Blowing: {topic}"
    ]
    
    # Choose title based on category
    if category.lower() == 'mystery':
        title = f"🔍 MYSTERY: {topic}"
    elif category.lower() == 'science':
        title = f"🔬 SCIENCE: {topic}"
    elif category.lower() == 'history':
        title = f"📜 HISTORY: {topic}"
    elif category.lower() == 'technology':
        title = f"💻 TECH: {topic}"
    else:
        title = random.choice(title_templates)
    
    # Ensure title is not too long (YouTube limit is 100 characters)
    if len(title) > 95:
        title = title[:92] + "..."
    
    # Generate description
    description = f"""
{topic}

🤯 Prepare to have your mind blown by this incredible fact!

{script[:200] + '...' if script and len(script) > 200 else script or 'Amazing content that will change how you see the world!'}

🔔 Subscribe for more mind-blowing facts!
👍 Like if this amazed you!
💬 Comment your thoughts below!

#shorts #facts #amazing #viral #trending #{category.lower()}

---
Daily dose of incredible facts that will leave you speechless! 
Subscribe to never miss out on fascinating discoveries and mind-bending truths.

© All content is original and created for educational purposes.
""".strip()
    
    # Generate tags
    base_tags = [
        'shorts',
        'facts',
        'amazing',
        'viral',
        'trending',
        'mindblowing',
        'incredible',
        'educational',
        'fascinating',
        'shocking'
    ]
    
    category_tags = {
        'history': ['history', 'historical', 'past', 'ancient', 'timeline'],
        'science': ['science', 'scientific', 'research', 'discovery', 'experiment'],
        'technology': ['technology', 'tech', 'innovation', 'future', 'digital'],
        'mystery': ['mystery', 'unexplained', 'strange', 'weird', 'paranormal'],
        'nature': ['nature', 'animals', 'wildlife', 'environment', 'planet'],
        'space': ['space', 'universe', 'astronomy', 'cosmos', 'galaxy'],
        'health': ['health', 'medical', 'body', 'wellness', 'healthcare'],
        'psychology': ['psychology', 'mind', 'brain', 'mental', 'behavior'],
        'entertainment': ['entertainment', 'movies', 'celebrity', 'music', 'culture'],
        'food': ['food', 'cooking', 'recipe', 'cuisine', 'nutrition']
    }
    
    # Combine base tags with category-specific tags
    tags = base_tags + category_tags.get(category.lower(), [])
    
    # Add topic-specific tags (extract keywords from topic)
    topic_words = topic.lower().split()
    for word in topic_words:
        if len(word) > 3 and word not in tags:
            tags.append(word)
    
    # Limit to 500 characters total (YouTube limit)
    tags_string = ','.join(tags)
    if len(tags_string) > 500:
        # Remove tags until under limit
        while len(','.join(tags)) > 500 and len(tags) > 10:
            tags.pop()
    
    return title, description, tags

def test_upload():
    """Test the upload functionality with a dummy video"""
    
    print("🧪 Testing YouTube upload functionality...")
    
    # Create a test video (1 second black screen)
    try:
        import moviepy.editor as mp
        
        # Create a simple test video
        test_video = mp.ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=1)
        test_video_path = "test_video.mp4"
        test_video.write_videofile(test_video_path, fps=30, verbose=False, logger=None)
        test_video.close()
        
        # Test upload
        uploader = YouTubeUploader()
        
        if uploader.youtube:
            print("✅ YouTube API authenticated successfully")
            
            # Get channel info
            channel_info = uploader.get_channel_info()
            if channel_info:
                print(f"📺 Channel: {channel_info['title']}")
                print(f"👥 Subscribers: {channel_info['subscriber_count']}")
            
            # Test metadata generation
            title, description, tags = generate_video_metadata(
                "Test Video Upload", 
                "Technology", 
                "This is a test video to verify upload functionality."
            )
            
            print(f"📝 Test title: {title}")
            print(f"🏷️ Test tags: {tags[:5]}...")
            
            # Note: Uncomment the line below to actually upload the test video
            # video_id = uploader.upload_video(test_video_path, title=title, description=description, tags=tags)
            
            print("✅ Upload test completed (actual upload skipped)")
        else:
            print("❌ YouTube API authentication failed")
        
        # Clean up test file
        if os.path.exists(test_video_path):
            os.remove(test_video_path)
            
    except ImportError:
        print("⚠️ moviepy not installed - cannot create test video")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_upload()