-- Data Loss Prevention Recovery Tables
-- Execute this in: https://app.supabase.com >> Your Project >> SQL Editor

CREATE TABLE IF NOT EXISTS session_checkpoints (
  id bigserial primary key,
  session_id text not null,
  stage text not null,
  checkpoint_data jsonb not null,
  saved_at timestamp with time zone not null,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

CREATE INDEX IF NOT EXISTS idx_session_checkpoint_session_id 
ON session_checkpoints(session_id);

CREATE INDEX IF NOT EXISTS idx_session_checkpoint_stage 
ON session_checkpoints(session_id, stage);

CREATE TABLE IF NOT EXISTS recovered_data_backup (
  id bigserial primary key,
  filename text not null,
  data jsonb not null,
  uploaded_at timestamp with time zone not null,
  created_at timestamp with time zone default now()
);

CREATE INDEX IF NOT EXISTS idx_recovered_data_backup_filename 
ON recovered_data_backup(filename);
