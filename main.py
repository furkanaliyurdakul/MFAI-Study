# SPDX-License-Identifier: MIT
"""Streamlit entry point – multi‑step learning platform wrapper.

Pages:
  • *Home* (study intro)
  • *Student Profile Survey*
  • *AI Learning Assistant* (multilingual study)
  • *Knowledge Test*
  • *User‑Experience Questionnaire*

Relies on :pyfile:`Gemini_UI.py` for AI assistant helpers.
"""

# ───────────────────────────────────────────────────────────────
# Streamlit‑wide setup
# ───────────────────────────────────────────────────────────────
from __future__ import annotations

import atexit
import json
import streamlit as st

# Import DEBUG_MODE before any debug prints
from config import DEBUG_MODE

# ── Page Config (MUST BE FIRST STREAMLIT COMMAND) ──────────────
st.set_page_config(page_title="AI Learning Platform", layout="wide")

# ── Authentication Check ──────────────────────────────────────
from login_page import require_authentication
credential_config = require_authentication()
if DEBUG_MODE:
    print("🔧 DEBUG: Authentication completed")

# ── Presence Tracker (for concurrent session monitoring) ────────
try:
    from presence_tracker import get_presence_tracker
    presence = get_presence_tracker(max_concurrent=2)  # Adjust max as needed
    if presence:
        print("✅ Presence tracker initialized")
    else:
        print("⚠️ Presence tracker returned None")
except Exception as e:
    presence = None
    print(f"⚠️ Presence tracker unavailable: {e}")
    import traceback
    traceback.print_exc()

# ── Initialize Session State (IMMEDIATELY AFTER AUTH) ─────────
def ensure_session_state_initialized():
    """Ensure all required session state variables are initialized with defaults."""
    if DEBUG_MODE:
        print("🔧 DEBUG: Starting session state initialization")
    # --- tutor‑related objects that Gemini_UI expects -----------------
    DEFAULTS = {
        "exported_images": [],  # list[Path] – exported PPT slides
        "transcription_text": "",  # Whisper output
        "selected_slide": "Slide 1",
        "debug_logs": [],  # collected via Gemini_UI.debug_log(...)
        "messages": [],
        "transcription_loaded": False,
        "slides_loaded": False
    }

    for k, v in DEFAULTS.items():
        st.session_state.setdefault(k, v)

    # Navigation & completion flags
    for key in (
        "current_page",
        "profile_completed",
        "learning_completed",
        "test_completed",
        "ueq_completed",
    ):
        st.session_state.setdefault(key, False if key != "current_page" else "home")
    
    # Track previous page for scroll-to-top detection
    st.session_state.setdefault("previous_page", None)
    
    if DEBUG_MODE:
        print("🔧 DEBUG: Session state initialization completed")

# Always ensure session state is properly initialized
ensure_session_state_initialized()
if DEBUG_MODE:
    print("🔧 DEBUG: About to start imports")

# ── Configuration ──────────────────────────────────────────────
from config import get_config, get_course_title, get_platform_name, get_ui_text
config = get_config()
if DEBUG_MODE:
    print("🔧 DEBUG: Config loaded")

# Language names for display
language_names = {
    "en": "English",
    "de": "German",
    "nl": "Dutch",
    "tr": "Turkish",
    "sq": "Albanian",
    "hi": "Hindi"
}

LABEL: str = config.platform.learning_section_name
atexit.register(lambda: get_learning_logger().save_logs(force=True))
atexit.register(lambda: page_dump(Path(sm.session_dir)))

# ── std‑lib ────────────────────────────────────────────
import os
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timezone

# ── third‑party ────────────────────────────────────────────────
#import google.generativeai as genai
#from google.genai.types import Content, Part
from PIL import Image
from google import genai
from google.genai import types

# ── local ──────────────────────────────────────────────────────
# NEW – Consent and information document -------------------------
DOCS_DIR = Path(__file__).parent / "docs"
CONSENT_PDF = DOCS_DIR / "Participant_Information_and_Consent.pdf"

from Gemini_UI import (
    TRANSCRIPTION_DIR,
    UPLOAD_DIR_AUDIO,
    UPLOAD_DIR_PPT,
    UPLOAD_DIR_PROFILE,
    build_prompt,
    create_summary_prompt,
    make_base_context,
    debug_log,
    parse_detailed_student_profile,
)

# Import UPLOAD_DIR_VIDEO with fallback for deployment issues
try:
    from Gemini_UI import UPLOAD_DIR_VIDEO
except ImportError:
    # Fallback: create video directory if import fails
    UPLOAD_DIR_VIDEO = Path.cwd() / "uploads" / "video"
    UPLOAD_DIR_VIDEO.mkdir(parents=True, exist_ok=True)
from Gemini_UI import export_ppt_slides as process_ppt_file  # alias → keep old name
from Gemini_UI import (
    parse_detailed_student_profile,
)
from Gemini_UI import (
    transcribe_audio as transcribe_audio_from_file,  # alias → keep old name
)
from learning_interaction_logger import get_learning_logger
from session_manager import get_session_manager
from page_timer import start as page_timer_start      # put this with the other imports
from page_timer import dump as page_dump

sm = get_session_manager()

if "_page_timer" not in st.session_state:
    from page_timer import start as page_timer_start
    
    page_timer_start("home")

# ── Authentication-based Configuration ─────────────────────────────────
# Language and modes are now set based on login credentials
if "language_code" not in st.session_state:
    # Get language from authentication system
    from authentication import get_auth_manager
    auth_manager = get_auth_manager()
    language_code = auth_manager.get_language_code()
    
    if language_code:
        # Always update language_code from auth_manager (picks up dev mode changes)
        st.session_state["language_code"] = language_code
        sm.language_code = language_code
    
    # Set special modes based on credentials
    if credential_config:
        st.session_state["dev_mode"] = credential_config.dev_mode
        st.session_state["fast_test_mode"] = credential_config.fast_test_mode
    else:
        # Default values when no authentication is active
        st.session_state["dev_mode"] = False
        st.session_state["fast_test_mode"] = False
    
    # CHECK CAPACITY AND REGISTER SESSION (except for dev mode)
    if DEBUG_MODE:
        print(f"🔧 DEBUG: Capacity check - presence={presence is not None}, credential_config={credential_config is not None}, dev_mode={credential_config.dev_mode if credential_config else 'N/A'}")
    
    if presence and credential_config and not credential_config.dev_mode:
        session_info = sm.get_session_info()
        if DEBUG_MODE:
            print(f"🔧 DEBUG: Checking session {session_info['session_id']}")
        
        # Check if session already exists in database
        existing_session = presence.get_session_info(session_info["session_id"])
        if DEBUG_MODE:
            print(f"🔧 DEBUG: Existing session in DB: {existing_session is not None}")
        
        if not existing_session:
            # New session - check capacity before registering
            if DEBUG_MODE:
                print(f"🔧 DEBUG: New session - checking capacity...")
            can_start, message = presence.can_start_interview()
            if DEBUG_MODE:
                print(f"🔧 DEBUG: Capacity check result: can_start={can_start}, message={message}")
            
            if not can_start:
                # Platform at capacity - show message and stop
                st.error("🚦 **Platform Currently at Capacity**")
                st.warning(message)
                
                active_count = presence.count_active_interviews()
                active_sessions = presence.count_active_sessions()
                
                st.info(
                    f"**Current Status:**\n\n"
                    f"- Active interviews: {active_count}/{presence.max_concurrent}\n"
                    f"- Total active sessions: {active_sessions}\n\n"
                    f"**What happened:**\n"
                    f"You logged in successfully, but all interview slots are currently occupied.\n\n"
                    f"**Next steps:**\n"
                    f"1. Click the **Logout** button in the sidebar\n"
                    f"2. Wait 2-5 minutes for a slot to open\n"
                    f"3. Try logging in again\n\n"
                    f"💡 Active interviews typically complete within 20-30 minutes."
                )
                
                st.stop()
            else:
                # Capacity available - register the session now
                presence.mark_session_started(
                    session_id=session_info["session_id"],
                    user_id=credential_config.username,
                    language_code=language_code
                )
                print(f"📡 Session {session_info['session_id']} registered in presence tracker")
                print(f"✅ Capacity check passed: {message}")
                st.session_state["session_registered"] = True  # Mark session as registered
        else:
            print(f"📡 Session {session_info['session_id']} already registered, skipping capacity check")
            st.session_state["session_registered"] = True  # Already registered
    elif presence and credential_config and credential_config.dev_mode:
        # Dev mode - always register session without capacity check
        session_info = sm.get_session_info()
        existing_session = presence.get_session_info(session_info["session_id"])
        if not existing_session:
            presence.mark_session_started(
                session_id=session_info["session_id"],
                user_id=credential_config.username,
                language_code=language_code
            )
            print(f"📡 [DEV MODE] Session {session_info['session_id']} registered in presence tracker")
            st.session_state["session_registered"] = True  # Mark dev session as registered

# ───────────────────────────────────────────────────────────────
# Globals & constants
# ───────────────────────────────────────────────────────────────
DEV_MODE: bool = st.session_state.get("dev_mode", False)
FAST_TEST_MODE: bool = st.session_state.get("fast_test_mode", False)
TOPIC: str = config.course.course_title
API_KEY: str = st.secrets["google"]["api_key"]

# ── Load Course Content (slides + transcription) ───────────────
# This loads the actual course materials that are the same for all users
from Gemini_UI import load_course_content
if not st.session_state.get("course_content_loaded", False):
    load_course_content()  # Loads slides and transcription from course files
    st.session_state["course_content_loaded"] = True
    if DEV_MODE:
        print(f"📚 Course content loaded: {len(st.session_state.get('exported_images', []))} slides")

# ── Inject JavaScript Heartbeat ────────────────────────────────
# This runs on every page load and keeps session active in Supabase
# ONLY inject heartbeat if session was successfully registered
if presence and credential_config and "language_code" in st.session_state and st.session_state.get("session_registered", False):
    session_info = sm.get_session_info()
    current_page = st.session_state.get("current_page", "home")
    print(f"📡 Injecting heartbeat for session {session_info['session_id']}, user {credential_config.username}, page {current_page}")
    presence.inject_heartbeat(
        session_id=session_info["session_id"],
        user_id=credential_config.username,
        language_code=st.session_state["language_code"],
        current_page=current_page
    )
else:
    print(f"⚠️ Heartbeat NOT injected - presence: {presence is not None}, credential: {credential_config is not None}, language: {'language_code' in st.session_state}")

# ── Scroll to Top on Page Navigation ──────────────────────────
# Only scroll when user actually navigates to a different page, not on every rerun
current_page = st.session_state.get("current_page", "home")
previous_page = st.session_state.get("previous_page", None)

if current_page != previous_page:
    # Page has changed - scroll to top
    st.markdown(
        """
        <script>
            window.scrollTo(0, 0);
        </script>
        """,
        unsafe_allow_html=True
    )
    # Update previous page tracker
    st.session_state["previous_page"] = current_page
    if DEBUG_MODE:
        print(f"🔧 DEBUG: Page changed from '{previous_page}' to '{current_page}' - scrolling to top")

# Yiman = AIzaSyCdNS08cjO_lvj35Ytvs8szbUmeAdo4aIA
# Furkan Ali = AIzaSyArkmZSrZaeWQSfL9CFkQ0jXaEe4D9sMEQ

# ───────────────────────────────────────────────────────────────
# Helper functions
# ───────────────────────────────────────────────────────────────

def current_language() -> str:
    """Get current language code from session state."""
    return st.session_state.get("language_code", "en")

def navigate_to(page: str) -> None:
    """Client‑side router with prerequisite checks."""

    # DEV MODE GOD MODE: Skip all checks
    if DEV_MODE:
        page_dump(Path(sm.session_dir))
        page_timer_start(page)
        st.session_state.current_page = page
        st.rerun()
        return

    allowed = False
    if page == "profile_survey":
        # Require consent before accessing profile survey
        allowed = st.session_state.get("consent_given", False)
        if not allowed:
            st.warning("Please read the study information and give your consent on the Home page first.")
    elif page == "learning":
        allowed = st.session_state.profile_completed
        if not allowed:
            st.warning(config.ui_text.warning_complete_profile)
    elif page == "knowledge_test":
        allowed = (
            st.session_state.profile_completed and st.session_state.learning_completed
        )
        if not allowed:
            st.warning(
                "Please finish the profile survey and explore the learning content first."
            )
    elif page == "ueq_survey":
        allowed = (
            st.session_state.profile_completed
            and st.session_state.learning_completed
            and st.session_state.test_completed
        )
        if not allowed:
            st.warning("Please finish all previous components before the UEQ survey.")
    elif page == "completion":
        # Completion page - only accessible if everything is done
        allowed = (
            st.session_state.profile_completed
            and st.session_state.learning_completed
            and st.session_state.test_completed
            and st.session_state.ueq_completed
        )
        if not allowed:
            st.warning("Please complete all interview components first.")
    elif page == "home":
        allowed = True

    if allowed:
        page_dump(Path(sm.session_dir))
        page_timer_start(page)
        st.session_state.current_page  = page
        st.rerun()


# ───────────────────────────────────────────────────────────────
# Sidebar navigation
# ───────────────────────────────────────────────────────────────

st.sidebar.title("Navigation")

# DEV MODE INDICATOR
if DEV_MODE:
    st.sidebar.warning("🔧 **DEV MODE ACTIVE**\n\nGod Mode: All pages unlocked")
    if FAST_TEST_MODE:
        st.sidebar.info("⚡ Fast Test Mode: Mock data loaded")

nav_items = [
    ("Home", "home", True),
    (config.ui_text.nav_profile, "profile_survey", st.session_state.get("profile_completed", False)),
    (f"{LABEL}", "learning", st.session_state.get("learning_completed", False)),
    (config.ui_text.nav_knowledge, "knowledge_test", st.session_state.get("test_completed", False)),
    (config.ui_text.nav_ueq, "ueq_survey", st.session_state.get("ueq_completed", False)),
]

# Add pilot smoke test page for dev mode only
if DEV_MODE:
    nav_items.append(("🧪 Pilot Smoke Test", "pilot_smoke_test", False))

for title, target, done in nav_items:
    prefix = "✅ " if done else "⬜ "
    # Disable navigation for non-dev users if requirements not met
    if not DEV_MODE:
        # Check if button should be disabled
        button_disabled = False
        if target == "profile_survey" and not st.session_state.get("consent_given", False):
            button_disabled = True
        elif target == "learning" and not st.session_state.get("profile_completed", False):
            button_disabled = True
        elif target == "knowledge_test" and not (st.session_state.get("profile_completed", False) and st.session_state.get("learning_completed", False)):
            button_disabled = True
        elif target == "ueq_survey" and not (st.session_state.get("profile_completed", False) and st.session_state.get("learning_completed", False) and st.session_state.get("test_completed", False)):
            button_disabled = True
        
        if st.sidebar.button(f"{prefix}{title}", disabled=button_disabled):
            navigate_to(target)
            st.rerun()
    else:
        # Dev mode - all buttons enabled
        if st.sidebar.button(f"{prefix}{title}"):
            navigate_to(target)
            st.rerun()

# Session info after navigation (no separator for clean UI)
st.sidebar.subheader("Session Info")
st.sidebar.info(f"**User:** {credential_config.description}")

# Show language selector for dev mode or static language for participants
if DEV_MODE:
    from config import get_supported_languages
    languages = get_supported_languages()
    
    # Get current language from session state if available
    current_lang = st.session_state.get("language_code", credential_config.language_code)
    current_index = list(languages.keys()).index(current_lang) if current_lang in languages else 0
    
    selected_lang = st.sidebar.selectbox(
        "🔧 Language (Dev Mode)",
        options=list(languages.keys()),
        format_func=lambda code: f"{languages[code]['display_name']} ({code})",
        index=current_index,
        key="dev_language_selector"
    )
    
    # Update session state if language changed
    if selected_lang != st.session_state.get("language_code"):
        st.session_state["language_code"] = selected_lang
        st.rerun()
else:
    # For participants, show fixed language
    st.sidebar.info(f"**Language:** {credential_config.language_code.upper()}")

if st.sidebar.button("Logout", type="secondary"):
    from authentication import get_auth_manager
    auth_manager = get_auth_manager()
    auth_manager.logout()
    st.rerun()

# ───────────────────────────────────────────────────────────────
# Page logic – each branch keeps the original behaviour
# ───────────────────────────────────────────────────────────────

if st.session_state.current_page == "home":
    # ------------------------------------------------------------------
    # HOME  ─ study intro
    # ------------------------------------------------------------------
    # Show capacity warning at entry
    from capacity_manager import get_capacity_manager
    capacity_mgr = get_capacity_manager()
    capacity_mgr.show_capacity_warning(location="home")
    
    st.title(f"{config.platform.learning_section_name} Platform")
    
    st.markdown(
        f"""
### Welcome – what this session is about

**Your Study Language: {language_names.get(current_language(), 'English')}**

You are taking part in our KU Leuven study on **language effects in AI-assisted learning**.
We are investigating whether the language used when learning with AI assistants affects how well students understand the material.

In today's session, you will learn about **{TOPIC}** using an AI assistant in **{language_names.get(current_language(), 'English')}**.

**Important**: Please use **only {language_names.get(current_language(), 'English')}** when interacting with the AI assistant. 
This ensures valid comparison across study participants.

---
#### What will happen? – step by step  
| Step | What you do | Time | What you provide |
|------|-------------|------|------------------|
| 1 | Read & sign the digital consent form | ≈ 5 min | e‑signature |
| 2 | **Student Profile Survey** | ≈ 10 min | demographics, language skills, AI knowledge |
| 3 | **{LABEL}** using LLM | ≈ 25 min | interact with AI assistant |
| 4 | **Knowledge Test** | ≈ 10 min | answers to 8 quiz items |
| 5 | **User‑Experience Questionnaire** | ≈ 10 min | 26 quick ratings |
| 6 | Short feedback | ≈ 10 min | feedback |

*Total time*: **~ 70 minutes**

---
#### Your role  
* Work through the steps **in the order shown** (use the sidebar).  
* Give honest answers – there are no right or wrong responses.  
* **Ask questions any time** – just speak to the facilitator.

---
#### Why we record your data  
We log your interactions with the AI assistant to analyze learning effectiveness across different languages.  
Your identity is pseudonymized; you may stop at any moment without penalt#### Research Focus: Language in AI Learning
You have been assigned to use the AI assistant in **{language_names.get(current_language(), 'English')}**.

**What this means**:  
• All AI responses will be in {language_names.get(current_language(), 'English')}  
• You should ask questions and chat with the AI in {language_names.get(current_language(), 'English')}  
• We are comparing learning outcomes across different language groups

**Your role**: Use the AI naturally to learn the material. There are no minimum interactions required—explore as much or as little as helpful for your learning.

---
When you are ready, click **"Start the Student Profile Survey"** below.  
Thank you for helping us understand how language affects AI-assisted learning!
""")
    # --- GDPR / informed-consent box ---------------------------------
    with st.expander("Study information & GDPR (click to read)"):
        st.markdown(
            "**Your key rights in 2 lines**  \n"
            "• You may stop at any moment without consequences.  \n"
            "• Pseudonymised study data are used **only** for academic research."
        )

        # Single download button for combined document
        with open(CONSENT_PDF, "rb") as f:
            st.download_button(
                "Download Participant Information and Consent Form (PDF)",
                f,
                file_name=CONSENT_PDF.name,
                type="primary"
            )
    # one-line checkbox underneath the expander (outside the `with` block!)
    consent_ok = st.checkbox(
        "I have read the documents above and **give my consent** to participate.",
        key="consent_checkbox"
    )
    st.session_state["consent_given"] = consent_ok

    # ─── write a one-time log entry ─────────────────────────────────
    if consent_ok and not st.session_state.get("consent_logged"):
        get_learning_logger().log_interaction(
            interaction_type="consent",
            user_input="checkbox ticked",
            system_response="(none)",
            metadata={}
        )
        st.session_state["consent_logged"] = True
        
        # Sync consent to analytics database
        from analytics_syncer import get_analytics_syncer
        analytics = get_analytics_syncer()
        if analytics:
            sm = get_session_manager()
            session_info = sm.get_session_info()
            analytics.update_consent(session_info["session_id"])

    # — facilitator: choose study condition --------------------------------
#    if "condition_chosen" not in st.session_state:
#        st.sidebar.subheader("⚙️ Study condition (facilitator only)")
#        cond = st.sidebar.radio(
#            "Show explanations as …", ["personalised", "generic"], key="cond_radio"
#        )
#        if st.sidebar.button("Assign & start"):

#            cond_flag = (cond == "personalised")          # True / False
#            cond_name = "personalised" if cond_flag else "generic"

#            st.session_state["use_personalisation"] = cond_flag
#            st.session_state["condition_chosen"] = True

            # --- NEW ----------------------------------------------------------
#            sm.condition = cond_name                     # <- update existing SessionManager
            # ------------------------------------------------------------------
#
#            st.rerun()


    # — fast test helper (mock profile only) --------------------------------
    # Course content (slides + transcription) is loaded for everyone
    # Fast test mode just provides a mock profile to skip the survey
    if FAST_TEST_MODE and not st.session_state.get("fast_test_setup_completed", False):
        if DEBUG_MODE:
            print(f"🔧 DEBUG: Setting up fast test mode - loading mock profile")
        
        sample_path = Path(__file__).parent / "uploads" / "profile" / "Test_User_profile.txt" 
        if sample_path.exists():
            profile_txt = sample_path.read_text(encoding="utf-8")
            st.session_state.profile_text = profile_txt
            st.session_state.profile_dict = parse_detailed_student_profile(profile_txt)
            if DEBUG_MODE:
                print("🔧 DEBUG: Fast test mode mock profile loaded")
        else:
            print(f"⚠️ WARNING: Mock profile not found at {sample_path}")

        st.session_state["fast_test_setup_completed"] = True
        st.rerun()

    if st.button(
        "Start Student Profile Survey",
        use_container_width=True,
        disabled=not st.session_state.get("consent_given", False),
    ):
        if st.session_state.get("consent_given", False):
            navigate_to("profile_survey")
        else:
            st.warning("Please give your consent first.")

# ------------------------------------------------------------------------
# PROFILE SURVEY  – writes profile text & dict to session_state
# ------------------------------------------------------------------------
elif st.session_state.current_page == "profile_survey":
    import importlib
    import testui_profilesurvey
    importlib.reload(testui_profilesurvey)

    # The module handles its own review display
    if st.session_state.get("show_review", False):
        st.session_state.profile_completed = True
        st.markdown("---")
        st.success(f"✅ Profile saved – proceed to the {LABEL} section.")
        if st.button(f"Continue to {LABEL}", use_container_width=True):
            navigate_to("learning")

# ------------------------------------------------------------------------
# AI LEARNING ASSISTANT  – Gemini AI assistant UI
# ------------------------------------------------------------------------
elif st.session_state.current_page == "learning":
    if not st.session_state.profile_completed and not DEV_MODE:
        st.warning("Please complete the Student Profile Survey first.")
        if st.button("Go to Student Profile Survey"):
            navigate_to("profile_survey")
    else:
        # Capacity already checked at login, just mark interview as started
        if presence and not st.session_state.get("interview_access_granted", False):
            st.session_state["interview_access_granted"] = True
            if DEV_MODE:
                st.success("✅ Access granted - interview session active")
        
        # --- header ------------------------------------------------------
        st.title(f"AI Learning Assistant")
        
        # Create main column layout (content on left, minimal on right)
        col_main, col_spacer = st.columns([4, 1])
        
        # Row 1: Explanation text (instructions)
        with col_main:
            
            st.markdown(
                f"""
            ### How to Use This Section

            You can interact with the AI assistant in two ways:

            1. **Ask about specific slides**: Click "Explain this slide" below any slide to get an explanation
            2. **Ask your own questions**: Type questions in the chat box about any concept from the material

            The AI assistant has access to all {config.course.total_slides} slides and the full lecture transcription**.

            **Expected interaction**: Please actively use the AI chat to explore concepts, ask clarifying questions, and deepen your understanding. This is the core learning experience we're studying.

            **Remember: Use {language_names.get(current_language(), 'English')} for all AI interactions**  
                            
            You are learning in **{language_names.get(current_language(), 'English')}** as part of our language study. 
            Please type your questions and read AI responses in this language.
            """
            )
        
        with col_spacer:
            st.write("")  # Minimal content

        #genai.configure(api_key=API_KEY)
        client = genai.Client(  api_key=API_KEY# picks up GEMINI_API_KEY env automatically
            # http_options={"api_version": "v1alpha"}  # optional if you need early features
        )

        # Initialize Gemini chat only once per session
        if DEBUG_MODE:
            print("🔧 DEBUG: About to check gemini_chat initialization")
        if "gemini_chat" not in st.session_state:
            if DEBUG_MODE:
                print("🔧 DEBUG: Creating new Gemini chat session")
            st.session_state.gemini_chat = client.chats.create(
                model="gemini-2.5-flash",
                history=[]
            )
            st.session_state.gemini_chat_initialized = False
            if DEBUG_MODE:
                print("🔧 DEBUG: Gemini chat session created")

        # Send base context only once per session  
        if not st.session_state.get("gemini_chat_initialized", False):
            if DEBUG_MODE:
                print("🔧 DEBUG: About to send base context to Gemini")

            base_ctx = make_base_context(
                language_code=current_language()
            )
            if DEBUG_MODE:
                print("🔧 DEBUG: Base context created, sending to Gemini...")

            st.session_state.gemini_chat.send_message(json.dumps(base_ctx))
            st.session_state.gemini_chat_initialized = True
            if DEBUG_MODE:
                print("🔧 DEBUG: Base context sent successfully")

            get_learning_logger().log_interaction(
                interaction_type="prime_context",
                user_input=base_ctx,           # already a small dict
                system_response="(no reply – prime only)",
                metadata={"language_code": current_language()},
            )

            #st.session_state.messages.append(
            #    {"role": "system", "content": json.dumps(base_ctx, indent=2)}
            #)

        
        #        # Sidebar uploads -------------------------------------------------
        #        st.sidebar.header("Input Files")
        #        audio_up = st.sidebar.file_uploader(
        #            "Upload Audio File", ["wav", "mp3", "ogg", "flac", "m4a", "mp4"]
        #        )
        #        ppt_up = st.sidebar.file_uploader("Upload PPT", ["ppt", "pptx"])
        #        st.sidebar.success("✅ Profile loaded from survey responses")

        

        if DEV_MODE:
            if DEBUG_MODE:
                print("🔧 DEBUG: Starting dev mode interaction tracking")
            # Live interaction tracking for development - TEMPORARILY DISABLED FOR DEBUGGING
            try:
                if DEBUG_MODE:
                    print("🔧 DEBUG: About to call get_interaction_counts()")
                # TEMPORARILY COMMENTED OUT TO TEST IF THIS IS THE HANG POINT
                # interaction_counts = get_learning_logger().get_interaction_counts()
                interaction_counts = {"slide_explanations": 0, "manual_chat": 0, "total_user_interactions": 0}
                if DEBUG_MODE:
                    print("🔧 DEBUG: get_interaction_counts() completed successfully (using mock data)")
                
                st.sidebar.info(
                    f"{len(get_learning_logger().log_entries) if hasattr(get_learning_logger(), 'log_entries') else 0} interactions buffered"
                )
                st.sidebar.metric("Slide Explanations", interaction_counts["slide_explanations"])
                st.sidebar.metric("Manual Chat", interaction_counts["manual_chat"]) 
                st.sidebar.metric("Total User Interactions", interaction_counts["total_user_interactions"])
                print("🔧 DEBUG: Dev mode metrics displayed successfully")
            except Exception as e:
                print(f"🔧 DEBUG: Error in dev mode interaction tracking: {e}")
                st.sidebar.error(f"Error loading interaction metrics: {e}")
            
            # Debug toggles ---------------------------------------------------
            if st.checkbox("Show Debug Logs"):
                st.subheader("Debug Logs")
                for l in st.session_state.get("debug_logs", []):
                    st.text(l)
            if st.checkbox("Show Parsed Profile"):
                st.json(st.session_state.profile_dict)

        # File upload section (controlled by upload_enabled flag) -------------
        if credential_config.upload_enabled:
            print("🔧 DEBUG: Starting file upload section (upload_enabled=True)")
            # Sidebar: Input Files
            st.sidebar.header("Input Files")
            audio_up = st.sidebar.file_uploader("Upload Audio File", ["wav", "mp3", "ogg", "flac", "m4a", "mp4"])
            ppt_up   = st.sidebar.file_uploader("Upload PPT", ["ppt", "pptx"])
            print("🔧 DEBUG: File upload section completed")
            
            # Handle audio upload -------------------------------------------
            if audio_up is not None:
                a_path = UPLOAD_DIR_AUDIO / audio_up.name
                a_path.write_bytes(audio_up.getbuffer())
                st.sidebar.success(f"Saved {audio_up.name}")
                if st.sidebar.button("Transcribe Audio"):
                    st.session_state.transcription_text = transcribe_audio_from_file(a_path)
                    st.sidebar.success("Transcription complete!")

            # Handle PPT upload ---------------------------------------------
            if ppt_up is not None:
                p_path = UPLOAD_DIR_PPT / ppt_up.name
                p_path.write_bytes(ppt_up.getbuffer())
                st.sidebar.success(f"Saved {ppt_up.name}")
                if st.sidebar.button("Process PPT"):
                    st.session_state.exported_images = process_ppt_file(p_path)
                    st.sidebar.success(
                        f"Exported {len(st.session_state.exported_images)} slides"
                )
        else:
            # No upload access: Use pre-processed course content
            print("🔧 DEBUG: Starting no-upload mode file loading")
            st.sidebar.header("Course Content")
            st.sidebar.info(f"Ask questions or request explanations about any concept")
            
            # Load pre-transcribed course content (cached)
            if DEV_MODE:
                print("🔧 DEBUG: About to check transcription loading")
            if not st.session_state.get("transcription_text"):
                if DEV_MODE:
                    print("🔧 DEBUG: Loading transcription file")
                transcription_file = TRANSCRIPTION_DIR / config.course.transcription_filename
                if transcription_file.exists():
                    try:
                        st.session_state.transcription_text = transcription_file.read_text(encoding="utf-8")
                        st.session_state.transcription_loaded = True
                        if DEV_MODE:
                            st.sidebar.success(f"✅ Transcription loaded ({len(st.session_state.transcription_text):,} chars)")
                            print("🔧 DEBUG: Transcription loaded successfully")
                    except Exception as e:
                        if DEV_MODE:
                            print(f"🔧 DEBUG: Error loading transcription: {e}")
                            st.sidebar.error(f"❌ Error loading transcription: {e}")
                        st.session_state.transcription_loaded = False
                else:
                    if DEV_MODE:
                        print("🔧 DEBUG: Transcription file not found")
                        st.sidebar.error(f"❌ {config.course.course_title} transcription not found")
                    st.session_state.transcription_loaded = False
            elif st.session_state.get("transcription_loaded", False):
                if DEV_MODE:
                    print("🔧 DEBUG: Transcription already loaded")
                    st.sidebar.success(f"✅ Transcription loaded ({len(st.session_state.transcription_text):,} chars)")
            
            # Load pre-processed course slides (cached)
            if not st.session_state.get("exported_images"):
                slides_dir = UPLOAD_DIR_PPT / config.course.slides_directory
                if slides_dir.exists():
                    slide_files = list(slides_dir.glob("Slide_* Genetics of Cancer.jpg"))
                    if slide_files:
                        # Sort numerically by extracting the number from the filename
                        def extract_slide_number(path):
                            import re
                            match = re.search(r'Slide_(\d+)', path.name)
                            return int(match.group(1)) if match else 0
                        
                        slide_files = sorted(slide_files, key=extract_slide_number)
                        st.session_state.exported_images = slide_files
                        st.session_state.slides_loaded = True
                        if DEV_MODE:
                            st.sidebar.success(f"✅ {len(slide_files)} slides loaded")
                    else:
                        if DEV_MODE:
                            st.sidebar.error("❌ No slide images found in slides directory")
                        st.session_state.slides_loaded = False
                else:
                    if DEV_MODE:
                        st.sidebar.error("❌ Slides directory not found")
                    st.session_state.slides_loaded = False
            elif st.session_state.get("slides_loaded", False):
                if DEV_MODE:
                    st.sidebar.success(f"✅ {len(st.session_state.exported_images)} slides loaded")




        # Slide selector --------------------------------------------------
        if st.session_state.exported_images:
            # Since files are already sorted numerically, create simple sequential labels
            slides = [f"Slide {i+1}" for i in range(len(st.session_state.exported_images))]
            
            selected_slide = st.sidebar.selectbox(
                "Select a Slide", slides, key="selected_slide"
            )
            
            # Show current slide filename for debugging
            if selected_slide:
                try:
                    # Extract index from the dropdown selection (Slide 1 = index 0, etc.)
                    slide_idx = int(selected_slide.split()[1]) - 1
                    if 0 <= slide_idx < len(st.session_state.exported_images):
                        current_file = st.session_state.exported_images[slide_idx].name
                        st.sidebar.caption(f"File: {current_file}")
                        
                        # Extract actual slide number from filename for verification
                        import re
                        match = re.search(r'Slide_(\d+)', current_file)
                        if match:
                            actual_slide_num = match.group(1)
                            expected_slide_num = str(slide_idx + 1)
                            if actual_slide_num != expected_slide_num:
                                st.sidebar.warning(f"⚠️ Mismatch: Selected {selected_slide} but showing Slide_{actual_slide_num}")
                except (ValueError, IndexError):
                    st.sidebar.error("Error parsing slide selection")
        else:
            selected_slide = None

        # Row 2: Chat messages, input, and explain button
        col_main, col_spacer = st.columns([4, 1])
        
        with col_main:
            st.header("LLM Chat")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"], unsafe_allow_html=True)

            # Chat input section (placed right after messages) ---------------------------------------
            user_chat = st.chat_input("Ask a follow‑up question …")
            if user_chat:
                payload = json.dumps({
                    **make_base_context(
                        language_code=current_language()
                    ),
                    "UserQuestion": user_chat
                })

                #reply = st.session_state.gemini_chat.send_message(payload)
                
                # Create thinking config step by step for debugging
                thinking_config = types.ThinkingConfig(includeThoughts=True)
                content_config = types.GenerateContentConfig(thinking_config=thinking_config)
                
                reply = st.session_state.gemini_chat.send_message(
                    payload,
                    config=content_config
                )
                
                st.session_state.messages.extend(
                    [
                        {"role": "user", "content": user_chat},
                        {"role": "assistant", "content": reply.text},
                    ]
                )
                get_learning_logger().log_interaction(
                    interaction_type="chat",
                    user_input=user_chat,
                    system_response=reply.text,
                    metadata={"slide": None, "language_code": current_language()},
                )
                st.rerun()

            # Generate explanation button (placed after chat input) --------------------------------
            ready = (
                st.session_state.transcription_text
                and st.session_state.exported_images
                and st.session_state.profile_completed  # Just check if they did the survey
            )
            if ready and selected_slide and st.button(f"Explain this slide"):
                s_idx = int(selected_slide.split()[1]) - 1
                img = Image.open(st.session_state.exported_images[s_idx])

                prompt_json = build_prompt(
                    f"Content from {selected_slide} (see slide image).",
                    st.session_state.transcription_text,
                    selected_slide,
                    language_code=current_language()
                )
                debug_log(prompt_json)

                # Create thinking config step by step for debugging
                thinking_config = types.ThinkingConfig(includeThoughts=True)
                content_config = types.GenerateContentConfig(thinking_config=thinking_config)
                
                reply = st.session_state.gemini_chat.send_message([img, prompt_json], config=content_config)

                summary = create_summary_prompt(selected_slide)
                st.session_state.messages.extend(
                    [
                        {"role": "user", "content": summary},
                        {"role": "assistant", "content": reply.text},
                    ]
                )
                st.session_state.learning_completed = True

                # Log & persist ----------------------------------------
                ll = get_learning_logger()
                ll.log_interaction(
                    interaction_type="slide_explanation",
                    user_input=prompt_json,
                    system_response=reply.text,
                    metadata={
                        "slide": selected_slide,
                        "language_code": current_language(),
                        "session_id": ll.session_manager.session_id,
                    },
                )
                # Flush logs at learning completion milestone
                ll.save_logs(force=True)
                st.rerun()

            if not ready:
                # Check what's missing and provide specific guidance
                missing_items = []
                if not st.session_state.transcription_text:
                    missing_items.append("audio transcription")
                if not st.session_state.exported_images:
                    missing_items.append("lecture slides") 
                if not st.session_state.profile_completed:
                    missing_items.append("student profile")
                
                if missing_items:
                    if "student profile" in missing_items and len(missing_items) == 1:
                        st.info("Complete the Student Profile Survey first to enable explanation generation.")
                    else:
                        if DEV_MODE:
                            st.info(f"⏳ Loading course content... Missing: {', '.join(missing_items)}")
                        else:
                            st.info("⏳ Loading course content...")
                else:
                    st.info("⏳ Preparing explanation generator...")
        
        with col_spacer:
            st.write("")  # Minimal content

        # Row 3: Preview files section
        col_main, col_spacer = st.columns([4, 1])
        
        with col_main:
            st.markdown("---")
            st.header("Preview Files")
            
            if st.session_state.exported_images and selected_slide:
                idx = int(selected_slide.split()[1]) - 1
                
                from pathlib import Path
                slide_path = st.session_state.exported_images[idx]
                
                # Convert to Path object if it isn't already
                if not isinstance(slide_path, Path):
                    slide_path = Path(slide_path)
                
                # Check if file exists
                if not slide_path.exists():
                    if DEV_MODE:
                        st.error(f"Slide not found: {slide_path.resolve()}")
                        st.write(f"Current working directory: {Path.cwd()}")
                        st.write(f"Looking for: {slide_path}")
                    else:
                        st.error("Slide content is currently unavailable.")
                    st.stop()
                
                try:
                    # Use PIL to open and verify the image
                    img = Image.open(slide_path)
                    caption = str(slide_path.name) if DEV_MODE else None
                    st.image(img, caption=caption, use_column_width=True)
                except Exception as e:
                    st.exception(e)
                    st.stop()

            # Video preview functionality
            video_path = UPLOAD_DIR_VIDEO / config.course.video_filename
            if video_path.exists():
                st.subheader("Lecture Recording")
                try:
                    with open(video_path, "rb") as video_file:
                        video_bytes = video_file.read()
                    st.video(video_bytes)
                    if DEV_MODE:
                        st.caption(f"{config.course.course_title} - Full Lecture")
                except Exception as e:
                    if DEV_MODE:
                        st.error(f"Error loading video: {e}")
                    else:
                        st.warning("Video content is temporarily unavailable.")
            else:
                st.info("Lecture recording will appear here when available")
        
        with col_spacer:
            st.write("")  # Minimal content

        # Navigation buttons ---------------------------------------------
        st.markdown("---")
        col_p, col_n = st.columns(2)
        with col_p:
            if st.button("Previous: Student Profile"):
                navigate_to("profile_survey")
        with col_n:
            if st.session_state.learning_completed:
                if st.button("Next: Knowledge Test"):
                    log_path = get_learning_logger().save_logs(force=True)
                    st.session_state["learning_log_file"] = log_path
                    navigate_to("knowledge_test")
            else:
                st.button("Next: Knowledge Test", disabled=True)
                st.info("Generate at least one explanation before proceeding.")

# ------------------------------------------------------------------------
# KNOWLEDGE TEST  – simple wrapper around *testui_knowledgetest*
# ------------------------------------------------------------------------
elif st.session_state.current_page == "knowledge_test":
    import importlib

    import testui_knowledgetest

    importlib.reload(testui_knowledgetest)

    if not st.session_state.profile_completed and not DEV_MODE:
        st.warning("Please complete the Student Profile Survey first.")
        if st.button("Go to Student Profile Survey"):
            navigate_to("profile_survey")
    elif not st.session_state.learning_completed and not DEV_MODE:
        st.warning(f"Please complete the {LABEL.lower()} section first.")
        if st.button(f"Go to {LABEL} Learning"):
            navigate_to("learning")
    else:
        if "score" in st.session_state:
            st.session_state.test_completed = True

        st.markdown("---")
        prev, nxt = st.columns(2)
        with prev:
            if st.button(f"Previous: {LABEL}"):
                navigate_to("learning")
        with nxt:
            if st.session_state.test_completed:
                if st.button("Next: User Experience Survey"):
                    navigate_to("ueq_survey")
            else:
                st.button("Next: User Experience Survey", disabled=True)
                st.info("Complete the Knowledge Test first.")

# ------------------------------------------------------------------------
# UEQ SURVEY  – wrapper around *testui_ueqsurvey*
# ------------------------------------------------------------------------
elif st.session_state.current_page == "ueq_survey":
    import importlib

    import testui_ueqsurvey

    importlib.reload(testui_ueqsurvey)

    if not st.session_state.profile_completed and not DEV_MODE:
        st.warning("Please complete the Student Profile Survey first.")
        if st.button("Go to Student Profile Survey"):
            navigate_to("profile_survey")
    elif not st.session_state.learning_completed and not DEV_MODE:
        st.warning(f"Please complete the {LABEL} Learning section first.")
        if st.button(f"Go to {LABEL} Learning"):
            navigate_to("learning")
    elif not st.session_state.test_completed and not DEV_MODE:
        st.warning("Please complete the Knowledge Test first.")
        if st.button("Go to Knowledge Test"):
            navigate_to("knowledge_test")
    else:
        # mark as completed once at least one answer present
        if any(
            resp.get("value") is not None
            for resp in st.session_state.get("responses", {}).values()
        ):
            st.session_state.ueq_completed = True

        st.markdown("---")
        col_b, col_f = st.columns(2)
        with col_b:
            if st.button("Previous: Knowledge Test"):
                navigate_to("knowledge_test")
        with col_f:
            if st.button("Finish"):
                # Simple completion - just navigate to thank you page
                navigate_to("completion")

# ------------------------------------------------------------------------
# COMPLETION PAGE  – Thank you page with upload processing
# ------------------------------------------------------------------------
elif st.session_state.current_page == "completion":
    # Clean completion page with upload processing in background
    st.title("Interview Complete!")
    
    st.markdown(f"""
    ## {config.ui_text.completion_thanks}
    
    You have successfully completed all components of the {config.course.course_title} learning interview:
    
    ✅ **{config.ui_text.nav_profile}**  
    ✅ **{config.platform.learning_section_name}**  
    ✅ **{config.ui_text.nav_knowledge}**  
    ✅ **{config.ui_text.nav_ueq}**
    
    ---
    
    ### What happens next?
    
    Your responses are being processed and uploaded securely for research analysis. This helps us improve AI-powered learning experiences for future students.
    
    **Research Impact**: Your participation contributes to understanding whether language choice in AI-assisted learning creates educational inequalities, helping ensure fair access to AI-powered education globally.
    
    **Data Security**: All your responses are pseudonymized and stored securely according to GDPR guidelines.
    """)
    
    st.markdown("""
    ### Next Steps
    
    Your participation is complete! Thank you for your time and dedication to this research.
    
    If you have any questions about the study or would like to receive information about the results, please contact the research team. Your contribution helps us understand how language affects AI-assisted learning.
    
    Thank you for helping advance educational equity in AI-powered learning!
    """)
    
    st.markdown("---")
    
    # Process uploads in background (only once)
    if not st.session_state.get("completion_processed", False):
        st.session_state["completion_processed"] = True
        
        print(f"\n{'='*60}")
        print(f"📦 COMPLETION PAGE: Starting upload process at {datetime.now()}")
        print(f"{'='*60}")
        
        # Show processing status
        with st.spinner("Processing your responses..."):
            try:
                sm = get_session_manager()
                session_info = sm.get_session_info()
                print(f"📋 Session ID: {session_info['session_id']}")
                print(f"📁 Session directory: {sm.session_dir}")
                
                # Flush any remaining logs before final analytics
                print(f"💾 Flushing learning logs...")
                ll = get_learning_logger()
                ll.save_logs(force=True)
                
                # Generate final analytics
                print(f"📊 Generating final analytics...")
                final_analytics_path = sm.create_final_analytics()
                print(f"✅ Analytics saved to: {final_analytics_path}")
                
                # Upload to Supabase
                print(f"☁️ Initializing Supabase storage...")
                from supabase_storage import get_supabase_storage
                storage = get_supabase_storage()
                print(f"✅ Storage initialized, connected: {storage.connected}")
                
                session_id = session_info["session_id"]
                
                # Upload all session files
                print(f"🚀 Calling storage.upload_session_files()...")
                success = storage.upload_session_files(sm, DEV_MODE)
                print(f"📤 Upload result: {'SUCCESS' if success else 'FAILED'}")
                
                # Mark session as completed in presence tracker
                if presence:
                    session_info = sm.get_session_info()
                    presence.mark_session_completed(session_info["session_id"])
                    print(f"📍 Session {session_info['session_id']} marked as completed")
                
                # Sync learning log and page durations to analytics database
                from analytics_syncer import get_analytics_syncer
                from pathlib import Path
                analytics = get_analytics_syncer()
                if analytics:
                    # Sync learning log
                    learning_log_path = Path(sm.learning_logs_dir) / sorted(
                        [f for f in os.listdir(sm.learning_logs_dir) if f.startswith("learning_log_")]
                    )[-1] if os.listdir(sm.learning_logs_dir) else None
                    
                    if learning_log_path and learning_log_path.exists():
                        # Read the JSON version (not txt)
                        json_log_path = Path(sm.session_dir) / "learning_logs" / "learning_interactions.json"
                        if json_log_path.exists():
                            analytics.sync_learning_log(session_id, json_log_path)
                    
                    # Sync page durations
                    page_durations_path = Path(sm.session_dir) / "meta" / "page_durations.json"
                    if page_durations_path.exists():
                        analytics.sync_page_durations(session_id, page_durations_path)
                    
                    # Mark session as completed
                    analytics.mark_completed(session_id)
                
                if success:
                    st.success("✅ Your responses have been successfully processed and uploaded!")
                    if DEV_MODE:
                        st.info(f"Session ID: `{session_id}`")
                else:
                    st.info("✅ Your responses have been saved locally.")
                    if DEV_MODE:
                        st.warning("⚠️ Cloud backup experienced some issues, but your data is secure.")
                
            except Exception as e:
                st.info("✅ Your responses have been saved locally.")
                if DEV_MODE:
                    st.warning(f"⚠️ Upload processing had issues: {str(e)}")
    else:
        # Already processed - show completion message
        st.success("✅ Your responses have been processed!")
        if DEV_MODE:
            session_info = sm.get_session_info()
            st.info(f"Session ID: `{session_info['session_id']}`")
    
    st.markdown("---")
    
    st.markdown("""
    ### Next Steps
    
    Please inform the facilitator that you have completed the session. They will guide you through the final brief interview (approximately 5 minutes).
    
    Thank you for your time and participation!
    """)
    
    st.markdown("---")
    
    # Action buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### What would you like to do?")
        
        if st.button("🔄 Start New Interview Session", use_container_width=True):
            # Reset all session state for new interview
            for key in ["profile_completed", "learning_completed", "test_completed", "ueq_completed", 
                       "completion_processed", "upload_completed", "responses", "messages", 
                       "exported_images", "transcription_text"]:
                if key in st.session_state:
                    del st.session_state[key]
            
            # Navigate to home
            navigate_to("home")
        
        if st.button("Return to Home Page", use_container_width=True):
            navigate_to("home")

# ------------------------------------------------------------------------
# PILOT SMOKE TEST (DEV MODE ONLY)
# ------------------------------------------------------------------------
elif st.session_state.current_page == "pilot_smoke_test":
    if not DEV_MODE:
        st.error("⛔ This page is only accessible in Development Mode")
        st.info("This is a facilitator-only testing page.")
        st.stop()
    
    st.title("🧪 Pilot Smoke Test")
    st.caption("Quick validation: prompts, model, and language guardrails")
    
    # Get API key
    api_key = None
    try:
        api_key = st.secrets["google"]["api_key"]
    except:
        pass
    
    if not api_key:
        import os
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        st.error("Missing GEMINI_API_KEY. Add it to .streamlit/secrets.toml under [google] or set as environment variable.")
        st.stop()
    
    from constants import LANGUAGE_CODES
    import google.genai as genai
    from google.genai import types
    import langid
    import time
    
    client = genai.Client(api_key=api_key)
    
    # Inputs
    col1, col2 = st.columns(2)
    
    with col1:
        lang = st.selectbox("Target response language", list(LANGUAGE_CODES.keys()), index=0)
    
    with col2:
        prompt_mode = st.radio("Prompt source", ["Synthetic", "Transcript snippet"], horizontal=True)
    
    snippet = None
    if prompt_mode == "Transcript snippet":
        if st.session_state.get("transcription_text"):
            snippet = st.session_state.transcription_text[:500]
        else:
            try:
                transcription_file = TRANSCRIPTION_DIR / config.course.transcription_filename
                if transcription_file.exists():
                    snippet = transcription_file.read_text(encoding="utf-8")[:500]
            except Exception as e:
                st.warning(f"Could not read transcript: {e}")
    
    user_task = st.text_area(
        "Task for the assistant", 
        value="Explain the concept in one simple sentence suitable for a beginner.", 
        height=100
    )
    
    if st.button("Run Test", type="primary", use_container_width=True):
        system = f"You MUST answer strictly in language code: {lang}. Keep response to ONE sentence."
        content = f"{user_task}\n\n"
        if snippet:
            content += f"Source:\n{snippet}\n\n"
        
        with st.spinner("Querying model..."):
            t0 = time.perf_counter()
            try:
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=content,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        temperature=0.2,
                        top_p=0.95,
                    )
                )
                latency_ms = int((time.perf_counter() - t0) * 1000)
                text = resp.text if hasattr(resp, 'text') else str(resp)
                code, score = langid.classify(text)
                pass_lang = (code == LANGUAGE_CODES[lang])
                
                st.markdown("---")
                st.subheader("Model Response")
                st.info(text or "*<empty>*")
                
                st.subheader("Language Verification")
                cols = st.columns(3)
                cols[0].metric("Expected", lang.upper())
                cols[1].metric("Detected", code.upper())
                cols[2].metric("Result", "✅ PASS" if pass_lang else "❌ FAIL")
                
                if not pass_lang:
                    st.warning(f"⚠️ Language mismatch: expected '{lang}', detected '{code}'.")
                else:
                    st.success("✅ Language verification passed!")
                    
                st.caption(f"Response time: {latency_ms}ms")
                
            except Exception as e:
                st.error(f"❌ Model call failed: {e}")
                import traceback
                with st.expander("Error details"):
                    st.code(traceback.format_exc())
    
    # Info section
    st.markdown("---")
    with st.expander("ℹ️ About this test"):
        st.markdown("""
        **Purpose**: Verify that the model responds in the correct language before pilot sessions.
        
        **Test procedure**:
        1. Select target language
        2. Choose synthetic prompt or use actual transcript snippet
        3. Run test
        4. Verify langid detection shows ✅ PASS
        
        **Note**: This test does NOT log interactions.
        """)

