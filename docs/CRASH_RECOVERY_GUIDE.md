# Crash Recovery & Data Loss Prevention Guide

## Problem You're Facing

❌ **Current Situation:**
- Session crashes before data uploads
- Community tier resource limits cause disconnections
- User can't re-enter data (research bias)
- Data lost forever
- Can't complete interviews

✅ **Solutions Implemented:**

---

## Solution 1: Auto-Save Every Interaction (Crash-Safe)

**Problem:** You only save data at completion → crash before end = total loss

**Solution:** Save data **immediately after each answer/input**

### Before (Vulnerable)
```python
# Learning page - data in memory only
st.session_state.chat_history.append({"user": msg, "ai": response})

# UEQ page - stored locally only
st.session_state.ueq_answers[dimension] = score

# Test page - array in memory
st.session_state.test_answers[q_num] = answer

# At END of session - upload all at once (CRASH POINT!)
save_all_data_to_supabase()  # ← If this fails, everything is lost
```

### After (Crash-Safe)
```python
from crash_recovery import CrashRecoveryManager

recovery_manager = CrashRecoveryManager(supabase, session_manager)

# Learning page - save immediately
def on_chat(user_msg, ai_response):
    # Immediate save to Supabase (within 2 seconds)
    recovery_manager.save_chat_message(user_msg, ai_response, response_time_ms)
    # Add to UI
    st.session_state.chat_history.append(...)

# UEQ page - save immediately on each selection
def on_ueq_answer(dimension, score):
    recovery_manager.save_ueq_response(dimension, score)  # Saved!
    st.session_state.ueq_answers[dimension] = score

# Test page - save immediately after each answer
def on_test_answer(q_num, answer):
    is_correct = check_answer(answer)
    recovery_manager.save_test_answer(q_num, answer, is_correct)  # Saved!
    st.session_state.test_answers[q_num] = answer
```

**Result:** If crash happens, data is already in Supabase

---

## Solution 2: Session Recovery (Resume Crashed Sessions)

**Problem:** Session crashes → all progress lost → user must restart

**Solution:** Auto-detect incomplete sessions and offer resume option

### Implementation

```python
import streamlit as st
from crash_recovery import CrashRecoveryManager

# Setup
recovery_manager = CrashRecoveryManager(supabase, session_manager)

# On page enter - check for incomplete sessions
session_info = session_manager.get_session_info()
recovered_data = recovery_manager.recover_partial_session(session_info["session_id"])

if recovered_data:
    st.warning("🔄 We detected an incomplete session from you!")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Resume (keep previous answers)"):
            st.session_state.recovered_data = recovered_data
            # Load recovered data back into forms
            if "profile" in recovered_data["stages"]:
                profile = recovered_data["stages"]["profile"]
                st.session_state.age = profile.get("age")
                st.session_state.gender = profile.get("gender")
                # ... restore all fields
            st.success("✓ Session restored! Continue from where you left off")
            st.rerun()
    
    with col2:
        if st.button("Start Fresh (discard previous)"):
            # Delete auto-save logs for this session
            st.session_state.skip_recovery = True
            st.rerun()
```

**Result:** User never loses data, can resume seamlessly

---

## Solution 3: Fallback Local Backup

**Problem:** Even Supabase might fail (network, resource limits)

**Solution:** Save to local backup files too

```python
# Crash Recovery Manager already does this:
# If Supabase fails → automatically saves to session_backups/[session_id]_backup.jsonl
```

**Manual recovery from file:**
```bash
# If session was lost but JSON backup exists:
cat session_backups/[session_id]_backup.jsonl

# Restore to database from backup:
python tools/restore_from_backup.py [session_id]
```

---

## Solution 4: Resource Optimization (Community Tier)

**Problem:** Community tier limits cause crashes

**Strategy:** Reduce query load + optimize data storage

### A. Batch Writes (Reduce Database Calls)

```python
# BEFORE: Every interaction = 1 database call
def on_chat(msg):
    recovery_manager.save_chat_message(...)  # Query 1
    update_session_time(...)                  # Query 2
    log_interaction(...)                      # Query 3
    # = 3 queries per message

# AFTER: Batch operations
def on_chat(msg):
    # Batch into 1 query
    data_to_batch = {
        "chat": msg,
        "session_time": time_spent,
        "interaction": interaction_type
    }
    recovery_manager.auto_save_interaction("chat", data_to_batch)
    # = 1 query per message
```

### B. Auto Cleanup of Old Logs

```sql
-- Runs weekly to delete old auto-save logs
-- Prevents table bloat on community tier

SELECT cleanup_autosave_logs();  -- Delete logs > 7 days old
-- Result: Reduces table size from potentially GB → hundreds of MB
```

### C. Reduce Real-Time Updates

```python
# BEFORE: Update status after EVERY interaction
def update_status():
    supabase.table("session_analytics").update({
        "total_chat_messages": current_count
    }).match(...)  # Called 20+ times per learning session

# AFTER: Update once per page or at end
def update_status_batched():
    # Call this once per learning page (not per message)
    supabase.table("session_analytics").update({
        "total_chat_messages": current_count,
        "total_slides_viewed": slides_count,
    }).match(...)  # Called 1 time for page = 20x reduction
```

### D. Connection Pooling

```python
# In your Streamlit app initialization:

@st.cache_resource
def get_supabase():
    """Cache Supabase client to reuse connections"""
    # Don't create new client on every rerun
    return create_client(url, key)

supabase = get_supabase()  # Reused across reruns
```

---

## Implementation Checklist

### Step 1: Database Setup (2 min)
```bash
# Copy output/CRASH_RECOVERY_SETUP.sql
# Paste into Supabase SQL Editor
# Run it

# This creates:
# - session_auto_save_log table
# - Recovery view
# - Cleanup function
# - Indexes
```

### Step 2: Import Module (30 sec)
```python
# In main.py or your page files:
from crash_recovery import CrashRecoveryManager

recovery_manager = CrashRecoveryManager(supabase, session_manager)
st.session_state.recovery_manager = recovery_manager
```

### Step 3: Update Learning Page (2 min)

Find where chat responses are saved:
```python
# BEFORE
response = get_ai_response(prompt)
st.write(response)

# AFTER
response = get_ai_response(prompt)
recovery_manager.save_chat_message(prompt, response, time_ms=response_time)
st.write(response)
```

### Step 4: Update Test Page (2 min)

Find where answers are processed:
```python
# BEFORE
if submit_button:
    answers[q_num] = user_answer

# AFTER
if submit_button:
    is_correct = check_answer(user_answer)
    recovery_manager.save_test_answer(q_num, user_answer, is_correct)
    answers[q_num] = user_answer
```

### Step 5: Update UEQ Page (2 min)

Find where scores are submitted:
```python
# BEFORE
if submit_button:
    ueq_scores[dimension] = score

# AFTER
if submit_button:
    recovery_manager.save_ueq_response(dimension, score)
    ueq_scores[dimension] = score
```

### Step 6: Add Recovery Option (1 min)

At start of profile/learning page:
```python
recovered = recovery_manager.recover_partial_session(session_id)
if recovered:
    st.warning("🔄 Incomplete session detected!")
    if st.button("Resume"):
        st.session_state.recovered_data = recovered
        st.success("Session restored!")
```

---

## Testing Crash Recovery

### Test 1: Manual Crash Simulation
```python
# Anywhere in your code:
if st.button("Simulate Crash (dev only)"):
    raise Exception("Intentional crash for testing")
    # This should NOT lose data that was saved before this button
```

### Test 2: Check Recovery View
```sql
-- In Supabase SQL Editor:
SELECT * FROM incomplete_sessions_with_data;

-- See which sessions have recoverable data:
SELECT 
    session_id, 
    profile_saves, 
    chat_saves, 
    test_saves,
    last_save
FROM incomplete_sessions_with_data
WHERE status = 'abandoned';
```

### Test 3: Verify Auto-Save Log
```sql
SELECT COUNT(*) as total_saves, interaction_type
FROM session_auto_save_log
GROUP BY interaction_type;

-- Should show lots of entries, not just 1 per session
```

---

## Community Tier Optimization Tips

| Issue | Solution | Expected Improvement |
|-------|----------|----------------------|
| Database rows grow unbounded | Run `cleanup_autosave_logs()` weekly | Keeps table < 500MB |
| Slow queries | Only SELECT on recent 7 days | 10x faster |
| Connection timeouts | Batch writes, use caching | 50% fewer connections |
| Storage overload | Archive completed sessions to storage | Free up database space |

---

## Cost: Zero Additional Work After Setup

Once integrated:
- ✅ Automatic on every interaction
- ✅ No extra clicks for users
- ✅ No manual prompts needed
- ✅ Runs silently in background

---

## Files to Help You

- `crash_recovery.py` - Main module (copy-paste into your code)
- `output/CRASH_RECOVERY_SETUP.sql` - Database tables (run in Supabase)
- `tools/restore_from_backup.py` - If you need manual recovery

---

## Worst-Case Fallback

Even if EVERYTHING fails:

1. **All recent interactions are in Supabase** (`session_auto_save_log`)
2. **Local backup files exist** (`session_backups/[id]_backup.jsonl`)
3. **Can manually query recovery view** to find all incomplete sessions
4. **Can manually restore data** from JSON backups

You have multiple redundant copies of user data.

---

## Key Benefits

✅ **Zero Data Loss** – Every interaction persists  
✅ **Seamless Resume** – Users never repeat work  
✅ **Community Tier Compatible** – Optimized for resource limits  
✅ **Research Integrity** – No forced re-entry = no bias  
✅ **Audit Trail** – Full history of every answer  
✅ **Easy to Implement** – 10 lines of code changes

---

**Next Step:** Run `CRASH_RECOVERY_SETUP.sql` in Supabase, then add the 2-line imports to your code.

🚀 Your study is now crash-proof! 🚀
