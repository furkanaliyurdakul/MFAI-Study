# Project Organization Guide

## Recommended Directory Structure

```
Gemini_UI V2/
├── main.py                          # 🎯 MAIN ENTRY POINT - start here
│
├── core/                            # Core application modules
│   ├── authentication.py
│   ├── config.py
│   ├── constants.py
│   ├── session_manager.py
│   └── page_timer.py
│
├── components/                      # UI components & pages
│   ├── login_page.py
│   ├── Gemini_UI.py                # Learning tutor UI
│   ├── testui_profilesurvey.py
│   ├── testui_knowledgetest.py
│   └── testui_ueqsurvey.py
│
├── infrastructure/                  # Backend services
│   ├── capacity_manager.py
│   ├── presence_tracker.py
│   ├── supabase_storage.py
│   └── personalized_learning_logger.py
│
├── pages/                          # Streamlit multi-page app pages
│   └── 999_Pilot_Multilingual_SmokeTest.py
│
├── tools/                          # Utility scripts
│   ├── preflight_check.py         # Pre-pilot validation
│   ├── generate_final_analytics.py
│   └── analyze_research_data.py
│
├── tests/                          # Test files
│   ├── test.py
│   └── test_authentication.py
│
├── docs/                           # Documentation
│   ├── ANALYTICS_DOCUMENTATION.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── DEPLOYMENT_CHECKLIST.md
│   └── PROJECT_STRUCTURE.md       # This file
│
├── uploads/                        # Course materials
│   ├── ppt/                       # Slide images
│   └── audio/                     # Audio files (if any)
│
├── transcriptions/                 # Course transcripts
│
├── output/                         # Session data (gitignored)
│   └── YYYYMMDD_HHMMSS_FakeName/
│
├── .streamlit/                     # Streamlit config
│   └── secrets.toml
│
├── requirements.txt                # Python dependencies
├── README.md                       # Project overview
├── .gitignore
├── install.bat                     # Windows setup script
└── start.bat                       # Windows launcher
```

## Quick Start Workflow

1. **First time setup:**
   ```bash
   pip install -r requirements.txt
   python tools/preflight_check.py
   ```

2. **Before each pilot session:**
   - Review `DEPLOYMENT_CHECKLIST.md`
   - Run `python tools/preflight_check.py`
   - Test with smoke test page

3. **Run the platform:**
   ```bash
   streamlit run main.py
   # or on Windows:
   start.bat
   ```

## File Categories

### 🎯 Entry Points
- `main.py` - Primary Streamlit app

### 🔧 Core Modules (keep in root or move to `core/`)
- `authentication.py` - Login & language assignment
- `config.py` - Platform configuration
- `constants.py` - Single source of truth for constants
- `session_manager.py` - Session lifecycle & data management
- `page_timer.py` - Page duration tracking

### 🎨 UI Components (keep in root or move to `components/`)
- `login_page.py` - Authentication interface
- `Gemini_UI.py` - Learning tutor UI (preview mode)
- `testui_profilesurvey.py` - Profile survey
- `testui_knowledgetest.py` - Knowledge test
- `testui_ueqsurvey.py` - UEQ survey

### 🏗️ Infrastructure (keep in root or move to `infrastructure/`)
- `capacity_manager.py` - Concurrent session limiting
- `presence_tracker.py` - Heartbeat & session tracking
- `supabase_storage.py` - Cloud backup
- `personalized_learning_logger.py` - Interaction logging

### 📊 Data & Output
- `output/` - Session data (automatically created)
- `uploads/` - Course materials
- `transcriptions/` - Course transcripts

### 🛠️ Tools & Scripts
- `tools/preflight_check.py` - Pre-deployment validation
- Other analysis scripts

### 📚 Documentation
- `README.md` - Project overview
- `ANALYTICS_DOCUMENTATION.md` - Analytics system
- `DEPLOYMENT_GUIDE.md` - Deployment instructions
- `DEPLOYMENT_CHECKLIST.md` - Pre-pilot checklist

## Migration Guide (Optional)

If you want to reorganize files into subdirectories, update imports:

```python
# Before:
from authentication import get_auth_manager

# After (if moved to core/):
from core.authentication import get_auth_manager
```

**Recommendation:** Keep current flat structure until after pilot sessions to avoid breaking imports. The current organization works well for a Streamlit app of this size.

## File Cleanup Candidates

Consider removing or archiving:
- `requirements_fixed.txt` (superseded by `requirements.txt`)
- `test.py` (if no longer needed)
- Old output sessions (archive after analysis)
