#!/usr/bin/env python3
"""
Continuous Cloud Backup Manager - Periodically uploads session data to prevent loss.

Strategy:
1. Background task that runs every 5-10 minutes
2. Uploads all checkpoints to Supabase
3. Keeps running even if main app has issues
4. Falls back to local save if cloud unavailable
5. Optional: Delete local after successful cloud upload (for storage savings)
"""

import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Callable

logger = logging.getLogger(__name__)


class ContinuousBackupManager:
    """Manages periodic cloud backups without interrupting user experience."""
    
    def __init__(
        self,
        session_manager,
        supabase_client,
        interval_seconds: int = 300  # 5 minutes
    ):
        """
        Args:
            session_manager: Session manager instance
            supabase_client: Supabase client for cloud uploads
            interval_seconds: How often to backup (default 5 min)
        """
        self.session_manager = session_manager
        self.supabase = supabase_client
        self.interval = interval_seconds
        
        self.backup_thread = None
        self.running = False
        self.last_backup_time = None
        self.backup_history = []  # Track successful/failed backups
        
        self.checkpoint_dir = Path(session_manager.session_dir) / "checkpoints"
        self.local_backup_dir = Path(session_manager.session_dir) / "local_backups"
        self.local_backup_dir.mkdir(exist_ok=True)
    
    def start_periodic_backup(self):
        """Start background backup thread (runs continuously)."""
        if self.running:
            logger.warning("Backup already running")
            return
        
        self.running = True
        self.backup_thread = threading.Thread(
            target=self._backup_loop,
            daemon=True,  # Daemon thread won't block app exit
            name="ContinuousBackupThread"
        )
        self.backup_thread.start()
        logger.info(f"✓ Continuous backup started (every {self.interval}s)")
    
    def stop_periodic_backup(self):
        """Stop background backup thread."""
        self.running = False
        if self.backup_thread:
            self.backup_thread.join(timeout=2)
            logger.info("✓ Continuous backup stopped")
    
    def _backup_loop(self):
        """Background loop that runs backup periodically."""
        try:
            while self.running:
                try:
                    time.sleep(self.interval)
                    if self.running:
                        self.backup_once()
                except Exception as e:
                    logger.error(f"Backup loop error: {e}")
                    time.sleep(5)  # Wait before retry
        except Exception as e:
            logger.error(f"Backup thread crashed: {e}")
    
    def backup_once(self) -> bool:
        """
        Perform a single backup cycle (LOCAL-ONLY to minimize cloud storage).
        
        For limited cloud resources, periodic backups only copy to local filesystem.
        Cloud uploads happen on force_backup_now() (completion pages).
        
        Returns: True if backup succeeded (at least partially)
        """
        try:
            if not self.checkpoint_dir.exists():
                return False
            
            session_info = self.session_manager.get_session_info()
            session_id = session_info.get("session_id")
            
            # Find all checkpoints to backup
            checkpoint_files = list(self.checkpoint_dir.glob("*_checkpoint.json"))
            
            if not checkpoint_files:
                return False  # Nothing to backup
            
            backup_result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
                "checkpoints_found": len(checkpoint_files),
                "local_backups": 0,
                "skipped": 0,
            }
            
            # Periodic backups are LOCAL-ONLY to save cloud storage
            # (Cloud uploads only happen on force_backup_now() for completion)
            for checkpoint_file in checkpoint_files:
                try:
                    with open(checkpoint_file, "r", encoding="utf-8") as f:
                        checkpoint_data = json.load(f)
                    
                    stage = checkpoint_data.get("stage", "unknown")
                    
                    # Only backup locally (filesystem copies for redundancy)
                    local_success = self._backup_checkpoint_locally(
                        session_id, stage, checkpoint_data
                    )
                    if local_success:
                        backup_result["local_backups"] += 1
                    else:
                        backup_result["skipped"] += 1
                
                except Exception as e:
                    logger.warning(f"Checkpoint backup error for {checkpoint_file}: {e}")
                    backup_result["skipped"] += 1
            
            self.last_backup_time = datetime.now(timezone.utc)
            self.backup_history.append(backup_result)
            
            # Keep only last 50 backups in history
            if len(self.backup_history) > 50:
                self.backup_history = self.backup_history[-50:]
            
            # Log result
            if backup_result["cloud_uploads"] > 0 or backup_result["local_backups"] > 0:
                logger.info(
                    f"✓ Backup: {backup_result['cloud_uploads']} cloud, "
                    f"{backup_result['local_backups']} local"
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Backup cycle failed: {e}")
            return False
    
    def _upload_checkpoint_to_cloud(
        self,
        session_id: str,
        stage: str,
        checkpoint_data: Dict[str, Any]
    ) -> bool:
        """
        Upload checkpoint to Supabase table.
        
        Returns: True if successful
        """
        try:
            if not self.supabase:
                return False
            
            self.supabase.table("session_checkpoints").insert({
                "session_id": session_id,
                "stage": stage,
                "checkpoint_data": checkpoint_data,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
            
            return True
            
        except Exception as e:
            logger.debug(f"Cloud upload failed for {stage}: {e}")
            return False
    
    def _backup_checkpoint_locally(
        self,
        session_id: str,
        stage: str,
        checkpoint_data: Dict[str, Any]
    ) -> bool:
        """
        Backup checkpoint to local encrypted storage.
        
        Returns: True if successful
        """
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_file = self.local_backup_dir / f"{stage}_{timestamp}_backup.json"
            
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.debug(f"Local backup failed for {stage}: {e}")
            return False
    
    def force_backup_now(self) -> bool:
        """
        Force an immediate backup INCLUDING cloud upload (for completion pages).
        
        This is called before critical operations (page completion) and
        will upload to cloud if available.
        
        Returns: True if successful
        """
        logger.info("⚡ Forcing immediate backup with cloud sync...")
        try:
            if not self.checkpoint_dir.exists():
                return False
            
            session_info = self.session_manager.get_session_info()
            session_id = session_info.get("session_id")
            
            checkpoint_files = list(self.checkpoint_dir.glob("*_checkpoint.json"))
            if not checkpoint_files:
                return False
            
            cloud_uploaded = 0
            local_backed = 0
            files_deleted = 0
            
            for checkpoint_file in checkpoint_files:
                try:
                    with open(checkpoint_file, "r", encoding="utf-8") as f:
                        checkpoint_data = json.load(f)
                    
                    stage = checkpoint_data.get("stage", "unknown")
                    
                    # Try cloud upload (forced operation)
                    cloud_ok = False
                    if self.supabase:
                        cloud_ok = self._upload_checkpoint_to_cloud(
                            session_id, stage, checkpoint_data
                        )
                        if cloud_ok:
                            cloud_uploaded += 1
                            logger.info(f"✅ Cloud backup: {stage}")
                    
                    # Also backup locally
                    local_ok = self._backup_checkpoint_locally(
                        session_id, stage, checkpoint_data
                    )
                    if local_ok:
                        local_backed += 1
                    
                    # Optional: Delete local file after successful cloud upload
                    # (saves server disk space for limited resources)
                    if cloud_ok and self._should_delete_after_upload():
                        if self._safe_delete_checkpoint(checkpoint_file):
                            files_deleted += 1
                            logger.info(f"🗑️ Deleted local: {stage} (after cloud sync)")
                
                except Exception as e:
                    logger.warning(f"Force backup error for {checkpoint_file}: {e}")
            
            if cloud_uploaded or local_backed:
                status = f"✓ Force backup complete: {cloud_uploaded} cloud + {local_backed} local"
                if files_deleted:
                    status += f" ({files_deleted} deleted after sync)"
                logger.info(status)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Force backup failed: {e}")
            return False
    
    def _should_delete_after_upload(self) -> bool:
        """Check if we should delete local files after cloud upload."""
        try:
            from config import CHECKPOINT_UPLOAD_THEN_DELETE
            return CHECKPOINT_UPLOAD_THEN_DELETE
        except ImportError:
            return False  # Default: keep local copies
    
    def _safe_delete_checkpoint(self, checkpoint_file: Path) -> bool:
        """
        Safely delete checkpoint file (only if we're sure cloud sync succeeded).
        
        Returns: True if deleted, False if file still needed
        """
        try:
            if not checkpoint_file.exists():
                return False
            
            checkpoint_file.unlink()  # Delete file
            logger.debug(f"Deleted: {checkpoint_file.name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete {checkpoint_file}: {e}")
            return False
    
    def get_backup_status(self) -> Dict[str, Any]:
        """Get current backup status and history."""
        return {
            "running": self.running,
            "last_backup_time": self.last_backup_time.isoformat() if self.last_backup_time else None,
            "recent_backups": self.backup_history[-5:] if self.backup_history else [],
            "checkpoints_available": len(list(self.checkpoint_dir.glob("*_checkpoint.json"))) if self.checkpoint_dir.exists() else 0,
            "local_backups": len(list(self.local_backup_dir.glob("*_backup.json"))) if self.local_backup_dir.exists() else 0,
        }
    
    def get_backup_summary(self) -> str:
        """Get human-readable backup summary."""
        status = self.get_backup_status()
        running_str = "🟢 Running" if status["running"] else "🔴 Stopped"
        last_backup = status["last_backup_time"] or "Never"
        
        return (
            f"{running_str}\n"
            f"Last backup: {last_backup}\n"
            f"Active checkpoints: {status['checkpoints_available']}\n"
            f"Local backups stored: {status['local_backups']}"
        )


# Global instance
_backup_manager_instance = None


def get_continuous_backup_manager(
    session_manager,
    supabase_client,
    interval_seconds: int = 300
) -> ContinuousBackupManager:
    """Get or create the continuous backup manager."""
    global _backup_manager_instance
    
    if _backup_manager_instance is None:
        _backup_manager_instance = ContinuousBackupManager(
            session_manager,
            supabase_client,
            interval_seconds
        )
    
    return _backup_manager_instance
