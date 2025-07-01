#!/usr/bin/env python3
"""
YouTube OAuth 2.0 Setup Script
This script helps set up OAuth 2.0 authentication for YouTube API by generating a token.pickle file.
Run this locally to perform the user consent flow, then upload token.pickle to your CI/CD secrets.
"""

import os
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_oauth(credentials_path='credentials.json', token_path='token.pickle'):
    """Set up OAuth 2.0 credentials for YouTube API."""
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

    try:
        # Check for credentials.json
        if not os.path.exists(credentials_path):
            logger.error(f"❌ Credentials file not found: {credentials_path}")
            logger.info("💡 Please download OAuth 2.0 credentials from Google Cloud Console and save as credentials.json")
            return False

        # Run OAuth 2.0 flow
        logger.info("🔐 Initiating OAuth 2.0 user consent flow")
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        credentials = flow.run_local_server(port=0)

        # Save the credentials to token.pickle
        with open(token_path, 'wb') as token:
            pickle.dump(credentials, token)
            logger.info(f"✅ Saved OAuth 2.0 token to {token_path}")

        logger.info("🎉 OAuth 2.0 setup completed successfully!")
        logger.info("💡 Upload token.pickle to your CI/CD secrets (e.g., GitHub Secrets as YOUTUBE_TOKEN)")
        return True

    except Exception as e:
        logger.error(f"❌ OAuth 2.0 setup failed: {str(e)}")
        logger.debug("Stack trace:", exc_info=True)
        return False

if __name__ == "__main__":
    if setup_oauth():
        print("✅ Setup complete. You can now use token.pickle in your automation.")
    else:
        print("❌ Setup failed. Check logs for details.")