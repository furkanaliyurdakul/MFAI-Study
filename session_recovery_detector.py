#!/usr/bin/env python3
"""
Session Recovery Detector - Auto-detects abandoned sessions and offers resumption.

When user logs in:
1. Check for incomplete sessions from same user/language in last N hours
2. If found, offer to resume (with recovered data)
3. If user accepts, restore session state and skip completed pages
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)


class SessionRecoveryDetector:
    """Detects and helps recover from abandoned sessions."""
    
    def __init__(self, session_manager, supabase_client=None, hours_lookback: int = 24):
        """
        Args:
            session_manager: Session manager instance
            supabase_client: Optional Supabase client for cloud recovery
            hours_lookback: How many hours back to search for abandoned sessions (default: 24)
        """
        self.session_manager = session_manager
        self.supabase = supabase_client
        self.hours_lookback = hours_lookback
        self.output_dir = Path(session_manager.output_dir)
    
    def find_incomplete_sessions(
        self, 
        credentials_folder: str,
        language_code: str,
        max_age_hours: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Find incomplete sessions for this user/language.
        
        Args:
            credentials_folder: e.g., 'dutch_cohort', 'german_cohort'
            language_code: e.g., 'nl', 'de'
            max_age_hours: Max age of sessions to recover (default: self.hours_lookback)
        
        Returns: List of incomplete session dicts with metadata
        """
        if max_age_hours is None:
            max_age_hours = self.hours_lookback
        
        incomplete_sessions = []
        
        try:
            # Look in appropriate subfolder
            cohort_dir = self.output_dir / credentials_folder
            if not cohort_dir.exists():
                return []
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            
            # Find all session directories
            for session_dir in cohort_dir.iterdir():
                if not session_dir.is_dir():
                    continue
                
                # Check if session is recently modified and incomplete
                try:
                    last_modified = datetime.fromtimestamp(
                        session_dir.stat().st_mtime,
                        tz=timezone.utc
                    )
                    
                    # Only consider recent sessions
                    if last_modified < cutoff_time:
                        continue
                    
                    # Check if has checkpoints directory
                    checkpoints_dir = session_dir / "checkpoints"
                    if not checkpoints_dir.exists():
                        continue
                    
                    # Load session metadata
                    meta_file = session_dir / "meta" / "session_info.json"
                    if not meta_file.exists():
                        continue
                    
                    with open(meta_file, "r", encoding="utf-8") as f:
                        session_info = json.load(f)
                    
                    # Check language match
                    if session_info.get("language_code") != language_code:
                        continue
                    
                    # Check completion status from checkpoints
                    progress = self._get_checkpoint_progress(checkpoints_dir)
                    
                    # Only suggest incomplete sessions
                    if any(not completed for completed in progress.values()):
                        incomplete_sessions.append({
                            "session_dir": session_dir,
                            "session_id": session_info.get("session_id"),
                            "fake_name": session_info.get("fake_name"),
                            "last_modified": last_modified.isoformat(),
                            "progress": progress,
                            "completion_percentage": sum(progress.values()) / len(progress) * 100,
                        })
                
                except Exception as e:
                    logger.warning(f"Error checking session {session_dir}: {e}")
                    continue
            
            # Sort by most recent first
            incomplete_sessions.sort(
                key=lambda s: datetime.fromisoformat(s["last_modified"]),
                reverse=True
            )
            
            return incomplete_sessions
            
        except Exception as e:
            logger.error(f"Failed to find incomplete sessions: {e}")
            return []
    
    def _get_checkpoint_progress(self, checkpoints_dir: Path) -> Dict[str, bool]:
        """Check which stages have completed checkpoints."""
        stages = ['profile', 'learning', 'knowledge_test', 'ueq']
        progress = {}
        
        for stage in stages:
            checkpoint_file = checkpoints_dir / f"{stage}_checkpoint.json"
            progress[stage] = checkpoint_file.exists()
        
        return progress
    
    def recover_session_data(self, session_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Recover all data from an abandoned session.
        
        Args:
            session_dir: Path to the session directory
        
        Returns: Dict with recovered data or None if recovery failed
        """
        try:
            checkpoints_dir = session_dir / "checkpoints"
            
            recovered_data = {
                "session_dir": str(session_dir),
                "recovered_at": datetime.now(timezone.utc).isoformat(),
                "stages": {}
            }
            
            # Load all available checkpoints
            for checkpoint_file in checkpoints_dir.glob("*_checkpoint.json"):
                try:
                    with open(checkpoint_file, "r", encoding="utf-8") as f:
                        checkpoint = json.load(f)
                        stage = checkpoint.get("stage", "unknown")
                        recovered_data["stages"][stage] = checkpoint.get("data", {})
                        logger.debug(f"✓ Recovered {stage} data")
                except Exception as e:
                    logger.warning(f"Failed to load checkpoint {checkpoint_file}: {e}")
                    continue
            
            return recovered_data if recovered_data["stages"] else None
            
        except Exception as e:
            logger.error(f"Recovery failed for {session_dir}: {e}")
            return None
    
    def get_recovery_suggestion(
        self,
        credentials_folder: str,
        language_code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the top incomplete session to suggest for recovery.
        
        Returns: Session to recover or None if no incomplete sessions found
        """
        incomplete = self.find_incomplete_sessions(credentials_folder, language_code)
        
        if incomplete:
            return incomplete[0]  # Most recent incomplete session
        
        return None
    
    def format_recovery_message(self, session: Dict[str, Any]) -> str:
        """Format a user-friendly recovery message."""
        progress_str = ", ".join(
            f"✓ {stage}" if completed else f"✗ {stage}"
            for stage, completed in session.get("progress", {}).items()
        )
        
        last_modified = datetime.fromisoformat(session["last_modified"])
        time_ago = datetime.now(timezone.utc) - last_modified
        
        # Format time nicely
        if time_ago.total_seconds() < 60:
            time_str = "just now"
        elif time_ago.total_seconds() < 3600:
            mins = int(time_ago.total_seconds() / 60)
            time_str = f"{mins} minute{'s' if mins != 1 else ''} ago"
        elif time_ago.total_seconds() < 86400:
            hours = int(time_ago.total_seconds() / 3600)
            time_str = f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(time_ago.total_seconds() / 86400)
            time_str = f"{days} day{'s' if days != 1 else ''} ago"
        
        return (
            f"🔄 **Session Recovery Available**\n\n"
            f"Found incomplete session from **{time_str}**:\n"
            f"- Progress: {session.get('completion_percentage', 0):.0f}% complete\n"
            f"- Stages: {progress_str}\n\n"
            f"Would you like to resume this session?"
        )
    
    def cloud_recovery_available(self, session_id: str) -> bool:
        """Check if this session has cloud backups available."""
        if not self.supabase:
            return False
        
        try:
            result = self.supabase.table("session_checkpoints").select(
                "session_id"
            ).eq("session_id", session_id).limit(1).execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.warning(f"Cloud recovery check failed: {e}")
            return False
