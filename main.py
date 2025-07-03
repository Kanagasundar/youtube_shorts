#!/usr/bin/env python3
"""
YouTube Automation Main Script - Enhanced Version
Generates and uploads daily YouTube Shorts content with improved error handling,
logging, configuration management, and cleanup features. Supports overlays, transitions,
captions, 9:16 cropping, OpenCV/Manim integration, and keyword-based Pexels queries.

Version: 1.2.2
Update Notes:
- Fixed typo in moviepy dependency check (VideoTipClip -> VideoFileClip).
- Retained robust OpenCV check with import cv2.
- Added detailed debugging for OpenCV import failures in check_dependencies.
- Enhanced logging for OpenCV, Manim, and NLTK to diagnose installation issues.
- Integrated enhanced video creation with overlays (text, stickers, logos), transitions (fade, zoom, slide),
  and animated captions using OpenCV and Manim.
- Updated to support 9:16 aspect ratio (1080x1920) for YouTube Shorts.
- Added keyword-based Pexels API queries using NLTK.
- Ensured video duration between 15-40 seconds with image durations of 0.5-6 seconds.

Dependencies:
- os, sys, traceback, shutil, signal, datetime, pathlib, logging, json, time, typing, importlib.util, dotenv
- Utils modules: topic_rotator, scripting, voice, video, thumbnail_generator, youtube_uploader
- Optional: psutil (for system health monitoring)
- moviepy, opencv-python, manim, nltk
"""

import os
import sys
import traceback
import shutil
import signal
from datetime import datetime, timedelta
from pathlib import Path
import logging
import json
import time
from typing import Optional, Tuple, Dict, Any
import importlib.util
from dotenv import load_dotenv
import subprocess

try:
    import psutil  # Optional for system health monitoring
except ImportError:
    psutil = None

# Load environment variables from .env file
load_dotenv()

# Configure logging with microsecond precision
def setup_logging():
    """Set up comprehensive logging configuration with microsecond precision."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    detailed_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = logging.FileHandler(
        log_dir / f"automation_{datetime.now().strftime('%Y%m%d')}.log",
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()

# Ensure the utils directory is in sys.path
SCRIPT_DIR = Path(__file__).parent.absolute()
UTILS_DIR = SCRIPT_DIR / 'utils'
OUTPUT_DIR = SCRIPT_DIR / 'output'
LOGS_DIR = SCRIPT_DIR / 'logs'

if str(UTILS_DIR) not in sys.path:
    sys.path.insert(0, str(UTILS_DIR))

# Global cleanup list for graceful shutdown
cleanup_files = []

def signal_handler(signum, frame):
    """Handle graceful shutdown on SIGINT/SIGTERM."""
    logger.warning(f"Received signal {signum}. Initiating graceful shutdown...")
    cleanup_temporary_files()
    sys.exit(1)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def cleanup_temporary_files():
    """Clean up temporary files created during execution."""
    global cleanup_files
    
    logger.info("🧹 Cleaning up temporary files...")
    cleaned_count = 0
    
    for file_path in cleanup_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Removed temporary file: {file_path}")
                cleaned_count += 1
        except Exception as e:
            logger.warning(f"Could not remove temporary file {file_path}: {e}")
    
    if cleaned_count > 0:
        logger.info(f"✅ Cleaned up {cleaned_count} temporary files")
    
    cleanup_files.clear()

def check_dependencies() -> bool:
    """Check if required dependencies are installed with robust detection."""
    logger.info("🔍 Checking dependencies...")
    
    required_packages = {
        'openai': ('import openai', 'openai'),
        'gtts': ('from gtts import gTTS', 'gTTS'),
        'pydub': ('from pydub import AudioSegment', 'AudioSegment'),
        'Pillow': ('from PIL import Image', 'Image'),
        'moviepy': ('from moviepy.editor import VideoFileClip', 'VideoFileClip'),
        'numpy': ('import numpy', 'numpy'),
        'google-auth': ('import google.auth', 'google.auth'),
        'google-auth-oauthlib': ('import google_auth_oauthlib', 'google_auth_oauthlib'),
        'google-api-python-client': ('from googleapiclient import discovery', 'discovery'),
        'requests': ('import requests', 'requests'),
        'opencv-python': ('import cv2', 'cv2'),
        'manim': ('from manim import Scene', 'Scene'),
        'nltk': ('import nltk', 'nltk'),
    }
    
    missing_packages = []
    
    for package_name, (import_statement, check_name) in required_packages.items():
        try:
            base_module = import_statement.split()[1].split('.')[0]
            for mod in list(sys.modules.keys()):
                if base_module in mod:
                    del sys.modules[mod]
            
            exec(import_statement)
            module = eval(check_name)
            version = getattr(module, '__version__', 
                           getattr(module, 'VERSION', 
                                  getattr(module, 'version', 'unknown')))
            spec = importlib.util.find_spec(base_module)
            logger.debug(f"✅ {package_name} ({check_name}) - v{version} from {spec.origin if spec else 'unknown'}")
            
            # Additional diagnostics for OpenCV
            if package_name == 'opencv-python':
                logger.debug(f"OpenCV details: sys.path={sys.path}")
                pip_list = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True)
                logger.debug(f"pip list output:\n{pip_list.stdout}")
            
        except (ImportError, AttributeError) as e:
            logger.error(f"❌ {package_name} ({check_name}) - Failed: {str(e)}")
            if package_name == 'opencv-python':
                logger.error("OpenCV diagnostic info:")
                logger.error(f"sys.path: {sys.path}")
                pip_list = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True)
                logger.error(f"pip list:\n{pip_list.stdout}")
                logger.error(f"Python executable: {sys.executable}")
                logger.error(f"Python version: {sys.version}")
            missing_packages.append(package_name)
    
    if missing_packages:
        logger.error(f"❌ Missing {len(missing_packages)} required packages:")
        for package in missing_packages:
            logger.error(f"   - {package}")
        print("\n💡 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        print("\n🔍 Python environment info:")
        print(f"   Python version: {sys.version}")
        print(f"   Python executable: {sys.executable}")
        site_packages = [p for p in sys.path if 'site-packages' in p]
        if site_packages:
            print(f"   Site packages: {site_packages[0]}")
        return False
    
    logger.info("✅ All required dependencies are available")
    return True

def validate_credentials_file() -> bool:
    """Validate the credentials.json file for OAuth 2.0."""
    credentials_path = SCRIPT_DIR / 'credentials.json'
    
    if not credentials_path.exists():
        logger.warning("⚠️ credentials.json not found in script directory")
        return False
    
    try:
        with open(credentials_path, 'r', encoding='utf-8') as f:
            creds_data = json.load(f)
        
        logger.debug(f"📝 Credentials file structure: {list(creds_data.keys())}")
        
        if 'installed' in creds_data:
            return _validate_oauth_credentials(creds_data['installed'], 'installed')
        elif 'web' in creds_data:
            return _validate_oauth_credentials(creds_data['web'], 'web')
        else:
            logger.error("❌ Unknown credentials format. Expected 'installed' or 'web' for OAuth 2.0")
            return False
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ credentials.json is not valid JSON: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error validating credentials.json: {e}")
        return False

def _validate_oauth_credentials(creds_data: dict, cred_type: str) -> bool:
    """Validate OAuth2 credentials."""
    required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
    logger.debug(f"📝 Detected {cred_type} application credentials (OAuth2)")
    missing_fields = [field for field in required_fields if field not in creds_data]
    
    if missing_fields:
        logger.error(f"❌ credentials.json missing required fields in '{cred_type}' section: {missing_fields}")
        return False
    
    for uri_field in ['auth_uri', 'token_uri']:
        uri = creds_data.get(uri_field, '')
        if not uri.startswith('https://'):
            logger.error(f"❌ Invalid {uri_field} in credentials: {uri}")
            return False
    
    logger.info(f"✅ OAuth2 {cred_type} application credentials validation passed")
    return True

def check_environment() -> bool:
    """Check if required environment variables are set."""
    logger.info("🔍 Checking environment variables...")
    
    required_vars = ['OPENAI_API_KEY', 'PEXELS_API_KEY']
    optional_vars = {
        'UPLOAD_TO_YOUTUBE': 'true',
        'VIDEO_PRIVACY': 'public',
        'VIDEO_CATEGORY_ID': '28',
        'DISCORD_WEBHOOK_URL': None,
        'TOPIC_OVERRIDE': None,
        'CATEGORY_OVERRIDE': None,
        'MAX_RETRIES': '5',
        'CLEANUP_OLD_FILES': 'true',
        'KEEP_FILES_DAYS': '7'
    }
    
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            logger.debug(f"✅ {var} is set (length: {len(value)})")
    
    for var, default in optional_vars.items():
        value = os.getenv(var)
        if value:
            logger.debug(f"✅ {var} = {value}")
        elif default:
            os.environ[var] = default
            logger.debug(f"ℹ️ {var} set to default: {default}")
        else:
            logger.debug(f"ℹ️ {var} not set (optional)")
    
    if missing_vars:
        logger.error(f"❌ Missing {len(missing_vars)} required environment variables:")
        for var in missing_vars:
            logger.error(f"   - {var}")
        print("\n💡 Set environment variables:")
        for var in missing_vars:
            print(f"   export {var}=your_value_here")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def setup_directories():
    """Create necessary directories."""
    directories = [OUTPUT_DIR, LOGS_DIR]
    
    for directory in directories:
        try:
            directory.mkdir(exist_ok=True)
            logger.debug(f"📁 Directory ready: {directory}")
        except Exception as e:
            logger.error(f"❌ Could not create directory {directory}: {e}")
            return False
    
    return True

def cleanup_old_files():
    """Clean up old output files based on KEEP_FILES_DAYS setting."""
    if os.getenv('CLEANUP_OLD_FILES', 'true').lower() != 'true':
        return
    
    try:
        keep_days = int(os.getenv('KEEP_FILES_DAYS', '7'))
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        cleaned_count = 0
        for directory in [OUTPUT_DIR, LOGS_DIR]:
            if directory.exists():
                for file_path in directory.iterdir():
                    if file_path.is_file():
                        file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_time < cutoff_date:
                            try:
                                file_path.unlink()
                                cleaned_count += 1
                                logger.debug(f"Removed old file: {file_path}")
                            except Exception as e:
                                logger.warning(f"Could not remove old file {file_path}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"🧹 Cleaned up {cleaned_count} old files (older than {keep_days} days)")
    
    except Exception as e:
        logger.warning(f"Error during old file cleanup: {e}")

def check_system_health() -> bool:
    """Perform a detailed health check of system resources."""
    logger.info("🏥 Checking system health...")
    
    try:
        stat = shutil.disk_usage(OUTPUT_DIR)
        available_gb = stat.free / (2**30)
        if available_gb < 1:
            logger.error(f"❌ Insufficient disk space: {available_gb:.1f} GB available")
            return False
        logger.debug(f"✅ Disk space available: {available_gb:.1f} GB")
        
        if psutil:
            memory = psutil.virtual_memory()
            available_mb = memory.available / (2**20)
            if available_mb < 512:
                logger.error(f"❌ Insufficient memory: {available_mb:.1f} MB available")
                return False
            logger.debug(f"✅ Memory available: {available_mb:.1f} MB")
            
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                logger.warning(f"⚠️ High CPU usage: {cpu_percent:.1f}%")
            logger.debug(f"✅ CPU usage: {cpu_percent:.1f}%")
        else:
            logger.warning("⚠️ psutil not available, skipping memory and CPU checks")
        
        logger.info("✅ System health check passed")
        return True
    except Exception as e:
        logger.error(f"❌ System health check failed: {e}")
        return False

def report_error(error: Exception):
    """Report errors with detailed information to logs and console."""
    logger.error(f"❌ Critical error occurred: {str(error)}")
    logger.debug("🔍 Full stack trace:", exc_info=True)
    print(f"\n❌ Critical Error: {str(error)}\nSee {LOGS_DIR}/automation_{datetime.now().strftime('%Y%m%d')}.log for details.")

def setup_check() -> bool:
    """Perform comprehensive setup checks before running automation."""
    logger.info("🔍 Performing setup checks...")
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Environment Variables", check_environment),
        ("Directories", setup_directories),
        ("System Health", check_system_health),
    ]
    
    for check_name, check_func in checks:
        logger.info(f"   Checking {check_name}...")
        if not check_func():
            logger.error(f"❌ {check_name} check failed")
            return False
    
    upload_enabled = os.getenv('UPLOAD_TO_YOUTUBE', 'true').lower() == 'true'
    
    if upload_enabled:
        logger.info("   Checking YouTube credentials...")
        if validate_credentials_file():
            logger.info("✅ credentials.json found and validated")
        else:
            logger.warning("⚠️ credentials.json validation failed")
            os.environ['UPLOAD_TO_YOUTUBE'] = 'false'
            upload_enabled = False
    
    if not upload_enabled:
        logger.info("ℹ️ YouTube upload disabled - videos will be saved locally only")
    
    cleanup_old_files()
    
    logger.info("✅ Setup checks completed successfully")
    return True

def import_modules() -> bool:
    """Import required modules with detailed error handling."""
    logger.info("📦 Importing utility modules...")
    
    modules_to_import = {
        'topic_rotator': ['get_today_topic'],
        'scripting': ['generate_script'],
        'voice': ['generate_voice'],
        'video': ['create_video'],
        'thumbnail_generator': ['generate_image_sequence'],
        'youtube_uploader': ['YouTubeUploader', 'generate_video_metadata']
    }
    
    imported_modules = {}
    
    for module_name in modules_to_import:
        for mod in list(sys.modules.keys()):
            if module_name in mod or 'openai' in mod.lower() or 'requests' in mod.lower():
                del sys.modules[mod]
    
    for module_name, functions in modules_to_import.items():
        module_path = UTILS_DIR / f"{module_name}.py"
        if not module_path.exists():
            logger.error(f"❌ Module file missing: {module_path}")
            _show_import_help(module_name)
            return False
        
        try:
            module = __import__(module_name)
            for func_name in functions:
                if not hasattr(module, func_name):
                    raise ImportError(f"Function '{func_name}' not found in module '{module_name}'")
                imported_modules[func_name] = getattr(module, func_name)
            logger.debug(f"✅ {module_name} imported successfully from {module_path}")
            
        except ImportError as e:
            logger.error(f"❌ Failed to import {module_name}: {e}")
            _show_import_help(module_name)
            return False
    
    globals().update(imported_modules)
    logger.info("✅ All utility modules imported successfully")
    return True

def _show_import_help(failed_module: str):
    """Show helpful information when module import fails."""
    print(f"\n💡 Module import failed for: {failed_module}")
    print("Make sure all required files are in the utils directory:")
    
    required_files = [
        'topic_rotator.py',
        'scripting.py',
        'voice.py',
        'video.py',
        'thumbnail_generator.py',
        'youtube_uploader.py'
    ]
    
    for file in required_files:
        file_path = UTILS_DIR / file
        status = "✅" if file_path.exists() else "❌"
        print(f"   {status} {file}")
    
    if not UTILS_DIR.exists():
        print(f"\n❌ Utils directory not found: {UTILS_DIR}")
        print("Please create the utils directory and add the required Python files.")

def retry_on_failure(func, max_retries: int = None, delay: float = 1.0):
    """Retry a function with exponential backoff."""
    if max_retries is None:
        max_retries = int(os.getenv('MAX_RETRIES', '5'))
    
    for attempt in range(max_retries + 1):
        try:
            result = func()
            if result is None:
                raise ValueError(f"Function {func.__name__} returned None")
            return result
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"❌ Failed after {max_retries} attempts: {str(e)}")
                raise
            wait_time = delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)

def generate_content_with_retry(topic: str, category: str) -> Tuple[str, str, list, str]:
    """Generate all content with retry logic."""
    
    def generate_script_step():
        logger.info("✍️ Generating script...")
        script = generate_script(topic, category)
        if not script or len(script.strip()) < 500:
            logger.error(f"❌ Generated script is too short ({len(script.strip()) if script else 0} characters)")
            script = f"""
Hook: Did you know about {topic.lower()}?
Body: This is a fascinating topic in the {category} category. Fact 1: It’s a key part of {category}. 
Fact 2: It has unique features that surprise everyone! Fact 3: Its impact is huge! 
Call to Action: Subscribe for more {category.lower()} facts!
"""
            logger.info(f"✅ Using fallback script ({len(script)} characters)")
        return script
    
    def generate_voice_step(script):
        logger.info("🎙️ Generating voice narration...")
        audio_path = generate_voice(script)
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not created: {audio_path}")
        cleanup_files.append(audio_path)
        return audio_path
    
    def generate_image_sequence_step(topic_param, script):
        logger.info("🖼️ Generating image sequence...")
        if not topic_param:
            logger.error("❌ Topic is empty, using default topic 'Nature Scene'")
            topic_param = "Nature Scene"
        return retry_on_failure(lambda: generate_image_sequence(topic_param, script, num_images=5), max_retries=1)
    
    def create_video_step(script, audio_path, image_paths):
        logger.info("🎬 Creating video...")
        output_dir = str(OUTPUT_DIR)
        video_path = create_video(audio_path, image_paths, output_dir, script)
        if not video_path or not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not created: {video_path}")
        logger.debug(f"Video file created at: {video_path}, size: {os.path.getsize(video_path) / (2**20):.1f} MB")
        cleanup_files.append(video_path)
        return video_path
    
    script = retry_on_failure(generate_script_step)
    logger.info(f"✅ Script generated ({len(script)} characters)")
    
    audio_path = retry_on_failure(lambda: generate_voice_step(script))
    logger.info(f"✅ Audio generated: {audio_path}")
    
    image_paths = retry_on_failure(lambda: generate_image_sequence_step(topic, script))
    logger.info(f"✅ Image sequence generated: {len(image_paths)} images")
    
    video_path = retry_on_failure(lambda: create_video_step(script, audio_path, image_paths))
    logger.info(f"✅ Video created: {video_path}")
    
    return script, audio_path, image_paths, video_path

def upload_to_youtube(video_path: str, thumbnail_path: str, script: str, topic: str, category: str) -> Optional[str]:
    """Upload video to YouTube with error handling."""
    
    upload_enabled = os.getenv('UPLOAD_TO_YOUTUBE', 'true').lower() == 'true'
    
    if not upload_enabled:
        logger.info("⚠️ Upload disabled (UPLOAD_TO_YOUTUBE=false)")
        logger.info(f"📁 Video saved locally: {video_path}")
        return None
    
    try:
        def upload_step():
            uploader = YouTubeUploader()
            if not uploader.youtube:
                raise RuntimeError("YouTube authentication failed")
            
            title, description, tags = generate_video_metadata(topic, category, script)
            
            logger.info(f"📝 Title: {title}")
            logger.info(f"🏷️ Tags: {', '.join(tags[:5])}...")
            
            video_id = uploader.upload_video(
                video_path=video_path,
                thumbnail_path=thumbnail_path,
                title=title,
                description=description,
                tags=tags
            )
            
            if not video_id:
                raise RuntimeError("Video upload returned no ID")
            
            return video_id, title
        
        video_id, title = retry_on_failure(upload_step)
        
        logger.info(f"🎉 SUCCESS! Video uploaded with ID: {video_id}")
        logger.info(f"🔗 Watch at: https://www.youtube.com/watch?v={video_id}")
        logger.info(f"🔗 YouTube Shorts: https://youtube.com/shorts/{video_id}")
        
        save_upload_info(video_id, title, topic, category, video_path, thumbnail_path)
        
        return video_id
        
    except Exception as upload_error:
        logger.error(f"❌ Upload process failed: {upload_error}")
        logger.info(f"📁 Video saved locally: {video_path}")
        raise upload_error

def save_upload_info(video_id: str, title: str, topic: str, category: str, video_path: str, thumbnail_path: str):
    """Save upload information to a structured log file."""
    
    log_file = LOGS_DIR / "upload_history.jsonl"
    
    timestamp = datetime.now().isoformat()
    
    log_entry = {
        "timestamp": timestamp,
        "video_id": video_id,
        "title": title,
        "topic": topic,
        "category": category,
        "video_path": video_path,
        "thumbnail_path": thumbnail_path,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "shorts_url": f"https://youtube.com/shorts/{video_id}",
        "privacy": os.getenv('VIDEO_PRIVACY', 'public'),
        "category_id": os.getenv('VIDEO_CATEGORY_ID', '28')
    }
    
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        readable_log = LOGS_DIR / "upload_history.txt"
        with open(readable_log, 'a', encoding='utf-8') as f:
            f.write(f"""
{timestamp}
Video ID: {video_id}
Title: {title}
Topic: {topic}
Category: {category}
Video Path: {video_path}
Thumbnail Path: {thumbnail_path}
YouTube URL: https://www.youtube.com/watch?v={video_id}
Shorts URL: https://youtube.com/shorts/{video_id}
{'='*80}
""")
        
        logger.info(f"📝 Upload info saved to: {log_file}")
        
    except Exception as e:
        logger.error(f"⚠️ Could not save upload info: {e}")

def main() -> int:
    """Main function to orchestrate the entire process."""
    start_time = time.time()
    logger.info("🚀 Starting YouTube Automation...")
    logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} (IST)")
    
    try:
        logger.info("📝 Step 1: Getting today's topic...")
        topic_override = os.getenv('TOPIC_OVERRIDE')
        category_override = os.getenv('CATEGORY_OVERRIDE')
        
        if topic_override:
            topic = topic_override
            category = category_override or 'General'
            logger.info(f"✅ Using override - Topic: {topic}, Category: {category}")
        else:
            try:
                topic, category = get_today_topic()
                if not topic or not category:
                    raise ValueError("Topic or category is empty from get_today_topic")
                logger.info(f"✅ Topic: {topic}")
                logger.info(f"✅ Category: {category}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get topic: {str(e)}. Using default topic.")
                topic, category = "Default Topic", "General"
        
        logger.info("🎨 Steps 2-5: Generating content...")
        script, audio_path, image_paths, video_path = generate_content_with_retry(topic, category)
        
        logger.info("📤 Step 6: Uploading to YouTube...")
        thumbnail_path = image_paths[-1] if image_paths else None
        try:
            video_id = upload_to_youtube(video_path, thumbnail_path, script, topic, category)
            
            if video_id:
                logger.info("✅ AUTOMATION COMPLETED SUCCESSFULLY WITH UPLOAD!")
                success_code = 0
            else:
                logger.info("✅ AUTOMATION COMPLETED SUCCESSFULLY (LOCAL SAVE ONLY)")
                success_code = 0
                
        except Exception as upload_error:
            logger.warning(f"Upload failed but content was generated: {upload_error}")
            logger.info("✅ AUTOMATION COMPLETED (UPLOAD FAILED)")
            success_code = 2
        
        cleanup_temporary_files()
        
        duration = time.time() - start_time
        logger.info(f"⏱️ Total execution time: {duration:.1f} seconds")
        
        return success_code
        
    except KeyboardInterrupt:
        logger.warning("⚠️ Process interrupted by user")
        cleanup_temporary_files()
        return 1
        
    except Exception as e:
        report_error(e)
        cleanup_temporary_files()
        return 1

if __name__ == "__main__":
    """Entry point for the script."""
    print("🤖 YouTube Automation Script - Enhanced Version")
    print("=" * 60)
    
    try:
        if not setup_check():
            print("\n❌ Setup checks failed. Please fix the issues above and try again.")
            sys.exit(1)
        
        if not import_modules():
            print("\n❌ Module import failed. Please check your utils directory.")
            sys.exit(1)
        
        exit_code = main()
        
        if exit_code == 0:
            print("\n🎉 Script completed successfully!")
        elif exit_code == 2:
            print("\n⚠️ Script completed with partial success (upload failed).")
        else:
            print("\n⚠️ Script completed with errors.")
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Script interrupted by user (Ctrl+C)")
        cleanup_temporary_files()
        sys.exit(1)
    except Exception as e:
        report_error(e)
        cleanup_temporary_files()
        sys.exit(1)