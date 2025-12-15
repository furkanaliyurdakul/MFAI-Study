# Deployment Checklist (Pilot Day)

## Config & Env
- [ ] Python >= 3.10 installed
- [ ] `pip install -r requirements.txt` completed successfully
- [ ] `GEMINI_API_KEY` set (or `.streamlit/secrets.toml` with `[google].api_key`)
- [ ] `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_BUCKET` set (if cloud mirror used)

## Preflight
- [ ] `python tools/preflight_check.py` returns **✅ ALL GOOD**

## Content freeze
- [ ] Slides exported to `uploads/ppt/<course>/picture/Slide_###.png`
- [ ] Transcript file present and readable
- [ ] Run app once to confirm `meta/experiment_meta.json` writes per session

## Capacity & Presence
- [ ] Supabase SQL cron executed (auto-abandon after 2 min)
- [ ] `capacity_manager` default max = 2
- [ ] Heartbeat page key correctly set to `"learning"`

## Data outputs (per session)
- [ ] `meta/interaction_counts.json` present after learning phase
- [ ] `knowledge_test/knowledge_test_results.json` written after test completion
- [ ] `ueq/ueq_responses.json` written after UEQ completion
- [ ] `meta/page_durations.json` tracking all page transitions
- [ ] `analytics/final_research_analytics.json` generated without errors

## Facilitator smoke test
- [ ] Open **🧪 Pilot: Multilingual Smoke Test** page
- [ ] For each language credential (en, de, nl, tr, sq, hi): run once; lang check shows ✅
- [ ] Verify latency is reasonable (<5000ms for typical queries)

## Authentication & Language Assignment
- [ ] All 6 language credentials created in `authentication.py`
- [ ] Each credential maps to correct language code (en, de, nl, tr, sq, hi)
- [ ] Dev mode credentials have `dev_mode=True`, `fast_test_mode=True`
- [ ] Participant credentials have both flags set to `False`

## Session Data Validation
- [ ] Test session completes full flow without errors
- [ ] `output/<session_id>/` directory structure is complete
- [ ] PII files (`original_profile.*`) present in output but NOT uploaded to Supabase
- [ ] Pseudonymized files use fake names from session ID

## Presence Tracking
- [ ] Heartbeat updates visible in Supabase `sessions` table
- [ ] `current_page` field updates correctly as user navigates
- [ ] `is_in_interview` flag true only on learning page
- [ ] Concurrent session limit enforced (max 2 active interviews)

## Post-Session Cleanup
- [ ] Session marked complete after UEQ submission
- [ ] Logs flushed to disk (no buffered data lost)
- [ ] `final_research_analytics.json` includes all expected fields
- [ ] No Python exceptions in terminal/logs during full session

## Final Go/No-Go Decision
- [ ] All critical checks (✅) passed
- [ ] Warnings (⚠️) reviewed and accepted or mitigated
- [ ] Facilitator has backup plan for technical issues
- [ ] Contact information for tech support available to participants
