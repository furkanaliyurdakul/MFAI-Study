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
    # Items where the POSITIVE word is on the LEFT in the UI → reverse (1..7 -> 7..1)
    REVERSE = {3, 4, 5, 9, 10, 12, 17, 18, 19, 21, 23, 24}
    
    def orient_pos(v: int, idx: int) -> int:
        """Orient value so 7 is always positive."""
        return 8 - v if idx in REVERSE else v  # still 1..7, but oriented so 7 is positive
    
    def to_interval(v: int) -> int:
        """Convert 1-7 (positive-oriented) to −3..+3."""
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
            v_pos = orient_pos(v_raw, n)
            val = to_interval(v_pos)
            vals.append(val)
        m = sum(vals) / len(vals)
        means[scale] = m
        grades[scale] = grade(m, *BENCH[scale])
    
    return {"means": means, "grades": grades}

st.title("User Experience Questionnaire")

st.markdown(
    """
This questionnaire evaluates your experience with the AI learning assistant and platform. For each item, select the point on the scale that best represents your impression.

Please decide spontaneously. Don't think too long about your decision to make sure that you convey your original impression.

Sometimes you may not be completely sure about your agreement with a particular attribute or you may find that the attribute does not apply completely to the particular product.

Nevertheless, please tick a circle in every line. It is your personal opinion that counts.

Please remember: there is no wrong or right answer!
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
    {"number": 3, "left": "creative", "right": "dull"},
    {"number": 4, "left": "easy to learn", "right": "difficult to learn"},
    {"number": 5, "left": "valuable", "right": "inferior"},
    {"number": 6, "left": "boring", "right": "exciting"},
    {"number": 7, "left": "not interesting", "right": "interesting"},
    {"number": 8, "left": "unpredictable", "right": "predictable"},
    {"number": 9, "left": "fast", "right": "slow"},
    {"number": 10, "left": "inventive", "right": "conventional"},
    {"number": 11, "left": "obstructive", "right": "supportive"},
    {"number": 12, "left": "good", "right": "bad"},
    {"number": 13, "left": "complicated", "right": "easy"},
    {"number": 14, "left": "unlikable", "right": "pleasing"},
    {"number": 15, "left": "usual", "right": "leading edge"},
    {"number": 16, "left": "unpleasant", "right": "pleasant"},
    {"number": 17, "left": "secure", "right": "not secure"},
    {"number": 18, "left": "motivating", "right": "demotivating"},
    {"number": 19, "left": "meets expectations", "right": "does not meet expectations"},
    {"number": 20, "left": "inefficient", "right": "efficient"},
    {"number": 21, "left": "clear", "right": "confusing"},
    {"number": 22, "left": "impractical", "right": "practical"},
    {"number": 23, "left": "organized", "right": "cluttered"},
    {"number": 24, "left": "attractive", "right": "unattractive"},
    {"number": 25, "left": "friendly", "right": "unfriendly"},
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

# Submit button
if st.button("Submit Responses"):
    # Require all 26 answers before submit
    missing = [i for i in range(1, 26+1) if f"q{i}" not in st.session_state.responses or st.session_state.responses[f"q{i}"]["value"] is None]
    if missing:
        st.warning("Please answer all 26 UEQ items before submitting.")
        st.stop()

    # --- all items answered: continue as before ---------------------
    st.success("Thank you for completing the User Experience Questionnaire!")

    # Mark UEQ as submitted
    st.session_state["ueq_submitted"] = True

    answers_dict = {
        key: entry["value"]  # 1‑7 scale value
        for key, entry in st.session_state.responses.items()
    }

    response_text = "User Experience Questionnaire Responses:\n"
    response_text += "=" * 50 + "\n\n"

    for q in questions:
        key = f"q{q['number']}"
        value = st.session_state.responses[key]["value"]
        response_text += f"{q['number']}. {q['left']} --- {q['right']}: {value}/7\n"

    # Display the responses
    st.text_area("Your Responses:", value=response_text, height=400)

    # Import the session manager
    from session_manager import get_session_manager

    # Get or create a session manager instance
    session_manager = get_session_manager()

    bench = evaluate_ueq(answers_dict)
    
    # Save via session manager to JSON (not TXT)
    payload = {
        "answers": answers_dict,            # q1..q26 -> 1..7 (as selected)
        "means": bench["means"],            # computed means per scale
        "grades": bench["grades"],          # grade per scale
    }
    sm = get_session_manager()
    sm.save_ueq(
        answers=payload["answers"], 
        benchmark={"means": payload["means"], "grades": payload["grades"]}, 
        free_text=st.session_state.get("saved_comment")
    )
    st.success("UEQ saved.")

    # Get the session info for display
    session_info = session_manager.get_session_info()
    fake_name = session_info.get("fake_name", "unknown")
    session_id = session_info.get("session_id", "unknown")

    st.success(f"Your responses have been saved with pseudonymized ID: {fake_name}")
    st.caption(f"Session ID: {session_id}")

# Determine language condition from session_manager
session_info = session_manager.get_session_info()
lang_code = session_info.get("language_code") or st.session_state.get("language_code", "en")
is_english_condition = (lang_code == "en")

st.markdown("#### Optional feedback (highly appreciated)")
st.write(
    "If you noticed anything unusual or important during the session, please write it here.\n\n"
    "**Helpful topics include:**\n"
    "- **Language quality:** Was the AI's language natural and correct? Any strange translations or mixed language?\n"
    "- **Clarity:** Were explanations clear and easy to follow?\n"
    "- **Trust/accuracy:** Any answers that seemed wrong, misleading, or overconfident?\n"
    "- **Usability:** Any technical issues, slow responses, or confusing UI elements?\n"
    "- **Anything else:** Any thought that could help us interpret your results."
)

if not is_english_condition:
    st.info(
        "**Comparison prompt (native-language condition):**\n"
        "- Compared to how you normally use ChatGPT/Gemini, did this session feel **easier, harder, or about the same**? Why?\n"
        "- Did using your native language change your confidence, speed, or understanding?"
    )
else:
    st.info(
        "**Optional reflection (English condition):**\n"
        "If you have used AI tools before, did this session feel similar to your usual usage? What felt different?"
    )

# --- comment widget -----------------------------------------
comment_txt = st.text_area(
    "Your feedback:",
    placeholder="Write your feedback here...",
    key="extra_comment",
    height=150,
    label_visibility="collapsed"
)

# --- save comment widget -----------------------------------
if st.button("Save comment", key="save_extra_comment"):
    comment = (comment_txt or "").strip()
    if comment:
        st.session_state["saved_comment"] = comment
        st.success("Your comment has been saved!")

        # If UEQ already submitted, re-save JSON with comment included
        if st.session_state.get("ueq_submitted", False):
            answers_dict = {
                key: entry["value"]
                for key, entry in st.session_state.responses.items()
                if entry["value"] is not None
            }
            bench = evaluate_ueq(answers_dict)
            session_manager.save_ueq(
                answers=answers_dict,
                benchmark=bench,
                free_text=comment,
            )
            st.success("Your comment has been added to your UEQ responses.")
    else:
        st.warning("Please enter a comment before saving.")