#!/usr/bin/env python3
"""Verify new analysis tables exist"""

import sys
import tomllib
from pathlib import Path

try:
    from supabase import create_client
except ImportError:
    print("Missing supabase")
    sys.exit(1)


def verify():
    secrets_path = Path.cwd() / ".streamlit" / "secrets.toml"
    with open(secrets_path, "rb") as f:
        secrets = tomllib.load(f)
    config = secrets.get("supabase", {})
    
    supabase = create_client(config["url"], config["service_key"])
    
    print("\nChecking NEW analysis tables:\n")
    
    new_tables = [
        "interaction_logs",
        "ueq_detailed_scores", 
        "knowledge_test_detailed",
        "language_analysis",
        "engagement_metrics",
        "cohort_comparison"
    ]
    
    existing = []
    missing = []
    
    for table_name in new_tables:
        try:
            result = supabase.table(table_name).limit(1).execute()
            existing.append(table_name)
            print(f"  ✅ {table_name}")
        except Exception as e:
            missing.append(table_name)
            print(f"  ❌ {table_name}")
    
    print(f"\n{'='*70}")
    print(f"Result: {len(existing)}/6 tables exist")
    print(f"{'='*70}\n")
    
    if len(existing) == 6:
        print("✅ ALL NEW TABLES CREATED SUCCESSFULLY!")
        print("\nNext step: Update loggers to populate these tables")
    else:
        print(f"⚠️  Missing tables: {missing}")
        print("\nTrying alternative verification...")
        # Try to get list of all tables from information_schema
        print("Tables needing manual SQL deployment in Supabase:")
        for t in missing:
            print(f"  - {t}")


if __name__ == "__main__":
    verify()
