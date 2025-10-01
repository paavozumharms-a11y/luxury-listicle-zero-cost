#!/usr/bin/env python3
import os, gspread, json, openai, requests, asyncio, edge_tts
from moviepy.editor import *

gc = gspread.service_account_from_dict(json.loads(os.environ["GOOGLE_SA"]))
sh = gc.open("RichTopics").sheet1
openai.api_key = None   # free tier

def fetch_script(topic):
    try:
        r = openai.ChatCompletion.create(model="gpt-3.5-turbo",
          messages=[{"role":"user","content":f"55-second countdown about expensive {topic}, hook, 3 facts, price reveal."}])
        return r['choices'][0]['message']['content']
    except: return f"Top 3 most expensive {topic} countdown… (dummy text)"

async def tts(text, out):
    await edge_tts.Communicate(text, "en-US-AriaNeural", rate="+20%").save(out)

def fetch_clip(keyword):
    url = f"https://pixabay.com/videos/api/?key=5308042-01ef7b52f5b1a34c5d1a&q={keyword}&orientation=vertical&per_page=3"
    data = requests.get(url).json()
    return [v['videos']['tiny']['url'] for v in data['hits']][:3]

def make_video(script, keyword):
    asyncio.run(tts(script, "voice.mp3"))
    audio = AudioFileClip("voice.mp3")
    clips = [VideoFileClip(v).resize(height=1920).crop(x_center=540, width=1080, height=1920) for v in fetch_clip(keyword)]
    final = concatenate_videoclips(clips, method="compose").set_audio(audio)
    final.write_videofile("rich.mp4", fps=30, codec="libx264", audio_codec="aac")

def upload_yt(file, title):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds = Credentials.from_service_account_info(json.loads(os.environ["GOOGLE_SA"]),
                                                  scopes=["https://www.googleapis.com/auth/youtube.upload"])
    youtube = build("youtube", "v3", credentials=creds)
    body = {"snippet":{"title":title,"categoryId":"24"},"status":{"privacyStatus":"public"}}
    youtube.videos().insert(part="snippet,status", body=body,
                           media_body=MediaFileUpload(file, chunks=-1, resumable=True)).execute()

def job():
    rows = sh.get_all_records()
    undone = [r for r in rows if not r.get('Done')]
    if not undone: return
    row = undone[0]
    keyword = row['Keyword']
    script  = fetch_script(keyword)
    make_video(script, keyword)
    upload_yt("rich.mp4", f"Top 3 Most Expensive {keyword} 🤯")
    idx = rows.index(row) + 2
    sh.update(f"B{idx}", True)   # mark done

if __name__ == "__main__":
    job()
