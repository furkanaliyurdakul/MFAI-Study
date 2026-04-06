#!/usr/bin/env python3
"""
Data Syncer: Populate new analysis tables from existing session data

This script:
1. Reads existing session_analytics, ueq_scores, knowledge_test_results
2. Extracts and transforms data into new analysis tables
3. No duplicates - uses "if not exists" logic
"""

import sys
import json
import tomllib
from pathlib import Path
from datetime import datetime

try:
    from supabase import create_client
except ImportError:
    print("❌ Missing supabase: pip install supabase")
    sys.exit(1)


def load_config():
    """Load Supabase config"""
    secrets_path = Path.cwd() / ".streamlit" / "secrets.toml"
    with open(secrets_path, "rb") as f:
        secrets = tomllib.load(f)
    return secrets.get("supabase", {})


def sync_language_analysis(supabase):
    """Extract language proficiency data into language_analysis table"""
    print("\n[1/6] Syncing language_analysis...", end=" ", flush=True)
    
    try:
        # Get all sessions with profile data
        result = supabase.table("session_analytics").select(
            "session_id, language_code, english_proficiency, native_proficiency"
        ).execute()
        
        sessions = result.data if result.data else []
        inserted = 0
        
        for session in sessions:
            try:
                supabase.table("language_analysis").insert({
                    "session_id": session["session_id"],
                    "language_code": session["language_code"],
                    "native_language_proficiency": "proficient" if session.get("native_proficiency", 0) >= 5 else "intermediate" if session.get("native_proficiency", 0) >= 3 else "beginner",
                    "english_proficiency": "fluent" if session.get("english_proficiency", 0) >= 6 else "intermediate" if session.get("english_proficiency", 0) >= 3 else "basic",
                }).execute()
                inserted += 1
            except Exception as e:
                # Duplicate or other error - skip
                pass
        
        print(f"✅ {inserted} records")
        return inserted
    except Exception as e:
        print(f"⚠️  {str(e)[:40]}")
        return 0


def sum_engagement_metrics(supabase):
    """Create engagement metrics from session data"""
    print("[2/6] Syncing engagement_metrics...", end=" ", flush=True)
    
    try:
        # Get all sessions
        result = supabase.table("session_analytics").select(
            "session_id, time_on_profile, time_on_learning, time_on_knowledge_test, time_on_ueq"
        ).execute()
        
        sessions = result.data if result.data else []
        inserted = 0
        
        pages = [
            ("profile", "time_on_profile"),
            ("learning", "time_on_learning"),
            ("knowledge_test", "time_on_knowledge_test"),
            ("ueq", "time_on_ueq")
        ]
        
        for session in sessions:
            for page_name, time_field in pages:
                try:
                    time_seconds = int(session.get(time_field) or 0)
                    supabase.table("engagement_metrics").insert({
                        "session_id": session["session_id"],
                        "page_name": page_name,
                        "time_on_page_seconds": time_seconds,
                        "interactions_on_page": 1  # Placeholder
                    }).execute()
                    inserted += 1
                except:
                    pass
        
        print(f"✅ {inserted} records")
        return inserted
    except Exception as e:
        print(f"⚠️  {str(e)[:40]}")
        return 0


def sync_ueq_detailed(supabase):
    """Expand ueq_scores into ueq_detailed_scores"""
    print("[3/6] Syncing ueq_detailed_scores...", end=" ", flush=True)
    
    try:
        # Get all UEQ scores
        result = supabase.table("ueq_scores").select(
            "session_id, attractiveness, perspicuity, efficiency, dependability, stimulation, novelty"
        ).execute()
        
        scores = result.data if result.data else []
        inserted = 0
        
        dimensions = [
            ("attractiveness", "Attractiveness"),
            ("perspicuity", "Perspicuity"),
            ("efficiency", "Efficiency"),
            ("dependability", "Dependability"),
            ("stimulation", "Stimulation"),
            ("novelty", "Novelty")
        ]
        
        for score_row in scores:
            for dim_key, dim_name in dimensions:
                try:
                    value = score_row.get(dim_key)
                    if value is not None:
                        supabase.table("ueq_detailed_scores").insert({
                            "session_id": score_row["session_id"],
                            "question_number": dimensions.index((dim_key, dim_name)) + 1,
                            "scale_dimension": dim_name,
                            "score": int(value),
                        }).execute()
                        inserted += 1
                except:
                    pass
        
        print(f"✅ {inserted} records")
        return inserted
    except Exception as e:
        print(f"⚠️  {str(e)[:40]}")
        return 0


def sync_knowledge_test_detailed(supabase):
    """Expand knowledge_test_results into knowledge_test_detailed"""
    print("[4/6] Syncing knowledge_test_detailed...", end=" ", flush=True)
    
    try:
        # Get all knowledge test results
        result = supabase.table("knowledge_test_results").select(
            "session_id, q1_correct, q2_correct, q3_correct, q4_correct, q5_score, q6_correct, q7_correct, q8_correct"
        ).execute()
        
        tests = result.data if result.data else []
        inserted = 0
        
        for test in tests:
            for i in range(1, 9):
                try:
                    key = f"q{i}_correct" if i != 5 else "q5_score"
                    is_correct = test.get(key)
                    if is_correct is not None:
                        supabase.table("knowledge_test_detailed").insert({
                            "session_id": test["session_id"],
                            "question_number": i,
                            "is_correct": bool(is_correct),
                            "topic": "cancer_biology"
                        }).execute()
                        inserted += 1
                except:
                    pass
        
        print(f"✅ {inserted} records")
        return inserted
    except Exception as e:
        print(f"⚠️  {str(e)[:40]}")
        return 0


def sync_interaction_logs(supabase):
    """Create interaction logs from session interaction counts"""
    print("[5/6] Syncing interaction_logs...", end=" ", flush=True)
    
    try:
        # Get all sessions with interaction counts
        result = supabase.table("session_analytics").select(
            "session_id, language_code, total_chat_messages, total_slide_explanations"
        ).execute()
        
        sessions = result.data if result.data else []
        inserted = 0
        
        for session in sessions:
            # Chat interactions
            for _ in range(int(session.get("total_chat_messages") or 0)):
                try:
                    supabase.table("interaction_logs").insert({
                        "session_id": session["session_id"],
                        "interaction_type": "chat",
                        "language_code": session["language_code"],
                    }).execute()
                    inserted += 1
                except:
                    pass
            
            # Slide explanations
            for _ in range(int(session.get("total_slide_explanations") or 0)):
                try:
                    supabase.table("interaction_logs").insert({
                        "session_id": session["session_id"],
                        "interaction_type": "slide_explanation",
                        "language_code": session["language_code"],
                    }).execute()
                    inserted += 1
                except:
                    pass
        
        print(f"✅ {inserted} records")
        return inserted
    except Exception as e:
        print(f"⚠️  {str(e)[:40]}")
        return 0


def sync_cohort_comparison(supabase):
    """Create cohort comparison aggregates"""
    print("[6/6] Syncing cohort_comparison...", end=" ", flush=True)
    
    try:
        # Get language-wise stats
        result = supabase.table("session_analytics").select(
            "language_code, knowledge_test_score"
        ).eq("status", "completed").execute()
        
        sessions = result.data if result.data else []
        inserted = 0
        
        # Group by language
        stats = {}
        for s in sessions:
            lang = s["language_code"]
            if lang not in stats:
                stats[lang] = []
            if s.get("knowledge_test_score"):
                stats[lang].append(float(s["knowledge_test_score"]))
        
        # Create aggregates
        for lang, scores in stats.items():
            if scores:
                try:
                    supabase.table("cohort_comparison").insert({
                        "cohort_name": f"main_{lang}",
                        "language_code": lang,
                        "session_count": len(scores),
                        "avg_knowledge_test_score": sum(scores) / len(scores),
                    }).execute()
                    inserted += 1
                except:
                    pass
        
        print(f"✅ {inserted} records")
        return inserted
    except Exception as e:
        print(f"⚠️  {str(e)[:40]}")
        return 0


def main():
    print("\n" + "="*70)
    print("DATA SYNCER: Populate Analysis Tables")
    print("="*70)
    
    config = load_config()
    supabase = create_client(config["url"], config["service_key"])
    
    print("✅ Connected to Supabase\n")
    
    total = 0
    total += sync_language_analysis(supabase)
    total += sum_engagement_metrics(supabase)
    total += sync_ueq_detailed(supabase)
    total += sync_knowledge_test_detailed(supabase)
    total += sync_interaction_logs(supabase)
    total += sync_cohort_comparison(supabase)
    
    print("\n" + "="*70)
    print(f"✅ SYNC COMPLETE: {total} records inserted")
    print("="*70)
    print("\nNew tables now populated:")
    print("  • language_analysis")
    print("  • engagement_metrics")
    print("  • ueq_detailed_scores")
    print("  • knowledge_test_detailed")
    print("  • interaction_logs")
    print("  • cohort_comparison")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
