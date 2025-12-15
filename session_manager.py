import datetime
import json
import os
import random
import string

import streamlit as st

from constants import KNOWLEDGE_JSON, UEQ_JSON, EXPERIMENT_META, INTERACTION_COUNTS
from analytics_syncer import get_analytics_syncer

# List of fake first names and last names for pseudonymization
FIRST_NAMES = [
    "Alex",
    "Bailey",
    "Cameron",
    "Dakota",
    "Ellis",
    "Finley",
    "Gray",
    "Harper",
    "Indigo",
    "Jordan",
    "Kennedy",
    "Logan",
    "Morgan",
    "Noah",
    "Oakley",
    "Parker",
    "Quinn",
    "Riley",
    "Sawyer",
    "Taylor",
    "Ursa",
    "Val",
    "Winter",
    "Xen",
    "Yael",
    "Zephyr",
]

LAST_NAMES = [
    "Adams",
    "Brooks",
    "Chen",
    "Davis",
    "Evans",
    "Foster",
    "Garcia",
    "Hayes",
    "Ivanov",
    "Johnson",
    "Kim",
    "Lee",
    "Miller",
    "Nguyen",
    "Ortiz",
    "Patel",
    "Quinn",
    "Robinson",
    "Smith",
    "Taylor",
    "Ueda",
    "Vargas",
    "Williams",
    "Xu",
    "Young",
    "Zhang",
]


class SessionManager:
    """Manages session data and file organization for the multilingual learning platform."""

    def __init__(self, language_code: str | None = None):
        """Initialize the session manager."""
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(self.base_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)

        self.language_code = language_code or "en"  # default to English
        
        # Get credential-based folder prefix if available
        self.folder_prefix = self._get_credential_folder_prefix()

        # Generate session ID if not already exists
        if not hasattr(self, "session_id"):
            self.create_new_session()
    
    def _get_credential_folder_prefix(self) -> str:
        """Get folder prefix based on current authentication credentials."""
        try:
            # Import here to avoid circular imports
            from authentication import get_auth_manager
            auth_manager = get_auth_manager()
            config = auth_manager.get_current_config()
            
            if config:
                # Update language_code from credential if available
                if hasattr(config, 'language_code'):
                    self.language_code = config.language_code
                return config.folder_prefix
            else:
                return "unknown_user"
        except (ImportError, AttributeError):
            # Fallback for cases where authentication isn't available
            return "legacy_session"

    def create_new_session(self):
        """Create a new session with timestamp and fake name as identifier."""
        import secrets
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fake_name = self._generate_fake_name()
        suffix = secrets.token_hex(2)  # 4 hex chars
        
        # Create credential-based session ID with random suffix
        self.session_id = f"{timestamp}_{fake_name}-{suffix}"
        
        # Create credential-organized directory structure
        credential_dir = os.path.join(self.output_dir, self.folder_prefix)
        os.makedirs(credential_dir, exist_ok=True)
        
        self.session_dir = os.path.join(credential_dir, self.session_id)
        os.makedirs(self.session_dir, exist_ok=True)

        # Create subdirectories for different types of data
        self.profile_dir = os.path.join(self.session_dir, "profile")
        self.knowledge_test_dir = os.path.join(self.session_dir, "knowledge_test")
        self.learning_logs_dir = os.path.join(self.session_dir, "learning_logs")
        self.ueq_dir = os.path.join(self.session_dir, "ueq")
        self.analytics_dir = os.path.join(self.session_dir, "analytics")  # New analytics directory

        os.makedirs(self.profile_dir, exist_ok=True)
        os.makedirs(self.knowledge_test_dir, exist_ok=True)
        os.makedirs(self.learning_logs_dir, exist_ok=True)
        os.makedirs(self.ueq_dir, exist_ok=True)
        os.makedirs(self.analytics_dir, exist_ok=True)

        with open(os.path.join(self.session_dir, "language.txt"), "w") as f:
            f.write(self.language_code)

        # Sync to analytics database
        analytics = get_analytics_syncer()
        if analytics:
            analytics.create_session_record(
                session_id=self.session_id,
                user_id=self.folder_prefix,
                language_code=self.language_code
            )

        return self.session_id

    def _generate_fake_name(self):
        """Generate a random fake name for pseudonymization."""
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        return f"{first_name}_{last_name}"

    def save_profile(self, profile_data: dict, original_name: str | None = None) -> str:
        """Save only pseudonymized profile (no PII stored).

        Args:
            profile_data (dict): The profile data to save
            original_name (str | None): Original name (ignored, for backwards compatibility)

        Returns:
            str: Path to the saved profile file
        """
        pseudo = dict(profile_data)
        # Overwrite any name with a pseudonym derived from session id
        pseudo["name"] = f"Participant_{self.session_id[-6:]}"
        os.makedirs(self.profile_dir, exist_ok=True)
        out = os.path.join(self.profile_dir, "pseudonymized_profile.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(pseudo, f, indent=2, ensure_ascii=False)
        
        # Sync to analytics database
        analytics = get_analytics_syncer()
        if analytics:
            from pathlib import Path
            analytics.sync_profile(
                session_id=self.session_id,
                profile_data=pseudo,
                file_path=Path(out)
            )
        
        return out

    def write_meta_json(self, filename: str, payload: dict) -> str:
        """Write JSON metadata file to <session>/meta/ directory.
        
        Args:
            filename (str): Name of the JSON file to write
            payload (dict): Dictionary to save as JSON
            
        Returns:
            str: Path to the saved file
        """
        meta_dir = os.path.join(self.session_dir, "meta")
        os.makedirs(meta_dir, exist_ok=True)
        path = os.path.join(meta_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)
        return path

    def _read_json_safe(self, path: str):
        """Safely read JSON file, return None on failure."""
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Could not load JSON from {path}: {e}")
            return None

    def save_knowledge_test_results(self, result_dict: dict) -> str:
        """Save knowledge test results as JSON.

        Args:
            result_dict (dict): The test results as a dictionary

        Returns:
            str: Path to the saved results file
        """
        path = os.path.join(self.knowledge_test_dir, "knowledge_test_results.json")
        os.makedirs(self.knowledge_test_dir, exist_ok=True)
        payload = {
            "language_code": self.language_code,
            "session_id": self.session_id,
            **result_dict
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        # Sync to analytics database
        analytics = get_analytics_syncer()
        if analytics:
            from pathlib import Path
            analytics.sync_knowledge_test(
                session_id=self.session_id,
                results=payload,
                file_path=Path(path)
            )
        
        return path

    def save_interaction_analytics(self, interaction_counts):
        """Save interaction analytics for research analysis.

        Args:
            interaction_counts (dict): Dictionary with interaction statistics

        Returns:
            str: Path to the saved analytics file
        """
        filename = "interaction_analytics.json"
        file_path = os.path.join(self.analytics_dir, filename)

        analytics_data = {
            "language_code": self.language_code,
            "session_id": self.session_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "interaction_counts": interaction_counts,
            "engagement_metrics": {
                "total_user_interactions": interaction_counts.get("total_user_interactions", 0),
                "slide_to_chat_ratio": (
                    interaction_counts.get("slide_explanations", 0) / 
                    max(interaction_counts.get("manual_chat", 1), 1)  # Avoid division by zero
                ),
                "interaction_distribution": {
                    "slide_explanations_pct": (
                        interaction_counts.get("slide_explanations", 0) / 
                        max(interaction_counts.get("total_user_interactions", 1), 1) * 100
                    ),
                    "manual_chat_pct": (
                        interaction_counts.get("manual_chat", 0) / 
                        max(interaction_counts.get("total_user_interactions", 1), 1) * 100
                    )
                }
            }
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(analytics_data, f, indent=4)

        return file_path

    def save_learning_log(self, log_data):
        """Save learning interaction logs in both TXT and JSON formats.

        Args:
            log_data (dict): The log data to save

        Returns:
            str: Path to the saved log file (txt)
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_txt = f"learning_log_{timestamp}.txt"
        filename_json = "learning_interactions.json"
        file_path_txt = os.path.join(self.learning_logs_dir, filename_txt)
        file_path_json = os.path.join(self.learning_logs_dir, filename_json)

        # Save as TXT (for human readability)
        with open(file_path_txt, "w", encoding="utf-8") as f:
            # Write session information
            f.write(f"Session ID: {log_data['session_id']}\n")
            f.write(f"Fake Name: {log_data['fake_name']}\n")
            f.write(f"Language: {self.language_code}\n\n")
            f.write(f"Timestamp: {log_data['timestamp']}\n")
            
            # Write interaction summary if available
            if "interaction_counts" in log_data:
                counts = log_data["interaction_counts"]
                f.write("\n=== INTERACTION SUMMARY ===\n")
                f.write(f"Slide Explanations Generated: {counts['slide_explanations']}\n")
                f.write(f"Manual Chat Messages: {counts['manual_chat']}\n")
                f.write(f"Total User Interactions: {counts['total_user_interactions']}\n")
                if counts['total_user_interactions'] > 0:
                    slide_pct = (counts['slide_explanations'] / counts['total_user_interactions']) * 100
                    chat_pct = (counts['manual_chat'] / counts['total_user_interactions']) * 100
                    f.write(f"Interaction Distribution: {slide_pct:.1f}% slides, {chat_pct:.1f}% chat\n")
            
            f.write("\n=== INTERACTIONS ===\n\n")

            # Write each interaction
            for interaction in log_data["interactions"]:
                f.write(f"--- Interaction at {interaction['timestamp']} ---\n")
                f.write(f"Type: {interaction['interaction_type']}\n")
                f.write(f"User Input: {interaction['user_input']}\n")
                f.write(f"System Response: {interaction['system_response']}\n")

                # Write metadata if available
                if "metadata" in interaction:
                    f.write("Metadata:\n")
                    for key, value in interaction["metadata"].items():
                        f.write(f"  {key}: {value}\n")

                f.write("\n")
        
        # Save as JSON (for analytics database)
        with open(file_path_json, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        # Sync to analytics database
        analytics = get_analytics_syncer()
        if analytics:
            from pathlib import Path
            analytics.sync_learning_log(
                session_id=self.session_id,
                log_path=Path(file_path_json)
            )

        return file_path_txt

    def save_ueq_responses(self, response_text):
        """Save UEQ survey responses.

        Args:
            response_text (str): The UEQ responses as text

        Returns:
            str: Path to the saved responses file
        """
        filename = "ueq_responses.txt"
        file_path = os.path.join(self.ueq_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Language: {self.language_code}\n\n")
            f.write(response_text)

        return file_path

    def get_session_info(self) -> dict:
        """Get information about the current session including baseline experiment metadata.

        Returns:
            dict: Session information with language, model, content version, etc.
        """
        info = {
            "session_id": getattr(self, "session_id", None),
            "fake_name": self.session_id.split("_", 1)[1] if hasattr(self, "session_id") else None,
            "timestamp": self.session_id.split("_", 1)[0] if hasattr(self, "session_id") else None,
            "session_dir": getattr(self, "session_dir", None),
            "language_code": getattr(self, "language_code", None),
        }
        
        # Try to load experiment metadata if available
        try:
            meta_path = os.path.join(self.session_dir, "meta", "experiment_meta.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                info.update({
                    "model_name": meta.get("model"),
                    "model_provider": meta.get("provider"),
                    "content_version": {
                        "slides_hash": meta.get("slides_hash"),
                        "transcript_hash": meta.get("transcript_hash"),
                    },
                })
        except Exception:
            # Keep info minimal if meta not yet written
            pass
        
        return info

    def save_ueq(self, answers: dict, benchmark: dict, free_text: str | None) -> str:
        """Save UEQ results as JSON.

        Args:
            answers: dict of q1..q26 -> 1..7
            benchmark: dict with 'means' and 'grades'
            free_text: optional comment

        Returns:
            str: Path to saved file
        """
        payload = {
            "answers": answers,
            "scale_means": benchmark["means"],
            "grades": benchmark["grades"],
            "comment": free_text or "",
            "language_code": self.language_code,
            "session_id": self.session_id,
        }
        path = os.path.join(self.ueq_dir, "ueq_responses.json")
        os.makedirs(self.ueq_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        
        # Sync to analytics database
        analytics = get_analytics_syncer()
        if analytics:
            from pathlib import Path
            ueq_data = {
                "means": benchmark["means"],
                "grades": benchmark["grades"]
            }
            analytics.sync_ueq(
                session_id=self.session_id,
                ueq_data=ueq_data,
                file_path=Path(path)
            )
        
        return path

    def create_final_analytics(self):
        """Create a comprehensive analytics JSON with all research data consolidated."""
        # Ensure analytics directory exists
        os.makedirs(self.analytics_dir, exist_ok=True)
        
        final_analytics = {
            "session_info": {
                "session_id": self.session_id,
                "pseudonym": self.session_id.split("_", 1)[1],
                "timestamp": self.session_id.split("_", 1)[0],
                "language_code": self.language_code,
                "session_dir": self.session_dir
            },
            "profile_data": None,
            "page_timings": None,
            "interaction_analytics": None,
            "ueq_results": None,
            "knowledge_test_results": None,
            "summary_metrics": {}
        }

        # Load profile data
        try:
            profile_path = os.path.join(self.profile_dir, "pseudonymized_profile.json")
            if os.path.exists(profile_path):
                with open(profile_path, "r", encoding="utf-8") as f:
                    final_analytics["profile_data"] = json.load(f)
        except Exception as e:
            print(f"Could not load profile data: {e}")

        # Load page timings
        try:
            page_timings_path = os.path.join(self.session_dir, "meta", "page_durations.json")
            if os.path.exists(page_timings_path):
                with open(page_timings_path, "r", encoding="utf-8") as f:
                    timings = json.load(f)
                    final_analytics["page_timings"] = timings
                    # Calculate total session time
                    final_analytics["summary_metrics"]["total_session_time_seconds"] = sum(timings.values())
                    final_analytics["summary_metrics"]["total_session_time_minutes"] = sum(timings.values()) / 60
        except Exception as e:
            print(f"Could not load page timings: {e}")

        # Load interaction analytics
        try:
            if os.path.exists(self.analytics_dir):
                interaction_files = [f for f in os.listdir(self.analytics_dir) if f.startswith("interaction_analytics")]
                if interaction_files:
                    # Get the most recent interaction analytics file
                    latest_file = max(interaction_files)
                    interaction_path = os.path.join(self.analytics_dir, latest_file)
                    with open(interaction_path, "r", encoding="utf-8") as f:
                        final_analytics["interaction_analytics"] = json.load(f)
        except Exception as e:
            print(f"Could not load interaction analytics: {e}")

        # Load UEQ results from JSON (source of truth)
        try:
            ueq_path = os.path.join(self.ueq_dir, UEQ_JSON)
            final_analytics["ueq_results"] = self._read_json_safe(ueq_path)
        except Exception as e:
            print(f"Could not load UEQ results: {e}")

        # Load knowledge test results from JSON (source of truth)
        try:
            knowledge_path = os.path.join(self.knowledge_test_dir, KNOWLEDGE_JSON)
            final_analytics["knowledge_test_results"] = self._read_json_safe(knowledge_path)
        except Exception as e:
            print(f"Could not load knowledge test results: {e}")

        # Calculate additional summary metrics
        try:
            # Learning engagement metrics with stable ratios
            if final_analytics["interaction_analytics"]:
                interaction_data = final_analytics["interaction_analytics"]
                slide_count = interaction_data.get("interaction_counts", {}).get("slide_explanations", 0)
                chat_count = interaction_data.get("interaction_counts", {}).get("manual_chat", 0)
                total_interactions = interaction_data.get("interaction_counts", {}).get("total_user_interactions", 0)
                
                # Compute stable ratios with divide-by-zero guards
                slide_to_chat_ratio = (slide_count / chat_count) if chat_count > 0 else 0
                slide_share = (slide_count / total_interactions) if total_interactions > 0 else 0
                
                final_analytics["summary_metrics"]["learning_engagement"] = {
                    "total_ai_interactions": total_interactions,
                    "slide_explanations": slide_count,
                    "manual_chat": chat_count,
                    "slide_to_chat_ratio": slide_to_chat_ratio,
                    "slide_share": slide_share
                }

            # UEQ summary metrics
            if final_analytics["ueq_results"]:
                ueq_data = final_analytics["ueq_results"]
                final_analytics["summary_metrics"]["ueq_summary"] = {
                    "scale_means": ueq_data.get("scale_means", {}),
                    "overall_grades": ueq_data.get("grades", {}),
                    "has_comment": bool(ueq_data.get("comment", "").strip())
                }

            # Knowledge test summary
            if final_analytics["knowledge_test_results"]:
                knowledge_data = final_analytics["knowledge_test_results"]
                if "answers" in knowledge_data:
                    total_questions = len(knowledge_data["answers"])
                    correct_answers = sum(1 for ans in knowledge_data["answers"].values() if ans.get("is_correct", False))
                    final_analytics["summary_metrics"]["knowledge_test_summary"] = {
                        "total_questions": total_questions,
                        "correct_answers": correct_answers,
                        "accuracy_percentage": (correct_answers / total_questions * 100) if total_questions > 0 else 0
                    }

            # Learning efficiency metrics
            if final_analytics["page_timings"] and final_analytics["interaction_analytics"]:
                learning_time = final_analytics["page_timings"].get("personalized_learning", 0)
                total_interactions = final_analytics["summary_metrics"].get("learning_engagement", {}).get("total_ai_interactions", 0)
                if learning_time > 0 and total_interactions > 0:
                    final_analytics["summary_metrics"]["learning_efficiency"] = {
                        "avg_time_per_interaction_seconds": learning_time / total_interactions,
                        "interactions_per_minute": (total_interactions / learning_time) * 60
                    }

        except Exception as e:
            print(f"Could not calculate summary metrics: {e}")

        # Save the final analytics file
        final_analytics_path = os.path.join(self.analytics_dir, "final_research_analytics.json")
        with open(final_analytics_path, "w", encoding="utf-8") as f:
            json.dump(final_analytics, f, indent=4, ensure_ascii=False)

        return final_analytics_path


session_manager = None  # keeps the singleton in the module


def get_session_manager() -> SessionManager:
    """Return ONE shared SessionManager instance for the whole app."""
    global session_manager

    if session_manager is not None:  # we already created / cached it
        return session_manager

    # Was it created somewhere else (e.g. on the Home page) and put into
    # session_state?  → reuse it
    if "session_manager" in st.session_state:
        session_manager = st.session_state["session_manager"]
        return session_manager

    # First call overall → create it, remember it everywhere
    session_manager = SessionManager()
    st.session_state["session_manager"] = session_manager
    return session_manager
