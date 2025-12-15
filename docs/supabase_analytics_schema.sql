-- ============================================================================
-- ANALYTICS TABLES FOR SESSION MONITORING
-- ============================================================================
-- These tables store aggregated session data for easy monitoring via mobile app
-- Data should be inserted after each session completes key milestones

-- Session Overview Table
-- Tracks high-level session progress and completion status
CREATE TABLE IF NOT EXISTS session_analytics (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    language_code TEXT NOT NULL,
    
    -- Timestamps
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    
    -- Completion flags
    consent_given BOOLEAN DEFAULT FALSE,
    profile_completed BOOLEAN DEFAULT FALSE,
    learning_completed BOOLEAN DEFAULT FALSE,
    knowledge_test_completed BOOLEAN DEFAULT FALSE,
    ueq_completed BOOLEAN DEFAULT FALSE,
    
    -- Time spent (seconds)
    time_on_profile DECIMAL(10,1),
    time_on_learning DECIMAL(10,1),
    time_on_knowledge_test DECIMAL(10,1),
    time_on_ueq DECIMAL(10,1),
    total_session_time DECIMAL(10,1),
    
    -- Interaction counts
    total_slides_viewed INTEGER DEFAULT 0,
    total_chat_messages INTEGER DEFAULT 0,
    total_slide_explanations INTEGER DEFAULT 0,
    
    -- Scores
    knowledge_test_score DECIMAL(5,2),  -- e.g., 87.50
    knowledge_test_grade TEXT,  -- e.g., "B+"
    
    -- Profile data (key demographics for quick filtering)
    age INTEGER,
    gender TEXT,
    education_level TEXT,
    field_of_study TEXT,
    english_proficiency INTEGER,  -- 1-7 scale
    native_proficiency INTEGER,   -- 1-7 scale
    genai_familiarity INTEGER,    -- 1-5 scale
    genai_usage INTEGER,          -- 0-3 scale
    
    -- File paths for detailed data
    profile_json_path TEXT,
    knowledge_test_json_path TEXT,
    ueq_json_path TEXT,
    learning_log_json_path TEXT,
    page_durations_json_path TEXT,
    
    -- Status
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_session_analytics_language ON session_analytics(language_code);
CREATE INDEX IF NOT EXISTS idx_session_analytics_status ON session_analytics(status);
CREATE INDEX IF NOT EXISTS idx_session_analytics_completed_at ON session_analytics(completed_at);
CREATE INDEX IF NOT EXISTS idx_session_analytics_user ON session_analytics(user_id);

-- UEQ Scores Table
-- Stores detailed UEQ dimension scores for analysis
CREATE TABLE IF NOT EXISTS ueq_scores (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES session_analytics(session_id),
    
    -- UEQ dimension scores (-3 to +3 scale)
    attractiveness DECIMAL(4,2),
    perspicuity DECIMAL(4,2),
    efficiency DECIMAL(4,2),
    dependability DECIMAL(4,2),
    stimulation DECIMAL(4,2),
    novelty DECIMAL(4,2),
    
    -- Grades (Excellent, Good, Above Average, Below Average, Bad)
    attractiveness_grade TEXT,
    perspicuity_grade TEXT,
    efficiency_grade TEXT,
    dependability_grade TEXT,
    stimulation_grade TEXT,
    novelty_grade TEXT,
    
    -- Overall satisfaction (calculated from attractiveness)
    overall_grade TEXT,
    
    -- Timestamp
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_ueq_session FOREIGN KEY (session_id) REFERENCES session_analytics(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ueq_session ON ueq_scores(session_id);

-- Knowledge Test Details Table
-- Stores question-level results for detailed analysis
CREATE TABLE IF NOT EXISTS knowledge_test_results (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES session_analytics(session_id),
    
    -- Individual question results (correct/incorrect)
    q1_correct BOOLEAN,
    q2_correct BOOLEAN,
    q3_correct BOOLEAN,
    q4_correct BOOLEAN,
    q5_score DECIMAL(4,2),  -- Partial credit for multi-select
    q6_correct BOOLEAN,
    q7_correct BOOLEAN,
    q8_correct BOOLEAN,
    
    -- User's actual answers (for review)
    q1_answer TEXT,
    q2_answer TEXT,
    q3_answer TEXT,
    q4_answer TEXT,
    q5_answer_a BOOLEAN,
    q5_answer_b BOOLEAN,
    q5_answer_c BOOLEAN,
    q5_answer_d BOOLEAN,
    q6_answer TEXT,
    q7_answer TEXT,
    q8_answer TEXT,
    
    -- Total score
    total_score DECIMAL(5,2),
    max_score DECIMAL(5,2) DEFAULT 8.0,
    percentage DECIMAL(5,2),
    grade TEXT,
    
    -- Timing
    time_taken_seconds INTEGER,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_knowledge_session FOREIGN KEY (session_id) REFERENCES session_analytics(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_knowledge_session ON knowledge_test_results(session_id);

-- Learning Interaction Summary
-- Aggregated metrics from learning session
CREATE TABLE IF NOT EXISTS learning_interactions (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES session_analytics(session_id),
    
    -- Slide interaction metrics
    slides_viewed INTEGER DEFAULT 0,
    slides_with_explanation INTEGER DEFAULT 0,
    
    -- Chat interaction metrics
    manual_chat_messages INTEGER DEFAULT 0,
    total_user_messages INTEGER DEFAULT 0,
    avg_message_length INTEGER,
    
    -- Timing
    first_interaction_at TIMESTAMPTZ,
    last_interaction_at TIMESTAMPTZ,
    total_duration_seconds INTEGER,
    
    -- File reference
    full_log_path TEXT,
    
    CONSTRAINT fk_learning_session FOREIGN KEY (session_id) REFERENCES session_analytics(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_learning_session ON learning_interactions(session_id);

-- ============================================================================
-- ANALYTICS VIEWS FOR DASHBOARD/MOBILE APP
-- ============================================================================

-- Completed Sessions View
-- Shows all fully completed sessions with key metrics
CREATE OR REPLACE VIEW completed_sessions AS
SELECT 
    sa.session_id,
    sa.user_id,
    sa.language_code,
    sa.started_at,
    sa.completed_at,
    sa.total_session_time / 60.0 AS session_duration_minutes,
    sa.age,
    sa.gender,
    sa.education_level,
    sa.field_of_study,
    
    -- Test performance
    sa.knowledge_test_score,
    sa.knowledge_test_grade,
    
    -- UEQ scores
    ueq.attractiveness,
    ueq.perspicuity,
    ueq.efficiency,
    ueq.dependability,
    ueq.stimulation,
    ueq.novelty,
    ueq.overall_grade AS ueq_overall_grade,
    
    -- Interaction metrics
    sa.total_slides_viewed,
    sa.total_chat_messages,
    sa.total_slide_explanations,
    
    -- Profile metrics
    sa.english_proficiency,
    sa.genai_familiarity
    
FROM session_analytics sa
LEFT JOIN ueq_scores ueq ON sa.session_id = ueq.session_id
WHERE sa.status = 'completed'
  AND sa.knowledge_test_completed = TRUE
  AND sa.ueq_completed = TRUE
ORDER BY sa.completed_at DESC;

-- Session Progress View
-- Shows current progress of all active/recent sessions
CREATE OR REPLACE VIEW session_progress AS
SELECT 
    session_id,
    user_id,
    language_code,
    started_at,
    ROUND(EXTRACT(EPOCH FROM (NOW() - started_at)) / 60.0, 1) AS minutes_elapsed,
    
    -- Progress flags
    consent_given,
    profile_completed,
    learning_completed,
    knowledge_test_completed,
    ueq_completed,
    
    -- Current stage
    CASE 
        WHEN NOT consent_given THEN 'Consent'
        WHEN NOT profile_completed THEN 'Profile Survey'
        WHEN NOT learning_completed THEN 'Learning'
        WHEN NOT knowledge_test_completed THEN 'Knowledge Test'
        WHEN NOT ueq_completed THEN 'UEQ Survey'
        ELSE 'Completed'
    END AS current_stage,
    
    -- Progress percentage
    CASE 
        WHEN ueq_completed THEN 100
        WHEN knowledge_test_completed THEN 80
        WHEN learning_completed THEN 60
        WHEN profile_completed THEN 40
        WHEN consent_given THEN 20
        ELSE 0
    END AS progress_percent,
    
    status
    
FROM session_analytics
WHERE status IN ('active', 'completed')
  AND started_at > NOW() - INTERVAL '24 hours'
ORDER BY started_at DESC;

-- Daily Statistics View
-- Aggregated metrics per day for tracking study progress
CREATE OR REPLACE VIEW daily_statistics AS
SELECT 
    DATE(completed_at) AS date,
    COUNT(*) AS sessions_completed,
    COUNT(*) FILTER (WHERE language_code = 'en') AS english_sessions,
    COUNT(*) FILTER (WHERE language_code = 'de') AS german_sessions,
    COUNT(*) FILTER (WHERE language_code = 'nl') AS dutch_sessions,
    COUNT(*) FILTER (WHERE language_code = 'tr') AS turkish_sessions,
    COUNT(*) FILTER (WHERE language_code = 'sq') AS albanian_sessions,
    COUNT(*) FILTER (WHERE language_code = 'hi') AS hindi_sessions,
    
    -- Average scores
    ROUND(AVG(knowledge_test_score), 2) AS avg_knowledge_score,
    ROUND(AVG(total_session_time / 60.0), 1) AS avg_duration_minutes,
    
    -- UEQ averages (would need to join with ueq_scores table)
    MIN(completed_at) AS first_session,
    MAX(completed_at) AS last_session
    
FROM session_analytics
WHERE status = 'completed'
  AND completed_at IS NOT NULL
GROUP BY DATE(completed_at)
ORDER BY date DESC;

-- Language Comparison View
-- Compare performance across language conditions
CREATE OR REPLACE VIEW language_comparison AS
SELECT 
    language_code,
    COUNT(*) AS total_sessions,
    
    -- Knowledge test metrics
    ROUND(AVG(knowledge_test_score), 2) AS avg_knowledge_score,
    ROUND(STDDEV(knowledge_test_score), 2) AS stddev_knowledge_score,
    MIN(knowledge_test_score) AS min_score,
    MAX(knowledge_test_score) AS max_score,
    
    -- Time metrics
    ROUND(AVG(total_session_time / 60.0), 1) AS avg_total_minutes,
    ROUND(AVG(time_on_learning / 60.0), 1) AS avg_learning_minutes,
    
    -- Interaction metrics
    ROUND(AVG(total_chat_messages), 1) AS avg_chat_messages,
    ROUND(AVG(total_slide_explanations), 1) AS avg_slide_explanations,
    
    -- Demographics
    ROUND(AVG(age), 1) AS avg_age,
    ROUND(AVG(english_proficiency), 2) AS avg_english_proficiency
    
FROM session_analytics
WHERE status = 'completed'
  AND knowledge_test_completed = TRUE
GROUP BY language_code
ORDER BY language_code;

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to update session analytics from JSON data
-- This would be called from Python after saving each component
CREATE OR REPLACE FUNCTION update_session_analytics(
    p_session_id TEXT,
    p_component TEXT,  -- 'profile', 'knowledge_test', 'ueq', 'learning'
    p_data JSONB
) RETURNS VOID AS $$
BEGIN
    -- Update based on component type
    IF p_component = 'profile' THEN
        UPDATE session_analytics
        SET 
            profile_completed = TRUE,
            age = (p_data->>'age')::INTEGER,
            gender = p_data->>'gender',
            education_level = p_data->>'education_level',
            field_of_study = p_data->>'field_of_study',
            english_proficiency = (p_data->>'english_proficiency')::INTEGER,
            native_proficiency = (p_data->>'native_proficiency')::INTEGER,
            genai_familiarity = (p_data->>'genai_familiarity')::INTEGER,
            genai_usage = (p_data->>'genai_usage')::INTEGER,
            updated_at = NOW()
        WHERE session_id = p_session_id;
        
    ELSIF p_component = 'knowledge_test' THEN
        UPDATE session_analytics
        SET 
            knowledge_test_completed = TRUE,
            knowledge_test_score = (p_data->>'percentage')::DECIMAL,
            knowledge_test_grade = p_data->>'grade',
            updated_at = NOW()
        WHERE session_id = p_session_id;
        
    ELSIF p_component = 'ueq' THEN
        UPDATE session_analytics
        SET 
            ueq_completed = TRUE,
            updated_at = NOW()
        WHERE session_id = p_session_id;
        
    ELSIF p_component = 'learning' THEN
        UPDATE session_analytics
        SET 
            learning_completed = TRUE,
            total_slides_viewed = (p_data->>'slides_viewed')::INTEGER,
            total_chat_messages = (p_data->>'chat_messages')::INTEGER,
            total_slide_explanations = (p_data->>'slide_explanations')::INTEGER,
            updated_at = NOW()
        WHERE session_id = p_session_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE session_analytics IS 'Main analytics table aggregating all session data for monitoring';
COMMENT ON TABLE ueq_scores IS 'Detailed UEQ dimension scores for each session';
COMMENT ON TABLE knowledge_test_results IS 'Question-level results from knowledge test';
COMMENT ON TABLE learning_interactions IS 'Aggregated metrics from learning session interactions';

COMMENT ON VIEW completed_sessions IS 'Shows all completed sessions with key performance metrics';
COMMENT ON VIEW session_progress IS 'Real-time view of session progress (last 24h)';
COMMENT ON VIEW daily_statistics IS 'Daily aggregated statistics for study monitoring';
COMMENT ON VIEW language_comparison IS 'Compare performance across language conditions';

-- ============================================================================
-- EXAMPLE QUERIES FOR MOBILE APP
-- ============================================================================

-- Get today's sessions
-- SELECT * FROM session_progress WHERE DATE(started_at) = CURRENT_DATE;

-- Get recent completions
-- SELECT * FROM completed_sessions LIMIT 10;

-- Get language performance
-- SELECT * FROM language_comparison;

-- Get specific session details
-- SELECT * FROM session_analytics WHERE session_id = 'xxxxx';

-- Count active sessions right now
-- SELECT COUNT(*) FROM session_progress WHERE status = 'active' AND current_stage IN ('Profile Survey', 'Learning', 'Knowledge Test', 'UEQ Survey');
