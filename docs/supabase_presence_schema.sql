-- Presence tracking table for real-time session monitoring
-- Run this in Supabase SQL Editor to create the table

CREATE TABLE IF NOT EXISTS presence (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    language_code TEXT NOT NULL,
    current_page TEXT,
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    is_in_interview BOOLEAN DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast queries on active sessions
CREATE INDEX IF NOT EXISTS idx_presence_active_sessions 
ON presence(status, last_seen) 
WHERE status = 'active';

-- Index for counting active interviews
CREATE INDEX IF NOT EXISTS idx_presence_active_interviews 
ON presence(status, is_in_interview, last_seen) 
WHERE status = 'active' AND is_in_interview = TRUE;

-- Index for language-based queries
CREATE INDEX IF NOT EXISTS idx_presence_language 
ON presence(language_code, status);

-- Enable Row Level Security (RLS)
ALTER TABLE presence ENABLE ROW LEVEL SECURITY;

-- Policy: Allow anonymous inserts/updates (for heartbeat from browser)
CREATE POLICY "Allow anonymous heartbeat updates" ON presence
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Optional: Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_presence_updated_at 
    BEFORE UPDATE ON presence
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- View for monitoring active sessions (useful for admin dashboard)
CREATE OR REPLACE VIEW active_sessions_view AS
SELECT 
    session_id,
    user_id,
    language_code,
    current_page,
    last_seen,
    started_at,
    is_in_interview,
    EXTRACT(EPOCH FROM (NOW() - last_seen)) as seconds_since_last_seen,
    EXTRACT(EPOCH FROM (NOW() - started_at)) / 60 as session_duration_minutes
FROM presence
WHERE status = 'active'
  AND last_seen > NOW() - INTERVAL '5 minutes'
ORDER BY last_seen DESC;

-- View for interview capacity monitoring
CREATE OR REPLACE VIEW interview_capacity AS
SELECT 
    COUNT(*) as active_interviews,
    COUNT(*) FILTER (WHERE language_code = 'en') as english_count,
    COUNT(*) FILTER (WHERE language_code = 'de') as german_count,
    COUNT(*) FILTER (WHERE language_code = 'nl') as dutch_count,
    COUNT(*) FILTER (WHERE language_code = 'tr') as turkish_count,
    COUNT(*) FILTER (WHERE language_code = 'sq') as albanian_count,
    COUNT(*) FILTER (WHERE language_code = 'hi') as hindi_count
FROM presence
WHERE status = 'active'
  AND is_in_interview = TRUE
  AND last_seen > NOW() - INTERVAL '1 minute';

COMMENT ON TABLE presence IS 'Real-time session presence tracking with JavaScript heartbeat';
COMMENT ON COLUMN presence.session_id IS 'Unique session identifier (UUID)';
COMMENT ON COLUMN presence.user_id IS 'Username/credential used for login';
COMMENT ON COLUMN presence.language_code IS 'Assigned language (en/de/nl/tr/sq/hi)';
COMMENT ON COLUMN presence.current_page IS 'Current page user is on';
COMMENT ON COLUMN presence.last_seen IS 'Last heartbeat timestamp from browser';
COMMENT ON COLUMN presence.started_at IS 'Session start timestamp';
COMMENT ON COLUMN presence.is_in_interview IS 'True if user is in learning/interview phase';
COMMENT ON COLUMN presence.status IS 'Session status: active, completed, or abandoned';
