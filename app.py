import streamlit as st
import os
from datetime import datetime, timedelta
from googleapiclient.discovery import build
import speech_recognition as sr
import isodate
import google.generativeai as genai

# --- API Configuration ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
youtube = build("youtube", "v3", developerKey=st.secrets["YOUTUBE_API_KEY"])

# --- Page Setup ---
st.set_page_config(page_title="🎬 YouTube Video Finder", layout="wide")
st.title("🎬 YouTube Video Finder & Analyzer")

# --- Input Mode ---
mode = st.radio("Choose input mode:", ["Text", "Voice"], horizontal=True)

# Import dependencies
try:
    import speech_recognition as sr
    voice_enabled = True
except ImportError:
    voice_enabled = False

def record_voice():
    """Records voice input from the user and transcribes it to text."""
    if not voice_enabled:
        st.warning("SpeechRecognition is not available. Please use text input.")
        return ""

    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            st.info("🎙 Speak now... (auto-stops after a pause)")
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
        query = r.recognize_google(audio)
        return query
    except sr.WaitTimeoutError:
        st.warning("⏱ No speech detected within timeout.")
    except sr.UnknownValueError:
        st.warning("❓ Could not understand audio.")
    except Exception as e:
        st.error(f"⚠️ Error during voice recognition: {e}")
    
    return ""

query = st.text_input("Enter your search query:") if mode == "Text" else ""
if mode == "Voice" and st.button("🎤 Start Recording"):
    with st.spinner("🎧 Listening..."):
        query = record_voice()
    if query:
        st.success(f"🗣️ You said: \"{query}\"")
    else:
        st.warning("No valid voice input detected.")

# --- YouTube Search ---
def search_youtube(query):
    if not query: return []
    try:
        after = (datetime.utcnow() - timedelta(days=14)).isoformat("T") + "Z"
        results = youtube.search().list(
            q=query, part="snippet", type="video", order="relevance",
            videoDuration="medium", maxResults=20, publishedAfter=after
        ).execute()
        return [item['id']['videoId'] for item in results.get('items', [])]
    except Exception as e:
        st.error(f"API Error: {e}")
        return []

def parse_duration(iso_duration):
    return isodate.parse_duration(iso_duration).total_seconds() / 60

def filter_videos(ids):
    if not ids: return []
    filtered = []
    try:
        details = youtube.videos().list(part="contentDetails,snippet", id=",".join(ids)).execute()
        for item in details.get("items", []):
            dur = parse_duration(item['contentDetails']['duration'])
            if 4 <= dur <= 20:
                filtered.append({
                    "title": item['snippet']['title'],
                    "url": f"https://www.youtube.com/watch?v={item['id']}",
                    "duration": round(dur, 2)
                })
    except Exception as e:
        st.error(f"Duration Filter Error: {e}")
    return filtered

def select_best_video(videos, query):
    if not videos or not query:
        return videos[0] if videos else None
    prompt = f"""You're an expert YouTube content curator. Pick the most relevant video to: "{query}"
Videos:
{chr(10).join([f"{i+1}. {v['title']}" for i, v in enumerate(videos)])}
Reply ONLY with the number. If none match, reply "0"."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        choice = model.generate_content(prompt).text.strip()
        idx = int(choice) - 1
        return videos[idx] if 0 <= idx < len(videos) else videos[0]
    except:
        return videos[0]

# --- Main Workflow ---
if query:
    with st.spinner("🔍 Searching YouTube..."):
        ids = search_youtube(query)

    if not ids:
        st.warning("No videos found.")
    else:
        with st.spinner("⏱️ Filtering by duration (4–20 min)..."):
            filtered = filter_videos(ids)

        if not filtered:
            st.warning("No videos in the 4–20 min range.")
        else:
            st.subheader("📄 Filtered Results:")
            for i, v in enumerate(filtered[:5]):
                st.markdown(f"{i+1}. **{v['title']}** ({v['duration']} min) - [Watch]({v['url']})")
            if len(filtered) > 5:
                st.markdown(f"...and {len(filtered)-5} more.")

            with st.spinner("🤖 Finding the best video..."):
                best = select_best_video(filtered, query)

            if best:
                st.subheader("🏆 Top Pick:")
                st.success(f"**{best['title']}** ({best['duration']} min)")
                st.markdown(f"[📺 Watch on YouTube]({best['url']})", unsafe_allow_html=True)

st.sidebar.header("Navigation")

# Sidebar navigation links with bullets
st.sidebar.markdown("- [GitHub Repo](https://github.com/nabdeep-patel/youtube-video-finder)")
st.sidebar.write("---")

# Connect with me section
st.sidebar.markdown("Connect with me:")
github_link = "[![GitHub](https://img.shields.io/badge/GitHub-Profile-blue?style=flat-square&logo=github)](https://github.com/nabdeep-patel)"
linkedin_link = "[![LinkedIn](https://img.shields.io/badge/LinkedIn-Profile-blue?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/nabdeeppatel)"
website_link = "[![Website](https://img.shields.io/badge/Personal-Website-blue?style=flat-square&logo=chrome)](https://linktr.ee/nabdeeppatel/store)"
email_link = "[![Email](https://img.shields.io/badge/Google-Mail-blue?style=flat-square&logo=gmail)](mailto:nabdeeppatel@gmail.com)"

st.sidebar.markdown(github_link + " " + linkedin_link + " " + website_link + " " + email_link)
st.sidebar.markdown("Created by Nabdeep Patel")
