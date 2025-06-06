import json
import os
import time
from youtubesearchpython import VideosSearch
import yt_dlp
import openai
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# === 환경설정 ===
BRANDS = ["롯데호텔", "신라호텔", "조선호텔", "베스트웨스턴"]
SHEET_ID = "YOUR_GOOGLE_SHEET_ID"
YOUTUBE_DATA_SHEET = "YoutubeData"
YOUTUBE_INSIGHTS_SHEET = "YoutubeInsights"

# === API 키 ===
openai.api_key = os.getenv("OPENAI_API_KEY")

# === Google Sheets 인증 ===
creds = Credentials.from_service_account_info(json.loads(os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")))
gc = gspread.authorize(creds)
sh = gc.open_by_key(SHEET_ID)
youtube_data_ws = sh.worksheet(YOUTUBE_DATA_SHEET)
youtube_insight_ws = sh.worksheet(YOUTUBE_INSIGHTS_SHEET)

def search_videos(brand):
    videos_search = VideosSearch(brand, limit=3)
    return videos_search.result()['result']

def extract_video_info(url):
    ydl_opts = {'skip_download': True, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("title"),
            "like_count": info.get("like_count"),
            "comment_count": info.get("comment_count"),
            "description": info.get("description"),
            "url": url
        }

def analyze_with_gpt(title, description):
    prompt = f"""유튜브 영상 제목과 설명을 기반으로 해당 브랜드가 어떤 마케팅 메시지를 전달하고 있는지 요약해줘.\n
제목: {title}\n설명: {description[:500]}"""
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def append_to_sheet(ws, row):
    ws.append_row(row, value_input_option="USER_ENTERED")

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    for brand in BRANDS:
        videos = search_videos(brand)
        for video in videos:
            url = video['link']
            info = extract_video_info(url)

            summary = analyze_with_gpt(info['title'], info['description'] or "")
            keywords = ", ".join(info['description'].split()[:5])

            # YoutubeData
            data_row = [
                today, brand, info['title'], info['comment_count'], info['like_count'],
                "", keywords, url
            ]
            append_to_sheet(youtube_data_ws, data_row)

            # YoutubeInsights
            insight_row = [
                today, brand, info['title'], keywords, summary, url
            ]
            append_to_sheet(youtube_insight_ws, insight_row)

            time.sleep(2)  # Rate limit 보호용

if __name__ == "__main__":
    main()
