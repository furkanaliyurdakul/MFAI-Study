# SPDX-License-Identifier: MIT
"""Session presence tracking for concurrent user management.

Uses JavaScript heartbeat to track active sessions in real-time via Supabase.
Prevents too many concurrent interviews from running simultaneously.
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PresenceTracker:
    """Tracks active user sessions via JavaScript heartbeat."""
    
    def __init__(self, supabase_client, max_concurrent: int = 2):
        """Initialize presence tracker.
        
        Args:
            supabase_client: Supabase client instance
            max_concurrent: Maximum number of concurrent active interviews
        """
        self.supabase = supabase_client
        self.max_concurrent = max_concurrent
        self.online_window_seconds = 60  # Consider user offline after 60s without heartbeat
        
    def inject_heartbeat(self, session_id: str, user_id: str, language_code: str, current_page: str):
        """Inject JavaScript heartbeat component that pings Supabase every 20 seconds.
        
        This runs in the browser and continues even without Streamlit reruns.
        Automatically stops when tab is closed or user navigates away.
        """
        # Get Supabase URL from secrets
        try:
            supabase_url = st.secrets["supabase"]["url"]
            supabase_anon_key = st.secrets["supabase"]["anon_key"]
        except (KeyError, FileNotFoundError):
            logger.warning("Supabase credentials not found - heartbeat disabled")
            return
        
        # JavaScript heartbeat code
        heartbeat_js = f"""
        <script>
        (function() {{
            const sessionId = "{session_id}";
            const userId = "{user_id}";
            const languageCode = "{language_code}";
            const supabaseUrl = "{supabase_url}";
            const supabaseKey = "{supabase_anon_key}";
            const currentPage = "{current_page}";
            const isInInterview = ["learning", "study", "interview"].includes(currentPage);
            
            // Send heartbeat to Supabase
            async function beat() {{
                const now = new Date().toISOString();
                
                try {{
                    const payload = {{
                        session_id: sessionId,
                        user_id: userId,
                        language_code: languageCode,
                        current_page: currentPage,
                        last_seen: now,
                        is_in_interview: isInInterview,
                        updated_at: now
                    }};
                    
                    const response = await fetch(`${{supabaseUrl}}/rest/v1/presence`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                            'apikey': supabaseKey,
                            'Authorization': `Bearer ${{supabaseKey}}`,
                            'Prefer': 'resolution=merge-duplicates'
                        }},
                        body: JSON.stringify(payload)
                    }});
                    
                    if (!response.ok) {{
                        console.log('Heartbeat response:', response.status);
                    }}
                }} catch (e) {{
                    console.warn('heartbeat failed', e);
                }}
            }}
            
            // Send initial heartbeat
            beat();
            
            // Set up interval for periodic heartbeats (every 20 seconds)
            const heartbeatInterval = setInterval(beat, 20000);
            
            // Cleanup on page unload
            window.addEventListener('beforeunload', function() {{
                clearInterval(heartbeatInterval);
            }});
        }})();
        </script>
        """
        
        # Render with zero height (invisible)
        components.html(heartbeat_js, height=0)
    
    def mark_session_started(self, session_id: str, user_id: str, language_code: str) -> bool:
        """Mark session as started in presence table.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.now(timezone.utc).isoformat()
            
            self.supabase.table("presence").upsert({
                "session_id": session_id,
                "user_id": user_id,
                "language_code": language_code,
                "current_page": "login",
                "last_seen": now,
                "started_at": now,
                "is_in_interview": False,
                "status": "active"
            }, on_conflict="session_id").execute()
            
            logger.info(f"Session {session_id} marked as started")
            return True
            
        except Exception as e:
            logger.error(f"Error marking session started: {e}")
            return False
    
    def mark_session_completed(self, session_id: str) -> bool:
        """Mark session as completed in presence table.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.supabase.table("presence").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat()
            }).eq("session_id", session_id).execute()
            
            logger.info(f"Session {session_id} marked as completed")
            return True
            
        except Exception as e:
            logger.error(f"Error marking session completed: {e}")
            return False
    
    def count_active_sessions(self) -> int:
        """Count currently active sessions (heartbeat within last 60 seconds).
        
        Returns:
            Number of active sessions
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.online_window_seconds)
            
            result = self.supabase.table("presence") \
                .select("session_id") \
                .eq("status", "active") \
                .gte("last_seen", cutoff.isoformat()) \
                .execute()
            
            count = len(result.data) if result.data else 0
            logger.info(f"Active sessions count: {count}")
            return count
            
        except Exception as e:
            logger.error(f"Error counting active sessions: {e}")
            return 0
    
    def count_active_interviews(self) -> int:
        """Count users currently in the interview/learning phase.
        
        Returns:
            Number of users actively doing the learning interview
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.online_window_seconds)
            
            result = self.supabase.table("presence") \
                .select("session_id") \
                .eq("status", "active") \
                .eq("is_in_interview", True) \
                .gte("last_seen", cutoff.isoformat()) \
                .execute()
            
            count = len(result.data) if result.data else 0
            logger.info(f"Active interviews count: {count}")
            return count
            
        except Exception as e:
            logger.error(f"Error counting active interviews: {e}")
            return 0
    
    def can_start_interview(self) -> tuple[bool, str]:
        """Check if user can start the interview based on concurrent limit.
        
        Returns:
            (can_start: bool, message: str)
        """
        try:
            # Count ALL active sessions (not just those in interview)
            # This prevents race conditions at login
            active_count = self.count_active_sessions()
            
            if active_count >= self.max_concurrent:
                return False, f"⏳ Platform is at capacity ({active_count}/{self.max_concurrent} active sessions). Please try again in a few minutes."
            
            return True, f"✅ Ready to start ({active_count}/{self.max_concurrent} currently active)"
            
        except Exception as e:
            logger.error(f"Error checking interview capacity: {e}")
            # Fail open - allow user to proceed if check fails
            return True, "⚠️ Unable to check capacity, proceeding anyway"
    
    def get_session_info(self, session_id: str) -> Optional[dict]:
        """Get presence info for a specific session.
        
        Returns:
            Session info dict or None if not found
        """
        try:
            result = self.supabase.table("presence") \
                .select("*") \
                .eq("session_id", session_id) \
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return None
    
    def cleanup_stale_sessions(self, hours: int = 3):
        """Mark sessions as abandoned if last_seen > X hours ago.
        
        This should be run periodically (e.g., daily cron job) to clean up
        sessions where users closed tab without completing.
        
        Args:
            hours: Number of hours before considering session stale
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            result = self.supabase.table("presence") \
                .update({"status": "abandoned"}) \
                .eq("status", "active") \
                .lt("last_seen", cutoff.isoformat()) \
                .execute()
            
            count = len(result.data) if result.data else 0
            logger.info(f"Marked {count} stale sessions as abandoned")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up stale sessions: {e}")
            return 0


# Global instance
_presence_tracker = None

def get_presence_tracker(max_concurrent: int = 3) -> Optional[PresenceTracker]:
    """Get or create the presence tracker instance.
    
    Args:
        max_concurrent: Maximum concurrent interviews allowed
        
    Returns:
        PresenceTracker instance or None if Supabase not available
    """
    global _presence_tracker
    
    if _presence_tracker is None:
        try:
            from supabase import create_client
            
            supabase = create_client(
                st.secrets["supabase"]["url"],
                st.secrets["supabase"]["service_key"]
            )
            
            _presence_tracker = PresenceTracker(supabase, max_concurrent)
            logger.info("Presence tracker initialized")
            print("✅ Presence tracker created successfully")
            
        except Exception as e:
            error_msg = f"Could not initialize presence tracker: {e}"
            logger.warning(error_msg)
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return None
    
    return _presence_tracker
