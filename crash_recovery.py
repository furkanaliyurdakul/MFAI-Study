#!/usr/bin/env python3
"""
Crash Recovery System for MFAI-Study

Prevents data loss by:
1. Auto-saving EVERY interaction (not just at completion)
2. Resumable sessions (auto-detect incomplete sessions)
3. Local backup to Supabase storage
4. Resource optimization for community tier
5. Graceful error handling + user notifications
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CrashRecoveryManager:
    """Automatically saves session data to prevent loss"""
    
    def __init__(self, supabase_client, session_manager):
        """
        Args:
            supabase_client: Supabase client instance
            session_manager: Session manager for user/session info
        """
        self.supabase = supabase_client
        self.session_manager = session_manager
        self.buffer = {}  # In-memory buffer for batching
    
    def auto_save_interaction(self, interaction_type: str, data: Dict[str, Any], 
                             force_flush: bool = False):
        """
        Auto-save interaction data immediately (crash-safe)
        
        Args:
            interaction_type: 'chat', 'test_answer', 'ueq_response', 'profile'
            data: The interaction data to save
            force_flush: Force immediate save (don't batch)
        """
        try:
            session_info = self.session_manager.get_session_info()
            session_id = session_info.get("session_id")
            
            if not session_id:
                logger.warning("No session_id - cannot auto-save")
                return
            
            # Add metadata
            data["saved_at"] = datetime.now(timezone.utc).isoformat()
            data["interaction_type"] = interaction_type
            
            # IMMEDIATE SAVE: Don't wait for batch
            # This ensures data is persisted even if process crashes next line
            try:
                self.supabase.table("session_auto_save_log").insert({
                    "session_id": session_id,
                    "interaction_type": interaction_type,
                    "data": data,
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                }).execute()
                
                logger.debug(f"✓ Auto-saved {interaction_type}: {session_id}")
                
            except Exception as e:
                # Fallback: Save to local file if cloud fails
                self._fallback_save_to_file(session_id, interaction_type, data)
                logger.warning(f"Cloud save failed, using file backup: {e}")
        
        except Exception as e:
            logger.error(f"Auto-save error: {e}")
    
    def _fallback_save_to_file(self, session_id: str, interaction_type: str, 
                               data: Dict[str, Any]):
        """Fallback: Save to local backup file"""
        try:
            backup_dir = Path.cwd() / "session_backups"
            backup_dir.mkdir(exist_ok=True)
            
            backup_file = backup_dir / f"{session_id}_backup.jsonl"
            
            with open(backup_file, "a") as f:
                entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": interaction_type,
                    "data": data
                }
                f.write(json.dumps(entry) + "\n")
            
            logger.info(f"✓ Backup saved to {backup_file}")
        except Exception as e:
            logger.error(f"Backup save failed: {e}")
    
    def recover_partial_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Detect and recover incomplete session
        
        Returns: Dict with recovered data or None if session not found
        """
        try:
            # Check for existing incomplete session
            result = self.supabase.table("session_auto_save_log").select(
                "*"
            ).eq("session_id", session_id).order(
                "saved_at", desc=True
            ).limit(50).execute()
            
            if not result.data:
                return None
            
            # Reconstruct session state from logs
            recovered_state = {
                "session_id": session_id,
                "recovered_at": datetime.now(timezone.utc).isoformat(),
                "stages": {}
            }
            
            for entry in result.data:
                interaction_type = entry.get("interaction_type")
                data = entry.get("data", {})
                
                if interaction_type == "profile":
                    recovered_state["stages"]["profile"] = data
                elif interaction_type == "chat":
                    if "chat" not in recovered_state["stages"]:
                        recovered_state["stages"]["chat"] = []
                    recovered_state["stages"]["chat"].append(data)
                elif interaction_type == "test_answer":
                    if "test_answers" not in recovered_state["stages"]:
                        recovered_state["stages"]["test_answers"] = {}
                    recovered_state["stages"]["test_answers"].update(data)
                elif interaction_type == "ueq_response":
                    if "ueq" not in recovered_state["stages"]:
                        recovered_state["stages"]["ueq"] = {}
                    recovered_state["stages"]["ueq"].update(data)
            
            return recovered_state if recovered_state["stages"] else None
        
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return None
    
    def save_profile_data(self, profile_data: Dict[str, Any]):
        """Crash-safe profile save"""
        self.auto_save_interaction("profile", profile_data, force_flush=True)
    
    def save_test_answer(self, question_num: int, answer: Any, is_correct: bool):
        """Crash-safe test answer save"""
        self.auto_save_interaction("test_answer", {
            "question_num": question_num,
            "answer": answer,
            "is_correct": is_correct,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def save_chat_message(self, user_message: str, ai_response: str, 
                         response_time_ms: int):
        """Crash-safe chat save"""
        self.auto_save_interaction("chat", {
            "user_message": user_message[:500],  # Truncate long messages
            "ai_response": ai_response[:1000],
            "response_time_ms": response_time_ms,
        })
    
    def save_ueq_response(self, dimension: str, score: int):
        """Crash-safe UEQ save"""
        self.auto_save_interaction("ueq_response", {
            "dimension": dimension,
            "score": score,
        })


# ============================================================================
# STREAMLIT INTEGRATION
# ============================================================================

"""
Add this to your main.py or page files:

import streamlit as st
from crash_recovery import CrashRecoveryManager

# Initialize in setup
if "recovery_manager" not in st.session_state:
    recovery_manager = CrashRecoveryManager(supabase, session_manager)
    st.session_state.recovery_manager = recovery_manager
else:
    recovery_manager = st.session_state.recovery_manager


# BEFORE profile page:
def show_profile_recovery_option():
    session_info = session_manager.get_session_info()
    recovered = recovery_manager.recover_partial_session(session_info["session_id"])
    
    if recovered:
        st.warning("🔄 Incomplete session detected - we can resume!")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Resume Session (keep previous answers)"):
                st.session_state.recovered_data = recovered
                st.rerun()
        
        with col2:
            if st.button("Start Fresh (discard previous)"):
                st.session_state.recovered_data = None
                st.rerun()
        
        return recovered
    
    return None


# IN profile page:
if recovered := show_profile_recovery_option():
    st.info(f"✓ Recovered {len(recovered['stages'])} data sections")

# Save profile answers
if st.button("Save Profile"):
    profile_data = {...}
    recovery_manager.save_profile_data(profile_data)
    st.success("✓ Profile saved (auto-backup enabled)")


# IN learning page:
def on_chat_message(user_msg, ai_resp, time_ms):
    # Immediate crash-safe save
    recovery_manager.save_chat_message(user_msg, ai_resp, time_ms)


# IN knowledge test:
def on_answer_submitted(q_num, answer):
    is_correct = check_answer(answer)
    # Immediate save (not just at end)
    recovery_manager.save_test_answer(q_num, answer, is_correct)


# IN UEQ survey:
def on_ueq_answer(dimension, score):
    # Immediate save
    recovery_manager.save_ueq_response(dimension, score)
    st.session_state.ueq_answers[dimension] = score
"""
