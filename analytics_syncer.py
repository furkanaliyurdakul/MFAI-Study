"""
Analytics data sync module.

Automatically syncs session data to Supabase analytics tables
for real-time monitoring via dashboard or mobile app.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import streamlit as st

logger = logging.getLogger(__name__)


class AnalyticsSyncer:
    """Syncs session data to Supabase analytics tables."""
    
    def __init__(self, supabase_client):
        """Initialize analytics syncer.
        
        Args:
            supabase_client: Supabase client instance (with service_key for write access)
        """
        self.supabase = supabase_client
        self._upload_status_table_missing_logged = False
    
    def create_session_record(self, session_id: str, user_id: str, language_code: str) -> bool:
        """Create initial session analytics record.
        
        Called when session starts (after login).
        
        Args:
            session_id: Unique session identifier
            user_id: User credential
            language_code: Assigned language
            
        Returns:
            True if successful
        """
        try:
            self.supabase.table("session_analytics").insert({
                "session_id": session_id,
                "user_id": user_id,
                "language_code": language_code,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "status": "active"
            }).execute()
            
            logger.info(f"Created analytics record for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create analytics record: {e}")
            return False
    
    def update_consent(self, session_id: str) -> bool:
        """Mark consent as given.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful
        """
        try:
            self.supabase.table("session_analytics").update({
                "consent_given": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("session_id", session_id).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update consent: {e}")
            return False
    
    def sync_profile(self, session_id: str, profile_data: Dict[str, Any], file_path: Path) -> bool:
        """Sync profile survey data to analytics.
        
        Args:
            session_id: Session identifier
            profile_data: Profile survey form data
            file_path: Path where profile JSON was saved
            
        Returns:
            True if successful
        """
        try:
            self.supabase.table("session_analytics").update({
                "profile_completed": True,
                "age": profile_data.get("age"),
                "gender": profile_data.get("gender"),
                "education_level": profile_data.get("education_level"),
                "field_of_study": profile_data.get("field_of_study"),
                "english_proficiency": profile_data.get("english_proficiency"),
                "native_proficiency": profile_data.get("native_proficiency"),
                "genai_familiarity": profile_data.get("genai_familiarity"),
                "genai_usage": profile_data.get("genai_usage"),
                "profile_json_path": str(file_path),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("session_id", session_id).execute()
            
            logger.info(f"Synced profile data for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync profile: {e}")
            return False
    
    def sync_knowledge_test(self, session_id: str, results: Dict[str, Any], file_path: Path) -> bool:
        """Sync knowledge test results to analytics.
        
        Args:
            session_id: Session identifier
            results: Knowledge test results dict
            file_path: Path where test results JSON was saved
            
        Returns:
            True if successful
        """
        try:
            # Update main session analytics
            self.supabase.table("session_analytics").update({
                "knowledge_test_completed": True,
                "knowledge_test_score": results.get("percentage"),
                "knowledge_test_grade": results.get("grade"),
                "knowledge_test_json_path": str(file_path),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("session_id", session_id).execute()
            
            # Insert detailed results
            answers = results.get("answers", {})
            # Extract answer data from {"user": answer, "correct": bool} structure
            # Current test has 5 single-choice questions (q1-q5)
            self.supabase.table("knowledge_test_results").insert({
                "session_id": session_id,
                "q1_correct": answers.get("q1", {}).get("correct", False),
                "q1_answer": answers.get("q1", {}).get("user"),
                "q2_correct": answers.get("q2", {}).get("correct", False),
                "q2_answer": answers.get("q2", {}).get("user"),
                "q3_correct": answers.get("q3", {}).get("correct", False),
                "q3_answer": answers.get("q3", {}).get("user"),
                "q4_correct": answers.get("q4", {}).get("correct", False),
                "q4_answer": answers.get("q4", {}).get("user"),
                "q5_score": 1.0 if answers.get("q5", {}).get("correct", False) else 0.0,
                "q5_answer_a": False,  # Q5 is single-choice in current version
                "q5_answer_b": False,
                "q5_answer_c": False,
                "q5_answer_d": False,
                "q6_correct": None,  # q6-q8 not implemented in current test
                "q6_answer": None,
                "q7_correct": None,
                "q7_answer": None,
                "q8_correct": None,
                "q8_answer": None,
                "total_score": results.get("score_total"),
                "max_score": results.get("max_score", 5.0),
                "percentage": (results.get("score_total", 0) / results.get("max_score", 5.0)) * 100 if results.get("max_score", 5.0) > 0 else 0,
                "grade": "pass" if (results.get("score_total", 0) / results.get("max_score", 5.0)) >= 0.6 else "fail",
                "submitted_at": datetime.now(timezone.utc).isoformat()
            }).execute()
            
            logger.info(f"Synced knowledge test for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync knowledge test: {e}")
            return False
    
    def sync_ueq(self, session_id: str, ueq_data: Dict[str, Any], file_path: Path) -> bool:
        """Sync UEQ results to analytics.
        
        Args:
            session_id: Session identifier
            ueq_data: UEQ results dict (with means and grades)
            file_path: Path where UEQ JSON was saved
            
        Returns:
            True if successful
        """
        try:
            means = ueq_data.get("means", {})
            grades = ueq_data.get("grades", {})
            
            # Update main session analytics
            self.supabase.table("session_analytics").update({
                "ueq_completed": True,
                "ueq_json_path": str(file_path),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("session_id", session_id).execute()
            
            # Insert detailed UEQ scores
            self.supabase.table("ueq_scores").insert({
                "session_id": session_id,
                "attractiveness": means.get("Attractiveness"),
                "perspicuity": means.get("Perspicuity"),
                "efficiency": means.get("Efficiency"),
                "dependability": means.get("Dependability"),
                "stimulation": means.get("Stimulation"),
                "novelty": means.get("Novelty"),
                "attractiveness_grade": grades.get("Attractiveness"),
                "perspicuity_grade": grades.get("Perspicuity"),
                "efficiency_grade": grades.get("Efficiency"),
                "dependability_grade": grades.get("Dependability"),
                "stimulation_grade": grades.get("Stimulation"),
                "novelty_grade": grades.get("Novelty"),
                "overall_grade": grades.get("Attractiveness"),  # Attractiveness is overall satisfaction
                "submitted_at": datetime.now(timezone.utc).isoformat()
            }).execute()
            
            logger.info(f"Synced UEQ for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync UEQ: {e}")
            return False
    
    def sync_learning_log(self, session_id: str, log_path: Path) -> bool:
        """Sync learning interaction summary to analytics.
        
        Reads the learning log JSON and extracts metrics.
        
        Args:
            session_id: Session identifier
            log_path: Path to learning log JSON file
            
        Returns:
            True if successful
        """
        try:
            # Read log file
            if not log_path.exists():
                logger.warning(f"Learning log not found: {log_path}")
                return False
            
            with open(log_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            # Extract metrics
            interactions = log_data.get("interactions", [])
            slide_explanations = sum(1 for i in interactions if i.get("interaction_type") == "slide_explanation")
            manual_chats = sum(1 for i in interactions if i.get("interaction_type") == "manual_chat")
            total_messages = len(interactions)
            
            # Calculate average message length
            user_messages = [i.get("user_input", "") for i in interactions if isinstance(i.get("user_input"), str)]
            avg_length = sum(len(msg) for msg in user_messages) / len(user_messages) if user_messages else 0
            
            # Get timestamps
            timestamps = [datetime.fromisoformat(i["timestamp"]) for i in interactions if "timestamp" in i]
            first_ts = min(timestamps).isoformat() if timestamps else None
            last_ts = max(timestamps).isoformat() if timestamps else None
            duration = (max(timestamps) - min(timestamps)).total_seconds() if len(timestamps) > 1 else 0
            
            # Update session analytics
            self.supabase.table("session_analytics").update({
                "learning_completed": True,
                "total_slides_viewed": len(set(i.get("metadata", {}).get("slide_number") for i in interactions if i.get("metadata", {}).get("slide_number"))),
                "total_chat_messages": manual_chats,
                "total_slide_explanations": slide_explanations,
                "learning_log_json_path": str(log_path),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("session_id", session_id).execute()
            
            # Insert interaction summary
            self.supabase.table("learning_interactions").insert({
                "session_id": session_id,
                "slides_viewed": len(set(i.get("metadata", {}).get("slide_number") for i in interactions if i.get("metadata", {}).get("slide_number"))),
                "slides_with_explanation": slide_explanations,
                "manual_chat_messages": manual_chats,
                "total_user_messages": total_messages,
                "avg_message_length": int(avg_length),
                "first_interaction_at": first_ts,
                "last_interaction_at": last_ts,
                "total_duration_seconds": int(duration),
                "full_log_path": str(log_path)
            }).execute()
            
            logger.info(f"Synced learning log for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync learning log: {e}")
            return False
    
    def sync_page_durations(self, session_id: str, durations_path: Path) -> bool:
        """Sync page duration data to analytics.
        
        Args:
            session_id: Session identifier
            durations_path: Path to page_durations.json
            
        Returns:
            True if successful
        """
        try:
            if not durations_path.exists():
                logger.warning(f"Page durations not found: {durations_path}")
                return False
            
            with open(durations_path, 'r', encoding='utf-8') as f:
                durations = json.load(f)
            
            # Update session analytics with timing data
            self.supabase.table("session_analytics").update({
                "time_on_profile": durations.get("profile_survey", 0),
                "time_on_learning": durations.get("learning", 0),
                "time_on_knowledge_test": durations.get("knowledge_test", 0),
                "time_on_ueq": durations.get("ueq_survey", 0),
                "total_session_time": sum(durations.values()),
                "page_durations_json_path": str(durations_path),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("session_id", session_id).execute()
            
            logger.info(f"Synced page durations for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync page durations: {e}")
            return False
    
    def mark_completed(self, session_id: str) -> bool:
        """Mark session as completed in analytics.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful
        """
        try:
            self.supabase.table("session_analytics").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("session_id", session_id).execute()
            
            logger.info(f"Marked session {session_id} as completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark session completed: {e}")
            return False

    def record_upload_status(
        self,
        session_id: str,
        status: str,
        phase: str,
        detail: str | None = None,
        uploaded_files: int | None = None,
        failed_files: int | None = None,
    ) -> bool:
        """Best-effort durability status event sink.

        Writes to optional table `storage_upload_status`. If the table does not
        exist yet, this method returns False but does not raise.
        """
        if self._upload_status_table_missing_logged:
            return False

        try:
            payload = {
                "session_id": session_id,
                "status": status,
                "phase": phase,
                "detail": detail,
                "uploaded_files": uploaded_files,
                "failed_files": failed_files,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
            self.supabase.table("storage_upload_status").insert(payload).execute()
            return True
        except Exception as e:
            error_text = str(e)
            missing_table = "PGRST205" in error_text and "storage_upload_status" in error_text
            if missing_table:
                if not self._upload_status_table_missing_logged:
                    logger.warning(
                        "Upload status events disabled: optional table 'storage_upload_status' is missing. "
                        "Apply output/STORAGE_UPLOAD_STATUS.sql to enable this telemetry."
                    )
                    self._upload_status_table_missing_logged = True
                return False
            logger.warning(f"Upload status event not persisted for {session_id}: {e}")
            return False


# Global instance
_analytics_syncer = None

def get_analytics_syncer() -> Optional[AnalyticsSyncer]:
    """Get or create analytics syncer instance.
    
    Returns:
        AnalyticsSyncer instance or None if Supabase not available
    """
    global _analytics_syncer
    
    if _analytics_syncer is None:
        try:
            from supabase import create_client
            
            # Use service_key for write access
            supabase = create_client(
                st.secrets["supabase"]["url"],
                st.secrets["supabase"]["service_key"]
            )
            
            _analytics_syncer = AnalyticsSyncer(supabase)
            logger.info("Analytics syncer initialized")
            
        except Exception as e:
            logger.warning(f"Could not initialize analytics syncer: {e}")
            return None
    
    return _analytics_syncer
