# System Design: Multilingual Fairness in AI-Assisted Learning Platform

## Research Objective

This platform conducts a controlled experiment to investigate **language-based inequalities in AI-assisted education**. The core research question is:

> **Does the language of AI instruction affect learning outcomes when using Large Language Models (LLMs) as educational assistants?**

**Critical Design Principle:** This is **NOT a personalization study**. All participants receive identical, standardized content. The **only experimental manipulation** is the language in which the AI responds to user queries.

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION & LANGUAGE ASSIGNMENT                  │
│  - Credential-based login (6 language cohorts)                          │
│  - Automatic language assignment via username                           │
│  - Session creation with pseudonymization                               │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SEQUENTIAL STUDY FLOW                           │
│                                                                         │
│  1. Home Page → Study Introduction & Consent                           │
│  2. Profile Survey → Demographics & Language Skills                    │
│  3. Learning Session → AI-Assisted Content Exploration                 │
│  4. Knowledge Test → 5-8 Multiple Choice Questions                     │
│  5. UEQ Survey → User Experience Questionnaire (26 items)              │
│  6. Completion → Session End & Data Finalization                       │
│                                                                         │
│  ⚠️ ONE-WAY PROGRESSION: No backward navigation (research integrity)   │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     DUAL DATA PERSISTENCE LAYER                         │
│                                                                         │
│  LOCAL FILE SYSTEM                  SUPABASE CLOUD DATABASE            │
│  ├─ output/                         ├─ session_analytics               │
│  │  ├─ english_cohort/              ├─ knowledge_test_results          │
│  │  ├─ german_cohort/               ├─ ueq_scores                      │
│  │  ├─ dutch_cohort/                ├─ learning_interactions           │
│  │  ├─ turkish_cohort/              ├─ page_timings                    │
│  │  ├─ albanian_cohort/             └─ presence_tracking               │
│  │  └─ hindi_cohort/                                                   │
│  │     └─ YYYYMMDD_HHMMSS_Pseudo_Name-suffix/                         │
│  │        ├─ profile/                                                  │
│  │        ├─ learning_logs/                                            │
│  │        ├─ knowledge_test/                                           │
│  │        ├─ ueq/                                                      │
│  │        ├─ analytics/                                                │
│  │        └─ meta/                                                     │
│                                                                         │
│  💾 Files: JSON + TXT        ☁️ Database: Real-time analytics          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components Deep Dive

### 1. Authentication & Language Assignment (`authentication.py`)

**Purpose:** Assign participants to experimental conditions via credentials

**Mechanism:**
- **6 credential types** corresponding to 6 language conditions:
  - `english_learner` → English (en) - High-resource control
  - `german_learner` → German (de) - High-resource European
  - `dutch_learner` → Dutch (nl) - High-resource European
  - `turkish_learner` → Turkish (tr) - Medium-resource
  - `albanian_learner` → Albanian (sq) - Low-resource
  - `hindi_learner` → Hindi (hi) - High-resource non-European
- Credentials determine: Language code, data folder prefix, special modes
- **Dev credentials** available for testing with full access

**Key Features:**
- SHA256 password hashing with salt
- Credential-based session isolation
- Automatic language code injection into session state
- Data organization by language cohort

---

### 2. Session Management (`session_manager.py`)

**Purpose:** Lifecycle management for participant sessions

**Session Creation:**
```
Session ID Format: YYYYMMDD_HHMMSS_PseudoName-4hexchars
Example: 20260119_143022_Parker_Nguyen-a7b3

Output Structure:
output/
└── {cohort}/                    # english_cohort, german_cohort, etc.
    └── {session_id}/
        ├── profile/              # Profile survey JSON
        ├── learning_logs/        # Interaction logs (JSON + TXT)
        ├── knowledge_test/       # Test results JSON
        ├── ueq/                  # UEQ responses JSON
        ├── analytics/            # Derived metrics
        └── meta/                 # Experiment metadata (model, timestamps)
```

**Data Responsibilities:**
- Profile pseudonymization (no PII stored)
- JSON serialization for all research data
- Interaction counting (slide explanations, manual chats)
- Final analytics consolidation
- Automatic sync to Supabase (if enabled)

**Pseudonymization:**
- Real names NEVER stored
- Fake names generated from pool (26 first names × 26 last names)
- Session ID includes pseudonym for human readability

---

### 3. Learning Interaction System (`Gemini_UI.py`, `learning_interaction_logger.py`)

**Purpose:** AI-powered content explanation with language manipulation

**Content Pipeline:**
```
English Course Materials (Fixed)
    ↓
[Slide Images] + [Lecture Transcription]
    ↓
Google Gemini 2.5 Flash API
    ↓
Prompt Construction (IN TARGET LANGUAGE)
    ↓
AI Response (IN TARGET LANGUAGE)
    ↓
Interaction Logging & Analytics
```

**Key Constraints:**
- **Slides:** Always English (course materials fixed)
- **Transcription:** Always English (lecture audio pre-processed)
- **AI Prompt:** Translated to target language
- **AI Response:** In target language
- **User Input:** Expected in target language

**Interaction Types:**
1. **Slide Explanation (INTERACTION_SLIDE):** User clicks "Explain this slide" button
2. **Manual Chat (INTERACTION_CHAT):** User types question in text box
3. **Prime Context:** System setup (not counted as user interaction)

**Prompt Structure (Translated to Target Language):**
```json
{
  "System": "You are an expert tutor explaining {course_title}...",
  "Role": "Educational assistant providing clear explanations...",
  "Objective": "Explain {slide_name} based on provided materials...",
  "Instructions": {
    "Formatting": "Use clear structure, examples, analogies...",
    "Tone": "Professional yet approachable...",
    "Guidelines": [
      "Use clear language appropriate for the topic",
      "Provide concrete examples",
      "Be thorough but concise",
      "Focus on practical understanding"
    ]
  },
  "Context": {
    "Slides": {
      "content": "<slide_text_extracted>",
      "usage_hint": "Primary source for this explanation"
    },
    "Transcript": {
      "content": "<lecture_transcription>",
      "usage_hint": "Professor's spoken explanation"
    }
  }
}
```

**CRITICAL DIFFERENCE FROM ATTACHED IMAGE:**
- **No personalization** - student profiles collected but NOT used in prompts
- Profiles used ONLY for demographic analysis (age, gender, language proficiency)
- All participants get identical standardized prompts
- Fairness comparison requires controlled, non-personalized content

---

### 4. Assessment System

#### 4.1 Student Profile Survey (`testui_profilesurvey.py`)

**Purpose:** Collect demographics and baseline characteristics (NOT for personalization)

**Data Collected:**
- Study language (read-only, assigned via credential)
- English proficiency (1-7 scale, unless English native)
- Native language proficiency (1-7 scale)
- GenAI familiarity and usage frequency
- Language used with AI assistants
- Age, gender, education level
- Field of study, degree program
- Prior {topic} knowledge

**Usage:**
- Stored for demographic analysis
- NOT used for prompt customization
- Enables subgroup analysis (e.g., high vs low English proficiency)

#### 4.2 Knowledge Test (`testui_knowledgetest.py`)

**Purpose:** Measure learning outcomes

**Structure:**
- 5-8 multiple-choice questions
- Fixed questions (same across all languages)
- Immediate feedback on submission
- Scoring: Total correct, percentage, pass/fail grade

**JSON Structure:**
```json
{
  "session_id": "...",
  "answers": {
    "q1": {"user": "A", "correct": true},
    "q2": {"user": "C", "correct": false},
    ...
  },
  "score_total": 4,
  "max_score": 5,
  "percentage": 80.0,
  "grade": "pass"
}
```

**Analytics Sync:**
- Per-question answers and correctness
- Overall score and grade
- Enables item-level analysis (e.g., which questions show language bias)

#### 4.3 UEQ Survey (`testui_ueqsurvey.py`)

**Purpose:** Measure user experience quality

**Methodology:**
- Standard UEQ instrument (26 paired items)
- 7-point semantic differential scale
- Calculates 6 dimensions: Attractiveness, Perspicuity, Efficiency, Dependability, Stimulation, Novelty
- Benchmark comparison against UEQ database

**CRITICAL FRAMING:**
- **Non-English Groups:** "Compare your {language} experience to how you imagine English would be"
- **English Group:** "Rate your actual experience (control group)"
- Ensures comparative evaluation across conditions

**Additional Feedback:**
- 2 open-ended questions:
  1. Language comparison (would English be better/worse/same?)
  2. What stood out about using AI in {language}?
- Mandatory minimum 50 characters (qualitative data quality)

---

### 5. Analytics & Data Syncing (`analytics_syncer.py`)

**Purpose:** Real-time data replication to Supabase for monitoring

**Supabase Tables:**
1. **session_analytics** - Master session table
   - Session metadata, completion flags, aggregated scores
   - Status tracking (active, completed, abandoned)

2. **knowledge_test_results** - Per-question test data
   - Individual answer correctness and responses
   - Enables item analysis

3. **ueq_scores** - UEQ dimension scores
   - 6 UEQ dimensions + benchmark grades
   - Comment field for qualitative feedback

4. **learning_interactions** - Interaction logs
   - Slide explanations vs manual chats
   - Timestamps, interaction types
   - Interaction counts (research metric)

5. **page_timings** - Time spent on each page
   - Learning session duration
   - Survey completion times

6. **presence_tracking** - Concurrent session monitoring
   - Active sessions by language
   - Heartbeat-based liveness detection
   - Capacity management (max 2 concurrent per language)

**Sync Strategy:**
- Write-on-save: Every save operation triggers Supabase sync
- Dual persistence: Files remain authoritative source
- Real-time dashboard updates
- Failure tolerance: Platform works offline if Supabase unavailable

---

### 6. Presence & Capacity Management (`presence_tracker.py`, `capacity_manager.py`)

**Purpose:** Prevent experimental contamination via participant overlap

**Problem:** Multiple concurrent participants in same language could:
- Discuss materials outside platform
- Share answers to knowledge test
- Compromise experimental independence

**Solution:**
- **Heartbeat System:** JavaScript injection sends ping every 30 seconds
- **Supabase Tracking:** Real-time presence table with session status
- **Capacity Limits:** Max 2 concurrent sessions per language (configurable)
- **Entry Warning:** Participants warned if capacity exceeded

**Status Management:**
- Active: Regular heartbeats detected
- Inactive: No heartbeat for 2 minutes
- Abandoned: Session started but never completed
- Completed: Full study flow finished

---

### 7. Configuration System (`config.py`, `constants.py`, `prompt_translations.py`)

**Purpose:** Centralized configuration with multilingual support

**Course Configuration:**
```python
@dataclass
class CourseConfig:
    course_title: str = "Introduction to Cancer Biology"
    course_code: str = "BIO301"
    total_slides: int = 86
    slides_directory: str = "picture"
    video_filename: str = "Genetics_of_Cancer_video.mp4"
    transcription_filename: str = "turbo_transcription_Introduction to Cancer Biology.txt"
```

**Model Configuration:**
```python
@dataclass
class ModelConfig:
    model_name: str = "gemini-2.0-flash-exp"
    temperature: float = 0.2  # Low variance for reproducibility
    top_p: float = 0.95
    model_provider: str = "Google GenAI"
```

**Language Support:**
```python
LANGUAGES = {
    "en": {"name": "English", "resource_level": "high"},
    "de": {"name": "German", "resource_level": "high"},
    "nl": {"name": "Dutch", "resource_level": "high"},
    "tr": {"name": "Turkish", "resource_level": "medium"},
    "sq": {"name": "Albanian", "resource_level": "low"},
    "hi": {"name": "Hindi", "resource_level": "medium"}
}
```

**Prompt Translations:**
- Full prompt structure translated to each language
- System instructions, role definitions, guidelines
- Avoids English bias in AI responses
- File: `prompt_translations.py` contains complete translations

---

## Data Flow: Complete Session Lifecycle

```
1. LOGIN (authentication.py)
   ├─ Credential verification
   ├─ Language code extraction
   ├─ Session creation in SessionManager
   └─ Supabase session_analytics record created

2. CONSENT (main.py → home page)
   ├─ PDF consent form display
   ├─ E-signature collection
   └─ Consent flag updated in Supabase

3. PROFILE SURVEY (testui_profilesurvey.py)
   ├─ Form completion (demographics, language skills)
   ├─ Numeric mapping (Likert scales → integers)
   ├─ JSON save: output/{cohort}/{session_id}/profile/
   ├─ Pseudonymization applied
   └─ Sync to Supabase session_analytics

4. LEARNING SESSION (main.py → learning page)
   ├─ Course content loaded (slides + transcription)
   ├─ Gemini chat initialized
   ├─ User interactions:
   │  ├─ Slide explanations (button clicks)
   │  └─ Manual chat inputs
   ├─ Interaction logging (types, timestamps, content)
   ├─ JSON save: output/{cohort}/{session_id}/learning_logs/
   └─ Sync to Supabase learning_interactions

5. KNOWLEDGE TEST (testui_knowledgetest.py)
   ├─ 5-8 multiple choice questions
   ├─ Answer collection and validation
   ├─ Scoring calculation
   ├─ JSON save: output/{cohort}/{session_id}/knowledge_test/
   └─ Sync to Supabase knowledge_test_results

6. UEQ SURVEY (testui_ueqsurvey.py)
   ├─ 26 UEQ items (7-point scales)
   ├─ Dimension calculation (6 scales)
   ├─ Benchmark comparison
   ├─ Open feedback collection (min 50 chars)
   ├─ JSON save: output/{cohort}/{session_id}/ueq/
   └─ Sync to Supabase ueq_scores

7. COMPLETION (main.py → completion page)
   ├─ Final analytics consolidation
   ├─ Page timing export
   ├─ Session status = completed
   └─ Thank you message + study code

8. BACKGROUND PROCESSES
   ├─ Page timer tracking (page_timer.py)
   ├─ Presence heartbeats (presence_tracker.py)
   └─ Automatic cleanup (abandoned sessions after 2 hours)
```

---

## Technical Stack

### Frontend
- **Streamlit 1.39.0** - Web UI framework
- **Python 3.11+** - Core runtime
- **JavaScript** - Heartbeat injection for presence tracking

### AI/ML
- **Google Gemini 2.5 Flash** - LLM for explanations
- **Google GenAI SDK** - API client (new SDK, not legacy genai)
- **langid** - Language detection for response verification

### Backend
- **Supabase** - PostgreSQL database + real-time subscriptions
- **supabase-py** - Python client library
- Service key authentication for write access

### Data & Analytics
- **Pandas** - Data manipulation
- **JSON** - Primary serialization format
- **pathlib** - File system operations

### Monitoring
- **atexit** - Cleanup hooks for data finalization
- **datetime** - UTC timestamps for reproducibility
- **logging** - Debug and error tracking

---

## Key Design Decisions & Rationale

### 1. Why No Personalization?

**Research Question:** Language effects, not personalization effects

**Implications:**
- Identical prompts across participants (within language)
- Profile data for analysis only, not prompt customization
- Cleaner causal inference (language is sole variable)
- Matches attached image's "Personalization" box but inverts it - we explicitly AVOID personalization

### 2. Why English Course Materials?

**Realism:** Most university courses use English materials globally

**Control:** Ensures language variable is isolated to AI interactions

**Practical:** Avoids translation artifacts in core content

### 3. Why Credential-Based Assignment?

**Randomization:** Instructor distributes credentials randomly

**Blinding:** Participants unaware of comparative design

**Data Organization:** Cohort folders enable clean analysis

### 4. Why Dual Persistence (Files + Database)?

**Redundancy:** File system = authoritative, Supabase = monitoring

**Offline Mode:** Platform works without internet

**Analytics:** Real-time dashboard access for researchers

**Archiving:** Files can be exported, version controlled

### 5. Why One-Way Navigation?

**Data Integrity:** Prevents answer revision after seeing later questions

**Test Validity:** Knowledge test can't be retaken after more learning

**Response Bias:** Profile answers shouldn't be influenced by later experience

---

## Comparison to Attached System Diagram

### Similarities
- Uses LLMs for educational content generation
- Includes evaluation component (knowledge test + UEQ)
- Structured pipeline from input to assessment

### Critical Differences

| Attached System | Your System |
|----------------|-------------|
| **Personalization:** Student profile → customized methods | **Standardization:** Profile for analysis only, NOT personalization |
| **Focus:** Tailored learning | **Focus:** Language fairness comparison |
| **Variable:** Personalization level | **Variable:** Language of AI responses |
| **Materials:** Possibly multilingual | **Materials:** English only (control) |
| **Goal:** Optimize individual learning | **Goal:** Detect language-based inequalities |

**Your system is a COMPARATIVE EXPERIMENTAL STUDY, not a personalized learning platform.**

---

## Research Output Structure

```
output/
├── english_cohort/          # Control group (n = ?)
│   ├── session_001/
│   ├── session_002/
│   └── ...
├── german_cohort/           # High-resource European (n = ?)
│   └── ...
├── dutch_cohort/            # High-resource European (n = ?)
│   └── ...
├── turkish_cohort/          # Medium-resource (n = ?)
│   └── ...
├── albanian_cohort/         # Low-resource (n = ?)
│   └── ...
└── hindi_cohort/            # High-resource non-European (n = ?)
    └── ...

Each session folder contains:
├── profile/pseudonymized_profile.json
├── learning_logs/
│   ├── learning_log_TIMESTAMP.txt
│   └── learning_interactions.json
├── knowledge_test/knowledge_test_results.json
├── ueq/ueq_responses.json
├── analytics/
│   ├── interaction_analytics.json
│   └── final_research_analytics.json
└── meta/
    ├── experiment_meta.json
    └── page_timings.json
```

---

## Current System Status

### Implemented ✅
- Full authentication with 6 language conditions
- Complete session lifecycle (login → completion)
- Profile, learning, knowledge test, UEQ
- Dual data persistence (files + Supabase)
- Real-time analytics syncing
- Presence tracking and capacity management
- Page timing and interaction logging
- Pseudonymization and GDPR compliance
- Multilingual prompt translations

### Recent Fixes ✅
- Knowledge test field mapping bug fixed
- Analytics logger handles empty interactions
- Loading spinners for AI responses
- Comparative UEQ framing for language groups
- Mandatory feedback with validation

### Testing Status 🧪
- Pilot testing completed with multiple participants
- Data recovery tools created (resync_pilot_knowledge_tests.py)
- Dev mode available for smoke testing

---

## How to Use This Prompt with Your LLM

**Context:** Give this document to your LLM and ask:

> "I have built this research platform for my Master's thesis. Based on this system design, help me with [specific task]:
> - Analyzing collected data patterns
> - Improving specific components
> - Debugging data flow issues
> - Designing new analytical queries
> - Writing research paper sections"

**The LLM will now understand:**
- Your research goal (language fairness, NOT personalization)
- System architecture (authentication → assessment → analytics)
- Data structure (cohort folders, JSON format)
- Key constraints (standardized prompts, no personalization)
- Technical stack (Streamlit, Gemini, Supabase)

---

## Additional Context Files

For deeper understanding, reference these in your workspace:

- **README.md** - Project overview and quick start
- **ANALYTICS_DOCUMENTATION.md** - Database schema and queries
- **DEPLOYMENT_GUIDE.md** - Server setup and configuration
- **PLATFORM_TEXT_AUDIT.md** - UX and messaging review
- **docs/supabase_analytics_schema.sql** - Database DDL

---

**Study:** Multilingual Fairness in AI-Assisted Learning  
**Institution:** KU Leuven / FH Dortmund  
**Researcher:** Furkan Ali Yurdakul  
**Thesis:** Master's Thesis 2025  
**Model:** Google Gemini 2.5 Flash (gemini-2.0-flash-exp)  
**Languages:** English (control), German, Dutch, Turkish, Albanian, Hindi
