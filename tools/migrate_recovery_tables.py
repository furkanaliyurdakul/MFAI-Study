#!/usr/bin/env python3
"""
Supabase Migration - Create tables for data loss prevention.

Run this ONCE before deploying the data loss prevention system.

Usage:
    python tools/migrate_recovery_tables.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from supabase import create_client

def run_migration():
    """Create necessary tables in Supabase."""
    
    print("\n" + "="*60)
    print("🗄️  SUPABASE MIGRATION: Data Loss Prevention Tables")
    print("="*60)
    
    try:
        # Get Supabase credentials from Streamlit secrets
        url = st.secrets["supabase"]["url"]
        service_key = st.secrets["supabase"]["service_key"]
        
        print(f"✓ Loaded Supabase config: {url[:50]}...")
        
        # Create client
        supabase = create_client(url, service_key)
        print("✓ Connected to Supabase")
        
        # SQL for creating tables
        sql_queries = [
            # Main session checkpoints table
            """
            CREATE TABLE IF NOT EXISTS session_checkpoints (
              id bigserial primary key,
              session_id text not null,
              stage text not null,
              checkpoint_data jsonb not null,
              saved_at timestamp with time zone not null,
              created_at timestamp with time zone default now(),
              updated_at timestamp with time zone default now()
            );
            """,
            
            # Index for faster lookups
            """
            CREATE INDEX IF NOT EXISTS idx_session_checkpoint_session_id 
            ON session_checkpoints(session_id);
            """,
            
            """
            CREATE INDEX IF NOT EXISTS idx_session_checkpoint_stage 
            ON session_checkpoints(session_id, stage);
            """,
            
            # Optional: recovered data backup (for emergency recovery)
            """
            CREATE TABLE IF NOT EXISTS recovered_data_backup (
              id bigserial primary key,
              filename text not null,
              data jsonb not null,
              uploaded_at timestamp with time zone not null,
              created_at timestamp with time zone default now()
            );
            """,
            
            """
            CREATE INDEX IF NOT EXISTS idx_recovered_data_backup_filename 
            ON recovered_data_backup(filename);
            """,
        ]
        
        print("\nExecuting migrations...")
        
        # Note: Supabase Python client doesn't support raw SQL directly
        # We need to use the SQL editor or do it manually
        print("\n⚠️  IMPORTANT: Manual Step Required")
        print("="*60)
        print("\nThe Supabase Python client doesn't support raw SQL execution.")
        print("Please execute the following SQL in your Supabase SQL Editor:\n")
        
        full_sql = "\n\n".join(sql_queries)
        print(full_sql)
        
        print("\n" + "="*60)
        print("Steps to complete migration:")
        print("1. Go to https://app.supabase.com >> Your Project >> SQL Editor")
        print("2. Copy and paste the SQL above")
        print("3. Execute the query (Ctrl+Enter)")
        print("4. Verify tables appear in 'Tables' section")
        print("="*60 + "\n")
        
        # Try to verify if tables exist
        try:
            result = supabase.table("session_checkpoints").select("*", count="exact").limit(0).execute()
            print("✓ Table 'session_checkpoints' already exists (verified)")
        except Exception:
            print("ⓘ Table 'session_checkpoints' not yet created (expected)")
        
        print("\n✅ Migration guide complete!")
        print("Next step: Create the tables using the SQL above, then restart your app.\n")
        
    except KeyError as e:
        print(f"\n❌ ERROR: Missing Supabase credentials in secrets: {e}")
        print("Make sure your .streamlit/secrets.toml has:")
        print("  [supabase]")
        print("  url = 'your-project-url'")
        print("  service_key = 'your-service-key'\n")
        return False
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        return False
    
    return True


def verify_tables():
    """Verify that tables were created successfully."""
    
    print("\n" + "="*60)
    print("🔍 VERIFYING TABLES")
    print("="*60 + "\n")
    
    try:
        url = st.secrets["supabase"]["url"]
        service_key = st.secrets["supabase"]["service_key"]
        supabase = create_client(url, service_key)
        
        # Check session_checkpoints table
        try:
            result = supabase.table("session_checkpoints").select("*", count="exact").limit(1).execute()
            print("✓ session_checkpoints table: EXISTS")
            print(f"  Current rows: {result.count if hasattr(result, 'count') else 'unknown'}")
        except Exception:
            print("✗ session_checkpoints table: MISSING (run migration)")
        
        # Check recovered_data_backup table
        try:
            result = supabase.table("recovered_data_backup").select("*", count="exact").limit(1).execute()
            print("✓ recovered_data_backup table: EXISTS")
            print(f"  Current rows: {result.count if hasattr(result, 'count') else 'unknown'}")
        except Exception:
            print("ℹ recovered_data_backup table: MISSING (optional for emergency recovery)")
        
        print("\n✅ Verification complete!\n")
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}\n")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Supabase Data Loss Prevention Migration")
    parser.add_argument("--verify", action="store_true", help="Just verify existing tables")
    
    args = parser.parse_args()
    
    if args.verify:
        verify_tables()
    else:
        success = run_migration()
        if success:
            print("\nYou can now run --verify after creating the tables:")
            print("  python tools/migrate_recovery_tables.py --verify\n")
