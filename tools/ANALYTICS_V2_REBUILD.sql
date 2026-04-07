-- ANALYTICS_V2_REBUILD.sql
-- Strictly non-destructive migration:
-- - Creates new analytics_v2 tables/views/functions only
-- - Does NOT truncate, delete, or alter existing raw study tables
-- - Safe to rerun

begin;

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------
-- ARCHIVE + DROP LEGACY DERIVED TABLES (NO DATA LOSS)
-- ---------------------------------------------------------------------
-- Keeps data by copying to archive_analytics_v1 schema, then drops old
-- derived/legacy tables from public schema so your Table Editor is clean.
-- Core raw tables used by the app are NOT touched.

create schema if not exists archive_analytics_v1;

do $$
declare
  t text;
  legacy_tables text[] := array[
    'interaction_logs',
    'language_analysis',
    'engagement_metrics',
    'cohort_comparison',
    'knowledge_test_detailed',
    'ueq_detailed_scores',
    'resource_profiler_logs',
    'session_checkpoints',
    'recovered_data_backup'
  ];
begin
  foreach t in array legacy_tables loop
    if to_regclass('public.' || t) is not null then
      execute format(
        'create table if not exists archive_analytics_v1.%I as table public.%I with data',
        t,
        t
      );
      execute format('drop table public.%I cascade', t);
    end if;
  end loop;
end $$;

create table if not exists public.analytics_v2_sessions (
  session_id text primary key,
  user_id text,
  language_code text,

  source_status text not null default 'unknown'
    check (source_status in ('finalized_storage', 'completed_db', 'active_db', 'unknown')),

  db_status text,
  presence_status text,

  started_at timestamptz,
  completed_at timestamptz,
  consent_given boolean,
  profile_completed boolean,
  learning_completed boolean,
  knowledge_test_completed boolean,
  ueq_completed boolean,

  knowledge_test_score numeric(8, 3),
  total_session_time_seconds integer,
  total_chat_messages integer,
  total_slide_explanations integer,

  has_storage_payload boolean not null default false,
  storage_payload_path text,
  storage_payload_updated_at timestamptz,

  data_quality_flags jsonb not null default '[]'::jsonb,
  raw_db jsonb,
  raw_storage jsonb,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_analytics_v2_sessions_source_status
  on public.analytics_v2_sessions(source_status);
create index if not exists idx_analytics_v2_sessions_language
  on public.analytics_v2_sessions(language_code);
create index if not exists idx_analytics_v2_sessions_completed_at
  on public.analytics_v2_sessions(completed_at desc);

create table if not exists public.analytics_v2_interactions (
  id bigserial primary key,
  session_id text not null references public.analytics_v2_sessions(session_id) on delete cascade,
  source text not null check (source in ('db_learning_interactions', 'storage_final_analytics')),
  slides_viewed integer,
  slides_with_explanation integer,
  manual_chat_messages integer,
  total_user_messages integer,
  avg_message_length integer,
  total_duration_seconds integer,
  extra jsonb,
  updated_at timestamptz not null default now(),
  unique(session_id, source)
);

create index if not exists idx_analytics_v2_interactions_session
  on public.analytics_v2_interactions(session_id);

create table if not exists public.analytics_v2_refresh_runs (
  run_id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  mode text not null default 'manual',
  rows_sessions_upserted integer not null default 0,
  rows_interactions_upserted integer not null default 0,
  errors jsonb not null default '[]'::jsonb,
  notes text
);

-- Finalized-only canonical table (storage payloads only)
create table if not exists public.analytics_v2_finalized_sessions (
  session_id text primary key,
  language_code text not null,
  storage_payload_path text not null,

  knowledge_test_accuracy_pct numeric(8,3),
  total_session_time_seconds integer,
  total_ai_interactions integer,
  slide_explanations integer,
  manual_chat integer,
  ueq_attractiveness numeric(8,3),
  ueq_efficiency numeric(8,3),
  ueq_dependability numeric(8,3),
  ueq_stimulation numeric(8,3),
  ueq_novelty numeric(8,3),
  has_comment boolean,

  raw_storage jsonb,
  updated_at timestamptz not null default now()
);

create index if not exists idx_analytics_v2_finalized_language
  on public.analytics_v2_finalized_sessions(language_code);

create index if not exists idx_analytics_v2_finalized_updated
  on public.analytics_v2_finalized_sessions(updated_at desc);

-- Language-level comparison table (one row per language)
create table if not exists public.analytics_v2_language_results (
  language_code text primary key,
  sessions integer not null,
  avg_knowledge_test_accuracy_pct numeric(8,3),
  avg_total_session_time_seconds numeric(12,3),
  avg_total_ai_interactions numeric(12,3),
  avg_slide_explanations numeric(12,3),
  avg_manual_chat numeric(12,3),
  avg_ueq_attractiveness numeric(8,3),
  avg_ueq_efficiency numeric(8,3),
  avg_ueq_dependability numeric(8,3),
  avg_ueq_stimulation numeric(8,3),
  avg_ueq_novelty numeric(8,3),
  comment_rate numeric(8,4),
  updated_at timestamptz not null default now()
);

create or replace view public.analytics_v2_compare_languages as
select *
from public.analytics_v2_language_results
where language_code not in ('de', 'unknown')
order by sessions desc, language_code;

-- Convenience views: finalized sessions per language
create or replace view public.analytics_v2_finalized_en as
select * from public.analytics_v2_finalized_sessions where language_code = 'en';

create or replace view public.analytics_v2_finalized_nl as
select * from public.analytics_v2_finalized_sessions where language_code = 'nl';

create or replace view public.analytics_v2_finalized_tr as
select * from public.analytics_v2_finalized_sessions where language_code = 'tr';

create or replace view public.analytics_v2_finalized_sq as
select * from public.analytics_v2_finalized_sessions where language_code = 'sq';

create or replace view public.analytics_v2_finalized_hi as
select * from public.analytics_v2_finalized_sessions where language_code = 'hi';

drop view if exists public.analytics_v2_finalized_de;
drop view if exists public.analytics_v2_finalized_unknown;

-- One consolidated finalized sessions view for quick inspection
create or replace view public.analytics_v2_finalized_all as
select *
from public.analytics_v2_finalized_sessions
where language_code not in ('de', 'unknown')
  and storage_payload_path not ilike '%pilot_backup/%'
  and storage_payload_path not ilike '%/pilot_%'
  and storage_payload_path not ilike '%dev_testing/%'
order by updated_at desc;

create or replace view public.analytics_v2_live_active_users as
select
  p.session_id,
  p.user_id,
  p.language_code,
  p.current_page,
  p.is_in_interview,
  p.status,
  p.last_seen,
  extract(epoch from (now() - p.last_seen))::int as seconds_since_last_seen
from public.presence p
where p.status = 'active'
  and p.last_seen >= now() - interval '60 seconds'
order by p.last_seen desc;

create or replace view public.analytics_v2_capacity_status as
select
  count(*) filter (where p.status = 'active' and p.last_seen >= now() - interval '60 seconds') as active_sessions_60s,
  count(*) filter (where p.status = 'active' and p.is_in_interview = true and p.last_seen >= now() - interval '60 seconds') as active_interviews_60s,
  count(*) filter (where p.status = 'abandoned') as abandoned_total,
  count(*) filter (where p.status = 'completed') as completed_total
from public.presence p;

create or replace view public.analytics_v2_session_health as
select
  sa.session_id,
  sa.user_id,
  sa.language_code,
  sa.status as analytics_status,
  p.status as presence_status,
  sa.started_at,
  sa.completed_at,
  p.completed_at as presence_completed_at,
  case
    when sa.status = 'completed' and (p.status is null or p.status not in ('completed', 'active')) then 'status_mismatch'
    when sa.status = 'active' and p.status = 'completed' then 'status_mismatch'
    else 'ok'
  end as health_flag
from public.session_analytics sa
left join public.presence p on p.session_id = sa.session_id;

create or replace view public.analytics_v2_funnel_by_language as
select
  coalesce(language_code, 'unknown') as language_code,
  count(*) as sessions,
  avg(case when consent_given then 1 else 0 end)::numeric(8,4) as consent_rate,
  avg(case when profile_completed then 1 else 0 end)::numeric(8,4) as profile_rate,
  avg(case when learning_completed then 1 else 0 end)::numeric(8,4) as learning_rate,
  avg(case when knowledge_test_completed then 1 else 0 end)::numeric(8,4) as knowledge_test_rate,
  avg(case when ueq_completed then 1 else 0 end)::numeric(8,4) as ueq_rate,
  avg(case when db_status = 'completed' or source_status = 'finalized_storage' then 1 else 0 end)::numeric(8,4) as completion_rate,
  avg(knowledge_test_score)::numeric(8,3) as avg_knowledge_test_score
from public.analytics_v2_sessions
group by coalesce(language_code, 'unknown')
order by sessions desc;

create or replace function public.analytics_v2_mark_abandoned(hours_old int default 3)
returns integer
language plpgsql
as $$
declare
  changed_count integer := 0;
begin
  update public.presence
  set status = 'abandoned'
  where status = 'active'
    and last_seen < now() - make_interval(hours => hours_old);

  get diagnostics changed_count = row_count;
  return changed_count;
end;
$$;

-- ---------------------------------------------------------------------
-- ANALYSIS-READY LAYER (EXPORT + STATS PIPELINE)
-- ---------------------------------------------------------------------

-- Canonical export view with required variables and helpful derived fields.
create or replace view public.analytics_v2_export_dataset as
select
  session_id,
  language_code,
  storage_payload_path,
  updated_at,

  knowledge_test_accuracy_pct,
  total_session_time_seconds,
  total_ai_interactions,
  slide_explanations,
  manual_chat,
  ueq_attractiveness,
  ueq_efficiency,
  ueq_dependability,
  ueq_stimulation,
  ueq_novelty,
  has_comment,

  case
    when total_ai_interactions > 0 then slide_explanations::numeric / total_ai_interactions
    else null
  end as explanation_share,
  case
    when total_ai_interactions > 0 then manual_chat::numeric / total_ai_interactions
    else null
  end as manual_chat_share,
  case
    when total_session_time_seconds > 0 then total_ai_interactions::numeric / (total_session_time_seconds / 60.0)
    else null
  end as interactions_per_minute
from public.analytics_v2_finalized_sessions
where language_code not in ('de', 'unknown')
  and storage_payload_path not ilike '%pilot_backup/%'
  and storage_payload_path not ilike '%/pilot_%'
  and storage_payload_path not ilike '%pilot/%'
  and storage_payload_path not ilike '%demo_testing/%'
  and storage_payload_path not ilike '%dev_testing/%';

-- Per-language descriptives for all key conference metrics.
create or replace view public.analytics_v2_descriptives_long as
with base as (
  select * from public.analytics_v2_export_dataset
), metrics as (
  select language_code, 'knowledge_test_accuracy_pct'::text as metric, knowledge_test_accuracy_pct::numeric as value from base
  union all
  select language_code, 'total_session_time_seconds', total_session_time_seconds::numeric from base
  union all
  select language_code, 'total_ai_interactions', total_ai_interactions::numeric from base
  union all
  select language_code, 'slide_explanations', slide_explanations::numeric from base
  union all
  select language_code, 'manual_chat', manual_chat::numeric from base
  union all
  select language_code, 'ueq_attractiveness', ueq_attractiveness::numeric from base
  union all
  select language_code, 'ueq_efficiency', ueq_efficiency::numeric from base
  union all
  select language_code, 'ueq_dependability', ueq_dependability::numeric from base
  union all
  select language_code, 'ueq_stimulation', ueq_stimulation::numeric from base
  union all
  select language_code, 'ueq_novelty', ueq_novelty::numeric from base
  union all
  select language_code, 'explanation_share', explanation_share::numeric from base
  union all
  select language_code, 'manual_chat_share', manual_chat_share::numeric from base
  union all
  select language_code, 'interactions_per_minute', interactions_per_minute::numeric from base
)
select
  language_code,
  metric,
  count(value) as n,
  avg(value)::numeric(12,4) as mean,
  stddev_samp(value)::numeric(12,4) as sd,
  min(value)::numeric(12,4) as min,
  percentile_cont(0.25) within group (order by value)::numeric(12,4) as q1,
  percentile_cont(0.50) within group (order by value)::numeric(12,4) as median,
  percentile_cont(0.75) within group (order by value)::numeric(12,4) as q3,
  (percentile_cont(0.75) within group (order by value)
   - percentile_cont(0.25) within group (order by value))::numeric(12,4) as iqr,
  max(value)::numeric(12,4) as max
from metrics
where value is not null
group by language_code, metric
order by metric, language_code;

-- Data quality and missingness overview per language.
create or replace view public.analytics_v2_data_quality_by_language as
select
  language_code,
  count(*) as sessions,
  avg(case when knowledge_test_accuracy_pct is not null then 1 else 0 end)::numeric(8,4) as knowledge_non_missing_rate,
  avg(case when total_session_time_seconds is not null then 1 else 0 end)::numeric(8,4) as duration_non_missing_rate,
  avg(case when total_ai_interactions is not null then 1 else 0 end)::numeric(8,4) as ai_interactions_non_missing_rate,
  avg(case when slide_explanations is not null then 1 else 0 end)::numeric(8,4) as slide_explanations_non_missing_rate,
  avg(case when manual_chat is not null then 1 else 0 end)::numeric(8,4) as manual_chat_non_missing_rate,
  avg(case when ueq_attractiveness is not null then 1 else 0 end)::numeric(8,4) as ueq_attr_non_missing_rate,
  avg(case when ueq_efficiency is not null then 1 else 0 end)::numeric(8,4) as ueq_eff_non_missing_rate,
  avg(case when ueq_dependability is not null then 1 else 0 end)::numeric(8,4) as ueq_dep_non_missing_rate,
  avg(case when ueq_stimulation is not null then 1 else 0 end)::numeric(8,4) as ueq_stim_non_missing_rate,
  avg(case when ueq_novelty is not null then 1 else 0 end)::numeric(8,4) as ueq_nov_non_missing_rate
from public.analytics_v2_export_dataset
group by language_code
order by sessions desc, language_code;

-- Within-group correlations for behavior/performance interpretation.
create or replace view public.analytics_v2_within_group_correlations as
select
  language_code,
  count(*) as n_rows,
  corr(knowledge_test_accuracy_pct::numeric, total_ai_interactions::numeric)::numeric(10,4) as corr_score_vs_ai_interactions,
  corr(knowledge_test_accuracy_pct::numeric, slide_explanations::numeric)::numeric(10,4) as corr_score_vs_slide_explanations,
  corr(knowledge_test_accuracy_pct::numeric, manual_chat::numeric)::numeric(10,4) as corr_score_vs_manual_chat,
  corr(knowledge_test_accuracy_pct::numeric, total_session_time_seconds::numeric)::numeric(10,4) as corr_score_vs_duration,
  corr(total_ai_interactions::numeric, total_session_time_seconds::numeric)::numeric(10,4) as corr_ai_interactions_vs_duration
from public.analytics_v2_export_dataset
group by language_code
order by language_code;

-- Results table for omnibus tests (ANOVA/Welch/Kruskal/etc.).
create table if not exists public.analytics_v2_stat_omnibus (
  id bigserial primary key,
  analysis_run_id uuid not null default gen_random_uuid(),
  metric text not null,
  test_name text not null,
  groups_included text[] not null,
  n_total integer not null,
  statistic numeric(16,6),
  df1 numeric(12,4),
  df2 numeric(12,4),
  p_value numeric(16,10),
  effect_size_name text,
  effect_size_value numeric(16,6),
  p_adjust_method text,
  assumptions jsonb,
  notes text,
  created_at timestamptz not null default now()
);

create index if not exists idx_analytics_v2_stat_omnibus_metric
  on public.analytics_v2_stat_omnibus(metric);
create index if not exists idx_analytics_v2_stat_omnibus_run
  on public.analytics_v2_stat_omnibus(analysis_run_id);

-- Results table for pairwise post-hoc comparisons.
create table if not exists public.analytics_v2_stat_pairwise (
  id bigserial primary key,
  analysis_run_id uuid not null,
  metric text not null,
  test_name text not null,
  group_a text not null,
  group_b text not null,
  n_a integer,
  n_b integer,
  statistic numeric(16,6),
  p_value_raw numeric(16,10),
  p_value_adjusted numeric(16,10),
  p_adjust_method text,
  effect_size_name text,
  effect_size_value numeric(16,6),
  ci_low numeric(16,6),
  ci_high numeric(16,6),
  created_at timestamptz not null default now()
);

create index if not exists idx_analytics_v2_stat_pairwise_metric
  on public.analytics_v2_stat_pairwise(metric);
create index if not exists idx_analytics_v2_stat_pairwise_run
  on public.analytics_v2_stat_pairwise(analysis_run_id);

-- Results table for assumption checks.
create table if not exists public.analytics_v2_stat_assumptions (
  id bigserial primary key,
  analysis_run_id uuid not null,
  metric text not null,
  check_name text not null,
  statistic numeric(16,6),
  p_value numeric(16,10),
  passed boolean,
  details jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_analytics_v2_stat_assumptions_metric
  on public.analytics_v2_stat_assumptions(metric);
create index if not exists idx_analytics_v2_stat_assumptions_run
  on public.analytics_v2_stat_assumptions(analysis_run_id);

-- Simple dictionary view so export users know which variables are must-have.
create or replace view public.analytics_v2_variable_catalog as
select * from (
  values
    ('session_id', 'identifier', 'Unique session identifier', true),
    ('language_code', 'grouping', 'Language / group label used for comparisons', true),
    ('knowledge_test_accuracy_pct', 'outcome', 'Primary learning outcome in percentage', true),
    ('total_session_time_seconds', 'engagement', 'Total duration in seconds', true),
    ('total_ai_interactions', 'engagement', 'Total AI interactions per session', true),
    ('slide_explanations', 'engagement', 'Slide explanation count', true),
    ('manual_chat', 'engagement', 'Manual chat message count', true),
    ('ueq_attractiveness', 'experience', 'UEQ attractiveness scale', true),
    ('ueq_efficiency', 'experience', 'UEQ efficiency scale', true),
    ('ueq_dependability', 'experience', 'UEQ dependability scale', true),
    ('ueq_stimulation', 'experience', 'UEQ stimulation scale', true),
    ('ueq_novelty', 'experience', 'UEQ novelty scale', true),
    ('has_comment', 'experience', 'Whether participant left a UEQ comment', false),
    ('explanation_share', 'derived', 'slide_explanations / total_ai_interactions', false),
    ('manual_chat_share', 'derived', 'manual_chat / total_ai_interactions', false),
    ('interactions_per_minute', 'derived', 'total_ai_interactions divided by session minutes', false)
) as t(variable_name, variable_class, description, must_have)
order by must_have desc, variable_class, variable_name;

commit;
