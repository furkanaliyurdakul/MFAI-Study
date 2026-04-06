#!/usr/bin/env python3
"""
Recovery Utilities - Helper functions to integrate data loss prevention into UI.

This module provides convenient functions for:
- Showing recovery prompts
- Applying recovered data to session state
- Tracking and logging recovery events
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Callable

import streamlit as st

logger = logging.getLogger(__name__)


def show_recovery_prompt(detector, credentials_folder: str, login_username: str, language_code: Optional[str] = None) -> Optional[bool]:
    """
    Display recovery UI if incomplete session found.
    
    Args:
        detector: SessionRecoveryDetector instance
        credentials_folder: e.g., 'dutch_cohort'
        login_username: The actual login user (e.g., 'dutch_learner')
            This is used instead of random fake_name to match user sessions
        language_code: e.g., 'nl'. If None, searches across all languages.
    
    Returns: 
        True if user wants to resume, False if skip recovery, None if no session found
    """
    incomplete_session = detector.get_recovery_suggestion(
        credentials_folder, login_username, language_code
    )
    
    if not incomplete_session:
        return None
    
    # Show recovery UI
    st.warning(detector.format_recovery_message(incomplete_session))
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✓ Resume Session", key="recover_yes", use_container_width=True):
            st.session_state["_recovery_choice"] = "resume"
            st.session_state["_recovery_session"] = incomplete_session
            return True
    
    with col2:
        if st.button("✗ Start Fresh", key="recover_no", use_container_width=True):
            st.session_state["_recovery_choice"] = "skip"
            return False
    
    # Persist until user chooses
    if "_recovery_choice" in st.session_state:
        return st.session_state["_recovery_choice"] == "resume"
    
    st.stop()  # Block further execution until user chooses


def apply_recovered_data(
    recovered_data: Dict[str, Any],
    checkpoint_manager,
    page_callbacks: Dict[str, Callable]
) -> Dict[str, bool]:
    """
    Apply recovered data to session state and notify pages.
    
    Args:
        recovered_data: Dict with 'stages' containing recovered data
        checkpoint_manager: CheckpointManager instance
        page_callbacks: Dict of {'page_name': callback_function}
                       Callbacks receive recovered data and restore state
    
    Returns: Dict of pages that were successfully restored
    """
    restored = {}
    
    try:
        stages = recovered_data.get("stages", {})
        stage_order = ["profile", "learning", "knowledge_test", "ueq"]
        last_completed_stage = None
        
        for stage, data in stages.items():
            try:
                # Call stage-specific restore callback
                if stage in page_callbacks:
                    page_callbacks[stage](data)
                    restored[stage] = True
                    st.session_state[f"{stage}_completed"] = True
                    last_completed_stage = stage
                    logger.info(f"✓ Restored {stage}")
                else:
                    logger.warning(f"No callback for stage {stage}")
            
            except Exception as e:
                logger.error(f"Failed to restore {stage}: {e}")
                restored[stage] = False
        
        # Update session state
        st.session_state["_recovery_applied"] = True
        st.session_state["_recovery_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Jump to the NEXT page after last completed stage
        # (so user continues from where they left off, not from home)
        if last_completed_stage:
            try:
                stage_idx = stage_order.index(last_completed_stage)
                next_stage_idx = stage_idx + 1
                
                if next_stage_idx < len(stage_order):
                    next_page = stage_order[next_stage_idx]
                    st.session_state["current_page"] = next_page
                    logger.info(f"✓ Jumping to next page: {next_page}")
                else:
                    # All stages completed, jump to results
                    st.session_state["current_page"] = "results"
                    logger.info("✓ All stages recovered, showing results")
            except Exception as e:
                logger.warning(f"Failed to determine next page: {e}")
        
        return restored
        
    except Exception as e:
        logger.error(f"Recovery application failed: {e}")
        return {}


def show_recovery_banner(recovered_stages: Dict[str, bool]) -> None:
    """Display result of recovery operation."""
    if not recovered_stages:
        return
    
    successful = sum(1 for v in recovered_stages.values() if v)
    total = len(recovered_stages)
    
    stage_names = {
        "profile": "Profile Survey",
        "learning": "Learning Session",
        "knowledge_test": "Knowledge Test",
        "ueq": "Experience Survey"
    }
    
    st.success(
        f"✓ **Session Recovered**: {successful}/{total} stages restored\n\n"
        f"Recovered:\n"
        + "\n".join(
            f"  ✓ {stage_names.get(stage, stage)}"
            for stage, restored in recovered_stages.items()
            if restored
        )
    )
    
    failed = [stage for stage, restored in recovered_stages.items() if not restored]
    if failed:
        st.info(
            f"Incomplete: " +
            ", ".join(stage_names.get(s, s) for s in failed)
        )


def log_recovery_event(
    session_manager,
    recovery_type: str,
    details: Dict[str, Any],
    success: bool = True
) -> None:
    """
    Log recovery event for research analysis.
    
    Args:
        session_manager: Session manager instance
        recovery_type: 'auto_detect', 'user_initiated', 'crash_recovery'
        details: Event details
        success: Whether recovery was successful
    """
    try:
        session_info = session_manager.get_session_info()
        
        event = {
            "session_id": session_info.get("session_id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recovery_type": recovery_type,
            "success": success,
            "details": details,
        }
        
        # Save to recovery log
        recovery_log_dir = Path(session_manager.session_dir) / "recovery_logs"
        recovery_log_dir.mkdir(exist_ok=True)
        
        log_file = recovery_log_dir / "recovery_events.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        
        logger.info(f"✓ Recovery event logged: {recovery_type}")
        
    except Exception as e:
        logger.warning(f"Failed to log recovery event: {e}")


def create_recovery_summary(checkpoint_manager, detected_sessions: list) -> Dict[str, Any]:
    """
    Create summary of recovery opportunities (for admin/researcher view).
    
    Args:
        checkpoint_manager: CheckpointManager instance
        detected_sessions: List of incomplete sessions
    
    Returns: Summary dict with recovery statistics
    """
    try:
        total_sessions = len(detected_sessions)
        if total_sessions == 0:
            return {
                "incomplete_sessions": 0,
                "data_at_risk": 0,
                "recovery_viable": 0,
            }
        
        # Calculate recovery viability
        recovery_viable = sum(
            1 for session in detected_sessions
            if session.get("completion_percentage", 0) > 25
        )
        
        # Estimate data loss if not recovered
        avg_progress = sum(s.get("completion_percentage", 0) for s in detected_sessions) / total_sessions
        data_at_risk = int(total_sessions * (avg_progress / 100))
        
        return {
            "incomplete_sessions": total_sessions,
            "data_at_risk": data_at_risk,
            "recovery_viable": recovery_viable,
            "average_progress": avg_progress,
            "sessions": [
                {
                    "session_id": s.get("session_id"),
                    "progress": f"{s.get('completion_percentage', 0):.0f}%",
                    "last_modified": s.get("last_modified"),
                }
                for s in detected_sessions[:10]  # Top 10
            ]
        }
        
    except Exception as e:
        logger.error(f"Recovery summary creation failed: {e}")
        return {}


def generate_recovery_report(output_path: Path, checkpoint_manager, detected_sessions: list) -> bool:
    """
    Generate a text report of recovery opportunities (useful for troubleshooting).
    
    Args:
        output_path: Where to save the report
        checkpoint_manager: CheckpointManager instance
        detected_sessions: List of incomplete sessions
    
    Returns: True if successful
    """
    try:
        summary = create_recovery_summary(checkpoint_manager, detected_sessions)
        
        report_lines = [
            "=== SESSION RECOVERY REPORT ===",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "SUMMARY",
            f"  Incomplete Sessions: {summary['incomplete_sessions']}",
            f"  Data at Risk: {summary['data_at_risk']}",
            f"  Viable for Recovery: {summary['recovery_viable']}",
            f"  Average Progress: {summary['average_progress']:.1f}%",
            "",
            "SESSIONS AVAILABLE FOR RECOVERY",
        ]
        
        for session in summary['sessions']:
            report_lines.append(
                f"  - {session['session_id']}: {session['progress']} "
                f"(modified: {session['last_modified']})"
            )
        
        # Write report
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        
        logger.info(f"✓ Recovery report saved to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return False


# Streamlit-specific helpers

def initialize_recovery_in_session_state():
    """Initialize recovery-related session state variables."""
    recovery_defaults = {
        "_recovery_choice": None,
        "_recovery_session": None,
        "_recovery_applied": False,
        "_recovery_timestamp": None,
    }
    
    for key, default in recovery_defaults.items():
        st.session_state.setdefault(key, default)


def should_block_for_recovery() -> bool:
    """Check if user needs to make recovery choice."""
    return (
        st.session_state.get("_recovery_choice") is None
        and st.session_state.get("_recovery_session") is not None
    )
