#!/usr/bin/env python3
"""
Supabase Inspector & Setup Script

Connects to your Supabase instance, inspects existing tables and schemas,
and provides configuration recommendations.

Usage:
    python tools/setup_supabase.py
"""

import sys
import tomllib
import json
from pathlib import Path
from datetime import datetime

# Try to import supabase
try:
    from supabase import create_client
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("   Run: pip install supabase")
    sys.exit(1)


def load_secrets():
    """Load Supabase credentials from .streamlit/secrets.toml"""
    secrets_path = Path.cwd() / ".streamlit" / "secrets.toml"
    
    if not secrets_path.exists():
        print(f"❌ Secrets file not found: {secrets_path}")
        sys.exit(1)
    
    try:
        with open(secrets_path, "rb") as f:
            secrets = tomllib.load(f)
        
        supabase_config = secrets.get("supabase", {})
        if not all(k in supabase_config for k in ["url", "service_key"]):
            print("❌ Missing Supabase credentials in secrets.toml")
            print("   Required: supabase.url, supabase.service_key")
            sys.exit(1)
        
        return supabase_config
    except Exception as e:
        print(f"❌ Error reading secrets.toml: {e}")
        sys.exit(1)


def extract_db_url(supabase_url, service_key):
    """Extract PostgreSQL connection parameters from Supabase URL and service key"""
    # Supabase URL format: https://xxxxx.supabase.co
    # Extract project ref
    project_ref = supabase_url.split("https://")[1].split(".")[0]
    return {"project_ref": project_ref}


def inspect_tables_via_rest(client):
    """Get list of tables using Supabase REST API"""
    try:
        # Try to query each known table
        tables = []
        for table_name in ["presence", "session_analytics", "pg_tables"]:
            try:
                resp = client.table(table_name).select("*").limit(1).execute()
                if resp and resp.data is not None:
                    tables.append(table_name)
            except Exception:
                pass
        
        return tables if tables else None
    except Exception as e:
        print(f"⚠️  Could not query tables via REST: {e}")
        return None


def test_table_info(client, table_name):
    """Test accessing a table and get basic info"""
    try:
        result = client.table(table_name).select("*").limit(1).execute()
        return {
            "exists": True,
            "accessible": True,
            "row_count": len(result.data) if result.data else 0
        }
    except Exception as e:
        return {
            "exists": False,
            "accessible": False,
            "error": str(e)
        }


def connect_supabase(config):
    """Create authenticated Supabase client using service key"""
    try:
        client = create_client(config["url"], config["service_key"])
        print(f"✅ Connected to Supabase: {config['url']}")
        return client
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        sys.exit(1)


def main():
    """Main inspection workflow"""
    print("\n" + "="*70)
    print("🔍 MFAI-Study Supabase Inspector")
    print("="*70)
    
    # Load credentials
    print("\n[1/3] Loading Supabase credentials...")
    config = load_secrets()
    print(f"     ✅ Supabase URL: {config['url']}")
    print(f"     ✅ Service key configured")
    
    # Connect to Supabase
    print("\n[2/3] Connecting to Supabase...")
    client = connect_supabase(config)
    
    # Check for required tables
    print("\n[3/3] Checking tables...")
    print("-" * 70)
    
    # Check presence table
    print("\n📊 TABLE: presence")
    presence_info = test_table_info(client, "presence")
    if presence_info["accessible"]:
        print("  ✅ EXISTS and ACCESSIBLE")
        try:
            result = client.table("presence").select("*").execute()
            print(f"  📈 Rows: {len(result.data) if result.data else 0}")
            if result.data and len(result.data) > 0:
                print(f"  🔍 Sample record:")
                print(f"     {json.dumps(result.data[0], indent=6, default=str)}")
        except Exception as e:
            print(f"  ⚠️  Error reading: {e}")
    else:
        print(f"  ❌ NOT FOUND or NOT ACCESSIBLE")
        if "error" in presence_info:
            print(f"     Error: {presence_info['error']}")
    
    # Check session_analytics table
    print("\n📊 TABLE: session_analytics")
    analytics_info = test_table_info(client, "session_analytics")
    if analytics_info["accessible"]:
        print("  ✅ EXISTS and ACCESSIBLE")
        try:
            result = client.table("session_analytics").select("*").execute()
            print(f"  📈 Rows: {len(result.data) if result.data else 0}")
            if result.data and len(result.data) > 0:
                print(f"  🔍 Sample record:")
                print(f"     {json.dumps(result.data[0], indent=6, default=str)}")
        except Exception as e:
            print(f"  ⚠️  Error reading: {e}")
    else:
        print(f"  ❌ NOT FOUND or NOT ACCESSIBLE")
        if "error" in analytics_info:
            print(f"     Error: {analytics_info['error']}")
    
    # Summary
    print("\n" + "="*70)
    print("📋 SUMMARY")
    print("="*70)
    presence_ok = presence_info.get("accessible", False)
    analytics_ok = analytics_info.get("accessible", False)
    
    if presence_ok and analytics_ok:
        print("\n✅ ALL TABLES CONFIGURED AND ACCESSIBLE")
        print("\nYour Supabase is ready for:")
        print("  • Real-time session presence tracking")
        print("  • Research data analytics collection")
        print("  • Concurrent session management")
    else:
        print("\n⚠️  SOME TABLES ARE MISSING")
        print("\nAction required:")
        if not presence_ok:
            print("  1. Create 'presence' table (instructions below)")
        if not analytics_ok:
            print("  2. Create 'session_analytics' table (instructions below)")
        
        print("\n" + "="*70)
        print("SQL TO RUN IN SUPABASE SQL EDITOR")
        print("="*70)
        
        if not presence_ok:
            print("""
-- Create presence table for session tracking
create table public.presence (
  session_id text primary key,
  user_id text not null,
  language_code text,
  current_page text,
  started_at timestamp with time zone,
  last_seen timestamp with time zone default now(),
  updated_at timestamp with time zone default now(),
  is_in_interview boolean default false,
  status text default 'active',
  completed_at timestamp with time zone,
  created_at timestamp with time zone default now()
);

create index presence_active_sessions on public.presence(status, last_seen desc);
create index presence_interview on public.presence(is_in_interview, last_seen desc);""")
        
        if not analytics_ok:
            print("""
-- Create session_analytics table for research data
create table public.session_analytics (
  session_id text primary key,
  user_id text,
  language_code text,
  started_at timestamp with time zone default now(),
  completed_at timestamp with time zone,
  profile_data jsonb,
  test_results jsonb,
  ueq_responses jsonb,
  interaction_count integer default 0,
  ai_responses integer default 0,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

create index session_analytics_user on public.session_analytics(user_id);
create index session_analytics_language on public.session_analytics(language_code);""")
        
        print("""
HOW TO RUN THIS SQL:
1. Go to https://app.supabase.com/projects
2. Click on: bbnmgwiiyvnksftwxxuc
3. Left sidebar → SQL Editor
4. Click "New query"
5. Paste the SQL above
6. Click "Run"
7. Re-run this script to verify
""")
    
    print("\n")


if __name__ == "__main__":
    main()
