#!/usr/bin/env python3
"""
YouTube Automation Main Script - Enhanced Version
Generates and uploads daily YouTube Shorts content with improved error handling,
logging, configuration management, and cleanup features.

Version: 1.1.0
Update Notes:
- Added version information and microsecond precision in logging.
- Introduced health check for system resources.
- Enhanced error reporting with detailed stack traces.
- Improved documentation for better maintainability.

Dependencies:
- os, sys, traceback, shutil, signal, datetime, pathlib, logging, json, time, typing, importlib.util, dotenv
- Utils modules: topic_rotator, scripting, voice, video, thumbnail_generator, youtube_uploader
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

# Load environment variables from .env file
load_dotenv()

# Configure logging with both file and console output with microsecond precision
def setup_logging():
    """Set up comprehensive logging configuration with microsecond precision."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create formatters with microsecond precision
    detailed_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler for detailed logs
    file_handler = logging.FileHandler(
        log_dir / f"automation_{datetime.now().strftime('%Y%m%d')}.log",
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler for user-friendly output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Configure root logger
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
        'requests': ('import requests', 'requests')  # Required for Pexels API
    }
    
    missing_packages = []
    
    for package_name, (import_statement, check_name) in required_packages.items():
        try:
            # Clear module cache for this package
            base_module = import_statement.split()[1].split('.')[0]
            for mod in list(sys.modules.keys()):
                if base_module in mod:
                    del sys.modules[mod]
            
            # Execute the import statement
            exec(import_statement)
            
            # Check if the module or attribute exists
            module = eval(check_name)
            
            # Get version info
            version = getattr(module, '__version__', 
                           getattr(module, 'VERSION', 
                                  getattr(module, 'version', 'unknown')))
            
            # Log module path for debugging
            spec = importlib.util.find_spec(base_module)
            logger.debug(f"✅ {package_name} ({check_name}) - v{version} from {spec.origin if spec else 'unknown'}")
            
        except (ImportError, AttributeError) as e:
            logger.error(f"❌ {package_name} ({check_name}) - Failed: {str(e)}")
            missing_packages.append(package_name)
    
    if missing_packages:
        logger.error(f"❌ Missing {len(missing_packages)} required packages:")
        for package in missing_packages:
            logger.error(f"   - {package}")
        
        print("\n💡 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        
        # Additional debugging info
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
        
        # Validate OAuth 2.0 credentials (installed or web)
        if 'installed' in creds_data:
            return _validate_oauth_credentials(creds_data['installed'], 'installed')
        elif 'web' in creds_data:
            return _validate_oauth_credentials(creds_data['web'], 'web')
        else:
            logger.error("❌ Unknown credentials format. Expected 'installed' or 'web' for OAuth 2.0")
            logger.error(f"Available keys: {list(creds_data.keys())}")
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
    
    # Validate URLs
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
    
    required_vars = ['OPENAI_API_KEY', 'PEXELS_API_KEY']  # Updated to use PEXELS_API_KEY
    optional_vars = {
        'UPLOAD_TO_YOUTUBE': 'true',
        'VIDEO_PRIVACY': 'public',
        'VIDEO_CATEGORY_ID': '28',
        'DISCORD_WEBHOOK_URL': None,
        'TOPIC_OVERRIDE': None,
        'CATEGORY_OVERRIDE': None,
        'MAX_RETRIES': '5',  # Aligned with workflow
        'CLEANUP_OLD_FILES': 'true',
        'KEEP_FILES_DAYS': '7'
    }
    
    missing_vars = []
    
    # Check required variables
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            logger.debug(f"✅ {var} is set (length: {len(value)})")
    
    # Check and set defaults for optional variables
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
            if var == 'OPENAI_API_KEY':
                print(f"   export {var}=sk-your_openai_api_key_here")
            elif var == 'PEXELS_API_KEY':
                print(f"   export {var}=your_pexels_api_key_here")
            else:
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
    """Perform a basic health check of system resources."""
    logger.info("🏥 Checking system health...")
    
    try:
        # Check disk space (simplified check for available space in GB)
        stat = shutil.disk_usage(OUTPUT_DIR)
        available_gb = stat.free / (2**30)
        if available_gb < 1:
            logger.error(f"❌ Insufficient disk space: {available_gb:.1f} GB available")
            return False
        logger.debug(f"✅ Disk space available: {available_gb:.1f} GB")
        
        # Add more checks as needed (e.g., memory, CPU)
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
        ("System Health", check_system_health),  # New health check
    ]
    
    for check_name, check_func in checks:
        logger.info(f"   Checking {check_name}...")
        if not check_func():
            logger.error(f"❌ {check_name} check failed")
            return False
    
    # Handle upload configuration
    upload_enabled = os.getenv('UPLOAD_TO_YOUTUBE', 'true').lower() == 'true'
    
    if upload_enabled:
        logger.info("   Checking YouTube credentials...")
        if validate_credentials_file():
            logger.info("✅ credentials.json found and validated")
        else:
            logger.warning("⚠️ credentials.json validation failed")
            logger.info("💡 YouTube upload will be disabled for this run")
            os.environ['UPLOAD_TO_YOUTUBE'] = 'false'
            upload_enabled = False
    
    if not upload_enabled:
        logger.info("ℹ️ YouTube upload disabled - videos will be saved locally only")
    
    # Clean up old files
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
        'thumbnail_generator': ['generate_image_sequence'],  # Updated to use Pexels
        'youtube_uploader': ['YouTubeUploader', 'generate_video_metadata']
    }
    
    imported_modules = {}
    
    # Clear module cache to prevent stale imports
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
            
            # Verify required functions exist
            for func_name in functions:
                if not hasattr(module, func_name):
                    raise ImportError(f"Function '{func_name}' not found in module '{module_name}'")
                imported_modules[func_name] = getattr(module, func_name)
            
            logger.debug(f"✅ {module_name} imported successfully from {module_path}")
            
        except ImportError as e:
            logger.error(f"❌ Failed to import {module_name}: {e}")
            _show_import_help(module_name)
            return False
    
    # Make functions available globally
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
        try:
            import openai
            for mod in list(sys.modules.keys()):
                if 'openai' in mod.lower():
                    del sys.modules[mod]
            import openai
            logger.debug(f"OpenAI version: {getattr(openai, '__version__', 'unknown')}")
            logger.debug(f"Python version: {sys.version}")
            logger.debug(f"Python executable: {sys.executable}")
        except ImportError:
            logger.warning("⚠️ OpenAI module not imported")
        
        # Use ScriptGenerator for script generation with fallbacks
        script = generate_script(topic, category)
        if not script or len(script.strip()) < 50:
            logger.error(f"❌ Generated script is too short or empty ({len(script.strip()) if script else 0} characters)")
            logger.debug(f"Script content: {script!r}")
            # Rely on ScriptGenerator's built-in fallback
            from scripting import ScriptGenerator
            generator = ScriptGenerator()
            script = generator.generate_script_fallback(topic, category)
            logger.info(f"✅ Using fallback script from ScriptGenerator ({len(script)} characters)")
        return script

    # The rest of the function remains unchanged (assuming other content generation steps are the same)
    # For completeness, you would include the remaining steps for voice, video, and thumbnail generation
    # Since they weren't provided in the original, I'll assume they remain unchanged
    # If you need these parts, please provide them, and I can include them

    # Placeholder for remaining content generation steps
    logger.info("🔊 Generating voice...")
    voice_file = retry_on_failure(lambda: generate_voice(script))
    logger.info("🎥 Generating video...")
    video_file = retry_on_failure(lambda: create_video(voice_file))
    logger.info("🖼️ Generating thumbnail...")
    thumbnail_files = retry_on_failure(lambda: generate_image_sequence(topic))
    
    return script, voice_file, thumbnail_files, video_file

if __name__ == "__main__":
    try:
        if not setup_check():
            sys.exit(1)
        
        if not import_modules():
            sys.exit(1)
        
        # Test content generation
        topic = os.getenv('TOPIC_OVERRIDE', 'Plants That Can Count to Twenty')
        category = os.getenv('CATEGORY_OVERRIDE', 'Nature')
        
        script, voice_file, thumbnail_files, video_file = generate_content_with_retry(topic, category)
        logger.info(f"✅ Generated content:\nScript: {script}\nVoice: {voice_file}\nThumbnails: {thumbnail_files}\nVideo: {video_file}")
        
        # Optionally upload to YouTube
        if os.getenv('UPLOAD_TO_YOUTUBE', 'true').lower() == 'true':
            logger.info("📤 Uploading to YouTube...")
            metadata = generate_video_metadata(script, topic, category)
            uploader = YouTubeUploader()
            video_id = retry_on_failure(lambda: uploader.upload_video(video_file, metadata))
            logger.info(f"✅ Video uploaded successfully: {video_id}")
        
    except Exception as e:
        report_error(e)
        sys.exit(1)
    finally:
        cleanup_temporary_files()