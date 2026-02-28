"""Pilot Data Backup & Cleanup Tool for Supabase.

Backs up all pilot testing data from Supabase (Storage + DB tables),
downloads it locally, and cleans Supabase for the actual experiment.

Usage:
    python tools/pilot_backup_and_clean.py

What it does:
  1. Lists all files in the 'interview-results' storage bucket
  2. Downloads them to a local backup folder (output/pilot_backup/)
  3. Copies them to a 'pilot_backup/' prefix inside the same bucket
  4. Exports all DB table data (session_analytics, knowledge_test_results,
     ueq_scores, learning_interactions, presence) to local JSON files
  5. Optionally deletes the original files and DB records from Supabase

Requires: supabase Python package (pip install supabase)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path so we can import project modules if needed
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from supabase import create_client
except ImportError:
    print("❌ 'supabase' package not installed. Run: pip install supabase")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════
BUCKET_NAME = "interview-results"
BACKUP_DIR = PROJECT_ROOT / "output" / "pilot_backup"
DB_BACKUP_DIR = BACKUP_DIR / "database_exports"

DB_TABLES = [
    "session_analytics",
    "knowledge_test_results",
    "ueq_scores",
    "learning_interactions",
    "presence",
]

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════
def get_credentials():
    """Get Supabase credentials - try secrets.toml first, then prompt."""
    url = None
    service_key = None

    # Try .streamlit/secrets.toml
    secrets_path = PROJECT_ROOT / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                tomllib = None

        if tomllib:
            with open(secrets_path, "rb") as f:
                secrets = tomllib.load(f)
            sb = secrets.get("supabase", {})
            url = sb.get("url")
            service_key = sb.get("service_key")

    if url and service_key:
        print(f"✅ Loaded credentials from .streamlit/secrets.toml")
        print(f"   URL: {url[:40]}...")
        return url, service_key

    # Prompt user
    print("\n🔑 Supabase credentials not found in secrets.toml.")
    print("   Enter them manually (find these in your Supabase dashboard → Settings → API):\n")
    url = input("   Supabase URL: ").strip()
    service_key = input("   Service Role Key (service_role): ").strip()

    if not url or not service_key:
        print("❌ Both URL and service key are required.")
        sys.exit(1)

    return url, service_key


def list_bucket_files(supabase, bucket_name, prefix=""):
    """Recursively list all files in a bucket under given prefix."""
    all_files = []

    try:
        items = supabase.storage.from_(bucket_name).list(prefix or "")
    except Exception as e:
        print(f"   ⚠️  Error listing '{prefix}': {e}")
        return all_files

    for item in items:
        name = item.get("name", "") if isinstance(item, dict) else getattr(item, "name", "")
        item_id = item.get("id", None) if isinstance(item, dict) else getattr(item, "id", None)
        metadata = item.get("metadata", None) if isinstance(item, dict) else getattr(item, "metadata", None)

        full_path = f"{prefix}/{name}".lstrip("/") if prefix else name

        # If item has no id and no metadata, it's likely a folder
        is_folder = (item_id is None and metadata is None)

        if is_folder:
            # Recurse into subfolder
            sub_files = list_bucket_files(supabase, bucket_name, full_path)
            all_files.extend(sub_files)
        else:
            all_files.append(full_path)

    return all_files


def download_file(supabase, bucket_name, file_path, local_path):
    """Download a single file from Supabase storage."""
    try:
        data = supabase.storage.from_(bucket_name).download(file_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"   ❌ Failed to download {file_path}: {e}")
        return False


def upload_file(supabase, bucket_name, source_data, dest_path):
    """Upload data to a new path in the bucket."""
    try:
        # Determine content type
        ext = Path(dest_path).suffix.lower()
        content_types = {
            ".json": "application/json",
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".mp4": "video/mp4",
        }
        content_type = content_types.get(ext, "application/octet-stream")

        result = supabase.storage.from_(bucket_name).upload(
            path=dest_path,
            file=source_data,
            file_options={"content-type": content_type}
        )

        # Check for errors
        if hasattr(result, "error") and result.error:
            if "already exists" in str(result.error).lower():
                return True  # Already backed up
            print(f"   ⚠️  Upload error for {dest_path}: {result.error}")
            return False
        return True
    except Exception as e:
        if "already exists" in str(e).lower() or "Duplicate" in str(e):
            return True  # Already backed up
        print(f"   ❌ Failed to upload {dest_path}: {e}")
        return False


def delete_files(supabase, bucket_name, file_paths, batch_size=50):
    """Delete files from bucket in batches."""
    deleted = 0
    for i in range(0, len(file_paths), batch_size):
        batch = file_paths[i:i + batch_size]
        try:
            supabase.storage.from_(bucket_name).remove(batch)
            deleted += len(batch)
        except Exception as e:
            print(f"   ⚠️  Error deleting batch: {e}")
    return deleted


def export_table(supabase, table_name):
    """Export all rows from a table. Returns list of dicts."""
    try:
        # Fetch all records (paginate for large tables)
        all_rows = []
        page_size = 1000
        offset = 0

        while True:
            result = supabase.table(table_name).select("*").range(offset, offset + page_size - 1).execute()
            rows = result.data if result.data else []
            all_rows.extend(rows)

            if len(rows) < page_size:
                break
            offset += page_size

        return all_rows
    except Exception as e:
        print(f"   ❌ Failed to export {table_name}: {e}")
        return []


def delete_table_rows(supabase, table_name, primary_key="session_id"):
    """Delete all rows from a table."""
    try:
        # For tables with session_id as PK or FK, we can delete all
        # Using a broad filter that matches everything
        if table_name == "presence":
            supabase.table(table_name).delete().neq("session_id", "___never_match___").execute()
        elif table_name in ("ueq_scores", "knowledge_test_results", "learning_interactions"):
            # These have serial PKs, delete via session_id reference
            supabase.table(table_name).delete().neq("session_id", "___never_match___").execute()
        else:
            supabase.table(table_name).delete().neq("session_id", "___never_match___").execute()
        return True
    except Exception as e:
        print(f"   ❌ Failed to delete rows from {table_name}: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════
# MAIN WORKFLOW
# ═══════════════════════════════════════════════════════════════════
def main():
    print("\n" + "=" * 65)
    print("  🧹 PILOT DATA BACKUP & CLEANUP TOOL")
    print("=" * 65)
    print(f"  Timestamp: {TIMESTAMP}")
    print(f"  Local backup dir: {BACKUP_DIR}")
    print("=" * 65 + "\n")

    # ── Step 0: Connect ──────────────────────────────────────────
    url, service_key = get_credentials()
    try:
        supabase = create_client(url, service_key)
        print("✅ Connected to Supabase\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

    # ── Step 1: List Storage Files ───────────────────────────────
    print("─" * 50)
    print("📁 STEP 1: Listing files in storage bucket...")
    print("─" * 50)

    all_files = list_bucket_files(supabase, BUCKET_NAME)

    # Separate existing backup files from pilot data
    pilot_files = [f for f in all_files if not f.startswith("pilot_backup/")]
    existing_backups = [f for f in all_files if f.startswith("pilot_backup/")]

    print(f"\n   Total files in bucket: {len(all_files)}")
    print(f"   Pilot data files: {len(pilot_files)}")
    print(f"   Existing backup files: {len(existing_backups)}")

    if pilot_files:
        # Group by top-level folder
        folders = {}
        for f in pilot_files:
            top = f.split("/")[0] if "/" in f else "(root)"
            folders.setdefault(top, []).append(f)

        print(f"\n   📂 Folder breakdown:")
        for folder, files in sorted(folders.items()):
            print(f"      {folder}/  ({len(files)} files)")
    else:
        print("   ℹ️  No pilot data files found in bucket.")

    # ── Step 2: Export DB Tables ─────────────────────────────────
    print(f"\n{'─' * 50}")
    print("🗃️  STEP 2: Exporting database tables...")
    print("─" * 50)

    table_data = {}
    for table in DB_TABLES:
        rows = export_table(supabase, table)
        table_data[table] = rows
        print(f"   {table}: {len(rows)} records")

    total_records = sum(len(v) for v in table_data.values())
    print(f"\n   Total records across all tables: {total_records}")

    # ── Preview & Confirm ────────────────────────────────────────
    print(f"\n{'=' * 65}")
    print("📋 BACKUP PLAN SUMMARY")
    print("=" * 65)
    print(f"   Storage files to back up: {len(pilot_files)}")
    print(f"   DB records to export:     {total_records}")
    print(f"\n   Actions:")
    print(f"   1. Download {len(pilot_files)} files to: {BACKUP_DIR}/storage/")
    print(f"   2. Copy files to 'pilot_backup/' prefix in Supabase bucket")
    print(f"   3. Save {total_records} DB records as JSON to: {DB_BACKUP_DIR}/")
    print(f"   4. [Optional] Delete originals from Supabase")
    print("=" * 65)

    if len(pilot_files) == 0 and total_records == 0:
        print("\n✅ Nothing to back up or clean. Supabase is already clean!")
        return

    confirm = input("\n   Proceed with backup? (yes/no): ").strip().lower()
    if confirm not in ("yes", "y"):
        print("   ⛔ Aborted.")
        return

    # ── Step 3: Download Files Locally ───────────────────────────
    print(f"\n{'─' * 50}")
    print("⬇️  STEP 3: Downloading storage files locally...")
    print("─" * 50)

    storage_backup_dir = BACKUP_DIR / "storage"
    downloaded = 0
    failed_downloads = []

    for i, file_path in enumerate(pilot_files, 1):
        local_path = storage_backup_dir / file_path
        success = download_file(supabase, BUCKET_NAME, file_path, local_path)
        if success:
            downloaded += 1
        else:
            failed_downloads.append(file_path)
        # Progress indicator
        if i % 10 == 0 or i == len(pilot_files):
            print(f"   Progress: {i}/{len(pilot_files)} files ({downloaded} OK, {len(failed_downloads)} failed)")

    print(f"\n   ✅ Downloaded: {downloaded}/{len(pilot_files)} files")
    if failed_downloads:
        print(f"   ❌ Failed: {len(failed_downloads)} files")
        for f in failed_downloads[:5]:
            print(f"      - {f}")

    # ── Step 4: Copy to pilot_backup/ prefix in Supabase ────────
    print(f"\n{'─' * 50}")
    print("☁️  STEP 4: Copying files to pilot_backup/ prefix in Supabase...")
    print("─" * 50)

    backed_up = 0
    failed_backups = []

    for i, file_path in enumerate(pilot_files, 1):
        # Read from local download
        local_path = storage_backup_dir / file_path
        if not local_path.exists():
            failed_backups.append(file_path)
            continue

        file_data = local_path.read_bytes()
        dest_path = f"pilot_backup/{TIMESTAMP}/{file_path}"

        success = upload_file(supabase, BUCKET_NAME, file_data, dest_path)
        if success:
            backed_up += 1
        else:
            failed_backups.append(file_path)

        if i % 10 == 0 or i == len(pilot_files):
            print(f"   Progress: {i}/{len(pilot_files)} files ({backed_up} OK, {len(failed_backups)} failed)")

    print(f"\n   ✅ Backed up in Supabase: {backed_up}/{len(pilot_files)} files")
    print(f"   📂 Backup prefix: pilot_backup/{TIMESTAMP}/")

    # ── Step 5: Save DB Exports Locally ──────────────────────────
    print(f"\n{'─' * 50}")
    print("💾 STEP 5: Saving database exports to local JSON...")
    print("─" * 50)

    DB_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    for table, rows in table_data.items():
        if rows:
            export_path = DB_BACKUP_DIR / f"{table}_{TIMESTAMP}.json"
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2, default=str, ensure_ascii=False)
            print(f"   ✅ {table}: {len(rows)} records → {export_path.name}")
        else:
            print(f"   ⏭️  {table}: 0 records (skipped)")

    # Also save a combined summary
    summary = {
        "backup_timestamp": TIMESTAMP,
        "storage_files_count": len(pilot_files),
        "storage_files": pilot_files,
        "table_record_counts": {t: len(r) for t, r in table_data.items()},
    }
    summary_path = BACKUP_DIR / f"backup_summary_{TIMESTAMP}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n   📋 Summary saved: {summary_path.name}")

    # ── Step 6: Delete Originals ─────────────────────────────────
    print(f"\n{'=' * 65}")
    print("🗑️  STEP 6: CLEANUP (DESTRUCTIVE)")
    print("=" * 65)
    print(f"   This will DELETE from Supabase:")
    print(f"   - {len(pilot_files)} original storage files")
    print(f"   - {total_records} database records across {len(DB_TABLES)} tables")
    print(f"\n   ⚠️  Backed-up copies in 'pilot_backup/' prefix will be KEPT.")
    print(f"   ⚠️  Local backup at '{BACKUP_DIR}' will be KEPT.")

    delete_confirm = input("\n   Delete originals from Supabase? (type DELETE to confirm): ").strip()

    if delete_confirm != "DELETE":
        print("\n   ⏭️  Skipped deletion. Originals left in place.")
        print("   ✅ Backup completed successfully! You can delete manually later.\n")
        return

    # Delete storage files
    print(f"\n   🗑️  Deleting {len(pilot_files)} storage files...")
    deleted_count = delete_files(supabase, BUCKET_NAME, pilot_files)
    print(f"   ✅ Deleted {deleted_count} storage files")

    # Delete DB records (order matters due to foreign keys)
    # Delete child tables first, then parent
    delete_order = [
        "ueq_scores",
        "knowledge_test_results",
        "learning_interactions",
        "presence",
        "session_analytics",  # Parent table last (FK references)
    ]

    print(f"\n   🗑️  Deleting database records...")
    for table in delete_order:
        if table_data.get(table):
            success = delete_table_rows(supabase, table)
            status = "✅" if success else "❌"
            print(f"   {status} {table}: {len(table_data[table])} records")
        else:
            print(f"   ⏭️  {table}: 0 records (nothing to delete)")

    print(f"\n{'=' * 65}")
    print("🎉 CLEANUP COMPLETE!")
    print("=" * 65)
    print(f"   ✅ Local backup:    {BACKUP_DIR}")
    print(f"   ✅ Supabase backup: pilot_backup/{TIMESTAMP}/")
    print(f"   ✅ Supabase cleaned and ready for the actual experiment!")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
