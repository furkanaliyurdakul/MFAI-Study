#!/usr/bin/env python3
"""
Emergency Recovery Mode - Activate if production is experiencing data loss.

This module provides one-click recovery for:
1. Users with incomplete sessions
2. Missed cloud uploads
3. Corrupted session data
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class EmergencyRecovery:
    """Emergency recovery operations for production issues."""
    
    def __init__(self, output_dir: Path, supabase_client=None):
        """
        Args:
            output_dir: Path to output directory with all sessions
            supabase_client: Optional Supabase client for cloud recovery
        """
        self.output_dir = output_dir
        self.supabase = supabase_client
        self.recovery_report = []
    
    def scan_all_incomplete_sessions(self) -> List[Dict]:
        """
        Scan entire output directory for incomplete sessions.
        
        Returns: List of incomplete sessions with metadata
        """
        incomplete = []
        
        try:
            for cohort_dir in self.output_dir.iterdir():
                if not cohort_dir.is_dir():
                    continue
                
                for session_dir in cohort_dir.iterdir():
                    if not session_dir.is_dir():
                        continue
                    
                    try:
                        # Check for checkpoints
                        checkpoints_dir = session_dir / "checkpoints"
                        if not checkpoints_dir.exists():
                            continue
                        
                        # Load session info
                        meta_file = session_dir / "meta" / "session_info.json"
                        if not meta_file.exists():
                            continue
                        
                        with open(meta_file, "r", encoding="utf-8") as f:
                            session_info = json.load(f)
                        
                        # Check completion
                        progress = self._get_progress(checkpoints_dir)
                        if all(progress.values()):
                            continue  # Skip completed sessions
                        
                        incomplete.append({
                            "session_dir": str(session_dir),
                            "session_id": session_info.get("session_id"),
                            "fake_name": session_info.get("fake_name"),
                            "cohort": cohort_dir.name,
                            "progress": progress,
                            "completion_percentage": sum(progress.values()) / len(progress) * 100,
                        })
                    
                    except Exception as e:
                        logger.warning(f"Error scanning {session_dir}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Scan failed: {e}")
        
        return incomplete
    
    def recover_lost_data(
        self,
        session_id: str,
        session_dir: Path,
        attempt_cloud_recovery: bool = True
    ) -> Tuple[bool, str]:
        """
        Attempt to recover lost data for a session.
        
        Args:
            session_id: Session ID to recover
            session_dir: Path to session directory
            attempt_cloud_recovery: Try to recover from cloud backups
        
        Returns: (success, message)
        """
        try:
            recovery_log = {
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operations": []
            }
            
            # 1. Recover from local checkpoints
            checkpoints_dir = session_dir / "checkpoints"
            if checkpoints_dir.exists():
                checkpoint_files = list(checkpoints_dir.glob("*_checkpoint.json"))
                recovery_log["operations"].append({
                    "operation": "local_checkpoint_recovery",
                    "checkpoints_found": len(checkpoint_files),
                })
            
            # 2. Recover from local backups
            backup_dir = session_dir / "local_backups"
            if backup_dir.exists():
                backup_files = list(backup_dir.glob("*_backup.json"))
                recovery_log["operations"].append({
                    "operation": "local_backup_recovery",
                    "backups_found": len(backup_files),
                })
            
            # 3. Attempt cloud recovery if enabled
            if attempt_cloud_recovery and self.supabase:
                try:
                    cloud_result = self.supabase.table("session_checkpoints").select(
                        "stage, checkpoint_data"
                    ).eq("session_id", session_id).execute()
                    
                    if cloud_result.data:
                        # Restore cloud data to local
                        for record in cloud_result.data:
                            stage = record.get("stage")
                            checkpoint_data = record.get("checkpoint_data")
                            
                            checkpoint_file = checkpoints_dir / f"{stage}_checkpoint.json"
                            if not checkpoint_file.exists():
                                with open(checkpoint_file, "w", encoding="utf-8") as f:
                                    json.dump(checkpoint_data, f, indent=2)
                        
                        recovery_log["operations"].append({
                            "operation": "cloud_recovery",
                            "stages_recovered": len(cloud_result.data),
                        })
                
                except Exception as e:
                    logger.warning(f"Cloud recovery failed: {e}")
            
            # Log recovery
            self.recovery_report.append(recovery_log)
            
            return True, f"Recovered session {session_id}"
            
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return False, f"Recovery failed: {str(e)}"
    
    def bulk_recover_incomplete_sessions(self) -> Dict[str, any]:
        """
        Recover all incomplete sessions in bulk.
        
        Returns: Summary stats {'recovered': int, 'failed': int}
        """
        incomplete = self.scan_all_incomplete_sessions()
        
        results = {
            "total_found": len(incomplete),
            "recovered": 0,
            "failed": 0,
            "recoveries": []
        }
        
        for session in incomplete:
            success, message = self.recover_lost_data(
                session["session_id"],
                Path(session["session_dir"])
            )
            
            if success:
                results["recovered"] += 1
            else:
                results["failed"] += 1
            
            results["recoveries"].append({
                "session_id": session["session_id"],
                "success": success,
                "message": message
            })
        
        return results
    
    def upload_all_recovered_data(self) -> Dict[str, any]:
        """
        Upload all recovered/local data to Supabase (in case earlier upload failed).
        
        Returns: Upload statistics
        """
        if not self.supabase:
            return {"status": "no_cloud_connection"}
        
        stats = {
            "files_uploaded": 0,
            "files_failed": 0,
            "sessions_processed": 0,
        }
        
        try:
            # Find all backed up session files
            for session_dir in self.output_dir.rglob("*"):
                if not session_dir.is_dir():
                    continue
                
                checkpoints = list(session_dir.glob("checkpoints/*_checkpoint.json"))
                local_backups = list(session_dir.glob("local_backups/*_backup.json"))
                
                total_files = len(checkpoints) + len(local_backups)
                if total_files == 0:
                    continue
                
                stats["sessions_processed"] += 1
                
                # Upload all
                for file_path in checkpoints + local_backups:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        
                        # Upload to Supabase
                        self.supabase.table("recovered_data_backup").insert({
                            "filename": file_path.name,
                            "data": data,
                            "uploaded_at": datetime.now(timezone.utc).isoformat(),
                        }).execute()
                        
                        stats["files_uploaded"] += 1
                    
                    except Exception as e:
                        logger.warning(f"Upload failed for {file_path.name}: {e}")
                        stats["files_failed"] += 1
        
        except Exception as e:
            logger.error(f"Bulk upload failed: {e}")
        
        return stats
    
    def generate_recovery_report(self, output_path: Path) -> bool:
        """
        Generate final recovery report.
        
        Args:
            output_path: Where to save report
        
        Returns: True if successful
        """
        try:
            report_lines = [
                "=== DATA LOSS PREVENTION RECOVERY REPORT ===",
                f"Generated: {datetime.now().isoformat()}",
                "",
                f"Recovery Events: {len(self.recovery_report)}",
                ""
            ]
            
            for event in self.recovery_report:
                report_lines.append(f"Session: {event['session_id']}")
                for op in event.get("operations", []):
                    report_lines.append(f"  - {op}")
                report_lines.append("")
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))
            
            logger.info(f"✓ Report saved to {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return False
    
    def _get_progress(self, checkpoints_dir: Path) -> Dict[str, bool]:
        """Get checkpoint progress for a session."""
        stages = ['profile', 'learning', 'knowledge_test', 'ueq']
        return {stage: (checkpoints_dir / f"{stage}_checkpoint.json").exists() for stage in stages}


# CLI Mode - run from command line for emergency recovery
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Emergency recovery tool")
    parser.add_argument("--output-dir", required=True, help="Path to output directory")
    parser.add_argument("--scan-only", action="store_true", help="Only scan, don't recover")
    parser.add_argument("--report", help="Save report to this file")
    
    args = parser.parse_args()
    
    recovery = EmergencyRecovery(Path(args.output_dir))
    
    if args.scan_only:
        incomplete = recovery.scan_all_incomplete_sessions()
        print(f"Found {len(incomplete)} incomplete sessions:")
        for session in incomplete:
            print(f"  - {session['session_id']}: {session['completion_percentage']:.0f}%")
    else:
        print("Starting bulk recovery...")
        results = recovery.bulk_recover_incomplete_sessions()
        print(f"Recovered: {results['recovered']}, Failed: {results['failed']}")
        
        if args.report:
            recovery.generate_recovery_report(Path(args.report))
            print(f"Report saved to {args.report}")
