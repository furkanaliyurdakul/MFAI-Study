import streamlit as st

FAST_TEST_MODE = st.session_state.get("fast_test_mode")

# Get current language from session state
current_language = st.session_state.get("language_code", "en")

# Language names dictionary
language_names = {
    "en": "English",
    "de": "German",
    "nl": "Dutch",
    "tr": "Turkish",
    "sq": "Albanian",
    "hi": "Hindi"
}

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
    """Map usage frequency labels to integers 0-3"""
    mapping = {
        "Never": 0,
        "Yes, once or rarely": 1,
        "Yes, occasionally": 2,
        "Yes, frequently": 3,
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
    init_form_field("genai_familiarity")
    init_form_field("genai_usage")
    init_form_field("genai_knowledge")
    init_form_field("formal_ai_training")
    init_form_field("gender")
    init_form_field("education_level")
    init_form_field("field_of_study")
    init_form_field("learning_language_preference")
    init_form_field("topic_interest")
    init_form_field("llm_language_usage")
    init_form_field("llm_usage_frequency")

    st.header("Section 1: Language Proficiency")

    # Q1 - Native language (pre-filled from credentials)
    st.text_input(
        "Q1. What is your native language?",
        value=language_names.get(current_language, "English"),
        disabled=True,
        key="native_language_display",
        help="Your assigned study language was set during enrollment and determines your experimental condition. This cannot be changed as we are researching how different languages affect learning with AI assistants. If you believe this is incorrect, please inform the research team."
    )

    # Q2 - English proficiency
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

    # Q3 - Native language proficiency
    native_proficiency = st.select_slider(
        f"Q3. How would you rate your proficiency in {language_names.get(current_language, 'your native language')}? *",
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
    st.header("Section 2: Prior Knowledge of Generative AI")

    # Q4 - Familiarity with GenAI tools
    genai_familiarity = st.radio(
        "Q4. How familiar are you with generative AI tools (e.g., ChatGPT, DALL-E)? *",
        [
            "1 - Not at all familiar",
            "2 - Slightly familiar",
            "3 - Moderately familiar",
            "4 - Familiar",
            "5 - Very familiar"
        ],
        index=None,
        key="genai_familiarity",
        help="Rate your general awareness and exposure to generative AI tools"
    )

    # Q5 - Usage frequency
    genai_usage = st.radio(
        "Q5. Have you used any generative AI tools before this study? *",
        [
            "Never",
            "Yes, once or rarely",
            "Yes, occasionally",
            "Yes, frequently"
        ],
        index=None,
        key="genai_usage",
        help="How often have you actually used tools like ChatGPT?"
    )

    # Q6 - Self-assessed knowledge
    genai_knowledge = st.radio(
        "Q6. \"I know a lot about generative AI (how it works and its concepts).\" *",
        [
            "1 - Strongly Disagree",
            "2 - Disagree",
            "3 - Neutral",
            "4 - Agree",
            "5 - Strongly Agree"
        ],
        index=None,
        key="genai_knowledge",
        help="Rate your agreement with this statement about your prior knowledge"
    )

    # Q7 - Formal training
    formal_ai_training = st.radio(
        "Q7. Have you ever taken a course or formal training in artificial intelligence or machine learning? *",
        ["Yes", "No"],
        index=None,
        key="formal_ai_training",
        help="This includes university courses, online courses, or professional training"
    )

    st.markdown("---")
    st.header("Section 3: Demographics and Background")

    # Q8 - Age
    age = st.number_input(
        "Q8. What is your age (in years)? *",
        min_value=16,
        max_value=100,
        value=20,
        step=1,
        key="age",
        help="Enter your age in years"
    )

    # Q9 - Gender
    gender = st.radio(
        "Q9. What is your gender? *",
        ["Male", "Female", "Non-binary", "Prefer not to say"],
        index=None,
        key="gender"
    )

    # Q10 - Education level
    education_level = st.radio(
        "Q10. What is your current level of education? *",
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

    # Q11 - Field of study
    field_of_study = st.radio(
        "Q11. What is your field of study or professional area? *",
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

    # Q12 - Learning language preference
    learning_language_preference = st.radio(
        "Q12. Do you generally prefer to learn new material in English or your native language? *",
        [
            "Primarily English",
            "Both English and native language equally",
            "Primarily native language"
        ],
        index=None,
        key="learning_language_preference",
        help="This helps us understand your language learning preferences"
    )

    # Q13 - Topic interest
    topic_interest = st.radio(
        "Q13. \"I am interested in learning about generative AI.\" *",
        [
            "1 - Strongly Disagree",
            "2 - Disagree",
            "3 - Neutral",
            "4 - Agree",
            "5 - Strongly Agree"
        ],
        index=None,
        key="topic_interest",
        help="Rate your interest in learning about generative AI"
    )

    # Q14 - LLM language usage
    llm_language_usage = st.radio(
        "Q14. When you use AI tools like ChatGPT or Gemini, which language do you primarily use? *",
        [
            "Primarily English",
            "Both English and native language equally",
            "Primarily native language"
        ],
        index=None,
        key="llm_language_usage",
        help="This helps us understand your prior experience with AI tools in different languages"
    )

    # Q15 - LLM usage frequency
    llm_usage_frequency = st.radio(
        "Q15. How often do you use AI tools like ChatGPT or Gemini? *",
        [
            "Daily",
            "Weekly",
            "Monthly",
            "Rarely",
            "Never"
        ],
        index=None,
        key="llm_usage_frequency",
        help="This helps us understand your experience level with AI assistants"
    )

    st.markdown("---")

    # Submit button
    submit_button = st.button("Submit Survey", key="submit_profile_survey", type="primary")

    if submit_button:
        if FAST_TEST_MODE:
            # Fast test mode with synthetic data (both labels and numeric codes)
            st.session_state.form_data = {
                "native_language": language_names.get(current_language, "English"),
                "english_proficiency": 5,
                "native_proficiency": 7,
                "genai_familiarity_label": "3 - Moderately familiar",
                "genai_familiarity": 3,
                "genai_usage_label": "Yes, occasionally",
                "genai_usage": 2,
                "genai_knowledge_label": "3 - Neutral",
                "genai_knowledge": 3,
                "formal_ai_training": "No",
                "age": 24,
                "gender": "Prefer not to say",
                "education_level": "Master's degree",
                "field_of_study": "Computer Science/IT",
                "learning_language_preference": "Both equally / No strong preference",
                "topic_interest_label": "4 - Agree",
                "topic_interest": 4,
                "llm_language_usage": "Both English and native language equally",
                "llm_usage_frequency": "Weekly"
            }
            st.session_state.show_review = True
            st.success("FAST_TEST_MODE: Synthetic profile created.")
            st.rerun()
        else:
            # Validate all required fields
            all_fields_filled = (
                english_proficiency is not None
                and native_proficiency is not None
                and genai_familiarity is not None
                and genai_usage is not None
                and genai_knowledge is not None
                and formal_ai_training is not None
                and age is not None
                and gender is not None
                and education_level is not None
                and (education_level != "Other" or (education_level_other and education_level_other.strip()))
                and field_of_study is not None
                and (field_of_study != "Other" or (field_of_study_other and field_of_study_other.strip()))
                and learning_language_preference is not None
                and topic_interest is not None
                and llm_language_usage is not None
                and llm_usage_frequency is not None
            )

            if all_fields_filled:
                # Store form data with both labels (for display) and numeric codes (for analysis)
                st.session_state.form_data = {
                    "native_language": language_names.get(current_language, "English"),
                    "english_proficiency": int(english_proficiency),
                    "native_proficiency": int(native_proficiency),
                    "genai_familiarity_label": genai_familiarity,
                    "genai_familiarity": familiarity_to_int(genai_familiarity),
                    "genai_usage_label": genai_usage,
                    "genai_usage": usage_to_int(genai_usage),
                    "genai_knowledge_label": genai_knowledge,
                    "genai_knowledge": likert_5_to_int(genai_knowledge),
                    "formal_ai_training": formal_ai_training,
                    "age": int(age),
                    "gender": gender,
                    "education_level": education_level,
                    "education_level_other": education_level_other if education_level_other else "",
                    "field_of_study": field_of_study,
                    "field_of_study_other": field_of_study_other if field_of_study_other else "",
                    "learning_language_preference": learning_language_preference,
                    "topic_interest_label": topic_interest,
                    "topic_interest": likert_5_to_int(topic_interest),
                    "llm_language_usage": llm_language_usage,
                    "llm_usage_frequency": llm_usage_frequency
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
        response_text = f"""Participant Profile Survey Responses
=====================================

Section 1: Language Proficiency
--------------------------------
Q1. Native Language: {form_data.get('native_language', 'N/A')}
Q2. English Proficiency: {form_data.get('english_proficiency', 'N/A')}/7
Q3. Native Language Proficiency: {form_data.get('native_proficiency', 'N/A')}/7

Section 2: Prior Knowledge of Generative AI
--------------------------------------------
Q4. Familiarity with GenAI Tools: {form_data.get('genai_familiarity_label', 'N/A')} (coded: {form_data.get('genai_familiarity', 'N/A')})
Q5. Previous Usage: {form_data.get('genai_usage_label', 'N/A')} (coded: {form_data.get('genai_usage', 'N/A')})
Q6. Self-Assessed Knowledge: {form_data.get('genai_knowledge_label', 'N/A')} (coded: {form_data.get('genai_knowledge', 'N/A')})
Q7. Formal AI Training: {form_data.get('formal_ai_training', 'N/A')}

Section 3: Demographics and Background
---------------------------------------
Q8. Age: {form_data.get('age', 'N/A')}
Q9. Gender: {form_data.get('gender', 'N/A')}
Q10. Education Level: {form_data.get('education_level', 'N/A')}{f" ({form_data.get('education_level_other')})" if form_data.get('education_level_other') else ''}
Q11. Field of Study: {form_data.get('field_of_study', 'N/A')}{f" ({form_data.get('field_of_study_other')})" if form_data.get('field_of_study_other') else ''}
Q12. Learning Language Preference: {form_data.get('learning_language_preference', 'N/A')}
Q13. Topic Interest: {form_data.get('topic_interest_label', 'N/A')} (coded: {form_data.get('topic_interest', 'N/A')})
Q14. LLM Language Usage: {form_data.get('llm_language_usage', 'N/A')}
Q15. LLM Usage Frequency: {form_data.get('llm_usage_frequency', 'N/A')}
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
