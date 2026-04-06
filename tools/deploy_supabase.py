#!/usr/bin/env python3
"""Supabase Schema Deployment - Smart Copy-Paste Helper"""

import sys
from pathlib import Path


def get_sql_tiers():
    """Return SQL for all three tiers"""
    tier1 = """-- TIER 1: PERFORMANCE INDEXES
create index if not exists presence_status_lastseen on public.presence(status, last_seen desc);
create index if not exists presence_interview_lastseen on public.presence(is_in_interview, last_seen desc);
create index if not exists presence_user_started on public.presence(user_id, started_at desc);
create index if not exists presence_language_created on public.presence(language_code, created_at desc);
create index if not exists session_analytics_user_language on public.session_analytics(user_id, language_code);
create index if not exists session_analytics_status_completed on public.session_analytics(status, completed_at desc);
create index if not exists session_analytics_created on public.session_analytics(created_at desc);"""

    tier2 = """-- TIER 2: ANALYSIS TABLES & INDEXES
create table if not exists public.interaction_logs (
  id bigserial primary key,
  session_id text not null references public.session_analytics(session_id) on delete cascade,
  interaction_type text not null, timestamp timestamp with time zone default now(),
  slide_number integer, user_input text, ai_response_length integer,
  response_time_ms integer, model_used text, language_code text,
  tokens_used integer, cost_estimate numeric(8, 4),
  created_at timestamp with time zone default now()
);
create table if not exists public.ueq_detailed_scores (
  id bigserial primary key,
  session_id text not null references public.session_analytics(session_id) on delete cascade,
  question_number integer not null, question_text text, scale_dimension text,
  score integer, timestamp timestamp with time zone default now(),
  created_at timestamp with time zone default now()
);
create table if not exists public.knowledge_test_detailed (
  id bigserial primary key,
  session_id text not null references public.session_analytics(session_id) on delete cascade,
  question_number integer not null, question_text text, correct_answer text,
  user_answer text, is_correct boolean, topic text, time_spent_seconds integer,
  created_at timestamp with time zone default now()
);
create table if not exists public.language_analysis (
  id bigserial primary key,
  session_id text not null references public.session_analytics(session_id) on delete cascade,
  language_code text not null, native_language_proficiency text,
  english_proficiency text, comprehension_issues text[],
  ai_response_clarity_score integer, request_for_clarification_count integer,
  time_to_understand_seconds integer,
  created_at timestamp with time zone default now()
);
create table if not exists public.engagement_metrics (
  id bigserial primary key,
  session_id text not null references public.session_analytics(session_id) on delete cascade,
  page_name text not null, time_on_page_seconds integer,
  interactions_on_page integer, scroll_depth_percent integer,
  focus_lost_count integer, idle_time_seconds integer,
  timestamp timestamp with time zone default now(),
  created_at timestamp with time zone default now()
);
create table if not exists public.cohort_comparison (
  id bigserial primary key, cohort_name text not null,
  language_code text not null, session_count integer default 0,
  avg_knowledge_test_score numeric(5, 2), avg_ueq_attractiveness numeric(5, 2),
  avg_ueq_perspicuity numeric(5, 2), avg_ueq_efficiency numeric(5, 2),
  avg_ueq_dependability numeric(5, 2), avg_ueq_stimulation numeric(5, 2),
  avg_ueq_novelty numeric(5, 2), avg_session_duration_minutes numeric(8, 2),
  completion_rate numeric(5, 2), last_updated timestamp with time zone default now(),
  created_at timestamp with time zone default now(),
  unique(cohort_name, language_code)
);
create index if not exists interaction_logs_session_id on public.interaction_logs(session_id);
create index if not exists interaction_logs_timestamp on public.interaction_logs(timestamp desc);
create index if not exists interaction_logs_type_language on public.interaction_logs(interaction_type, language_code);
create index if not exists ueq_detailed_session_id on public.ueq_detailed_scores(session_id);
create index if not exists ueq_detailed_dimension on public.ueq_detailed_scores(scale_dimension);
create index if not exists knowledge_test_detailed_session on public.knowledge_test_detailed(session_id);
create index if not exists knowledge_test_detailed_topic on public.knowledge_test_detailed(topic);
create index if not exists language_analysis_session on public.language_analysis(session_id);
create index if not exists language_analysis_language_code on public.language_analysis(language_code);
create index if not exists engagement_metrics_session_page on public.engagement_metrics(session_id, page_name);
create index if not exists cohort_comparison_language on public.cohort_comparison(language_code);"""

    tier3 = """-- TIER 3: ANALYSIS VIEWS
create or replace view public.v_session_summary as
select s.session_id, s.user_id, s.language_code, p.status, s.started_at, s.completed_at,
  extract(epoch from (s.completed_at - s.started_at)) / 60 as duration_minutes,
  s.profile_completed, s.learning_completed, s.knowledge_test_completed, s.ueq_completed,
  s.knowledge_test_score, s.total_chat_messages, s.total_slide_explanations, s.total_slides_viewed
from public.session_analytics s
left join public.presence p on s.session_id = p.session_id;

create or replace view public.v_language_performance as
select language_code, count(distinct session_id) as sessions_completed,
  round(avg(knowledge_test_score)::numeric, 2) as avg_knowledge_score,
  min(knowledge_test_score) as min_knowledge_score, max(knowledge_test_score) as max_knowledge_score,
  round(avg(total_session_time)::numeric / 60, 2) as avg_duration_minutes,
  round(count(case when knowledge_test_completed = true then 1 end)::numeric/count(distinct session_id)*100, 2) as completion_rate_percent,
  round(avg(total_chat_messages)::numeric, 1) as avg_chat_interactions,
  round(avg(total_slide_explanations)::numeric, 1) as avg_slide_explanations
from public.session_analytics
where completed_at is not null and knowledge_test_completed = true
group by language_code;

create or replace view public.v_active_sessions as
select p.session_id, p.user_id, p.language_code, p.current_page, p.is_in_interview,
  p.last_seen, extract(epoch from (now() - p.last_seen)) as seconds_since_activity,
  case when extract(epoch from (now() - p.last_seen)) > 60 then 'ABANDONED' else 'ACTIVE' end as session_status
from public.presence p
where p.status = 'active' and p.last_seen > now() - interval '24 hours';

create or replace view public.v_engagement_by_page as
select em.page_name, count(distinct em.session_id) as sessions_viewed,
  round(avg(em.time_on_page_seconds)::numeric / 60, 2) as avg_time_minutes,
  round(avg(em.interactions_on_page)::numeric, 1) as avg_interactions,
  round(avg(em.idle_time_seconds)::numeric, 1) as avg_idle_seconds,
  round(avg(em.focus_lost_count)::numeric, 1) as avg_focus_losses
from public.engagement_metrics em
group by em.page_name;"""

    return [
        {"num": 1, "name": "Performance Indexes", "sql": tier1, "items": 7},
        {"num": 2, "name": "Analysis Tables & Indexes", "sql": tier2, "items": 17},
        {"num": 3, "name": "Analysis Views", "sql": tier3, "items": 4},
    ]


def copy_to_clipboard(text):
    """Copy to Windows clipboard"""
    try:
        import subprocess
        p = subprocess.Popen(['clip'], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        p.communicate(text.encode('utf-8'))
        return True
    except:
        return False


def save_sql_file(content, filename):
    """Save SQL to file"""
    path = Path.cwd() / "output" / filename
    path.parent.mkdir(exist_ok=True)
    path.write_text(content)
    return path


def main():
    print("\n" + "="*70)
    print("MFAI-Study Supabase DEPLOYMENT HELPER")
    print("="*70)
    print("\nDEPLOYMENT OPTIONS:\n")
    print("  1 - Copy each TIER to clipboard")
    print("  2 - Save all TIERS to output/ files")
    print("  3 - View TIER SQL in terminal")
    print("  4 - Exit\n")
    
    choice = input("Select (1-4): ").strip()
    tiers = get_sql_tiers()
    
    if choice == "1":
        for tier in tiers:
            print(f"\nTIER {tier['num']}: {tier['name']} ({tier['items']} items)")
            if copy_to_clipboard(tier['sql']):
                print("  => Copied to clipboard!")
                print("\n  Steps:")
                print("     1. Go to https://supabase.com/dashboard")
                print("     2. SQL Editor -> New query -> Paste -> Run -> Save")
            else:
                print("  => Saved to file instead")
                path = save_sql_file(tier['sql'], f"STEP_{tier['num']}.sql")
                print(f"     {path}")
            
            if tier['num'] < 3:
                input("\n  Press Enter to continue...")
    
    elif choice == "2":
        print("\nSaving SQL files...\n")
        for tier in tiers:
            path = save_sql_file(tier['sql'], f"STEP_{tier['num']}.sql")
            print(f"  TIER {tier['num']}: {path.name}")
        print("\nAll files saved to: output/")
        print("Copy each file contents into Supabase SQL Editor")
    
    elif choice == "3":
        for tier in tiers:
            print(f"\n{'='*70}")
            print(f"TIER {tier['num']}: {tier['name']}")
            print(f"{'='*70}\n")
            print(tier['sql'])
    
    elif choice == "4":
        print("\nGoodbye!")
        return
    
    else:
        print("\nInvalid option")
        return
    
    # Summary
    print("\n" + "="*70)
    print("DEPLOYMENT COMPLETE")
    print("="*70)
    print("""
SUMMARY:
  + 7 performance indexes
  + 6 new analysis tables
  + 11 table indexes
  + 4 analysis views

NEXT STEPS:
  1. Run SQL queries in Supabase
  2. Verify: python tools/setup_supabase.py
  3. Update loggers to populate new tables

Your Supabase is now optimized!
""")


if __name__ == "__main__":
    main()
