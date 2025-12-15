# SPDX-License-Identifier: MIT
"""Capacity management system for concurrent user limiting.

Monitors:
- Active sessions (from presence tracker)
- Google API usage limits
- Average session duration
- Provides smart wait time estimates
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
import json
from pathlib import Path


class CapacityManager:
    """Manages platform capacity and provides intelligent access control."""
    
    def __init__(self, presence_tracker, session_manager):
        self.presence = presence_tracker
        self.session_manager = session_manager
        
        # Google API limits (Gemini 2.5 Flash free tier)
        self.GOOGLE_API_RPM_LIMIT = 10  # Requests per minute
        self.GOOGLE_API_TPM_LIMIT = 250000  # Tokens per minute
        self.GOOGLE_API_RPD_LIMIT = 250  # Requests per day
        
        # Average session estimates (will be updated from real data)
        self.AVG_PROFILE_MINUTES = 5
        self.AVG_LEARNING_MINUTES = 30
        self.AVG_TEST_MINUTES = 5
        
    def get_capacity_status(self) -> Dict:
        """Get comprehensive capacity status.
        
        Returns:
            Dict with capacity info, API limits, active sessions, wait estimates
        """
        if not self.presence:
            return {
                "available": True,
                "reason": "Capacity tracking not available",
                "can_proceed": True
            }
        
        # Count active interviews
        active_interviews = self.presence.count_active_interviews()
        max_concurrent = self.presence.max_concurrent
        
        # Get active sessions details
        active_sessions = self.presence.count_active_sessions()
        
        # Calculate wait time estimate
        if active_interviews >= max_concurrent:
            wait_minutes = self._estimate_wait_time()
            next_available = datetime.now() + timedelta(minutes=wait_minutes)
        else:
            wait_minutes = 0
            next_available = datetime.now()
        
        # Check API limits (would need implementation to track actual usage)
        api_status = self._check_api_limits()
        
        return {
            "available": active_interviews < max_concurrent and api_status["available"],
            "active_interviews": active_interviews,
            "max_concurrent": max_concurrent,
            "total_active_sessions": active_sessions,
            "slots_available": max(0, max_concurrent - active_interviews),
            "wait_minutes": wait_minutes,
            "next_available": next_available,
            "api_status": api_status,
            "can_proceed": active_interviews < max_concurrent and api_status["available"]
        }
    
    def _estimate_wait_time(self) -> int:
        """Estimate wait time based on active session data.
        
        Uses page timing data to predict when next slot opens.
        """
        # Get average time remaining for active interviews
        # This would query the presence table to see how long current sessions have been running
        # For now, use conservative estimate
        return self.AVG_LEARNING_MINUTES // 2  # Assume halfway through on average
    
    def _check_api_limits(self) -> Dict:
        """Check Google API usage against limits.
        
        Returns:
            Dict with API status and remaining capacity
        """
        # TODO: Implement actual API usage tracking
        # For now, return optimistic estimate
        # You would need to:
        # 1. Track API calls in a file/database
        # 2. Count calls in last minute, last day
        # 3. Estimate tokens per request
        
        return {
            "available": True,
            "rpm_used": 0,  # Would track actual usage
            "rpm_limit": self.GOOGLE_API_RPM_LIMIT,
            "rpd_used": 0,  # Would track daily usage
            "rpd_limit": self.GOOGLE_API_RPD_LIMIT,
            "estimated_safe": True
        }
    
    def show_capacity_warning(self, location: str = "home"):
        """Show capacity warning/status to user.
        
        Args:
            location: Where in the flow (home, profile, learning)
        """
        status = self.get_capacity_status()
        
        if not status["can_proceed"]:
            if location == "learning":
                # Hard block at learning page
                st.error("🚦 **Platform at Capacity**")
                st.warning(
                    f"**{status['active_interviews']}/{status['max_concurrent']}** interviews currently in progress.\n\n"
                    f"**Estimated wait time:** ~{status['wait_minutes']} minutes\n\n"
                    f"**Next available:** {status['next_available'].strftime('%H:%M')}\n\n"
                    "This page will automatically refresh when a slot opens."
                )
                
                # Auto-refresh button
                if st.button("🔄 Check Again", key="refresh_capacity"):
                    st.rerun()
                
                # Auto-refresh every 30 seconds
                st.markdown(
                    """
                    <meta http-equiv="refresh" content="30">
                    <p style="color: gray; font-size: 0.9em;">
                    ⏱️ Auto-refreshing every 30 seconds...
                    </p>
                    """,
                    unsafe_allow_html=True
                )
                return False
            
            elif location == "home":
                # Soft warning at home
                st.warning(
                    f"⚠️ **High Platform Usage**\n\n"
                    f"{status['active_interviews']}/{status['max_concurrent']} interviews in progress. "
                    f"You may need to wait ~{status['wait_minutes']} minutes before starting the learning section."
                )
                return True  # Allow to continue to profile
        
        elif status["slots_available"] <= 1:
            # Almost at capacity - show info
            st.info(
                f"**Platform Status:** {status['slots_available']} slot(s) available. "
                f"Complete each step without delay for best experience."
            )
        
        return True  # Can proceed
    
    def check_and_wait(self) -> bool:
        """Check capacity and show non-blocking wait UI if needed.
        
        Returns:
            True if slot available (stops execution if not)
        """
        status = self.get_capacity_status()
        
        if status.get("can_proceed"):
            return True
        
        active = status.get("active_interviews", 0)
        cap = status.get("max_concurrent", self.presence.max_concurrent if self.presence else 2)
        wait_min = status.get("wait_minutes", 1)
        
        st.warning(f"Capacity reached: {active}/{cap} active interviews. Please wait ~{wait_min} min.")
        st.button("🔄 Check again", on_click=st.rerun)
        st.stop()


def get_capacity_manager():
    """Get or create capacity manager instance."""
    if "capacity_manager" not in st.session_state:
        from presence_tracker import get_presence_tracker
        from session_manager import get_session_manager
        
        presence = get_presence_tracker()
        session_mgr = get_session_manager()
        
        st.session_state.capacity_manager = CapacityManager(presence, session_mgr)
    
    return st.session_state.capacity_manager
