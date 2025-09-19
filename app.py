import streamlit as st
from google.cloud import translate_v2 as translate
from google.cloud import speech
from google.cloud import texttospeech
from google.cloud import language_v1
import google.generativeai as genai
import pyperclip
import tempfile
import os
import wave
import audioop
from audio_recorder_streamlit import audio_recorder
# ---------- Initialize Google Clients ----------
# Check if we are running on Streamlit Cloud
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
    # For local development, it will use your local setup
    # Make sure you have set GOOGLE_APPLICATION_CREDENTIALS and GEMINI_API_KEY
    # as environment variables locally.
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))



# ---------- Initialize Google Clients ----------
translate_client = translate.Client()
speech_client = speech.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()
language_client = language_v1.LanguageServiceClient()
gemini_model = genai.GenerativeModel("gemini-1.5-flash")
# ---------- Configure Gemini ----------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
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
        /* Global */
        body, .stApp {
            background-color: #fdf6f0;
            font-family: 'Poppins', sans-serif;
            color: #4a2f2f;
        }
        h1, h2, h3, h4 {
            color: #4a2f2f;
            font-weight: 600;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #8d493a, #d9b99b);
            color: white;
            padding-top: 2rem;
        }
        section[data-testid="stSidebar"] .css-1v3fvcr, 
        section[data-testid="stSidebar"] .css-1d391kg {
            color: white !important;
            font-size: 1.05rem;
            font-weight: 500;
        }
        section[data-testid="stSidebar"] h1 {
            color: white;
            font-size: 1.6rem;
            font-weight: 700;
        }

        /* Buttons */
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

        /* Ask Kala */
        .ask-kala-box {
            background: #fff;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 20px;
        }
        .stTextInput > div > div > input {
            border-radius: 25px;
            border: 1px solid #d9b99b;
            padding: 10px 18px;
        }

        /* Chat bubbles */
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

        /* Cards */
        .artisan-card {
            background: #fff;
            border-radius: 16px;
            padding: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            text-align: center;
            transition: all 0.2s ease;
        }
        .artisan-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        }
        .artisan-card img {
            border-radius: 12px;
            margin-bottom: 10px;
        }

        /* Footer links */
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
    st.image("logo.jpeg", width=100)  # ✅ Added brand logo
    st.markdown("<h1 style='text-align:center; font-size:3rem;'>KalaSetu</h1>", unsafe_allow_html=True)
    st.markdown("---")
    pages = [
        "Home",
        "Translation",
        "Speech-to-Text",
        "Text-to-Speech",
        "Price Advisor",
        "Social Media Generator"
    ]
    selected_page = st.radio(
        "Navigation",
        pages,
        key="sidebar_nav",
        label_visibility="hidden"  # ✅ Hides the small label above radio
    )

# ---------- Extra CSS for Sidebar Navigation ----------
st.markdown("""
    <style>
        section[data-testid="stSidebar"] .stRadio > div {
            font-size: 2.1rem;   /* ✅ Bigger text */
            color: white !important;
        }
    </style>
""", unsafe_allow_html=True)


# ---------- Home ----------
if selected_page == "Home":
    st.markdown("<h1>Welcome, Artisan!</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:1.1rem; color:#7b4b3a;'>How can I assist you today?</p>", unsafe_allow_html=True)

    # Ask Kala
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

    # Display chat history
    for speaker, msg in st.session_state["kala_chat"]:
        bubble_class = "chat-user" if speaker == "You" else "chat-kala"
        st.markdown(f"<div class='chat-bubble {bubble_class}'><b>{speaker}:</b> {msg}</div>", unsafe_allow_html=True)

    # Featured Artisans
    st.subheader("Featured Artisans")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='artisan-card'><img src='https://dsource.in/sites/default/files/resource/sandalwood-carving-sagara/introduction/minigallery/9223/10.jpg' width='100%'><h4>JayaRama</h4><p>Bengaluru</p><p> Trace their craft's history back over a thousand years, with connections to ancient history</p></div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='artisan-card'><img src='https://www.shutterstock.com/shutterstock/videos/3733502593/thumb/1.jpg?ip=x480' width='100%'><h4>Meera</h4><p>Jaipur</p><p>Keeping the culture of Rajasthan alive</p></div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='artisan-card'><img src='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSFr9TMom0D9oxmFYEUZBkxB5vYHvCdBM67gA&s' width='100%'><h4>Asha</h4><p>Kochi</p><p>Pottery that tells the stories of Kerala</p></div>", unsafe_allow_html=True)
    st.markdown("<p class='see-more'><b>See more →</b></p>", unsafe_allow_html=True)

# ---------- Other Pages ----------
elif selected_page == "Translation":
    st.header("Translation")
    text = st.text_area("Enter text", key="translate_input")
    target_lang = st.selectbox("Translate to", ["Hindi", "Kannada", "Tamil", "Telugu", "Malayalam", "English"], key="translate_lang")
    lang_codes = {"Hindi": "hi", "Kannada": "kn", "Tamil": "ta", "Telugu": "te", "Malayalam": "ml", "English": "en"}
    if st.button("Translate", key="translate_button"):
        result = translate_client.translate(text, target_language=lang_codes[target_lang])
        st.success(result["translatedText"])
        st.session_state["usage"]["translation"] += 1
        show_copy_share(result["translatedText"], "Translation")

# ---------- Speech-to-Text ----------
elif selected_page == "Speech-to-Text":
    st.header("Speech to Text")
    lang = st.selectbox("Select Speech Language", ["English (India)", "Hindi (India)", "Kannada (India)", "Tamil (India)", "Telugu (India)", "Malayalam (India)"], key="speech_lang")
    lang_map = {"English (India)": "en-IN", "Hindi (India)": "hi-IN", "Kannada (India)": "kn-IN", "Tamil (India)": "ta-IN", "Telugu (India)": "te-IN", "Malayalam (India)": "ml-IN"}
    st.subheader("🎙 Record Your Voice")
    audio_bytes = audio_recorder(key="speech_record")
    if audio_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_bytes)
            audio_path = f.name
        with wave.open(audio_path, "rb") as wf:
            params = wf.getparams()
            channels = wf.getnchannels()
            frames = wf.readframes(wf.getnframes())
        if channels > 1:
            mono_frames = audioop.tomono(frames, 2, 1, 1)
            with wave.open(audio_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(params.sampwidth)
                wf.setframerate(params.framerate)
                wf.writeframes(mono_frames)
        try:
            with open(audio_path, "rb") as audio_file:
                content = audio_file.read()
            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=params.framerate,
                language_code=lang_map[lang],
            )
            response = speech_client.recognize(config=config, audio=audio)
            text = " ".join([res.alternatives[0].transcript for res in response.results])
            st.success(f"*Transcribed Text:* {text}")
            st.session_state["usage"]["speech"] += 1
            show_copy_share(text, "Speech-to-Text")
        except Exception as e:
            st.error(f"Could not transcribe. Please try again. ({e})")
        finally:
            os.remove(audio_path)

# ---------- Text-to-Speech ----------
elif selected_page == "Text-to-Speech":
    st.header("Text-to-Speech")
    text = st.text_area("Enter text to convert to speech", key="tts_input")
    lang = st.selectbox("Language", ["English", "Hindi", "Kannada", "Tamil", "Telugu", "Malayalam"], key="tts_lang")
    lang_map = {"English": "en", "Hindi": "hi", "Kannada": "kn", "Tamil": "ta", "Telugu": "te", "Malayalam": "ml"}
    if st.button("Convert to Audio", key="tts_button"):
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(language_code=lang_map[lang], ssml_gender=texttospeech.SsmlVoiceGender.FEMALE)
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        audio_file_path = "output.mp3"
        with open(audio_file_path, "wb") as out:
            out.write(response.audio_content)
        with open(audio_file_path, "rb") as audio_file:
            st.audio(audio_file.read(), format="audio/mp3")
        st.session_state["usage"]["tts"] += 1
        os.remove(audio_file_path)

# ---------- Price Advisor ----------
elif selected_page == "Price Advisor":
    st.header("Price Advisor")
    product = st.text_input("Product Name", key="price_product")
    cost = st.number_input("Production Cost (₹)", min_value=0, key="price_cost")
    trend = st.slider("Product Trend (1 = low demand, 5 = very trending)", 1, 5, 3, key="price_trend")
    place = st.selectbox("Place of Selling", ["Metro City", "Urban Town", "Rural Area"], key="price_place")
    place_factor = {"Metro City": 1.5, "Urban Town": 1.2, "Rural Area": 1.0}
    if st.button("Suggest Prices", key="price_button"):
        document = language_v1.Document(content=f"{product} {trend}", type_=language_v1.Document.Type.PLAIN_TEXT)
        sentiment = language_client.analyze_sentiment(request={"document": document}).document_sentiment
        trend_factor = 1 + (sentiment.score / 2)
        min_price = cost * 1.2
        standard_price = cost * (1.3 + (trend * 0.1)) * place_factor[place] * trend_factor
        premium_price = cost * (2.0 + (trend * 0.2)) * place_factor[place] * trend_factor
        st.success(f"🟢 Minimum Price: ₹{min_price:.2f}")
        st.success(f"🟡 Standard Price: ₹{standard_price:.2f}")
        st.success(f"🔴 Premium Price: ₹{premium_price:.2f}")
        st.session_state["usage"]["price"] += 1

# ---------- Social Media Generator ----------
elif selected_page == "Social Media Generator":
    st.header("Social Media Content Generator")
    option = st.radio("Choose Content Type", ["Caption", "Story from My Words", "Hashtags"], key="social_option")
    lang_codes = {"English": "en", "Hindi": "hi", "Kannada": "kn", "Tamil": "ta", "Telugu": "te", "Malayalam": "ml"}
    def show_translations(text, feature_name):
        for lang, code in lang_codes.items():
            try:
                translated = translate_client.translate(text, target_language=code)["translatedText"]
                st.markdown(f"{lang}:** {translated}")
            except Exception:
                st.warning(f"Could not translate to {lang}.")
        show_copy_share(text, feature_name)
    if option == "Caption":
        product = st.text_input("Product Name", key="social_caption_product")
        usp = st.text_input("Unique Feature", key="social_caption_usp")
        if st.button("Generate Caption", key="social_caption_button"):
            caption = f"✨ Check out our {product}! {usp}. Made with love ❤ #KalaSetu"
            st.success(caption)
            st.session_state["usage"]["social"] += 1
            show_translations(caption, "Caption")
    elif option == "Story from My Words":
        story = st.text_area("Write your story", key="social_story_input")
        if st.button("Generate Story Description", key="social_story_button"):
            description = f"✨ Behind every creation lies a story. {story}. This isn’t just a product, it’s a piece of culture, crafted with love and passion. By choosing this, you support our artisans and carry a tradition into your life. 🌸"
            st.success(description)
            st.session_state["usage"]["social"] += 1
            show_translations(description, "Story")
    elif option == "Hashtags":
        product = st.text_input("Product Type (e.g., Saree, Pottery)", key="social_hashtag_product")
        if st.button("Generate Hashtags", key="social_hashtag_button"):
            hashtags = f"#{product} #Handmade #SupportArtisans #KalaSetu"
            st.success(hashtags)
            st.session_state["usage"]["social"] += 1
            show_translations(hashtags, "Hashtags")