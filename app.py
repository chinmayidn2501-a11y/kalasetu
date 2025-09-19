import streamlit as st
from google.cloud import translate_v2 as translate
from google.cloud import speech
from google.cloud import texttospeech
from google.cloud import language_v1
from pydub import AudioSegment
import io
import google.generativeai as genai
import pyperclip
import tempfile
import os
from audio_recorder_streamlit import audio_recorder

# ---------- Initialize Google Clients ----------
if "GOOGLE_CREDENTIALS" in st.secrets:
    # Create credentials file from Streamlit secrets
    creds_json = st.secrets["GOOGLE_CREDENTIALS"]
    with open("gcp-creds.json", "w") as f:
        f.write(creds_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp-creds.json"

    # Configure Gemini with the key from secrets
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
else:
    # For local development
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ---------- Initialize Google Clients ----------
translate_client = translate.Client()
speech_client = speech.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()
language_client = language_v1.LanguageServiceClient()
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# ---------- Session State ----------
if "usage" not in st.session_state:
    st.session_state["usage"] = {"translation": 0, "speech": 0, "tts": 0, "social": 0, "price": 0}
if "history" not in st.session_state:
    st.session_state["history"] = []
if "selected_page" not in st.session_state:
    st.session_state["selected_page"] = "Home"
if "kala_chat" not in st.session_state:
    st.session_state["kala_chat"] = []

# ---------- Page Config + Custom Theme ----------
st.set_page_config(page_title="KalaSetu", layout="wide")

st.markdown("""
    <style>
        body, .stApp {
            background-color: #fdf6f0;
            font-family: 'Poppins', sans-serif;
            color: #4a2f2f;
        }
        h1, h2, h3, h4 {
            color: #4a2f2f;
            font-weight: 600;
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #8d493a, #d9b99b);
            color: white;
            padding-top: 2rem;
        }
        .stButton > button {
            background-color: #8d493a;
            color: white;
            border-radius: 25px;
            padding: 8px 20px;
            font-size: 0.95rem;
            border: none;
            box-shadow: 0 2px 6px rgba(0,0,0,0.15);
        }
        .stButton > button:hover {
            background-color: #5d2e2e;
            color: #fff;
        }
        .chat-bubble {
            padding: 10px 16px;
            border-radius: 16px;
            margin: 6px 0;
            max-width: 75%;
            font-size: 0.95rem;
            line-height: 1.4;
        }
        .chat-user {
            background: #fff3e0;
            margin-left: auto;
            text-align: right;
        }
        .chat-kala {
            background: #fdeaea;
            margin-right: auto;
        }
        .artisan-card {
            background: #fff;
            border-radius: 16px;
            padding: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            text-align: center;
        }
        .artisan-card img {
            border-radius: 12px;
            margin-bottom: 10px;
        }
        .see-more {
            text-align: right;
            font-size: 0.9rem;
            color: #4a2f2f;
        }
    </style>
""", unsafe_allow_html=True)

# ---------- Utility: Copy + Share ----------
def show_copy_share(text, feature_name=""):
    if st.button(f"Copy {feature_name}", key=f"copy_{feature_name}"):
        pyperclip.copy(text)
        st.success("Copied to clipboard!")

    wa_url = f"https://wa.me/?text={text}"
    fb_url = f"https://www.facebook.com/sharer/sharer.php?u={text}"
    st.markdown(f"[Share on WhatsApp]({wa_url}) | [Share on Facebook]({fb_url})", unsafe_allow_html=True)

    st.session_state["history"].append(f"[{feature_name}] {text}")

# ---------- Sidebar ----------
with st.sidebar:
    if os.path.exists("logo.jpeg"):
        st.image("logo.jpeg", width=100)
    st.markdown("<h1 style='text-align:center; font-size:3rem;'>KalaSetu</h1>", unsafe_allow_html=True)
    st.markdown("---")
    pages = ["Home", "Translation", "Speech-to-Text", "Text-to-Speech", "Price Advisor", "Social Media Generator"]
    selected_page = st.radio("Navigation", pages, key="sidebar_nav", label_visibility="hidden")

# ---------- Home ----------
if selected_page == "Home":
    st.markdown("<h1>Welcome, Artisan!</h1>", unsafe_allow_html=True)
    st.subheader("Ask Kala")
    user_input = st.text_input("Type your message here...", key="ask_kala_input")
    if st.button("Send", key="ask_kala_send") and user_input.strip():
        try:
            response = gemini_model.generate_content(user_input)
            reply = response.text
            st.session_state["kala_chat"].append(("You", user_input))
            st.session_state["kala_chat"].append(("Kala", reply))
        except Exception as e:
            st.session_state["kala_chat"].append(("Kala", f"⚠️ Error: {e}"))

    for speaker, msg in st.session_state["kala_chat"]:
        bubble_class = "chat-user" if speaker == "You" else "chat-kala"
        st.markdown(f"<div class='chat-bubble {bubble_class}'><b>{speaker}:</b> {msg}</div>", unsafe_allow_html=True)

# ---------- Translation ----------
elif selected_page == "Translation":
    st.header("Translation")
    text = st.text_area("Enter text", key="translate_input")
    target_lang = st.selectbox("Translate to", ["Hindi", "Kannada", "Tamil", "Telugu", "Malayalam", "English"])
    lang_codes = {"Hindi": "hi", "Kannada": "kn", "Tamil": "ta", "Telugu": "te", "Malayalam": "ml", "English": "en"}
    if st.button("Translate"):
        result = translate_client.translate(text, target_language=lang_codes[target_lang])
        st.success(result["translatedText"])
        show_copy_share(result["translatedText"], "Translation")

# ---------- Speech-to-Text ----------
elif selected_page == "Speech-to-Text":
    st.header("Speech to Text")
    lang = st.selectbox("Select Speech Language", ["English (India)", "Hindi (India)", "Kannada (India)", "Tamil (India)", "Telugu (India)", "Malayalam (India)"])
    lang_map = {"English (India)": "en-IN", "Hindi (India)": "hi-IN", "Kannada (India)": "kn-IN", "Tamil (India)": "ta-IN", "Telugu (India)": "te-IN", "Malayalam (India)": "ml-IN"}
    st.subheader("🎙 Record Your Voice")
    audio_bytes = audio_recorder()

    if audio_bytes:
        try:
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav").set_channels(1)
            content = audio.raw_data
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=audio.frame_rate,
                language_code=lang_map[lang],
            )
            recognition_audio = speech.RecognitionAudio(content=content)
            response = speech_client.recognize(config=config, audio=recognition_audio)
            text = " ".join([res.alternatives[0].transcript for res in response.results])
            st.success(f"*Transcribed Text:* {text}")
            show_copy_share(text, "Speech-to-Text")
        except Exception as e:
            st.error(f"Could not transcribe. Error: {e}")

# ---------- Text-to-Speech ----------
elif selected_page == "Text-to-Speech":
    st.header("Text-to-Speech")
    text = st.text_area("Enter text to convert to speech")
    lang = st.selectbox("Language", ["English", "Hindi", "Kannada", "Tamil", "Telugu", "Malayalam"])
    lang_map = {"English": "en", "Hindi": "hi", "Kannada": "kn", "Tamil": "ta", "Telugu": "te", "Malayalam": "ml"}
    if st.button("Convert to Audio"):
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(language_code=lang_map[lang], ssml_gender=texttospeech.SsmlVoiceGender.FEMALE)
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(response.audio_content)
            tmp_path = tmp.name
        st.audio(tmp_path, format="audio/mp3")
        os.remove(tmp_path)
