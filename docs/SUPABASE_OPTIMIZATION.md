# Supabase Optimization Roadmap

## ✅ CURRENT STATE (Verified)

| Component | Status | Details |
|-----------|--------|---------|
| **presence table** | ✅ Optimal | 75 rows, core heartbeat tracking working |
| **session_analytics table** | ✅ Optimal | 78 rows, 90+ columns for comprehensive data |
| **Indexes** | ⚠️ Basic | Has basic indexes, needs optimization |
| **RLS Policies** | ✅ Working | Service role and anon key configured |
| **Analysis capability** | ⚠️ Limited | Only aggregate data, no question-level detail |

---

## 🚀 RECOMMENDED ENHANCEMENTS

### TIER 1: CRITICAL (High Performance Impact)
**Performance Indexes** - Run these FIRST
```
✓ Heartbeat detection: presence(status, last_seen DESC)
✓ Interview counting: presence(is_in_interview, last_seen DESC)  
✓ User history: presence(user_id, started_at DESC)
✓ Language analysis: presence(language_code, created_at DESC)
✓ Session analytics: multiple composite indexes
```
**Impact**: 10-100x faster queries for capacity checks, cohort analysis

### TIER 2: RESEARCH TABLES (Rich Data Collection)
**6 new tables for detailed analysis:**

1. **interaction_logs** - Per-interaction details
   - What: Every AI explanation, chat message, etc.
   - Why: Analyze AI response quality, interaction patterns
   - Columns: user_input, ai_response_length, response_time_ms, tokens_used, cost_estimate

2. **ueq_detailed_scores** - Question-level UEQ data
   - What: Individual question responses (not just aggregated)
   - Why: Detailed fairness analysis per question category
   - Columns: question_number, scale_dimension, score (-3 to +3)

3. **knowledge_test_detailed** - Question-level test responses
   - What: Individual question answers and correctness
   - Why: Identify which concepts are harder per language
   - Columns: question_text, correct_answer, is_correct, time_spent_seconds, topic

4. **language_analysis** - Language-specific metrics
   - What: Language proficiency, comprehension issues, clarity scores
   - Why: PRIMARY TABLE for language fairness research
   - Columns: proficiency levels, comprehension_issues[], clarity_score, request_for_clarification_count

5. **engagement_metrics** - Page-level engagement
   - What: Time per page, interactions, scroll depth, focus loss
   - Why: Identify if certain pages are problematic
   - Columns: time_on_page_seconds, interactions, scroll_depth_percent, idle_time

6. **cohort_comparison** - Pre-aggregated statistics
   - What: Cached statistics per language cohort
   - Why: Fast dashboards without real-time aggregation
   - Columns: avg_scores, completion_rates, durations per language

### TIER 3: ANALYSIS VIEWS (Pre-built Queries)

| View | Purpose | Key Columns |
|------|---------|------------|
| **v_session_summary** | Complete session overview | session_id, duration_minutes, completion_status, ai_interactions |
| **v_language_performance** | Cohort comparison | language, sessions, avg_score, completion_rate, avg_duration |
| **v_active_sessions** | Real-time monitoring | session_id, current_page, seconds_since_activity, status |
| **v_engagement_by_page** | Page analytics | page_name, avg_time, avg_interactions, avg_idleness |

---

## 🔧 IMPLEMENTATION ROADMAP

### Step 1: Run Performance Indexes (5 min)
```bash
# Go to Supabase SQL Editor
# Copy SQL from: tools/optimize_supabase.py output
# Paste "STEP 1" - Performance Indexes section
# Expected indexes: 7 new indexes
```
**Benefit**: Immediate 10-100x query performance improvement

### Step 2: Create Analysis Tables (10 min)
```bash
# Copy SQL "STEP 2" - New Analysis Tables section
# Runs: 6 tables + 11 indexes
# No data required - just schema
```
**Benefit**: Enables detailed data collection

### Step 3: Create Views (5 min)
```bash
# Copy SQL "STEP 3" - Analysis Views section
# Runs: 4 views for analysis
# Uses existing + new tables
```
**Benefit**: Pre-built dashboards ready to use

### Step 4: Update Python Code (30 min - NOT URGENT)
Currently: Basic session data collection
Next: Populate new tables from:
- `learning_interaction_logger.py` → interaction_logs
- `testui_ueqsurvey.py` → ueq_detailed_scores
- `testui_knowledgetest.py` → knowledge_test_detailed
- Session profile → language_analysis
- `page_timer.py` → engagement_metrics

---

## 📊 ANALYSIS EXAMPLES (After Optimization)

### Language Fairness Analysis
```sql
SELECT language_code, 
       COUNT(*) as sessions,
       AVG(knowledge_test_score) as avg_score,
       AVG(comprehension_issues::text[]) as issues_per_language
FROM language_analysis
GROUP BY language_code;
```
**Shows**: Is one language systematically harder/easier?

### Engagement Patterns by Language
```sql
SELECT language_code, page_name,
       AVG(time_on_page_seconds) as avg_time,
       AVG(focus_lost_count) as avg_distractions
FROM engagement_metrics em
JOIN session_analytics sa ON em.session_id = sa.session_id
GROUP BY language_code, page_name;
```
**Shows**: Which pages struggle per language?

### AI Interaction Quality
```sql
SELECT language_code,
       ROUND(AVG(response_time_ms)) as avg_response_ms,
       ROUND(AVG(ai_response_length / tokens_used::float), 2) as tokens_per_char,
       COUNT(*) as interactions
FROM interaction_logs
GROUP BY language_code;
```
**Shows**: Is AI faster/more efficient for certain languages?

---

## ✅ DEPLOYMENT CHECKLIST

- [ ] Run STEP 1: Performance Indexes (Supabase SQL Editor)
- [ ] Run STEP 2: Analysis Tables (Supabase SQL Editor)  
- [ ] Run STEP 3: Analysis Views (Supabase SQL Editor)
- [ ] Test new tables: `python tools/setup_supabase.py`
- [ ] (Later) Update analytics_syncer.py to populate new tables
- [ ] (Later) Create Streamlit dashboard using views

---

## 🎯 EXPECTED OUTCOMES

### After Indexes:
- ✅ Heartbeat queries drop from ~500ms to <10ms
- ✅ Cohort analysis queries 10-50x faster
- ✅ Capacity checks (expensive queries) now instant

### After Tables:
- ✅ 6 new tables ready for data collection
- ✅ Schema normalized for statistical analysis
- ✅ Foreign keys prevent orphaned data

### After Views:
- ✅ 4 pre-built queries for common reports
- ✅ No need to write SQL for basic analysis
- ✅ Dashboard-ready data structures

### After Python Updates:
- ✅ Question-level data for research
- ✅ Real-time engagement tracking
- ✅ AI cost analysis
- ✅ Language fairness metrics

---

## ⚠️ IMPORTANT NOTES

1. **These are all read-friendly operations** - No breaking changes to existing code
2. **Existing data unaffected** - All tables use IF NOT EXISTS
3. **Foreign keys enable cascading** - Delete a session → auto-clean related data
4. **RLS policies secured** - Service role still has admin access
5. **Views are read-only** - Safe to query from dashboards

---

## 📞 QUESTIONS?

Lines in this file reference the `tools/optimize_supabase.py` script which generates all SQL automatically. You can re-run it anytime to see the latest recommendations.
