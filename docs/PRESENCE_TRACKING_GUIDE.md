# Presence Tracking & Concurrent Session Management

## Overview

This system tracks active user sessions in real-time using JavaScript heartbeats sent from the browser to Supabase. It enables:
- Real-time monitoring of active sessions
- Limiting concurrent interviews
- Automatic detection of abandoned sessions
- Session analytics and capacity planning

## Architecture

### 1. **Supabase Database Table**
The `presence` table stores real-time session information:
- `session_id`: Unique identifier for each session
- `user_id`: Username/credential
- `language_code`: Assigned language (en/de/nl/tr/sq/hi)
- `current_page`: Current page user is viewing
- `last_seen`: Last heartbeat timestamp (updated every 20s)
- `started_at`: Session start time
- `is_in_interview`: Boolean flag for learning phase
- `status`: active/completed/abandoned

### 2. **JavaScript Heartbeat**
Client-side JavaScript runs in the browser and:
- Sends heartbeat to Supabase REST API every 20 seconds
- Updates `last_seen` timestamp
- Automatically stops when tab closes
- Independent of Streamlit reruns

### 3. **Python PresenceTracker**
Server-side tracking logic:
- Counts active sessions (heartbeat within last 60s)
- Enforces concurrent user limits
- Marks sessions as completed/abandoned

## Setup Instructions

### Step 1: Create Supabase Table

1. Open your Supabase project dashboard
2. Go to **SQL Editor**
3. Run the SQL script: `docs/supabase_presence_schema.sql`
4. Verify table created: Go to **Table Editor** → find `presence` table

### Step 2: Add Supabase Credentials

In `.streamlit/secrets.toml`, ensure you have:

```toml
[supabase]
url = "https://your-project.supabase.co"
anon_key = "your-anon-key"  # Public key - safe for browser
service_key = "your-service-role-key"  # Private key - for server
```

**Important:** 
- `anon_key` is used by JavaScript heartbeat (public, safe)
- `service_key` is used by Python for uploads (private, server-only)

### Step 3: Configure Concurrent Limit

In `main.py`, adjust the maximum concurrent interviews:

```python
# Initialize presence tracker with your desired limit
presence = get_presence_tracker(max_concurrent=3)  # Change 3 to your limit
```

### Step 4: Test the System

1. **Run the app locally:**
   ```bash
   streamlit run main.py
   ```

2. **Login and navigate to the learning page**

3. **Check Supabase:**
   - Go to **Table Editor** → `presence` table
   - You should see your session with `last_seen` updating every ~20 seconds

4. **Test concurrent limiting:**
   - Open multiple browser tabs
   - Login with different credentials in each
   - Try to access the learning page
   - After reaching the limit, new users should see capacity message

### Step 5: Monitor Active Sessions

**Via Supabase Dashboard:**
```sql
-- View active sessions (last 5 minutes)
SELECT * FROM active_sessions_view;

-- Check interview capacity
SELECT * FROM interview_capacity;
```

**Via Python (in dev mode):**
```python
from presence_tracker import get_presence_tracker

presence = get_presence_tracker()

# Count active sessions
active_count = presence.count_active_sessions()
print(f"Active sessions: {active_count}")

# Count active interviews
interview_count = presence.count_active_interviews()
print(f"Active interviews: {interview_count}")
```

## How It Works

### Session Lifecycle

1. **User logs in** → `mark_session_started()` called
   - Creates record in `presence` table
   - `status = 'active'`

2. **User navigates pages** → Heartbeat runs continuously
   - JavaScript sends POST to Supabase every 20 seconds
   - Updates `last_seen` timestamp
   - Updates `current_page` field

3. **User starts learning** → Capacity check
   - `can_start_interview()` checks concurrent limit
   - If under limit: sets `is_in_interview = true`
   - If at capacity: denies access with message

4. **User closes tab** → Heartbeat stops automatically
   - `last_seen` stops updating
   - After 60s, considered offline
   - Cleanup job can mark as `status = 'abandoned'`

5. **User finishes** → `mark_session_completed()` called
   - Updates `status = 'completed'`
   - Sets `completed_at` timestamp

### Capacity Enforcement

When user tries to access learning page:
```python
if presence:
    can_start, message = presence.can_start_interview()
    
    if not can_start:
        st.error(message)  # "Platform at capacity..."
        st.stop()  # Block access
```

The check counts sessions where:
- `status = 'active'`
- `is_in_interview = true`
- `last_seen > 60 seconds ago`

## Configuration Options

### Adjusting Concurrent Limit

```python
# In main.py
presence = get_presence_tracker(max_concurrent=5)  # Allow 5 concurrent
```

### Changing Heartbeat Frequency

```python
# In presence_tracker.py, line 64
setInterval(sendHeartbeat, 30000);  # Change to 30 seconds
```

### Adjusting Online Window

```python
# In presence_tracker.py, __init__
self.online_window_seconds = 90  # Consider offline after 90s
```

## Maintenance

### Cleanup Stale Sessions

Run periodically (e.g., daily cron job):

```python
from presence_tracker import get_presence_tracker

presence = get_presence_tracker()
count = presence.cleanup_stale_sessions(hours=3)
print(f"Cleaned up {count} stale sessions")
```

This marks sessions as `abandoned` if `last_seen > 3 hours ago`.

### Manual Cleanup via SQL

```sql
-- Mark sessions abandoned if inactive for 3+ hours
UPDATE presence
SET status = 'abandoned'
WHERE status = 'active'
  AND last_seen < NOW() - INTERVAL '3 hours';
```

## Troubleshooting

### Heartbeat not working

**Check browser console:**
- Open DevTools → Console tab
- Look for heartbeat errors
- Common issues:
  - CORS errors → Check Supabase RLS policies
  - 401 errors → Check `anon_key` in secrets
  - Network errors → Check Supabase URL

**Check Supabase:**
- Go to **Table Editor** → `presence`
- Verify `last_seen` is updating
- If not updating → Check RLS policy allows anonymous inserts

### Users not being blocked at capacity

**Check logs:**
```python
# In dev mode, check console output
print(f"Active interviews: {presence.count_active_interviews()}")
print(f"Max allowed: {presence.max_concurrent}")
```

**Check query:**
- Ensure `last_seen` is recent (within 60s)
- Ensure `is_in_interview = true`
- Check index exists: `idx_presence_active_interviews`

### Session marked as abandoned too quickly

**Increase online window:**
```python
self.online_window_seconds = 120  # 2 minutes instead of 60s
```

Or increase heartbeat frequency (send more often).

## Deployment Notes

### Streamlit Community Cloud

The JavaScript heartbeat works on Streamlit Cloud! The `components.html()` function renders client-side JavaScript that runs in the user's browser, regardless of hosting.

**Verify after deployment:**
1. Deploy to Streamlit Cloud
2. Login and navigate to learning page
3. Check Supabase `presence` table
4. Confirm `last_seen` updates every 20 seconds

### CORS Configuration

Supabase automatically handles CORS for REST API when using the `anon_key`. The RLS policy in the setup SQL allows anonymous access:

```sql
CREATE POLICY "Allow anonymous heartbeat updates" ON presence
    FOR ALL USING (true) WITH CHECK (true);
```

## Security Considerations

1. **anon_key in JavaScript**: Safe - it's designed for browser use
2. **RLS Policy**: Allows all operations - acceptable for presence tracking
3. **No sensitive data**: Table only contains session metadata
4. **service_key**: Never exposed to client - used only server-side

## Analytics Queries

### Active users by language

```sql
SELECT 
    language_code,
    COUNT(*) as active_count
FROM presence
WHERE status = 'active'
  AND last_seen > NOW() - INTERVAL '1 minute'
GROUP BY language_code
ORDER BY active_count DESC;
```

### Session duration analysis

```sql
SELECT 
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at)) / 60) as avg_duration_minutes,
    MAX(EXTRACT(EPOCH FROM (completed_at - started_at)) / 60) as max_duration_minutes
FROM presence
WHERE status = 'completed';
```

### Peak usage times

```sql
SELECT 
    DATE_TRUNC('hour', started_at) as hour,
    COUNT(*) as sessions_started
FROM presence
GROUP BY hour
ORDER BY hour DESC
LIMIT 24;
```

## Support

For issues or questions:
1. Check browser console for JavaScript errors
2. Check Supabase logs: **Database** → **Logs**
3. Enable dev mode: `st.session_state["dev_mode"] = True`
4. Check Python logs for presence tracker errors
