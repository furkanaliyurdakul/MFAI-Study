# SPDX-License-Identifier: MIT
"""Authentication system for the AI Learning Platform.

Manages secure login with different credential types for study participants
and research team members. Organizes data collection by credential type.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Dict, Optional
import streamlit as st


@dataclass
class CredentialConfig:
    """Configuration for a specific credential type."""
    username: str
    password_hash: str
    language_code: str  # "en", "de", "nl", "tr", "sq", "hi"
    description: str
    folder_prefix: str  # for organizing data by language in Supabase
    dev_mode: bool = False
    fast_test_mode: bool = False
    upload_enabled: bool = False


class AuthenticationManager:
    """Manages authentication and session state for the learning platform."""
    
    def __init__(self):
        self.credentials = self._initialize_credentials()
    
    def _hash_password(self, password: str) -> str:
        """Create secure hash of password with salt."""
        salt = "learning_platform_2025"  # Platform-specific salt
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    
    def _initialize_credentials(self) -> Dict[str, CredentialConfig]:
        """Initialize available credentials for the platform."""
        return {
            # English (High-resource control)
            "english": CredentialConfig(
                username="english_learner",
                password_hash=self._hash_password("EnglishStudy2025!"),
                language_code="en",
                description="English Language Participant",
                folder_prefix="english_cohort",
                dev_mode=False,
                fast_test_mode=False,
                upload_enabled=False
            ),
            
            # German (High-resource European)
            "german": CredentialConfig(
                username="german_learner",
                password_hash=self._hash_password("GermanStudy2025!"),
                language_code="de",
                description="German Language Participant",
                folder_prefix="german_cohort",
                dev_mode=False,
                fast_test_mode=False,
                upload_enabled=False
            ),
            
            # Dutch (High-resource European alternative)
            "dutch": CredentialConfig(
                username="dutch_learner",
                password_hash=self._hash_password("DutchStudy2025!"),
                language_code="nl",
                description="Dutch Language Participant",
                folder_prefix="dutch_cohort",
                dev_mode=False,
                fast_test_mode=False,
                upload_enabled=False
            ),
            
            # Turkish (Medium-resource)
            "turkish": CredentialConfig(
                username="turkish_learner",
                password_hash=self._hash_password("TurkishStudy2025!"),
                language_code="tr",
                description="Turkish Language Participant",
                folder_prefix="turkish_cohort",
                dev_mode=False,
                fast_test_mode=False,
                upload_enabled=False
            ),
            
            # Albanian (Low-resource)
            "albanian": CredentialConfig(
                username="albanian_learner",
                password_hash=self._hash_password("AlbanianStudy2025!"),
                language_code="sq",
                description="Albanian Language Participant",
                folder_prefix="albanian_cohort",
                dev_mode=False,
                fast_test_mode=False,
                upload_enabled=False
            ),
            
            # Hindi (Medium-resource, optional)
            "hindi": CredentialConfig(
                username="hindi_learner",
                password_hash=self._hash_password("HindiStudy2025!"),
                language_code="hi",
                description="Hindi Language Participant",
                folder_prefix="hindi_cohort",
                dev_mode=False,
                fast_test_mode=False,
                upload_enabled=False
            ),
            
            # Development mode - full access (defaults to English)
            "dev": CredentialConfig(
                username="dev",
                password_hash=self._hash_password("dev"),
                language_code="en",  # Default to English for dev
                description="Development Mode - Full Access",
                folder_prefix="dev_testing",
                dev_mode=True,
                fast_test_mode=False,
                upload_enabled=True
            ),
            
            # Fast test mode - quick tutorial (defaults to English)
            "fasttest": CredentialConfig(
                username="fasttest",
                password_hash=self._hash_password("fasttest"),
                language_code="en",  # Default to English for demo
                description="Fast Test Mode - Quick Tutorial",
                folder_prefix="demo_testing",
                dev_mode=False,
                fast_test_mode=True,
                upload_enabled=False
            ),
            
            # Combined dev + fast test mode for testing
            "devfast": CredentialConfig(
                username="devfast",
                password_hash=self._hash_password("devfast"),
                language_code="en",  # Default to English for combined mode
                description="Development + Fast Test Mode",
                folder_prefix="dev_fast_testing",
                dev_mode=True,
                fast_test_mode=True,
                upload_enabled=True
            )
        }
    
    def authenticate(self, username: str, password: str) -> Optional[CredentialConfig]:
        """Authenticate user and return credential config if valid."""
        # Find credential by matching username field
        for credential in self.credentials.values():
            if credential.username == username:
                password_hash = self._hash_password(password)
                if password_hash == credential.password_hash:
                    # Optional: Log successful authentication for monitoring
                    try:
                        import streamlit as st
                        if 'auth_log' not in st.session_state:
                            st.session_state.auth_log = []
                        st.session_state.auth_log.append(f"✅ {username} authenticated successfully")
                    except ImportError:
                        pass
                    return credential
        
        # Optional: Log failed authentication attempts for debugging
        try:
            import streamlit as st
            if 'auth_log' not in st.session_state:
                st.session_state.auth_log = []
            st.session_state.auth_log.append(f"❌ Failed login attempt: {username}")
        except ImportError:
            pass
            
        return None
    
    def is_authenticated(self) -> bool:
        """Check if current session has valid authentication."""
        return (
            st.session_state.get("authenticated", False) and
            st.session_state.get("credential_config") is not None
        )
    
    def get_current_config(self) -> Optional[CredentialConfig]:
        """Get current authenticated user's credential configuration."""
        if self.is_authenticated():
            return st.session_state.get("credential_config")
        return None
    
    def logout(self) -> None:
        """Clear authentication and reset session."""
        # Clear authentication state
        st.session_state["authenticated"] = False
        st.session_state["credential_config"] = None
        
        # Clear session data to prevent data leakage between users
        session_keys_to_clear = [
            "current_page", "profile_completed", "learning_completed", 
            "test_completed", "ueq_completed", "completion_processed",
            "upload_completed", "responses", "messages", 
            "exported_images", "transcription_text",
            "selected_slide", "debug_logs", "language_code",
            "consent_given", "consent_logged",
            "show_review", "gemini_chat", "_page_timer", "session_initialized",
            "transcription_loaded", "slides_loaded", "gemini_chat_initialized",
            "capacity_checked", "interview_access_granted", "session_registered",
            "session_manager", "previous_page"  # Clear SessionManager to force new session_id on next login
        ]
        
        for key in session_keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        # Re-initialize essential session state variables with default values
        # This prevents KeyError when accessing these variables after logout
        st.session_state["current_page"] = "home"
        st.session_state["profile_completed"] = False
        st.session_state["learning_completed"] = False
        st.session_state["test_completed"] = False
        st.session_state["ueq_completed"] = False
    
    def get_language_code(self) -> Optional[str]:
        """Get language code from current authenticated credential.
        
        Returns:
            Language code (e.g., 'en', 'de', 'tr') or None if not authenticated
        """
        config = self.get_current_config()
        if not config:
            return None
        
        # Check if language was set in session state (e.g., by dev mode selector)
        if "language_code" in st.session_state:
            return st.session_state["language_code"]
        
        # Otherwise use credential's default language
        return config.language_code
    
    def get_available_usernames(self) -> Dict[str, str]:
        """Get list of available usernames for display purposes."""
        return {
            username: config.description 
            for username, config in self.credentials.items()
        }


# Global authentication manager instance
_auth_manager = None

def get_auth_manager() -> AuthenticationManager:
    """Get singleton authentication manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthenticationManager()
    return _auth_manager