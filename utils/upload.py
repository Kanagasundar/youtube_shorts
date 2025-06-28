from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaFileUpload
import os
from utils.affiliate import get_affiliate_link

def upload_video(video_file, title, description_template):
    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    flow = InstalledAppFlow.from_client_secrets_file("credentials/client_secret.json", scopes)
    creds = flow.run_console()
    youtube = build('youtube', 'v3', credentials=creds)

#     affiliate_link = get_affiliate_link()
    final_description = description_template.replace("{link}", affiliate_link)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": final_description,
                "tags": ["AI", "tools", "money", "shorts"],
                "categoryId": "27"
            },
            "status": {
                "privacyStatus": "public"
            }
        },
        media_body=MediaFileUpload(video_file)
    )

    response = request.execute()
    print("Upload Success: https://youtube.com/watch?v=" + response["id"])
