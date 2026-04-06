#!/usr/bin/env python3
"""
Logger Integration Mixin

Add this to your existing loggers to auto-populate analysis tables.
Prevents duplicates using upsert pattern.
"""

from datetime import datetime, timezone
import logging


class AnalysisTableWriter:
    """Mixin to write to analysis tables - add to your existing loggers"""
    
    def __init__(self, supabase_client):
        """Initialize with Supabase client"""
        self.supabase = supabase_client
        self.logger = logging.getLogger(__name__)
    
    def log_interaction(self, session_id: str, interaction_type: str, language_code: str, 
                       user_input: str = None, response_length: int = None, 
                       response_time_ms: int = None, model_used: str = "gemini-2.5-flash"):
        """Log AI interaction to interaction_logs table"""
        try:
            self.supabase.table("interaction_logs").insert({
                "session_id": session_id,
                "interaction_type": interaction_type,
                "language_code": language_code,
                "user_input": user_input[:500] if user_input else None,  # Truncate long inputs
                "ai_response_length": response_length,
                "response_time_ms": response_time_ms,
                "model_used": model_used,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as e:
            self.logger.debug(f"Could not log interaction: {e}")
    
    def log_page_engagement(self, session_id: str, page_name: str, 
                           time_on_page_seconds: int, interactions_count: int = 1,
                           idle_time_seconds: int = 0):
        """Log page engagement metrics"""
        try:
            self.supabase.table("engagement_metrics").insert({
                "session_id": session_id,
                "page_name": page_name,
                "time_on_page_seconds": time_on_page_seconds,
                "interactions_on_page": interactions_count,
                "idle_time_seconds": idle_time_seconds,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as e:
            self.logger.debug(f"Could not log engagement: {e}")
    
    def log_language_analysis(self, session_id: str, language_code: str,
                             native_proficiency: str, english_proficiency: str,
                             clarity_score: int = None, clarification_requests: int = 0):
        """Log language-specific analysis"""
        try:
            self.supabase.table("language_analysis").upsert({
                "session_id": session_id,
                "language_code": language_code,
                "native_language_proficiency": native_proficiency,
                "english_proficiency": english_proficiency,
                "ai_response_clarity_score": clarity_score,
                "request_for_clarification_count": clarification_requests,
            }, on_conflict="session_id").execute()
        except Exception as e:
            self.logger.debug(f"Could not log language analysis: {e}")
    
    def log_test_question(self, session_id: str, question_number: int, 
                         question_text: str, is_correct: bool, topic: str = "cancer_biology",
                         time_spent_seconds: int = None):
        """Log individual knowledge test question"""
        try:
            self.supabase.table("knowledge_test_detailed").insert({
                "session_id": session_id,
                "question_number": question_number,
                "question_text": question_text,
                "is_correct": is_correct,
                "topic": topic,
                "time_spent_seconds": time_spent_seconds,
            }).execute()
        except Exception as e:
            self.logger.debug(f"Could not log test question: {e}")
    
    def log_ueq_score(self, session_id: str, question_number: int, 
                     question_text: str, scale_dimension: str, score: int):
        """Log individual UEQ question response"""
        try:
            self.supabase.table("ueq_detailed_scores").insert({
                "session_id": session_id,
                "question_number": question_number,
                "question_text": question_text,
                "scale_dimension": scale_dimension,
                "score": score,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as e:
            self.logger.debug(f"Could not log UEQ score: {e}")


# ============================================================================
# EXAMPLE USAGE IN EXISTING LOGGERS
# ============================================================================

"""
1. In learning_interaction_logger.py, add to class:
   
   class LearningLogger(AnalysisTableWriter):
       def __init__(self):
           super().__init__(supabase_client)
           # ... rest of init
       
       def log_interaction(self, interaction_type, user_input, system_response, metadata=None):
           # ... existing code ...
           
           # NEW: Also log to analysis table
           session_info = self.session_manager.get_session_info()
           super().log_interaction(
               session_id=session_info["session_id"],
               interaction_type=interaction_type,
               language_code=session_info.get("language_code", "en"),
               user_input=str(user_input)[:500],
               response_time_ms=metadata.get("response_time_ms") if metadata else None,
               model_used="gemini-2.5-flash"
           )

2. In testui_ueqsurvey.py, after calculating scores:
   
   from analytics_table_writer import AnalysisTableWriter
   writer = AnalysisTableWriter(supabase)
   
   for dimension, score in scores.items():
       writer.log_ueq_score(
           session_id=session_info["session_id"],
           question_number=1,
           question_text=dimension,
           scale_dimension=dimension,
           score=score
       )

3. In testui_knowledgetest.py, for each question:
   
   writer.log_test_question(
       session_id=session_info["session_id"],
       question_number=q_num,
       question_text="Question text here",
       is_correct=user_answer == correct_answer,
       topic="cancer_biology"
   )

"""
