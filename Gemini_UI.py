# SPDX‑License‑Identifier: MIT
"""Gemini‑powered slide tutor.

Streamlit page that lets a user upload slides, audio and a student profile,
then requests a personalised (or generic) explanation from Gemini 2.5.
"""

# ── std‑lib ────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

# Heavy / Windows‑only libs are *imported* but only initialised when needed
# import pythoncom  # Disabled for Linux deployment

# ── third‑party ────────────────────────────────────────────────────────────
import streamlit as st

# ── local imports ──────────────────────────────────────────────────────────
from config import config
from constants import SLIDE_FILENAME_RE
# import whisper  # Disabled - using pre-transcribed content
# import win32com.client  # Disabled for Linux deployment

# ── local ─────────────────────────────────────────────────────────────────
from session_manager import get_session_manager

# ──────────────────────────────────────────────────────────────────────────
# Configuration constants
# ──────────────────────────────────────────────────────────────────────────
ROOT: Path = Path.cwd()
UPLOAD_DIR_AUDIO: Path = ROOT / "uploads" / "audio"
UPLOAD_DIR_PPT: Path = ROOT / "uploads" / "ppt"
UPLOAD_DIR_PROFILE: Path = ROOT / "uploads" / "profile"
UPLOAD_DIR_VIDEO: Path = ROOT / "uploads" / "video"
TRANSCRIPTION_DIR: Path = ROOT / "transcriptions"

for p in (
    UPLOAD_DIR_AUDIO,
    UPLOAD_DIR_PPT,
    UPLOAD_DIR_PROFILE,
    UPLOAD_DIR_VIDEO,
    TRANSCRIPTION_DIR,
):
    p.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────
# Streamlit page‑level setup
# ──────────────────────────────────────────────────────────────────────────
FAST_TEST_MODE: bool = st.session_state.get("fast_test_mode", False)

st.markdown(
    """
    <style>
    .block-container {max-width: 90%; padding-left: 2rem; padding-right: 2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# All users get identical treatment - only language varies

# ──────────────────────────────────────────────────────────────────────────
# Session‑state helpers
# ──────────────────────────────────────────────────────────────────────────

_DEFAULT_SESSION_STATE = {
    "exported_images": [],
    "transcription_text": "",
    "messages": [],
    "selected_slide": "Slide 1",
    "profile_dict": {},
}

for k, v in _DEFAULT_SESSION_STATE.items():
    st.session_state.setdefault(k, v)


def debug_log(msg: str) -> None:
    """Collect debug statements in *one* place so they can be shown via a checkbox."""
    st.session_state.setdefault("debug_logs", []).append(msg)


# ──────────────────────────────────────────────────────────────────────────
# Prompt builders
# ──────────────────────────────────────────────────────────────────────────

def make_base_context(language_code: str = "en") -> dict:
    """
    Return the immutable context we want to feed Gemini **before every** exchange.

    • The SYSTEM + Formatting rules are included for all runs.
    • Language enforcement ensures responses match the user's assigned language.
    • NO student profile - all users get identical treatment.
    • ALL prompt text is in the target language to avoid English bias.
    """
    from prompt_translations import get_prompts
    prompts = get_prompts(language_code)
    
    base = {
        "System": prompts["system_chat"],

        # universal formatting rules (in target language)
        "Instructions": {
            "Formatting": prompts["formatting_rules"],
            "Tone": prompts["tone"],
        },
    }

    return base

def create_summary_prompt(slide: str) -> str:
    """Return the user‑facing summary prompt for logging."""
    return (
        f"Generate an explanation for {slide}. "
    )

""" potential bias
    if not personalised:
        return (
            f"Generate an explanation for {slide}. "
        )


    name = profile.get("Name", "the student")
    proficiency = profile.get("CurrentProficiency", "unknown level")
    learning_strats = ", ".join(profile.get("PreferredLearningStrategies", []))
    barriers = ", ".join(profile.get("PotentialBarriers", []))
    short_goals = "; ".join(profile.get("ShortTermGoals", []))

    return (
        f"Generating a {label_loc} explanation for {slide} tailored specifically to {name}, "
        f"who is at a {proficiency.lower()} level.\n\n"
        f"{name}'s strongest subject is {profile.get('StrongestSubject', 'N/A')}, "
        f"while they find {profile.get('WeakestSubject', 'N/A')} challenging.\n"
        f"Preferred learning methods include: {learning_strats}.\n\n"
        f"The explanation will explicitly address potential barriers such as {barriers}, "
        f"while aligning with their short‑term academic goal(s): {short_goals}.\n\n"
        f"Language complexity and examples will reflect their interests "
        f"({', '.join(profile.get('Hobbies', []))}) and major ({profile.get('Major', 'N/A')})."
    )
"""

def create_structured_prompt(
    slide_txt: str, transcript: str, slide: str, language_code: str = "en"
) -> str:
    """Gemini JSON prompt – standardized explanation based on course content only.
    
    All prompt text is in the target language to ensure fair comparison without English bias.
    """
    from prompt_translations import get_prompts
    prompts = get_prompts(language_code)

    # ── prompt ----------------------------------------------------- #
    prompt_dict = {
        # ── SYSTEM (high‑level reminders) ───────────────────────────────
        "System": prompts["system_explanation"],

        # ── ROLE & OBJECTIVE ────────────────────────────────────────
        "Role": prompts["role_tutor"],
        "Objective": prompts["objective_explanation"].format(slide=slide),

        # ── INSTRUCTIONS / RESPONSE RULES ───────────────────────────────
        "Instructions": {
            "Formatting": prompts["formatting_rules"],
            "Tone": prompts["tone"],
            "Guidelines": [
                prompts["guideline_clear_language"],
                prompts["guideline_examples"],
                prompts["guideline_thorough"],
                prompts["guideline_practical"],
            ],
        },

        # ── CONTEXT ─────────────────────────────────────────────────
        "Context": {
            "Slides": {
                "content": slide_txt,
                "usage_hint": prompts["slides_hint"].format(slide=slide)
            },
            "Transcript": {
                "content": transcript,
                "usage_hint": prompts["transcript_hint"],
            },
        },
    }

    # Return pretty‑printed JSON string because `build_prompt()` expects it
    return json.dumps(prompt_dict, indent=2)



# ──────────────────────────────────────────────────────────────────────────
# Profile parser (regex‑based, matches the survey export)
# ──────────────────────────────────────────────────────────────────────────


def parse_detailed_student_profile(text: str) -> dict:
    """Convert the long profile *text blob* into a structured dict."""

    def _grab(pattern: str, default: str = "") -> str:
        m = re.search(pattern, text, re.MULTILINE)
        return m.group(1).strip() if m else default

    profile: dict = {
        "Name": _grab(r"1\.\s*Name:\s*(.+)"),
        "Age": int(_grab(r"2\.\s*Age:\s*(\d+)", "0")),
        "StudyBackground": _grab(r"3\.\s*Study background:\s*(.+)"),
        "Major": _grab(r"4\.\s*Major of education:\s*(.+)"),
        "WorkExperience": _grab(r"5\.\s*Work experience:\s*(.+)"),
    }

    hobbies = _grab(r"6\.\s*Hobbies or interests:\s*(.+)")
    profile["Hobbies"] = [h.strip() for h in hobbies.split(",")] if hobbies else []

    # --- academic performance table -------------------------------------
    perf_section = re.search(
        r"7\. Academic performance ranking.*?:(.*?)(?=8\.)", text, re.DOTALL
    )
    scores: dict[str, int] = {}
    if perf_section:
        for subj, sc in re.findall(r"[A-L]\.\s*(.+?):\s*(\d)", perf_section.group(1)):
            scores[subj.strip()] = int(sc)
    profile["AcademicPerformance"] = scores

    profile["StrongestSubject"] = _grab(r"8\.\s*Strongest Subject:\s*(.+)")
    profile["WeakestSubject"] = _grab(r"9\.\s*Most Challenging Subject:\s*(.+)")

    # --- learning priorities -------------------------------------------
    prio_section = re.search(
        r"10\. Learning priorities ranking.*?:(.*?)(?=11\.)", text, re.DOTALL
    )
    priorities: dict[str, int] = {}
    if prio_section:
        for item, rating in re.findall(
            r"[A-F]\.\s*(.+?):\s*(\d)", prio_section.group(1)
        ):
            priorities[item.strip()] = int(rating)
    profile["LearningPriorities"] = priorities

    # --- rest -----------------------------------------------------------
    profile["PreferredLearningStrategies"] = [
        s.strip()
        for s in _grab(r"11\. Preferred learning strategy:\s*(.+)").split(";")
        if s.strip()
    ]
    profile["CurrentProficiency"] = _grab(r"12\.\s*Current proficiency level:\s*(.+)")

    profile["ShortTermGoals"] = [
        g.strip()
        for g in _grab(r"13\.\s*Short-term academic goals:\s*(.+)").split(";")
        if g.strip()
    ]
    profile["LongTermGoals"] = [
        g.strip()
        for g in _grab(r"14\.\s*Long-term academic/career goals:\s*(.+)").split(";")
        if g.strip()
    ]
    profile["PotentialBarriers"] = [
        b.strip()
        for b in _grab(r"15\.\s*Potential Barriers:\s*(.+)").split(";")
        if b.strip()
    ]

    return profile


# ──────────────────────────────────────────────────────────────────────────
# File helpers (Whisper + PowerPoint automation)
# ──────────────────────────────────────────────────────────────────────────


def transcribe_audio(audio_path: Path) -> str:
    """Transcribe *audio_path* with Whisper – cached on disk."""
    model_name = "turbo"
    trans_path = TRANSCRIPTION_DIR / f"{model_name}_transcription_{audio_path.stem}.txt"

    if trans_path.exists():
        debug_log(f"Using cached transcription: {trans_path.name}")
        return trans_path.read_text(encoding="utf‑8")

    # DISABLED FOR DEPLOYMENT: Whisper functionality disabled for Linux deployment
    debug_log("Whisper functionality disabled - returning empty transcription")
    return "Transcription functionality disabled - using pre-transcribed content"


def export_ppt_slides(ppt_path: Path) -> list[Path]:
    """Return a list of exported PNG slide paths given a .pptx file.
    
    DISABLED FOR DEPLOYMENT: This function is disabled for Linux deployment.
    Pre-processed slides are used instead.
    """
    debug_log("export_ppt_slides called but disabled for deployment")
    return []


# ──────────────────────────────────────────────────────────────────────────
# Prompt wrapper (generic vs personalised)
# ──────────────────────────────────────────────────────────────────────────


def build_prompt(
    slide_txt: str, transcript: str, slide: str, language_code: str = "en"
) -> str:
    """Return the JSON prompt string based on course content only."""
    return create_structured_prompt(slide_txt, transcript, slide, language_code)


@st.cache_data(show_spinner=False)
def _load_transcript_cached(transcript_path: str) -> str:
    """Cached helper to load transcription text."""
    from pathlib import Path
    path = Path(transcript_path)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


@st.cache_data(show_spinner=False)
def _load_slides_cached(slides_dir: str) -> list:
    """Cached helper to load slide paths."""
    from pathlib import Path
    from constants import SLIDE_FILENAME_RE
    dir_path = Path(slides_dir)
    if dir_path.exists():
        # Filter and sort slides with robust error handling
        valid_slides = []
        # Support both .png and .jpg/.jpeg extensions
        for pattern in ["Slide_*.png", "Slide_*.jpg", "Slide_*.jpeg"]:
            for p in dir_path.glob(pattern):
                # Remove " Genetics of Cancer" or other course-specific suffixes before the extension
                stem = p.stem.split(' Genetics of Cancer')[0].split(' of Lecture')[0]
                match = SLIDE_FILENAME_RE.search(stem)
                if match:
                    try:
                        slide_num = int(match.group(1))
                        valid_slides.append((slide_num, p))
                    except (ValueError, IndexError):
                        continue
        # Sort by slide number and return paths
        valid_slides.sort(key=lambda x: x[0])
        return [path for _, path in valid_slides]
    return []


def load_course_content() -> None:
    """Load course slides and transcription from files.
    
    This loads the actual course materials that are the same for all users.
    Profile is NOT loaded here - it's created fresh each session.
    """
    # Load all course slides (cached)
    if not st.session_state.get("exported_images"):
        slides_dir = ROOT / "uploads" / "ppt" / config.course.slides_directory
        slide_files = _load_slides_cached(str(slides_dir))
        if slide_files:
            st.session_state.exported_images = slide_files
            debug_log(f"Loaded {len(slide_files)} {config.course.course_title} slides")
        else:
            debug_log(f"⚠️ No slides found in {slides_dir}")
    
    # Load course transcription (cached)
    if not st.session_state.get("transcription_text"):
        transcription_file = TRANSCRIPTION_DIR / config.course.transcription_filename
        debug_log(f"Attempting to load transcription from: {transcription_file}")
        transcript = _load_transcript_cached(str(transcription_file))
        if transcript:
            st.session_state.transcription_text = transcript
            debug_log(f"✅ Loaded {config.course.course_title} transcription ({len(transcript)} chars)")
        else:
            debug_log(f"⚠️ Transcription not found or empty at {transcription_file}")
            debug_log(f"Loaded {config.course.course_title} transcription from {transcription_file.name}")
    
    # Set default slide selection
    if not st.session_state.get("selected_slide"):
        st.session_state.selected_slide = "Slide 1"


# ──────────────────────────────────────────────────────────────────────────
# Streamlit UI logic – *main* entry point
# ──────────────────────────────────────────────────────────────────────────


def main() -> None:
    st.title(f"Explanation Generator - {config.course.course_title}")
    
    # Preview-only page notice
    st.info("📝 Preview-only page: content loader & materials. The study chat runs in the main flow.")

    # 1) Fast‑test stub ---------------------------------------------------
    if FAST_TEST_MODE:
        st.session_state.exported_images = [
            ROOT / "uploads" / "ppt" / "picture" / "Slide_1 Genetics of Cancer.jpg"
        ]
        st.session_state.transcription_text = (
            "This is a mock transcription for fast testing."
        )
        st.session_state.profile_dict = {
            "Name": "Test User",
            "CurrentProficiency": "Intermediate",
            "StrongestSubject": "Mathematics",
            "WeakestSubject": "Physics",
            "PreferredLearningStrategies": [
                "Detailed, step‑by‑step explanations similar to in‑depth lectures",
            ],
            "PotentialBarriers": ["Lack of prior knowledge"],
            "ShortTermGoals": ["Understand core concepts"],
            "Hobbies": ["Chess", "Reading"],
            "Major": "Engineering",
            "LearningPriorities": {
                "Understanding interrelationships among various concepts": 5,
                "Applying theory to real-world problems": 5,
            },
        }
        st.session_state.selected_slide = "Slide 1"
    else:
        # Production mode: Load course content automatically
        if not st.session_state.exported_images:
            # Load all course slides
            slides_dir = ROOT / "uploads" / "ppt" / config.course.slides_directory
            if slides_dir.exists():
                slide_files = sorted(
                    slides_dir.glob("Slide_*.png"),
                    key=lambda p: int(SLIDE_FILENAME_RE.search(p.stem).group(1))
                )
                st.session_state.exported_images = slide_files
                debug_log(f"Loaded {len(slide_files)} {config.course.course_title} slides")
        
        if not st.session_state.transcription_text:
            # Load course transcription
            transcription_file = TRANSCRIPTION_DIR / config.course.transcription_filename
            if transcription_file.exists():
                st.session_state.transcription_text = transcription_file.read_text(encoding="utf-8")
                debug_log(f"Loaded {config.course.course_title} transcription from {transcription_file.name}")
        
        # Profile is created fresh each session through the learning platform
        # No preloading needed in production mode
        
        if not st.session_state.selected_slide:
            st.session_state.selected_slide = "Slide 1"

    # 2) Load profile from session dir if already stored ------------------
    if not st.session_state.profile_dict:
        sm = get_session_manager()
        orig_profile = sm.profile_dir / "original_profile.txt"
        if orig_profile.exists():
            prof_txt = orig_profile.read_text(encoding="utf-8")
            st.session_state.profile_text = prof_txt
            st.session_state.profile_dict = parse_detailed_student_profile(prof_txt)
            debug_log(f"Loaded profile from {orig_profile}")

    # 3) Sidebar – content information -------------------------------------
    # Show content status
    if st.session_state.exported_images:
        st.sidebar.success(f"✅ {len(st.session_state.exported_images)} slides loaded")
    if st.session_state.transcription_text:
        st.sidebar.success("✅ Transcription loaded")
    if st.session_state.profile_dict:
        st.sidebar.success("✅ Student profile loaded")

    # -- debug toggles ----------------------------------------------------
    if st.checkbox("Show Debug Logs"):
        st.subheader("Debug Logs")
        for l in st.session_state.get("debug_logs", []):
            st.text(l)

    if st.checkbox("Show Parsed Profile"):
        st.json(st.session_state.profile_dict)

    # Content is pre-loaded in production mode - no upload processing needed
    # Profile is created fresh each session through the learning platform

    # 4) Sidebar – slide selector ----------------------------------------
    if st.session_state.exported_images:
        slide_opts = [
            f"Slide {i+1}" for i in range(len(st.session_state.exported_images))
        ]
        selected_slide = st.sidebar.selectbox(
            "Select a Slide", slide_opts, key="selected_slide"
        )

    # 5) Chat section (full width) ----------------------------------------
    st.header("LLM Chat")
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"], unsafe_allow_html=True)

    if (
        not st.session_state.exported_images
        or not st.session_state.transcription_text
    ):
        st.info(
            "Upload and process audio + PPT (and a profile) to enable prompting."
        )

    # 6) Preview files section (below chat) -------------------------------
    st.markdown("---")
    st.header("Preview Files")
    
    if st.session_state.transcription_text:
        st.subheader("Transcription")
        st.text_area("Output", st.session_state.transcription_text, height=150)

    if st.session_state.exported_images and selected_slide:
        idx = int(selected_slide.split()[1]) - 1
        st.subheader("Selected Slide")
        st.image(
            str(st.session_state.exported_images[idx]),
            caption=selected_slide,
            use_container_width=True,
        )

    # Video preview functionality
    try:
        video_path = UPLOAD_DIR_VIDEO / config.course.video_filename
    except NameError:
        # Fallback if UPLOAD_DIR_VIDEO isn't defined
        video_path = Path.cwd() / "uploads" / "video" / config.course.video_filename
    
    if video_path.exists():
        st.subheader("Lecture Recording")
        try:
            with open(video_path, "rb") as video_file:
                video_bytes = video_file.read()
            st.video(video_bytes)
            st.caption(f"{config.course.course_title} - Full Lecture")
        except Exception as e:
            st.error(f"Error loading video: {e}")
    else:
        st.info("Lecture recording will appear here when available")

    if "profile_text" in st.session_state:
        st.subheader("Student Profile")
        st.text_area("Profile", st.session_state.profile_text, height=150)


if __name__ == "__main__":
    main()
