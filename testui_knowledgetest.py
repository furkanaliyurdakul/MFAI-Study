import datetime
import os

import streamlit as st
from config import config
import page_timer

# Start timing this page
page_timer.start("knowledge_test")

st.title(f"Knowledge Test - {config.course.course_title}")

st.markdown(
    """
This assessment measures your knowledge of key concepts in Generative AI, including Large Language Models (LLMs), supervised learning, and AI applications, as covered in the lecture materials.

The assessment consists of 8 questions. Question 5 is a multiple-select question where you can choose more than one answer. You receive 0.25 points for each correct choice in Question 5 (maximum 1.0 point). All other questions are single-choice and worth 1 point each.

**Note:** This test is for research purposes only. Your score does not affect your participation. Please answer to the best of your ability, as your honest performance helps us compare learning outcomes across different language groups.

There is no time limit.

Ready to begin?
"""
)

# Question 1 - Single choice radio button
st.markdown(
    "**1. Which of these is the best definition of 'Generative AI'?**"
)
q1_options = [
    "Artificial intelligence systems that can map from an input A to an output B.",
    "Any web-based application that generates text.",
    "AI that can produce high-quality content, such as text, images, and audio.",
    "A form of web search.",
]
q1 = st.radio("Select one answer for question 1:", q1_options, key="knowledge_q1", index=None)

# Question 2 - Single choice radio button
st.markdown(
    "**2. Which of these is the most accurate description of a Large Language Model (LLM)?**"
)
q2_options = [
    "It generates text by finding a writing partner to work with you.",
    "It generates text by using supervised learning to carry out web search.",
    "It generates text by repeatedly predicting the next word.",
    "It generates text by repeatedly predicting words in random order.",
]
q2 = st.radio("Select one answer for question 2:", q2_options, key="knowledge_q2", index=None)

# Question 3 - Single choice radio button
st.markdown(
    "**3. True or False: Because an LLM has learned from many web pages on the internet, its answers are always more trustworthy than other sources on the internet.**"
)
q3_options = [
    "True",
    "False",
]
q3 = st.radio("Select one answer for question 3:", q3_options, key="knowledge_q3", index=None)

# Question 4 - Single choice radio button
st.markdown(
    "**4. Why do we call AI a general-purpose technology, similar to electricity or the internet?**"
)
q4_options = [
    "Because it is useful for many different tasks.",
    "Because it can chat.",
    "Because it includes both supervised learning and generative AI.",
    "Because it can be accessed via the general web.",
]
q4 = st.radio("Select one answer for question 4:", q4_options, key="knowledge_q4", index=None)

# Question 5 - Multiple choice checkboxes
st.markdown(
    "**5. Which of these tasks are good examples of what an LLM or other Generative AI system can do? Select all that apply. (Q5 score is out of 4 options.)**"
)
q5_option_a = st.checkbox("Summarise a long article into a short paragraph.", key="knowledge_q5_a")
q5_option_b = st.checkbox("Earn a university degree on behalf of a student.", key="knowledge_q5_b")
q5_option_c = st.checkbox("Translate a paragraph from English into Turkish.", key="knowledge_q5_c")
q5_option_d = st.checkbox("Proofread a text and suggest clearer wording.", key="knowledge_q5_d")

# Question 6 - Single choice radio button
st.markdown(
    "**6. A hospital uses AI to look at X-ray images and label each one as 'healthy' or 'disease present'. According to the course, which AI tool does this mainly use?**"
)
q6_options = [
    "Generative AI",
    "Supervised learning",
    "Unsupervised learning",
    "Reinforcement learning",
]
q6 = st.radio("Select one answer for question 6:", q6_options, key="knowledge_q6", index=None)

# Question 7 - Single choice radio button
st.markdown(
    "**7. You hear of a company using an LLM to automatically route incoming customer emails to the right department. Which of these use cases is it most likely to be?**"
)
q7_options = [
    "Employees are copy-pasting the emails into a web interface to decide how to route them.",
    "The company has a software-based application that uses an LLM to automatically route the emails.",
]
q7 = st.radio("Select one answer for question 7:", q7_options, key="knowledge_q7", index=None)

# Question 8 - Single choice radio button
st.markdown(
    "**8. According to the lecture, what is one advantage of training a very large AI model (instead of a small one) on more and more data?**"
)
q8_options = [
    "A large model quickly reaches a performance limit and then stops improving.",
    "A large model keeps improving its performance as you give it more data, while a small model improves much less.",
    "A large model always performs worse than a small model on real tasks.",
    "Only small models can be used with supervised learning.",
]
q8 = st.radio("Select one answer for question 8:", q8_options, key="knowledge_q8", index=None)

# Correct Answers
correct_answers = {
    "knowledge_q1": "AI that can produce high-quality content, such as text, images, and audio.",
    "knowledge_q2": "It generates text by repeatedly predicting the next word.",
    "knowledge_q3": "False",
    "knowledge_q4": "Because it is useful for many different tasks.",
    "knowledge_q5_a": True,  # Summarise a long article
    "knowledge_q5_b": False,  # Earn a university degree (incorrect option)
    "knowledge_q5_c": True,  # Translate a paragraph
    "knowledge_q5_d": True,  # Proofread a text
    "knowledge_q6": "Supervised learning",
    "knowledge_q7": "The company has a software-based application that uses an LLM to automatically route the emails.",
    "knowledge_q8": "A large model keeps improving its performance as you give it more data, while a small model improves much less.",
}

# Initialize session state for test completion status
if "test_submitted" not in st.session_state:
    st.session_state.test_submitted = False

# Disable inputs if test has already been submitted
if st.session_state.test_submitted:
    st.warning("You have already submitted this test. Your results have been saved.")

    # Display the saved results if available
    if "result_summary" in st.session_state:
        st.success(f"You scored {st.session_state.score:.2f}/8!")
        st.markdown("### Your Test Results")
        st.markdown(
            st.session_state.result_summary.replace("\n", "<br>"),
            unsafe_allow_html=True,
        )
else:
    # Two-step submission process
    if "confirm_submission" not in st.session_state:
        st.session_state.confirm_submission = False

    if st.button("Submit and calculate score"):
        # Enforce completion of all single-choice items
        required = {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q6": q6, "q7": q7, "q8": q8}
        if any(v is None or v == "" for v in required.values()):
            st.warning("Please answer all questions before submitting.")
            st.stop()
        
        st.session_state.confirm_submission = True

    if st.session_state.confirm_submission:
        st.warning(
            "⚠️ Are you sure you want to submit? You won't be able to retake this test."
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Cancel"):
                st.session_state.confirm_submission = False
                st.rerun()
        with col2:
            if st.button("Confirm Submission"):
                # Timer will automatically stop when navigating to next page
                
                # Q5 flags and 4-option partial credit
                q5_flags = {
                    "A": bool(q5_option_a),
                    "B": bool(q5_option_b),
                    "C": bool(q5_option_c),
                    "D": bool(q5_option_d),
                }
                q5_correct = sum([
                    int(q5_flags["A"] == correct_answers["knowledge_q5_a"]),
                    int(q5_flags["B"] == correct_answers["knowledge_q5_b"]),
                    int(q5_flags["C"] == correct_answers["knowledge_q5_c"]),
                    int(q5_flags["D"] == correct_answers["knowledge_q5_d"]),
                ])
                q5_score = q5_correct / 4.0
                
                # Build JSON result dict
                answers_dict = {
                    "q1": {"user": q1, "correct": q1 == correct_answers["knowledge_q1"]},
                    "q2": {"user": q2, "correct": q2 == correct_answers["knowledge_q2"]},
                    "q3": {"user": q3, "correct": q3 == correct_answers["knowledge_q3"]},
                    "q4": {"user": q4, "correct": q4 == correct_answers["knowledge_q4"]},
                    "q5": {
                        "A": (q5_flags["A"] == correct_answers["knowledge_q5_a"]),
                        "B": (q5_flags["B"] == correct_answers["knowledge_q5_b"]),
                        "C": (q5_flags["C"] == correct_answers["knowledge_q5_c"]),
                        "D": (q5_flags["D"] == correct_answers["knowledge_q5_d"]),
                    },
                    "q6": {"user": q6, "correct": q6 == correct_answers["knowledge_q6"]},
                    "q7": {"user": q7, "correct": q7 == correct_answers["knowledge_q7"]},
                    "q8": {"user": q8, "correct": q8 == correct_answers["knowledge_q8"]},
                }
                
                total_correct = (
                    int(answers_dict["q1"]["correct"]) + int(answers_dict["q2"]["correct"]) +
                    int(answers_dict["q3"]["correct"]) + int(answers_dict["q4"]["correct"]) +
                    q5_score + int(answers_dict["q6"]["correct"]) + int(answers_dict["q7"]["correct"]) +
                    int(answers_dict["q8"]["correct"])
                )
                
                result = {
                    "answers": answers_dict,
                    "q5_subscore": q5_score,
                    "score_total": float(total_correct),
                    "max_score": 8.0,  # treat Q5 as 1.0 in total
                }
                
                # Save via session manager
                from session_manager import get_session_manager
                sm = get_session_manager()
                sm.save_knowledge_test_results(result)
                st.success("Knowledge test saved.")

                # Store the score in session state to mark test as completed
                st.session_state.score = total_correct
                st.session_state.test_submitted = True

                st.success(f"You scored {total_correct:.2f}/8!")

                # Summary with detailed breakdown
                q5_response = []
                if q5_option_a:
                    q5_response.append("A")
                if q5_option_b:
                    q5_response.append("B")
                if q5_option_c:
                    q5_response.append("C")
                if q5_option_d:
                    q5_response.append("D")
                q5_text = ", ".join(q5_response) if q5_response else "None selected"
                
                result_summary = f"""
Your Responses:
--------------------------------------
1. {q1} {'✓' if answers_dict['q1']['correct'] else '✗'}
2. {q2} {'✓' if answers_dict['q2']['correct'] else '✗'}
3. {q3} {'✓' if answers_dict['q3']['correct'] else '✗'}
4. {q4} {'✓' if answers_dict['q4']['correct'] else '✗'}
5. {q5_text} (Partial credit: {q5_correct}/4 options correct)
6. {q6} {'✓' if answers_dict['q6']['correct'] else '✗'}
7. {q7} {'✓' if answers_dict['q7']['correct'] else '✗'}
8. {q8} {'✓' if answers_dict['q8']['correct'] else '✗'}

Total Score: {total_correct:.2f}/8
"""

                # Store the result summary in session state
                st.session_state.result_summary = result_summary

                # Get the session info for display
                session_info = sm.get_session_info()
                fake_name = session_info["fake_name"]

                st.success(
                    f"Your results have been saved with pseudonymized ID: {fake_name}"
                )

                # Display detailed results with correct/incorrect answers highlighted
                st.markdown("### Your Test Results")

                # Format the results with colored indicators for correct/incorrect answers
                formatted_results = "<h4>Question 1:</h4>"
                formatted_results += f"<p>Your answer: {q1} {'✅' if answers_dict['q1']['correct'] else '❌'}</p>"
                if not answers_dict["q1"]["correct"]:
                    formatted_results += (
                        f"<p>Correct answer: {correct_answers['knowledge_q1']}</p>"
                    )

                formatted_results += "<h4>Question 2:</h4>"
                formatted_results += f"<p>Your answer: {q2} {'✅' if answers_dict['q2']['correct'] else '❌'}</p>"
                if not answers_dict["q2"]["correct"]:
                    formatted_results += (
                        f"<p>Correct answer: {correct_answers['knowledge_q2']}</p>"
                    )

                formatted_results += "<h4>Question 3:</h4>"
                formatted_results += f"<p>Your answer: {q3} {'✅' if answers_dict['q3']['correct'] else '❌'}</p>"
                if not answers_dict["q3"]["correct"]:
                    formatted_results += (
                        f"<p>Correct answer: {correct_answers['knowledge_q3']}</p>"
                    )

                formatted_results += "<h4>Question 4:</h4>"
                formatted_results += f"<p>Your answer: {q4} {'✅' if answers_dict['q4']['correct'] else '❌'}</p>"
                if not answers_dict["q4"]["correct"]:
                    formatted_results += (
                        f"<p>Correct answer: {correct_answers['knowledge_q4']}</p>"
                    )

                formatted_results += "<h4>Question 5 (Multiple Select):</h4>"
                formatted_results += f"<p>Your answers: {q5_text}</p>"
                formatted_results += f"<p>Score: {q5_correct}/4 options correct (partial credit: {q5_score:.2f}/1.0)</p>"
                formatted_results += "<p>Correct answers: A (Summarise), C (Translate), D (Proofread)</p>"

                formatted_results += "<h4>Question 6:</h4>"
                formatted_results += f"<p>Your answer: {q6} {'✅' if answers_dict['q6']['correct'] else '❌'}</p>"
                if not answers_dict["q6"]["correct"]:
                    formatted_results += (
                        f"<p>Correct answer: {correct_answers['knowledge_q6']}</p>"
                    )

                formatted_results += "<h4>Question 7:</h4>"
                formatted_results += f"<p>Your answer: {q7} {'✅' if answers_dict['q7']['correct'] else '❌'}</p>"
                if not answers_dict["q7"]["correct"]:
                    formatted_results += (
                        f"<p>Correct answer: {correct_answers['knowledge_q7']}</p>"
                    )

                formatted_results += "<h4>Question 8:</h4>"
                formatted_results += f"<p>Your answer: {q8} {'✅' if answers_dict['q8']['correct'] else '❌'}</p>"
                if not answers_dict["q8"]["correct"]:
                    formatted_results += (
                        f"<p>Correct answer: {correct_answers['knowledge_q8']}</p>"
                    )

                formatted_results += f"<h4>Total Score: {total_correct:.2f}/8</h4>"

                st.markdown(formatted_results, unsafe_allow_html=True)
