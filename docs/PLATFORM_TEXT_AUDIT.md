# Platform Text Audit - User-Facing Content Review
**Date:** December 15, 2025  
**Purpose:** Identify outdated references, unclear instructions, potential bias, and missing information

---

## 🔴 CRITICAL ISSUES FOUND

### 1. **HOME PAGE - Study Description Contains WRONG Research Focus**

**Location:** `main.py` lines 430-433

**Current Text:**
```
You are taking part in our KU Leuven study on **AI‑generated, personalised learning explanations**.  
We are studying whether tailoring explanations to a learner's background affects their understanding 
of the material compared to providing general explanations.
```

**❌ PROBLEM:** This describes a PERSONALIZATION study, but your current research is about LANGUAGE FAIRNESS and MULTILINGUAL LEARNING, not personalization!

**✅ CORRECT TEXT SHOULD BE:**
```
You are taking part in our KU Leuven study on **language fairness in AI-assisted learning**.  
We are investigating whether the language of instruction affects learning outcomes when using 
large language models (LLMs) as study assistants.
```

---

### 2. **HOME PAGE - Misleading Step Description**

**Location:** `main.py` line 444 (Step 2)

**Current Text:**
```
| 2 | **Student Profile Survey** | ≈ 8 min | background, learning goals |
```

**❌ PROBLEM:** Says "learning goals" but the survey does NOT ask about learning goals - it collects demographics and GenAI knowledge only

**✅ CORRECT TEXT:**
```
| 2 | **Student Profile Survey** | ≈ 8 min | demographics, language skills, AI knowledge |
```

---

### 3. **HOME PAGE - Time Estimates Don't Match Reality**

**Location:** `main.py` lines 444-448

**Current Text:**
```
| 3 | **{LABEL}** using LLM | ≈ 25 min | questions to the LLM (optional) |
| 4 | **Knowledge Test** | ≈ 10 min | answers to 5 quiz items |
```

**❌ PROBLEMS:** 
- Says "5 quiz items" but knowledge test has **8 questions**
- Says questions to LLM are "optional" but this is misleading - participants should engage

**✅ CORRECT TEXT:**
```
| 3 | **{LABEL}** using LLM | ≈ 25 min | interact with AI assistant |
| 4 | **Knowledge Test** | ≈ 10 min | answers to 8 quiz questions |
```

---

### 4. **HOME PAGE - Biased Language About Data Recording**

**Location:** `main.py` lines 465-467

**Current Text:**
```
We log your inputs and the system's responses to analyse the tutor's effectiveness.  
Your name is replaced by a random code; you may stop at any moment without penalty.
```

**❌ PROBLEM:** Says "tutor's effectiveness" which could bias participants to think the AI is teaching them (authority bias)

**✅ CORRECT TEXT:**
```
We log your interactions with the AI assistant to analyze learning effectiveness across different languages.  
Your identity is pseudonymized; you may stop at any moment without penalty.
```

---

### 5. **PROFILE SURVEY - Incorrect Study Description**

**Location:** `testui_profilesurvey.py` lines 74-76

**Current Text:**
```
This survey collects background variables (language skills, prior AI knowledge, 
and demographics) used only for analysis of learning outcomes. It is not used for 
personalizing the AI tutor.
```

**❌ PROBLEM:** Says "AI tutor" which implies teaching/tutoring relationship (bias)

**✅ CORRECT TEXT:**
```
This survey collects background variables (language skills, prior AI knowledge, 
and demographics) used only for analysis of learning outcomes. The AI assistant 
provides the same learning content to all participants in your assigned language.
```

---

### 6. **LEARNING PAGE - Misleading Title and Description**

**Location:** `main.py` lines 591-594

**Current Text:**
```
st.title(f"AI Learning Tutor")
st.markdown(
    f"This component lets you generate explanations with the uploaded slides and lecture audio."
)
```

**❌ PROBLEMS:**
- "AI Learning Tutor" implies tutoring/teaching (authority bias)
- "uploaded slides" suggests user action, but content is pre-loaded
- "generate explanations" might confuse participants about what they should do

**✅ CORRECT TEXT:**
```
st.title(f"AI Learning Assistant")
st.markdown(
    f"Interact with the AI assistant to explore the course materials. You can ask questions 
    about the slides or request explanations of concepts covered in the lecture."
)
```

---

### 7. **LEARNING PAGE - Content Info Box Misleading**

**Location:** `main.py` line 700

**Current Text:**
```
st.sidebar.info(f"**{config.course.course_title}**\n\nUsing pre-loaded course materials:\n- {config.course.total_slides} lecture slides\n- Complete audio transcription")
```

**✅ ACCEPTABLE** but could be clearer about what participants should do

**✅ IMPROVED TEXT:**
```
st.sidebar.info(f"**Course Content**\n\n{config.course.course_title}\n\n✓ {config.course.total_slides} lecture slides loaded\n✓ Lecture transcription available\n\n💡 Ask questions or request explanations about any concept")
```

---

### 8. **KNOWLEDGE TEST - Misleading Introduction**

**Location:** `testui_knowledgetest.py` lines 12-24

**Current Text:**
```
Welcome to the knowledge assessment on Generative AI. This test evaluates your understanding 
of key concepts covered in the lecture materials, including Large Language Models (LLMs), 
supervised learning, and AI applications.

The assessment consists of 8 questions that cover fundamental concepts in Generative AI. 
Questions 5 is a multiple-select question where you can choose more than one correct answer 
(partial credit applies). All other questions are single-choice.

Feel free to trust your intuition and apply the knowledge you've gained from the lecture materials. 
Your spontaneous responses often best reflect your true understanding of these important concepts.

At the end of the test, you'll be able to see your score and review your answers. Remember, this 
is a learning opportunity to help you gauge your knowledge in Generative AI.

Ready to begin? Let's explore your understanding together!
```

**⚠️ POTENTIAL ISSUES:**
- "evaluate your understanding" might stress participants
- "trust your intuition" could bias toward guessing
- "learning opportunity" contradicts it being a test
- "Let's explore your understanding together!" is too casual/encouraging (experimenter bias)

**✅ IMPROVED TEXT:**
```
This assessment measures your knowledge of key concepts in Generative AI, including Large Language 
Models (LLMs), supervised learning, and AI applications, as covered in the lecture materials.

The assessment consists of 8 questions. Question 5 is a multiple-select question where you can 
choose more than one answer (partial credit applies). All other questions are single-choice.

Please answer based on what you learned from the materials. There is no time limit.

Ready to begin?
```

---

### 9. **UEQ SURVEY - Instructions Could Bias Responses**

**Location:** `testui_ueqsurvey.py` lines 71-83

**Current Text:**
```
This questionnaire helps us evaluate your experience with the platform. For each item, please 
select a point on the scale that best represents your impression.

Please decide spontaneously. Don't think too long about your decision to make sure that you 
convey your original impression.

Sometimes you may not be completely sure about your agreement with a particular attribute or 
you may find that the attribute does not apply completely to the particular product.

Nevertheless, please tick a circle in every line. It is your personal opinion that counts.

Please remember: there is no wrong or right answer!
```

**✅ ACCEPTABLE** - This is standard UEQ text, but could clarify what "the platform" refers to

**✅ SLIGHTLY IMPROVED:**
```
This questionnaire evaluates your experience with the AI learning assistant and platform. 
For each item, select the point on the scale that best represents your impression.

Please decide spontaneously. Don't think too long to ensure you convey your immediate impression.

Even if you're not completely sure about an attribute or find it doesn't fully apply, please 
respond to every item. Your personal opinion is what matters.

There are no wrong or right answers!
```

---

### 10. **COMPLETION PAGE - Misleading Research Description**

**Location:** `main.py` lines 1086-1088

**Current Text:**
```
**Research Impact**: Your participation contributes to understanding how personalized AI 
explanations affect learning outcomes in complex scientific topics.
```

**❌ PROBLEM:** Again mentions "personalized AI explanations" - WRONG STUDY!

**✅ CORRECT TEXT:**
```
**Research Impact**: Your participation contributes to understanding whether language choice 
in AI-assisted learning creates educational inequalities, helping ensure fair access to 
AI-powered education globally.
```

---

## 🟡 MODERATE ISSUES (Clarity & Completeness)

### 11. **HOME PAGE - Missing Information About Language Assignment**

**Location:** `main.py` lines 430-470

**❌ PROBLEM:** Never explains to participants that they are assigned a specific language or why

**✅ ADD THIS AFTER STEP TABLE:**
```
#### Your Study Conditions
You have been assigned to complete this session in **{LANGUAGE_NAME}**. All learning materials 
and AI interactions will be in this language. This is part of our research comparing learning 
outcomes across different languages.
```

---

### 12. **PROFILE SURVEY - Q1 Unclear Why Native Language is Pre-filled**

**Location:** `testui_profilesurvey.py` lines 91-97

**Current Text:**
```
st.text_input(
    "Q1. What is your native language?",
    value=language_names.get(current_language, "English"),
    disabled=True,
    key="native_language_display",
    help="Pre-selected based on your login credentials"
)
```

**❌ PROBLEM:** Participants might be confused why they can't change it or think it's wrong

**✅ IMPROVED HELP TEXT:**
```
help="Your assigned study language, based on your participant credentials. This determines the 
language of all learning materials in this session."
```

---

### 13. **KNOWLEDGE TEST - No Explanation of Scoring System**

**Location:** `testui_knowledgetest.py` line 12-24

**❌ PROBLEM:** Doesn't explain how Q5 partial credit works

**✅ ADD AFTER "partial credit applies":**
```
Question 5 is a multiple-select question where you can choose more than one answer. You receive 
0.25 points for each correct choice (maximum 1.0 point). All other questions are worth 1 point each.
```

---

### 14. **LEARNING PAGE - No Instructions on How to Interact**

**Location:** `main.py` lines 591-594

**❌ PROBLEM:** Participants might not know what to do or how to ask questions

**✅ ADD CLEAR INSTRUCTIONS:**
```
### How to Use This Section

You can interact with the AI assistant in two ways:

1. **Ask about specific slides**: Click "Explain this slide" below any slide to get an explanation
2. **Ask your own questions**: Type questions in the chat box about any concept from the lecture

The AI assistant has access to all {config.course.total_slides} slides and the full lecture 
transcription. Feel free to explore the content at your own pace.
```

---

### 15. **COMPLETION PAGE - Missing Next Steps for Participant**

**Location:** `main.py` lines 1160-1170

**❌ PROBLEM:** Doesn't tell participants what to do next (wait for facilitator? leave? interview?)

**✅ ADD:**
```
### Next Steps

Please inform the facilitator that you have completed the session. They will guide you through 
the final brief interview (approximately 5 minutes).

Thank you for your time and participation!
```

---

## 🟢 MINOR ISSUES (Style & Consistency)

### 16. **Inconsistent Terminology**
- Sometimes "AI tutor" (wrong)
- Sometimes "AI assistant" (correct)
- Sometimes "platform" (ambiguous)
- Sometimes "system" (technical)

**✅ FIX:** Use "AI assistant" or "AI learning assistant" consistently everywhere

---

### 17. **Inconsistent Capitalization**
- "Student Profile Survey" vs "student profile survey"
- "Knowledge Test" vs "knowledge test"

**✅ FIX:** Use title case consistently when referring to section names

---

### 18. **Time Estimates Precision**
- Uses "≈ 8 min", "≈ 25 min" format
- But then says "~ 60 minutes" for total

**✅ FIX:** Use consistent format (either ≈ or ~ throughout)

---

## ✅ THINGS THAT ARE GOOD (Keep As Is)

1. ✅ GDPR consent language is clear and compliant
2. ✅ Pseudonymization is well explained
3. ✅ "No right or wrong answers" messaging reduces test anxiety
4. ✅ UEQ standard text maintains comparability with other studies
5. ✅ Withdrawal rights are clearly stated
6. ✅ Data security messaging is appropriate
7. ✅ Profile survey questions are neutral and clear
8. ✅ Knowledge test questions are well-written
9. ✅ Navigation labels are clear
10. ✅ Disabled buttons prevent sequence violations

---

## 📋 PRIORITY ACTION ITEMS

### HIGH PRIORITY (Must Fix - Accuracy & Bias)
1. ❗ Fix study description on HOME page (personalization → language fairness)
2. ❗ Fix "5 quiz items" → "8 questions"  
3. ❗ Remove "AI tutor" terminology (use "AI assistant")
4. ❗ Fix completion page research description
5. ❗ Clarify profile survey purpose (not for personalization)

### MEDIUM PRIORITY (Clarity & Completeness)
6. ⚠️ Add explanation of language assignment
7. ⚠️ Add instructions for learning page interaction
8. ⚠️ Clarify Q5 partial credit scoring
9. ⚠️ Fix "learning goals" → "demographics"
10. ⚠️ Add "next steps" on completion page

### LOW PRIORITY (Consistency & Polish)
11. 🔹 Standardize terminology throughout
12. 🔹 Fix time estimate formatting
13. 🔹 Consistent capitalization
14. 🔹 Improve learning page content info

---

## 🎯 RECOMMENDED TEXT UPDATES

I can now implement all these fixes systematically. Would you like me to:

1. **Fix all HIGH PRIORITY items immediately** (critical accuracy issues)
2. **Then address MEDIUM PRIORITY** (clarity improvements)
3. **Finally polish LOW PRIORITY** (consistency)

Or would you like to review specific sections first before I make changes?

---

## 📊 SUMMARY STATISTICS

- **Total pages audited:** 6 (Home, Profile Survey, Learning, Knowledge Test, UEQ, Completion)
- **Critical issues found:** 10
- **Moderate issues found:** 5
- **Minor issues found:** 3
- **Items that are good:** 10

**Overall Assessment:** Platform text needs significant updates to match current research focus (language fairness, NOT personalization). Several references to old study design remain.
