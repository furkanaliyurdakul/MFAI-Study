# MFAI-Study: Multilingual Fairness in AI-Assisted Learning

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.39.0-red.svg)](https://streamlit.io)
[![License](https://img.shields.io/badge/license-Research-green.svg)](LICENSE)

A research platform investigating **fairness across languages** in AI-powered learning environments. Built with Streamlit and Google Gemini 2.5 Flash for KU Leuven Master's thesis research.

**Key Features:**
- 🌍 6-language experimental conditions (en, de, nl, tr, sq, hi)
- 🤖 Consistent AI model across all conditions (Gemini 2.5 Flash)
- 📊 Comprehensive analytics and interaction logging
- 🔒 GDPR-compliant pseudonymization
- 📈 Real-time UEQ benchmarking and knowledge assessment

## Study Design

This platform investigates **fairness across languages** in AI-powered learning environments. Participants are randomly assigned to one of **6 language conditions**:
- **English (en)** – Germanic, high-resource
- **German (de)** – Germanic, high-resource
- **Dutch (nl)** – Germanic, mid-resource
- **Turkish (tr)** – Turkic, mid-resource
- **Albanian (sq)** – Indo-European (Albanian branch), low-resource
- **Hindi (hi)** – Indo-European (Indo-Aryan), high-resource

The experimental manipulation is the **language of LLM responses** while course materials remain in English. All participants interact with the same GenAI tutor (Google Gemini 2.5 Flash) but receive explanations in their assigned language.

### Reproducibility Note
- **Model**: `gemini-2.5-flash` via Google GenAI SDK
- **Temperature**: 0.2 (low variance for consistency)
- **Top-p**: 0.95 (nucleus sampling)
- **Model provider & version**: Stored in `meta/experiment_meta.json` for each session
- **Content version**: Tracked in session metadata for longitudinal comparisons

---
## Directory structure

Each time a participant opens the app a new _session directory_ is created under **`output/`**:

```
output/
  ├── 20250427_120345_Alex_Smith/   # <timestamp>_<fake-name>
  │   ├── profile/                  # uploaded & parsed student profile
  │   ├── knowledge_test/           # quiz results
  │   ├── learning_logs/            # tutor‑chat logs
  │   ├── ueq/                      # UEQ answers + benchmark
  │   ├── analytics/                # interaction analytics & final research data
  │   │   ├── interaction_analytics.json
  │   │   └── final_research_analytics.json  # ★ Comprehensive research data
  │   └── meta/                     # page‑timer JSON, etc.
  └── research_analysis.json        # ★ Aggregate analysis across all sessions
```

### Pseudonymisation in a nutshell
1. When `SessionManager` starts it creates the session ID `(timestamp + fake name)` and writes it to `output/…/condition.txt`.
2. A **pseudonymised** copy of the profile replaces the real name with the fake name.  Down‑stream components read only this copy.
3. All later artefacts (chat logs, test results, UEQ) live in the same folder and therefore inherit the fake identifier.

---
## Key components
| file | role |
|------|------|
| `main.py` | navigation, page timer, session wiring, language routing |
| `Gemini_UI.py` | multilingual tutor UI & helpers (preview-only mode) |
| `session_manager.py` | directory & pseudonym handling, analytics consolidation |
| `personalized_learning_logger.py` | buffered file logger for tutor interactions |
| `testui_profilesurvey.py` | student‑profile questionnaire |
| `testui_knowledgetest.py` | 5‑item multiple‑choice quiz (Q5 partial credit) |
| `testui_ueqsurvey.py` | 26‑item UEQ short form + benchmark (reverse-coded) |
| `page_timer.py` | per‑page dwell‑time measurement (monotonic clock) |
| `constants.py` | single source of truth for platform constants |
| `authentication.py` | credential-based language assignment & dev mode |
| `presence_tracker.py` | concurrent session limiting via Supabase |
| `capacity_manager.py` | non-blocking wait UI for platform capacity |
| `supabase_storage.py` | cloud backup for session data (PII-safe) |

---
## Language Assignment

Language conditions are assigned via **authentication credentials** (not visible to participants).  
Each credential maps to one of the 6 language codes (en, de, nl, tr, sq, hi).

```python
# authentication.py – credential configuration
{"username": "pilot_en_01", "language_code": "en"}
{"username": "pilot_de_01", "language_code": "de"}
# ... etc for all 6 languages
```

The language is **locked at login** and stored in:
1. `st.session_state["language_code"]` – runtime state
2. `output/<session>/meta/experiment_meta.json` – permanent record

**No UI toggle exists** to prevent participants from changing language mid-session.

---
## Selecting the study condition *(personalised vs generic)*

Participants must **not** know which branch they get.  
The choice is therefore made in **code, not in the UI**.

```python
# main.py – near the top
DEFAULT_PERSONALISED: bool = True  # True → personalised, False → generic
```

1. Set the flag, save the file, restart the Streamlit server.
2. The flag is copied into `st.session_state["use_personalisation"]` and cached for the whole run.
3. `SessionManager` writes the chosen condition to `output/…/condition.txt` so it is visible during analysis.

*Tip:* when `DEV_MODE = True` you can still uncomment the old facilitator radio‑button to flip the condition interactively while testing.

---
## Research Analytics System

This platform includes a comprehensive analytics system that automatically consolidates all research data into a single JSON file per session. When participants complete the study (finish UEQ survey), a `final_research_analytics.json` file is generated containing:

- **Session info**: ID, condition, pseudonym, timestamps
- **Page timings**: Time spent on each phase of the study
- **Interaction data**: AI interactions, slide explanations, manual chat
- **UEQ results**: Survey responses, scale scores, benchmark grades
- **Knowledge test**: Answers, accuracy, performance metrics
- **Summary metrics**: Learning efficiency, engagement patterns

### Analytics Tools

```bash
# Generate final analytics for all sessions
python generate_final_analytics.py

# Generate for specific session
python generate_final_analytics.py --session 20250922_142955_Winter_Smith

# Create aggregate research analysis
python analyze_research_data.py
```

See **`ANALYTICS_DOCUMENTATION.md`** for complete details on the analytics system and research data structure.

---
## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/furkanaliyurdakul/MFAI-Study.git
cd MFAI-Study

# Create virtual environment
python -m venv .venv

# Activate environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements_fixed.txt
```

### Running Locally

```bash
# Launch the Streamlit server
streamlit run main.py

# App will open at http://localhost:8501
```

### External Access (Optional)

```bash
# Expose for remote participants using ngrok
ngrok http 8501
# Copy the forwarded URL for participants
```

## 📦 Data Output

All session data appears under **`output/`** immediately during the session.  
After data collection, zip the `output/` folder for analysis.

## 📖 Additional Documentation

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** – Production deployment instructions
- **[ANALYTICS_DOCUMENTATION.md](ANALYTICS_DOCUMENTATION.md)** – Analytics schema and metrics
- **[docs/](docs/)** – Technical documentation and guides

## 🔒 Privacy & Ethics

- **Pseudonymization:** Real names replaced with fake identifiers at collection
- **GDPR Compliant:** Full participant information and consent process
- **Ethics Approval:** KU Leuven Research Ethics Committee
- **Data Security:** Local storage + optional encrypted cloud backup

## 📧 Contact

**Researcher:** Furkan Ali Yurdakul  
**Affiliation:** KU Leuven / FH Dortmund  
**Study:** Master's Thesis - Multilingual Fairness in AI-Assisted Learning

For questions about the study or technical issues, please open an issue or contact the research team.

## 📝 Citation

If you use this platform or adapt it for your research:

```bibtex
@mastersthesis{yurdakul2025mfai,
  author = {Yurdakul, Furkan Ali},
  title = {Multilingual Fairness in AI-Assisted Learning: An Experimental Study},
  school = {KU Leuven / FH Dortmund},
  year = {2025},
  type = {Master's Thesis}
}
```

## ⚠️ Research Use Only

This platform is designed specifically for academic research. The codebase includes comprehensive logging and analytics to support rigorous analysis of language fairness in AI-assisted learning.

---

**Built with:** Python 3.11+ | Streamlit 1.39.0 | Google Gemini 2.5 Flash | Supabase (optional)
