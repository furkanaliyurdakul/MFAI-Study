#!/usr/bin/env python3
"""
Checkpoint Manager - Saves session progress at each stage to prevent data loss.

Strategy:
1. After each page completion, create a checkpoint file
2. Checkpoints contain session state + all data collected so far
3. Periodically upload checkpoints to cloud
4. If crash occurs, user can resume from last checkpoint
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages stage checkpoints to enable session resumption."""
    
    def __init__(self, session_manager, supabase_client=None):
        """
        Args:
            session_manager: Session manager instance
            supabase_client: Optional Supabase client for cloud backups
        """
        self.session_manager = session_manager
        self.supabase = supabase_client
        
        # Create checkpoints directory
        self.checkpoints_dir = Path(session_manager.session_dir) / "checkpoints"
        self.checkpoints_dir.mkdir(exist_ok=True)
        
        self.current_stage = None
    
    def create_checkpoint(
        self, 
        stage: str, 
        data: Dict[str, Any],
        upload_to_cloud: bool = False
    ) -> Optional[Path]:
        """
        Create a checkpoint for current stage with all collected data.
        
        Args:
            stage: 'profile', 'learning', 'knowledge_test', 'ueq'
            data: Dictionary containing all data collected for this stage
            upload_to_cloud: Whether to immediately attempt cloud upload
        
        Returns: Path to checkpoint file or None if failed
        """
        try:
            session_info = self.session_manager.get_session_info()
            session_id = session_info.get("session_id")
            
            checkpoint = {
                "session_id": session_id,
                "stage": stage,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data,
                "metadata": {
                    "fake_name": session_info.get("fake_name"),
                    "language_code": session_info.get("language_code"),
                    "credentials_folder": session_info.get("credentials_folder", "unknown"),
                }
            }
            
            # Save checkpoint locally
            checkpoint_file = self.checkpoints_dir / f"{stage}_checkpoint.json"
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✓ Checkpoint created: {stage} at {checkpoint_file}")
            
            # Optionally upload to cloud immediately
            if upload_to_cloud and self.supabase:
                self._upload_checkpoint_to_cloud(checkpoint_file, stage, session_id)
            
            self.current_stage = stage
            return checkpoint_file
            
        except Exception as e:
            logger.error(f"Checkpoint creation failed: {e}")
            return None
    
    def _upload_checkpoint_to_cloud(self, checkpoint_file: Path, stage: str, session_id: str):
        """Upload checkpoint to Supabase for cloud backup."""
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                checkpoint_data = json.load(f)
            
            self.supabase.table("session_checkpoints").insert({
                "session_id": session_id,
                "stage": stage,
                "checkpoint_data": checkpoint_data,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
            
            logger.debug(f"✓ Cloud checkpoint for {stage}: {session_id}")
            
        except Exception as e:
            logger.warning(f"Cloud checkpoint failed for {stage}: {e}")
            # Silent fail - local backup is already saved
    
    def get_latest_checkpoint(self, stage: Optional[str] = None) -> Optional[Dict]:
        """
        Retrieve latest checkpoint (optionally for specific stage).
        
        Args:
            stage: Optional specific stage to retrieve ('profile', 'learning', etc)
        
        Returns: Checkpoint dict or None
        """
        try:
            if stage:
                # Get specific stage checkpoint
                checkpoint_file = self.checkpoints_dir / f"{stage}_checkpoint.json"
                if checkpoint_file.exists():
                    with open(checkpoint_file, "r", encoding="utf-8") as f:
                        return json.load(f)
            else:
                # Get most recent checkpoint (any stage)
                checkpoints = list(self.checkpoints_dir.glob("*_checkpoint.json"))
                if checkpoints:
                    # Sort by modification time, get latest
                    latest = max(checkpoints, key=lambda p: p.stat().st_mtime)
                    with open(latest, "r", encoding="utf-8") as f:
                        return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve checkpoint: {e}")
            return None
    
    def get_session_progress(self) -> Dict[str, bool]:
        """
        Check which stages have checkpoints (completed).
        
        Returns: {'profile': True, 'learning': True, 'knowledge_test': False, ...}
        """
        stages = ['profile', 'learning', 'knowledge_test', 'ueq']
        progress = {}
        
        for stage in stages:
            checkpoint_file = self.checkpoints_dir / f"{stage}_checkpoint.json"
            progress[stage] = checkpoint_file.exists()
        
        return progress
    
    def export_all_checkpoints(self) -> Dict[str, Any]:
        """
        Export all checkpoints into a single summary dict.
        Useful for final analytics and recovery.
        """
        export = {
            "session_id": self.session_manager.get_session_info().get("session_id"),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "progress": self.get_session_progress(),
            "checkpoints": {}
        }
        
        try:
            for checkpoint_file in self.checkpoints_dir.glob("*_checkpoint.json"):
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    checkpoint = json.load(f)
                    stage = checkpoint.get("stage", "unknown")
                    export["checkpoints"][stage] = checkpoint
        except Exception as e:
            logger.error(f"Export failed: {e}")
        
        return export
    
    def is_session_complete(self) -> bool:
        """Check if all stages have been completed."""
        progress = self.get_session_progress()
        return all(progress.values())
    
    def get_completion_percentage(self) -> int:
        """Get percentage of session completion based on checkpoints."""
        progress = self.get_session_progress()
        completed = sum(progress.values())
        total = len(progress)
        return int((completed / total) * 100) if total > 0 else 0
