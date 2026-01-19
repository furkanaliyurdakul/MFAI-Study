"""
Re-sync Knowledge Test Data for Pilot Sessions

This script re-syncs knowledge test results from pilot sessions to Supabase
with the corrected field name mappings. Use after fixing analytics_syncer.py
to recover per-question answer data.

Usage:
    python tools/resync_pilot_knowledge_tests.py
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics_syncer import get_analytics_syncer


def find_knowledge_test_files(base_dir: str) -> list[tuple[str, Path]]:
    """Find all knowledge_test_results.json files in output directories.
    
    Args:
        base_dir: Base output directory to search
        
    Returns:
        List of (session_id, file_path) tuples
    """
    results = []
    base_path = Path(base_dir)
    
    # Search through cohort directories
    for cohort_dir in base_path.iterdir():
        if not cohort_dir.is_dir():
            continue
            
        # Search through session directories
        for session_dir in cohort_dir.iterdir():
            if not session_dir.is_dir():
                continue
                
            # Look for knowledge test results
            kt_file = session_dir / "knowledge_test" / "knowledge_test_results.json"
            if kt_file.exists():
                session_id = session_dir.name
                results.append((session_id, kt_file))
    
    return results


def load_knowledge_test_json(file_path: Path) -> dict | None:
    """Load and validate knowledge test JSON file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON dict or None if invalid
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate required fields
        if "answers" not in data or "session_id" not in data:
            print(f"  ⚠️  Missing required fields in {file_path}")
            return None
            
        return data
        
    except Exception as e:
        print(f"  ❌ Error reading {file_path}: {e}")
        return None


def resync_knowledge_test(session_id: str, test_data: dict, file_path: Path, syncer) -> bool:
    """Re-sync a single knowledge test to Supabase.
    
    Args:
        session_id: Session identifier
        test_data: Knowledge test data from JSON
        file_path: Path to JSON file
        syncer: AnalyticsSyncer instance
        
    Returns:
        True if successful
    """
    try:
        # First check if session exists in database
        result = syncer.supabase.table("session_analytics").select("session_id").eq("session_id", session_id).execute()
        
        if not result.data:
            print(f"  ⚠️  Session {session_id} not found in database - skipping")
            return False
        
        # Delete existing knowledge test results to avoid duplicates
        syncer.supabase.table("knowledge_test_results").delete().eq("session_id", session_id).execute()
        
        # Re-sync with corrected field mappings
        success = syncer.sync_knowledge_test(
            session_id=session_id,
            results=test_data,
            file_path=file_path
        )
        
        return success
        
    except Exception as e:
        print(f"  ❌ Error syncing {session_id}: {e}")
        return False


def main():
    """Main execution function."""
    print("=" * 70)
    print("Knowledge Test Re-Sync Tool")
    print("=" * 70)
    print()
    
    # Get base output directory
    base_dir = Path(__file__).parent.parent / "output"
    
    if not base_dir.exists():
        print(f"❌ Output directory not found: {base_dir}")
        return
    
    print(f"📁 Scanning for knowledge test files in: {base_dir}")
    print()
    
    # Find all knowledge test files
    kt_files = find_knowledge_test_files(str(base_dir))
    
    if not kt_files:
        print("⚠️  No knowledge test files found!")
        return
    
    print(f"✅ Found {len(kt_files)} knowledge test files")
    print()
    
    # Initialize analytics syncer
    print("🔗 Connecting to Supabase...")
    syncer = get_analytics_syncer()
    
    if not syncer:
        print("❌ Failed to initialize analytics syncer")
        print("   Check your Supabase credentials in config.py")
        return
    
    print("✅ Connected to Supabase")
    print()
    
    # Process each file
    print("-" * 70)
    print("Re-syncing Knowledge Tests:")
    print("-" * 70)
    print()
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for session_id, file_path in kt_files:
        print(f"📝 Processing: {session_id}")
        
        # Load JSON
        test_data = load_knowledge_test_json(file_path)
        if not test_data:
            error_count += 1
            continue
        
        # Validate session_id matches
        if test_data.get("session_id") != session_id:
            print(f"  ⚠️  Session ID mismatch in JSON: {test_data.get('session_id')} vs {session_id}")
            skip_count += 1
            continue
        
        # Re-sync to database
        if resync_knowledge_test(session_id, test_data, file_path, syncer):
            success_count += 1
            print(f"  ✅ Successfully re-synced")
        else:
            error_count += 1
        
        print()
    
    # Summary
    print("=" * 70)
    print("Re-Sync Summary:")
    print("=" * 70)
    print(f"✅ Successfully re-synced: {success_count}")
    print(f"⏭️  Skipped:               {skip_count}")
    print(f"❌ Errors:                {error_count}")
    print(f"📊 Total processed:       {len(kt_files)}")
    print()
    
    if success_count > 0:
        print("🎉 Knowledge test data has been recovered!")
        print("   Per-question answers are now available in Supabase for analysis.")
    
    if error_count > 0:
        print()
        print("⚠️  Some files had errors. Check the output above for details.")


if __name__ == "__main__":
    main()
