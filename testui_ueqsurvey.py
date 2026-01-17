import os

import streamlit as st
from session_manager import get_session_manager

session_manager = get_session_manager()

# Get session info once at the top for use throughout the page
# This includes language_code, session_id, fake_name, etc.
session_info_global = session_manager.get_session_info()

# ---- UEQ CALCULATION FUNCTION ------
def evaluate_ueq(raw: dict) -> dict:
    """Evaluate UEQ scores based on the raw responses.
    Returns dictionary with 'means' and 'grades' keys for session_manager.save_ueq().
    """
    # All questions now have consistent orientation: negative on left (1), positive on right (7)
    # No reversal needed since UI presentation matches calculation expectation
    
    def to_interval(v: int) -> int:
        """Convert 1-7 scale to −3..+3 interval."""
        return v - 4  # 1..7 -> -3..+3
    
    # UEQ scale definitions
    SCALES = {
        "Attractiveness": [1, 12, 14, 16, 24, 25],
        "Perspicuity": [2, 4, 13, 21],
        "Efficiency": [9, 20, 22, 23],
        "Dependability": [8, 11, 17, 19],
        "Stimulation": [5, 6, 7, 18],
        "Novelty": [3, 10, 15, 26],
    }
    
    # UEQ benchmark values (mean, standard deviation)
    BENCH = {
        "Attractiveness": (1.50, 0.85),
        "Perspicuity": (1.45, 0.83),
        "Efficiency": (1.38, 0.79),
        "Dependability": (1.25, 0.86),
        "Stimulation": (1.17, 0.96),
        "Novelty": (0.78, 0.96),
    }
    
    def grade(mean: float, bench_mean: float, sd: float) -> str:
        """Grade the mean against benchmark."""
        if mean >= bench_mean + 0.5 * sd:
            return "excellent"
        if mean >= bench_mean:
            return "good"
        if mean >= bench_mean - 0.5 * sd:
            return "okay"
        return "weak"
    
    # Calculate means and grades for each scale
    means, grades = {}, {}
    for scale, items in SCALES.items():
        vals = []
        for n in items:
            v_raw = raw[f"q{n}"]
            val = to_interval(v_raw)  # Direct conversion - all scales now consistent
            vals.append(val)
        m = sum(vals) / len(vals)
        means[scale] = m
        grades[scale] = grade(m, *BENCH[scale])
    
    return {"means": means, "grades": grades}

st.title("User Experience Questionnaire")

# Get language name for display
language_name = {
    "en": "English",
    "de": "German", 
    "nl": "Dutch",
    "tr": "Turkish",
    "sq": "Albanian",
    "hi": "Hindi"
}.get(session_info_global.get("language_code", "en"), "English")

st.markdown(
    f"""
This questionnaire evaluates **your experience with the AI learning assistant in {language_name}** (the chat interface and AI responses you just used).

{"**Important - How to answer these questions:**" if session_info_global.get("language_code", "en") != "en" else "**How to answer these questions:**"}

{f'''You just used the AI assistant in **{language_name}**. When answering each question, please **compare** this experience to what you imagine your experience would be like if you had used the AI in **English** instead.

**Think comparatively:**
- Would this experience be better or worse if the AI responded in English?
- Would you feel more or less comfortable/confident using English?
- Compare your {language_name} experience against your expectation of an English experience

Your comparison helps us understand whether AI quality differs across languages. There are no right or wrong answers - we need your honest impression of this language comparison.''' if session_info_global.get("language_code", "en") != "en" else f'''You used the AI assistant in **{language_name}** (your native language). When answering each question, please rate your **actual experience** with this AI learning tool.

**Focus on:**
- How the AI assistant helped (or didn't help) your learning
- The quality and usefulness of AI explanations
- Your overall satisfaction with the learning experience

You're rating your actual experience - there are no comparisons needed since you're in the control group.'''}

For each item, select the point on the scale that best represents your impression. The scale goes from **negative attributes on the left** to **positive attributes on the right**.

Don't think too long about your decision to make sure that you convey your original impression.

Sometimes you may not be completely sure about your agreement with a particular attribute or you may find that the attribute does not apply completely. Nevertheless, please tick a circle in every line. It is your personal opinion that counts.
There are no wrong or right answers!
"""
)

# Dictionary to store responses
if "responses" not in st.session_state:
    st.session_state.responses = {}

# CSS for styling
st.markdown(
    """
<style>
.question-container {
    margin-bottom: 20px;
    padding: 10px;
    border-left: 3px solid #0E4B99;
    background-color: #f0f2f6;
}
.question-divider {
    margin: 10px 0;
    border-bottom: 1px solid #e0e0e0;
}
</style>
""",
    unsafe_allow_html=True,
)

# The 26 question pairs from the actual UEQ
questions = [
    {"number": 1, "left": "annoying", "right": "enjoyable"},
    {"number": 2, "left": "not understandable", "right": "understandable"},
    {"number": 3, "left": "dull", "right": "creative"},
    {"number": 4, "left": "difficult to learn", "right": "easy to learn"},
    {"number": 5, "left": "inferior", "right": "valuable"},
    {"number": 6, "left": "boring", "right": "exciting"},
    {"number": 7, "left": "not interesting", "right": "interesting"},
    {"number": 8, "left": "unpredictable", "right": "predictable"},
    {"number": 9, "left": "slow", "right": "fast"},
    {"number": 10, "left": "conventional", "right": "inventive"},
    {"number": 11, "left": "obstructive", "right": "supportive"},
    {"number": 12, "left": "bad", "right": "good"},
    {"number": 13, "left": "complicated", "right": "easy"},
    {"number": 14, "left": "unlikable", "right": "pleasing"},
    {"number": 15, "left": "usual", "right": "leading edge"},
    {"number": 16, "left": "unpleasant", "right": "pleasant"},
    {"number": 17, "left": "not secure", "right": "secure"},
    {"number": 18, "left": "demotivating", "right": "motivating"},
    {"number": 19, "left": "does not meet expectations", "right": "meets expectations"},
    {"number": 20, "left": "inefficient", "right": "efficient"},
    {"number": 21, "left": "confusing", "right": "clear"},
    {"number": 22, "left": "impractical", "right": "practical"},
    {"number": 23, "left": "cluttered", "right": "organized"},
    {"number": 24, "left": "unattractive", "right": "attractive"},
    {"number": 25, "left": "unfriendly", "right": "friendly"},
    {"number": 26, "left": "conservative", "right": "innovative"},
]

# Display each question with improved layout
for q in questions:
    # Create three columns for better layout
    col_left, col_scale, col_right = st.columns([1, 3, 1])

    with col_left:
        st.markdown(
            f"<div style='text-align: right;'>{q['left']}</div>",
            unsafe_allow_html=True,
        )

    with col_scale:
        # Create the radio buttons
        key = f"q{q['number']}"
        selected_value = st.radio(
            f"Select a value for question {q['number']}",
            options=list(range(1, 8)),
            horizontal=True,
            key=key,
            label_visibility="collapsed",
            index=None,
        )

    with col_right:
        st.markdown(
            f"<div style='text-align: left;'>{q['right']}</div>", unsafe_allow_html=True
        )

    # Store the response
    st.session_state.responses[key] = {
        "question": f"{q['left']} --- {q['right']}",
        "value": selected_value,
    }

    # Add a subtle divider between questions
    st.markdown("<div class='question-divider'></div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("### Final Step: Your Feedback")

st.info("💡 Your written feedback is the most valuable part of this study. It helps us understand whether AI creates language-based inequalities in education.")

# Determine language condition from session_manager
session_info = session_manager.get_session_info()
lang_code = session_info.get("language_code") or st.session_state.get("language_code", "en")
is_english_condition = (lang_code == "en")

if not is_english_condition:
    st.markdown(
        f"""
**Please answer these two questions about your experience learning in {language_name}:**

**1. Language Comparison (most important):**  
If you had learned this material using AI in **English** instead of {language_name}, would your learning experience have been **better, worse, or about the same**? Please explain why — be specific about what would change (e.g., understanding, confidence, speed, question quality, AI response quality).

**2. What affected your experience?**  
Mention anything that stood out — good or bad — about using AI in {language_name}. Examples: translation issues, unnatural phrasing, mixed languages, clarity problems, surprising quality, preference for English/native language, technical issues, etc.
"""
    )
else:
    st.markdown(
        """
**Please answer these two questions about your experience learning in English:**

**1. Language and Learning (most important):**  
Do you think your learning experience would have been **different** if the AI had responded in a **non-native language** you speak? Would it have been better, worse, or similar? Why? (If you only speak English, imagine learning in a language you studied at school.)

**2. What affected your experience?**  
Mention anything that stood out — good or bad — about using the AI assistant. Examples: explanation clarity, confusing terminology, accuracy concerns, response quality, technical issues, comparison to other AI tools you've used, etc.
"""
    )

# --- comment widget -----------------------------------------
comment_txt = st.text_area(
    "Your feedback (required):",
    placeholder="Please answer the two questions above...",
    key="extra_comment",
    height=200,
    help="Your written feedback is essential for understanding language effects in AI learning"
)

st.markdown("---")

# --- Single Finish Interview Button -----------------------------------
if st.button("✅ Finish Interview", type="primary", use_container_width=True):
    # Validate all 26 questions are answered
    missing = [i for i in range(1, 27) if f"q{i}" not in st.session_state.responses or st.session_state.responses[f"q{i}"]["value"] is None]
    
    if missing:
        st.error(f"⚠️ Please answer all 26 questions before finishing. Missing: {len(missing)} question(s)")
        st.warning(f"Unanswered questions: {', '.join([f'Q{i}' for i in missing[:5]])}{'...' if len(missing) > 5 else ''}")
        st.stop()
    
    # Validate comment is provided
    comment = (comment_txt or "").strip()
    if not comment:
        st.error("⚠️ Please provide your written feedback above. Your insights about language comparison are essential for this research.")
        st.stop()
    
    # Check minimum length (at least 50 characters to ensure substantive response)
    if len(comment) < 50:
        st.error("⚠️ Please provide more detailed feedback (at least a few sentences). Your comparison insights are crucial for understanding language effects.")
        st.stop()
    
    # Collect all answers
    answers_dict = {
        key: entry["value"]
        for key, entry in st.session_state.responses.items()
    }
    
    # Calculate UEQ scores
    bench = evaluate_ueq(answers_dict)
    
    # Save everything to JSON file
    sm = get_session_manager()
    file_path = sm.save_ueq(
        answers=answers_dict,
        benchmark={"means": bench["means"], "grades": bench["grades"]},
        free_text=comment
    )
    
    # Mark as submitted and completed
    st.session_state["ueq_submitted"] = True
    st.session_state["ueq_completed"] = True
    
    # Get session info for confirmation
    session_info = sm.get_session_info()
    fake_name = session_info.get("fake_name", "unknown")
    
    # Show success message
    st.success(f"✅ Thank you! Your responses have been saved successfully!")
    st.success("💬 Your feedback has been recorded and is invaluable for this research.")
    st.caption(f"Pseudonymized ID: {fake_name}")
    
    # Brief pause for user to see confirmation
    import time
    time.sleep(1.5)
    
    # Navigate to completion page
    st.rerun()

st.caption("After clicking 'Finish Interview', your responses and feedback will be saved and you'll proceed to the completion page.")