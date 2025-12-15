-- Automatic session abandonment function
-- This function automatically marks sessions as 'abandoned' when last_seen is older than 2 minutes (missed 6 heartbeats)
-- Run this SQL in your Supabase SQL Editor after creating the presence table

-- Function to automatically abandon stale sessions
CREATE OR REPLACE FUNCTION auto_abandon_stale_sessions()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    -- Mark sessions as abandoned if last_seen is older than 2 minutes (120 seconds)
    -- This means they missed at least 6 heartbeats (20 seconds each)
    UPDATE presence
    SET 
        status = 'abandoned',
        updated_at = NOW()
    WHERE 
        status = 'active'
        AND last_seen < NOW() - INTERVAL '2 minutes';
END;
$$;

-- Schedule this function to run every minute using pg_cron extension
-- Note: pg_cron needs to be enabled in your Supabase project
-- Go to Database → Extensions → Enable "pg_cron"

-- First, enable the pg_cron extension (only needs to be done once)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule the function to run every minute
SELECT cron.schedule(
    'auto-abandon-stale-sessions',  -- Job name
    '* * * * *',                      -- Every minute (cron format)
    $$SELECT auto_abandon_stale_sessions();$$
);

-- To verify the scheduled job was created:
SELECT * FROM cron.job;

-- To remove the scheduled job (if needed):
-- SELECT cron.unschedule('auto-abandon-stale-sessions');

-- Alternative: If pg_cron is not available, you can use a trigger approach
-- This marks sessions as abandoned immediately when queried
CREATE OR REPLACE VIEW active_sessions_with_auto_abandon AS
SELECT 
    session_id,
    user_id,
    language_code,
    current_page,
    last_seen,
    started_at,
    is_in_interview,
    CASE 
        WHEN status = 'active' AND last_seen < NOW() - INTERVAL '2 minutes' THEN 'abandoned'
        ELSE status
    END as status,
    created_at,
    updated_at
FROM presence
WHERE last_seen > NOW() - INTERVAL '5 minutes';  -- Only show recent sessions

-- Grant permissions
GRANT EXECUTE ON FUNCTION auto_abandon_stale_sessions() TO postgres, anon, authenticated;

-- Test the function manually (optional)
-- SELECT auto_abandon_stale_sessions();
