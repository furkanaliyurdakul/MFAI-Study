# SPDX-License-Identifier: MIT
"""Login page for the AI Learning Platform.

Provides secure authentication interface and session management.
"""

from __future__ import annotations

import streamlit as st
from authentication import get_auth_manager, CredentialConfig
from config import config


def show_login_page() -> bool:
    """
    Display login page and handle authentication.
    
    Returns:
        True if user successfully authenticated, False otherwise
    """
    print("🔧 DEBUG: show_login_page() called")
    auth_manager = get_auth_manager()
    
    # Header
    st.title(f"{config.platform.platform_name}")
    st.markdown("---")
    
    # Main login interface
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.header("Secure Access")
        st.markdown("""
        Welcome to the platform.
        
        Please enter your credentials to access the system.
        """)
        
        # Login form
        with st.form("login_form", clear_on_submit=False):
            st.subheader("Login Credentials")
            
            username = st.text_input(
                "Username",
                placeholder="Enter your assigned username",
                help="Use the exact username provided to you"
            )
            
            password = st.text_input(
                "Password", 
                type="password",
                placeholder="Enter your password",
                help="Passwords are case-sensitive"
            )
            
            login_button = st.form_submit_button(
                "Access Platform",
                use_container_width=True,
                type="primary"
            )
            
            if login_button:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    # Attempt authentication
                    with st.spinner("Verifying credentials..."):
                        credential_config = auth_manager.authenticate(username, password)
                        
                        if credential_config:
                            # Successful authentication - mark authenticated first
                            st.session_state["authenticated"] = True
                            st.session_state["credential_config"] = credential_config
                            
                            # Configure special modes
                            st.session_state["dev_mode"] = credential_config.dev_mode
                            st.session_state["fast_test_mode"] = credential_config.fast_test_mode
                            
                            st.success(f"Authentication successful! Welcome.")
                            st.info("Redirecting to platform...")
                            
                            # Force page refresh to load main application
                            st.rerun()
                        else:
                            st.error("Invalid username or password. Please check your credentials and try again.")
                            
                            # Show minimal debug info for developers only
                            if st.session_state.get("dev_mode", False) and "auth_log" in st.session_state and st.session_state.auth_log:
                                with st.expander("Authentication Log", expanded=False):
                                    for log_entry in st.session_state.auth_log[-5:]:  # Show last 5 entries
                                        st.text(log_entry)
    
    # Information panels
    st.markdown("---")
    
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.subheader("Platform Information")
        st.markdown("""
        **Usage Instructions:**  
        - Complete all platform components in sequence
        - Follow the navigation steps provided
        - Use the menu on the left to navigate
        """)
    
    with col_info2:
        st.subheader("Privacy & Security")
        st.markdown("""
        **Data Protection:**  
        - Secure data handling
        - Privacy-compliant processing
        
        **Session Security:**  
        - Secure login verification
        - Automatic session management
        """)
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
        <small>
        Learning Platform | 2025
        </small>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    return auth_manager.is_authenticated()


def show_logout_interface() -> None:
    """Show logout option in sidebar for authenticated users."""
    auth_manager = get_auth_manager()
    config = auth_manager.get_current_config()
    
    if config:
        # Dev mode sidebar info
        if st.session_state.get("dev_mode", False) or getattr(config, "dev_mode", False):
            with st.sidebar:
                st.caption("DEV — session info")
                st.json({
                    "session_id": st.session_state.get("session_id"),
                    "language": st.session_state.get("language_code"),
                    "username": config.username,
                })
                if "auth_log" in st.session_state and st.session_state.auth_log:
                    with st.expander("Authentication Log"):
                        for entry in st.session_state.auth_log[-10:]:
                            st.text(entry)
        
        # Session info will be shown in main.py after navigation
        # (moved to keep UI clean and organized)


def require_authentication() -> CredentialConfig:
    """
    Require authentication and return current config.
    
    If not authenticated, shows login page and stops execution.
    If authenticated, returns the current credential configuration.
    """
    auth_manager = get_auth_manager()
    
    print(f"🔧 DEBUG: require_authentication called, is_authenticated: {auth_manager.is_authenticated()}")
    
    if not auth_manager.is_authenticated():
        print("🔧 DEBUG: Not authenticated, showing login page")
        # Show login page and stop execution
        show_login_page()
        st.stop()
    
    print("🔧 DEBUG: User authenticated, adding logout interface")
    # Add logout interface to sidebar
    show_logout_interface()
    
    config = auth_manager.get_current_config()
    print(f"🔧 DEBUG: Returning config for user: {config.username if config else 'None'}")
    return config