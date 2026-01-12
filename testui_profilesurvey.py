import streamlit as st

# Language names dictionary (module-level constant)
LANGUAGE_NAMES = {
    "en": "English",
    "de": "German",
    "nl": "Dutch",
    "tr": "Turkish",
    "sq": "Albanian",
    "hi": "Hindi"
}

def get_get_current_language()():
    """Get current language from session state."""
    return st.session_state.get("language_code", "en")

def get_fast_test_mode():
    """Get fast test mode flag."""
    return st.session_state.get("fast_test_mode", False)

# Module-level flags (evaluated once when first accessed)
FAST_TEST_MODE = get_fast_test_mode()

# Initialize session state for form submission
if "show_review" not in st.session_state:
    st.session_state.show_review = False

# Function to initialize form fields
def init_form_field(key, default=None):
    if key not in st.session_state:
        st.session_state[key] = default

# Helper functions to map labels to numeric codes for analysis
def likert_5_to_int(label: str) -> int:
    """Map 5-point Likert scale labels to integers 1-5"""
    mapping = {
        "1 - Strongly Disagree": 1,
        "2 - Disagree": 2,
        "3 - Neutral": 3,
        "4 - Agree": 4,
        "5 - Strongly Agree": 5,
    }
    return mapping.get(label, None)

def familiarity_to_int(label: str) -> int:
    """Map familiarity labels to integers 1-5"""
    mapping = {
        "1 - Not at all familiar": 1,
        "2 - Slightly familiar": 2,
        "3 - Moderately familiar": 3,
        "4 - Familiar": 4,
        "5 - Very familiar": 5,
    }
    return mapping.get(label, None)

def usage_to_int(label: str) -> int:
    """Map usage frequency labels to integers 0-4"""
    mapping = {
        "Never": 0,
        "Rarely (once or twice total)": 1,
        "Occasionally (monthly)": 2,
        "Regularly (weekly)": 3,
        "Frequently (daily)": 4,
    }
    return mapping.get(label, None)

#  ═══════════════════════════════════════════════════════════════════
#  MAIN CONTENT - Either show form OR show review (never both)
#  ═══════════════════════════════════════════════════════════════════

if not st.session_state.show_review:
    # ───────────────────────────────────────────────────────────────
    # FORM MODE - Display the survey questions
    # ───────────────────────────────────────────────────────────────
    
    st.title("Participant Profile Survey")
    st.caption(
        "This survey collects background variables (language skills, prior AI knowledge, "
        "and demographics) used only for analysis of learning outcomes. The AI assistant "
        "provides the same learning content to all participants in your assigned language."
    )

    # Initialize all form fields (skip widgets with proper defaults)
    init_form_field("biology_education")
    init_form_field("cancer_biology_familiarity")
    init_form_field("cancer_biology_knowledge")
    init_form_field("topic_interest")
    init_form_field("genai_familiarity")
    init_form_field("genai_usage")
    init_form_field("llm_language_usage")
    init_form_field("gender")
    init_form_field("education_level")
    init_form_field("field_of_study")
    init_form_field("learning_language_preference")

    st.header("Section 1: Language Proficiency")

    # Q1 - Native language (pre-filled from credentials)
    st.text_input(
        "Q1. What is your native language?",
        value=LANGUAGE_NAMES.get(get_get_current_language()(), "English"),
        disabled=True,
        key="native_language_display",
        help="Your assigned study language was set during enrollment and determines your experimental condition. This cannot be changed as we are researching how different languages affect learning with AI assistants. If you believe this is incorrect, please inform the research team."
    )

    # Q2 - English proficiency (only show if study language is NOT English to avoid duplicate)
    if get_current_language() != "en":
        english_proficiency = st.select_slider(
            "Q2. How would you rate your proficiency in English? *",
            options=[1, 2, 3, 4, 5, 6, 7],
            value=4,
            format_func=lambda x: {
                1: "1 - Basic",
                2: "2 - Elementary",
                3: "3 - Intermediate",
                4: "4 - Upper-Intermediate",
                5: "5 - Advanced",
                6: "6 - Proficient",
                7: "7 - Native-like"
            }.get(x, str(x)),
            key="english_proficiency",
            help="Rate your English language ability on a scale from 1 (Basic) to 7 (Native-like)"
        )
    else:
        # For English native speakers, set English proficiency to native-like automatically
        english_proficiency = 7
        st.session_state["english_proficiency"] = 7

    # Q3 - Native language proficiency
    question_number = "Q2" if get_current_language() == "en" else "Q3"
    native_proficiency = st.select_slider(
        f"{question_number}. How would you rate your proficiency in {LANGUAGE_NAMES.get(get_current_language(), 'your native language')}? *",
        options=[1, 2, 3, 4, 5, 6, 7],
        value=7,
        format_func=lambda x: {
            1: "1 - Basic",
            2: "2 - Elementary",
            3: "3 - Intermediate",
            4: "4 - Upper-Intermediate",
            5: "5 - Advanced",
            6: "6 - Proficient",
            7: "7 - Native-like"
        }.get(x, str(x)),
        key="native_proficiency",
        help="Rate your native language ability on the same scale"
    )

    st.markdown("---")
    st.header("Section 2: Subject Knowledge and Learning Background")
    st.caption(
        "These questions help us understand your baseline knowledge of cancer biology, "
        "which is important for analyzing how effectively you learn with the AI assistant."
    )

    # Adjust question numbers based on whether Q2 was shown
    q_offset = 0 if get_current_language() == "en" else 1
    
    # Q4/Q3 - Biology/medicine education
    biology_education = st.radio(
        f"Q{3 + q_offset}. Have you ever taken formal courses in biology or medicine? *",
        [
            "Yes, at university level",
            "Yes, at high school level only",
            "No, never"
        ],
        index=None,
        key="biology_education",
        help="This helps us understand your scientific background in life sciences"
    )

    # Q5/Q4 - Cancer biology familiarity
    cancer_biology_familiarity = st.radio(
        f"Q{4 + q_offset}. Before this study, how familiar were you with cancer biology concepts? *",
        [
            "1 - Not at all familiar",
            "2 - Slightly familiar",
            "3 - Moderately familiar",
            "4 - Familiar",
            "5 - Very familiar"
        ],
        index=None,
        key="cancer_biology_familiarity",
        help="Rate your prior exposure to topics like genetic mutations, tumor development, oncogenes, etc."
    )

    # Q6/Q5 - Self-assessed cancer biology knowledge
    cancer_biology_knowledge = st.radio(
        f"Q{5 + q_offset}. \"I know a lot about cancer biology (genetic mechanisms, tumor development, and cellular processes).\" *",
        [
            "1 - Strongly Disagree",
            "2 - Disagree",
            "3 - Neutral",
            "4 - Agree",
            "5 - Strongly Agree"
        ],
        index=None,
        key="cancer_biology_knowledge",
        help="Rate your agreement with this statement about your current knowledge level"
    )

    # Q7/Q6 - Interest in topic
    topic_interest = st.radio(
        f"Q{6 + q_offset}. \"I am interested in learning about cancer biology.\" *",
        [
            "1 - Strongly Disagree",
            "2 - Disagree",
            "3 - Neutral",
            "4 - Agree",
            "5 - Strongly Agree"
        ],
        index=None,
        key="topic_interest",
        help="Your motivation to learn this topic may affect learning outcomes"
    )

    st.markdown("---")
    st.header("Section 3: AI Assistant Experience")
    st.caption(
        "These questions help us understand your prior experience with AI assistants, "
        "which may affect how comfortably you interact with the learning tool."
    )

    # Q8/Q7 - Familiarity with GenAI tools
    genai_familiarity = st.radio(
        f"Q{7 + q_offset}. How familiar are you with generative AI assistants (e.g., ChatGPT, Claude, Gemini)? *",
        [
            "1 - Not at all familiar",
            "2 - Slightly familiar",
            "3 - Moderately familiar",
            "4 - Familiar",
            "5 - Very familiar"
        ],
        index=None,
        key="genai_familiarity",
        help="Rate your general awareness and exposure to AI chat assistants"
    )

    # Q9/Q8 - Usage frequency
    genai_usage = st.radio(
        f"Q{8 + q_offset}. How often do you use AI assistants like ChatGPT, Claude, or Gemini? *",
        [
            "Never",
            "Rarely (once or twice total)",
            "Occasionally (monthly)",
            "Regularly (weekly)",
            "Frequently (daily)"
        ],
        index=None,
        key="genai_usage",
        help="How often have you actually used conversational AI tools?"
    )

    # Q10/Q9 - AI language usage
    llm_language_usage = st.radio(
        f"Q{9 + q_offset}. When you use AI assistants, which language do you primarily use? *",
        [
            "Primarily English",
            "Both English and my native language equally",
            "Primarily my native language",
            "I have never used AI assistants"
        ],
        index=None,
        key="llm_language_usage",
        help="Understanding your language habits with AI helps interpret your comfort level in this study"
    )

    st.markdown("---")
    st.header("Section 4: Demographics and Background")

    # Q11/Q10 - Age
    age = st.number_input(
        f"Q{10 + q_offset}. What is your age (in years)? *",
        min_value=16,
        max_value=100,
        value=20,
        step=1,
        key="age",
        help="Enter your age in years"
    )

    # Q12/Q11 - Gender
    gender = st.radio(
        f"Q{11 + q_offset}. What is your gender? *",
        ["Male", "Female", "Non-binary", "Prefer not to say"],
        index=None,
        key="gender"
    )

    # Q13/Q12 - Education level
    education_level = st.radio(
        f"Q{12 + q_offset}. What is your current level of education? *",
        [
            "Bachelor's degree",
            "Master's degree",
            "PhD",
            "Other"
        ],
        index=None,
        key="education_level",
        help="Select your current degree level (completed or in progress)"
    )

    # Conditional "Other" text input for education level
    education_level_other = None
    if education_level == "Other":
        education_level_other = st.text_input(
            "Please specify your education level:",
            key="education_level_other",
            help="E.g., High school, Professional certification, Trade school, etc."
        )

    # Q14/Q13 - Field of study
    field_of_study = st.radio(
        f"Q{13 + q_offset}. What is your field of study or professional area? *",
        [
            "Computer Science/IT",
            "Engineering (non-IT)",
            "Natural Sciences (Physics, Chemistry, Biology, etc.)",
            "Mathematics/Statistics",
            "Business/Economics",
            "Social Sciences (Psychology, Sociology, etc.)",
            "Humanities (Languages, History, Philosophy, etc.)",
            "Medicine/Health Sciences",
            "Arts/Design",
            "Education",
            "Law",
            "Other"
        ],
        index=None,
        key="field_of_study"
    )

    # Conditional "Other" text input for field of study
    field_of_study_other = None
    if field_of_study == "Other":
        field_of_study_other = st.text_input(
            "Please specify your field:",
            key="field_of_study_other",
            help="Enter your field of study or professional area"
        )

    # Q15/Q14 - Learning language preference
    learning_language_preference = st.radio(
        f"Q{14 + q_offset}. Do you generally prefer to learn new material in English or your native language? *",
        [
            "Strongly prefer English",
            "Somewhat prefer English",
            "No strong preference",
            "Somewhat prefer native language",
            "Strongly prefer native language"
        ],
        index=None,
        key="learning_language_preference",
        help="This is KEY for interpreting how language choice affects your learning experience"
    )

    st.markdown("---")

    # Submit button
    submit_button = st.button("Submit Survey", key="submit_profile_survey", type="primary")

    if submit_button:
        if FAST_TEST_MODE:
            # Fast test mode with synthetic data (both labels and numeric codes)
            st.session_state.form_data = {
                "native_language": LANGUAGE_NAMES.get(get_current_language(), "English"),
                "english_proficiency": 5,
                "native_proficiency": 7,
                "biology_education": "Yes, at high school level only",
                "cancer_biology_familiarity_label": "2 - Slightly familiar",
                "cancer_biology_familiarity": 2,
                "cancer_biology_knowledge_label": "2 - Disagree",
                "cancer_biology_knowledge": 2,
                "topic_interest_label": "3 - Neutral",
                "topic_interest": 3,
                "genai_familiarity_label": "3 - Moderately familiar",
                "genai_familiarity": 3,
                "genai_usage_label": "Occasionally (monthly)",
                "genai_usage": 2,
                "llm_language_usage": "Both English and my native language equally",
                "age": 24,
                "gender": "Prefer not to say",
                "education_level": "Master's degree",
                "field_of_study": "Computer Science/IT",
                "learning_language_preference": "No strong preference"
            }
            st.session_state.show_review = True
            st.success("FAST_TEST_MODE: Synthetic profile created.")
            st.rerun()
        else:
            # Validate all required fields
            all_fields_filled = (
                english_proficiency is not None
                and native_proficiency is not None
                and biology_education is not None
                and cancer_biology_familiarity is not None
                and cancer_biology_knowledge is not None
                and topic_interest is not None
                and genai_familiarity is not None
                and genai_usage is not None
                and llm_language_usage is not None
                and age is not None
                and gender is not None
                and education_level is not None
                and (education_level != "Other" or (education_level_other and education_level_other.strip()))
                and field_of_study is not None
                and (field_of_study != "Other" or (field_of_study_other and field_of_study_other.strip()))
                and learning_language_preference is not None
            )

            if all_fields_filled:
                # Store form data with both labels (for display) and numeric codes (for analysis)
                st.session_state.form_data = {
                    "native_language": LANGUAGE_NAMES.get(get_current_language(), "English"),
                    "english_proficiency": int(english_proficiency),
                    "native_proficiency": int(native_proficiency),
                    "biology_education": biology_education,
                    "cancer_biology_familiarity_label": cancer_biology_familiarity,
                    "cancer_biology_familiarity": familiarity_to_int(cancer_biology_familiarity),
                    "cancer_biology_knowledge_label": cancer_biology_knowledge,
                    "cancer_biology_knowledge": likert_5_to_int(cancer_biology_knowledge),
                    "topic_interest_label": topic_interest,
                    "topic_interest": likert_5_to_int(topic_interest),
                    "genai_familiarity_label": genai_familiarity,
                    "genai_familiarity": familiarity_to_int(genai_familiarity),
                    "genai_usage_label": genai_usage,
                    "genai_usage": usage_to_int(genai_usage),
                    "llm_language_usage": llm_language_usage,
                    "age": int(age),
                    "gender": gender,
                    "education_level": education_level,
                    "education_level_other": education_level_other if education_level_other else "",
                    "field_of_study": field_of_study,
                    "field_of_study_other": field_of_study_other if field_of_study_other else "",
                    "learning_language_preference": learning_language_preference
                }
                
                # Save profile data to JSON
                from session_manager import get_session_manager
                session_manager = get_session_manager()
                
                # save_profile now pseudonymizes internally, no need to pass name
                file_path = session_manager.save_profile(
                    st.session_state.form_data,
                    original_name=None
                )
                
                st.session_state.show_review = True
                st.success("Survey submitted successfully!")
                st.rerun()
            else:
                st.error("Please answer all required questions marked with * before submitting.")

else:
    # ───────────────────────────────────────────────────────────────
    # REVIEW MODE - Display the submitted responses
    # ───────────────────────────────────────────────────────────────
    
    st.title("Participant Profile Survey")
    st.markdown("---")
    st.header("Review Your Responses")
    
    form_data = st.session_state.get("form_data", {})
    
    if form_data:
        # Adjust question numbers based on whether Q2 was shown
        q_offset = 0 if get_current_language() == "en" else 1
        
        # Build English proficiency line only for non-English languages
        english_prof_line = f"Q2. English Proficiency: {form_data.get('english_proficiency', 'N/A')}/7\n" if get_current_language() != "en" else ""
        
        response_text = f"""Participant Profile Survey Responses
=====================================

Section 1: Language Proficiency
--------------------------------
Q1. Native Language: {form_data.get('native_language', 'N/A')}
{english_prof_line}Q{2 if get_get_current_language()() == "en" else 3}. Native Language Proficiency: {form_data.get('native_proficiency', 'N/A')}/7

Section 2: Subject Knowledge and Learning Background
-----------------------------------------------------
Q{3 + q_offset}. Biology/Medicine Education: {form_data.get('biology_education', 'N/A')}
Q{4 + q_offset}. Cancer Biology Familiarity: {form_data.get('cancer_biology_familiarity_label', 'N/A')} (coded: {form_data.get('cancer_biology_familiarity', 'N/A')})
Q{5 + q_offset}. Cancer Biology Knowledge: {form_data.get('cancer_biology_knowledge_label', 'N/A')} (coded: {form_data.get('cancer_biology_knowledge', 'N/A')})
Q{6 + q_offset}. Topic Interest: {form_data.get('topic_interest_label', 'N/A')} (coded: {form_data.get('topic_interest', 'N/A')})

Section 3: AI Assistant Experience
-----------------------------------
Q{7 + q_offset}. AI Assistant Familiarity: {form_data.get('genai_familiarity_label', 'N/A')} (coded: {form_data.get('genai_familiarity', 'N/A')})
Q{8 + q_offset}. AI Usage Frequency: {form_data.get('genai_usage_label', 'N/A')} (coded: {form_data.get('genai_usage', 'N/A')})
Q{9 + q_offset}. AI Language Usage: {form_data.get('llm_language_usage', 'N/A')}

Section 4: Demographics and Background
---------------------------------------
Q{10 + q_offset}. Age: {form_data.get('age', 'N/A')}
Q{11 + q_offset}. Gender: {form_data.get('gender', 'N/A')}
Q{12 + q_offset}. Education Level: {form_data.get('education_level', 'N/A')}{f" ({form_data.get('education_level_other')})" if form_data.get('education_level_other') else ''}
Q{13 + q_offset}. Field of Study: {form_data.get('field_of_study', 'N/A')}{f" ({form_data.get('field_of_study_other')})" if form_data.get('field_of_study_other') else ''}
Q{14 + q_offset}. Learning Language Preference: {form_data.get('learning_language_preference', 'N/A')}
"""
        
        st.text_area(
            "Your responses:",
            value=response_text,
            height=400,
            disabled=True
        )
        
        st.info("Your responses have been saved. You may now proceed to the next section.")
    else:
        st.error("No form data found. Please submit the survey again.")

