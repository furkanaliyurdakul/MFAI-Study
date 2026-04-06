# Data Loss Prevention Integration Guide

## Overview

This guide explains how to integrate the new data loss prevention systems into your Gemini_UI application.

**Components Created:**
1. `checkpoint_manager.py` - Saves session progress at each stage
2. `session_recovery_detector.py` - Detects abandoned sessions
3. `continuous_backup_manager.py` - Periodically uploads to cloud
4. `recovery_utils.py` - UI helpers for recovery

## Integration Steps

### Step 1: Add Imports to main.py

Add these imports near the top of main.py (after existing imports):

```python
from checkpoint_manager import CheckpointManager
from session_recovery_detector import SessionRecoveryDetector
from continuous_backup_manager import get_continuous_backup_manager
from recovery_utils import (
    show_recovery_prompt,
    apply_recovered_data,
    show_recovery_banner,
    log_recovery_event,
    initialize_recovery_in_session_state,
)
```

### Step 2: Initialize Managers in Session State

In the `ensure_session_state_initialized()` function or after session setup, add:

```python
# Recovery managers (initialize once per session)
if "checkpoint_manager" not in st.session_state:
    sm = get_session_manager()
    from supabase_storage import get_supabase_storage
    storage = get_supabase_storage()
    
    st.session_state.checkpoint_manager = CheckpointManager(sm, storage.supabase if storage.connected else None)
    st.session_state.recovery_detector = SessionRecoveryDetector(sm, storage.supabase if storage.connected else None)
    st.session_state.backup_manager = get_continuous_backup_manager(sm, storage.supabase if storage.connected else None)
    
    # Start periodic backups
    st.session_state.backup_manager.start_periodic_backup()
    
    initialize_recovery_in_session_state()
```

### Step 3: Add Recovery Prompt After Login

In your authentication section (after `require_authentication()` and before page rendering), add:

```python
# Check for abandoned sessions that can be recovered
if credential_config and "language_code" in st.session_state:
    detector = st.session_state.get("recovery_detector")
    if detector:
        recovery_choice = show_recovery_prompt(
            detector,
            credential_config.folder_prefix,
            st.session_state["language_code"]
        )
        
        if recovery_choice is True:  # User chose to resume
            recovered_session = st.session_state.get("_recovery_session")
            if recovered_session:
                # Load and recover the data
                session_dir = recovered_session["session_dir"]
                recovered_data = detector.recover_session_data(Path(session_dir))
                
                if recovered_data:
                    # Define page callbacks for restoration
                    page_callbacks = {
                        "profile": lambda data: st.session_state.update({"profile_data": data}),
                        "learning": lambda data: st.session_state.update({"learning_messages": data.get("messages", [])}),
                        "knowledge_test": lambda data: st.session_state.update({"test_answers": data}),
                        "ueq": lambda data: st.session_state.update({"ueq_responses": data}),
                    }
                    
                    # Apply recovery
                    restored = apply_recovered_data(recovered_data, st.session_state.checkpoint_manager, page_callbacks)
                    show_recovery_banner(restored)
                    
                    # Log recovery event
                    sm = get_session_manager()
                    log_recovery_event(sm, "user_initiated", {"restored_stages": list(restored.keys())})
                    
                    # Switch session directory to the recovered one
                    st.session_state["session_dir"] = session_dir
```

### Step 4: Save Checkpoints After Each Page

After the user completes each stage, save a checkpoint with all collected data:

#### 4a. Profile Survey Completion

In the profile survey completion section:

```python
if st.session_state.profile_completed:
    # Collect all profile data
    profile_data = {
        "name": st.session_state.get("profile_name"),
        "age": st.session_state.get("profile_age"),
        "education": st.session_state.get("profile_education"),
        # ... other profile fields
    }
    
    # Save checkpoint
    checkpoint_manager = st.session_state.get("checkpoint_manager")
    if checkpoint_manager:
        checkpoint_manager.create_checkpoint(
            stage="profile",
            data=profile_data,
            upload_to_cloud=True  # Immediate cloud upload for important stage
        )
```

#### 4b. Learning Session Completion

After learning_completed is set to True:

```python
if st.session_state.learning_completed:
    # Collect learning data (messages, interaction log, etc.)
    learning_data = {
        "messages": st.session_state.get("messages", []),
        "interaction_count": st.session_state.get("interaction_count", 0),
        "slides_viewed": st.session_state.get("slides_viewed", []),
    }
    
    checkpoint_manager = st.session_state.get("checkpoint_manager")
    if checkpoint_manager:
        checkpoint_manager.create_checkpoint(
            stage="learning",
            data=learning_data,
            upload_to_cloud=False  # Batch upload handled by continuous backup
        )
```

#### 4c. Knowledge Test Completion

After test_completed is set to True:

```python
if st.session_state.test_completed:
    # Collect test data
    test_data = {
        "answers": st.session_state.get("test_answers", {}),
        "score": st.session_state.get("test_score"),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    
    checkpoint_manager = st.session_state.get("checkpoint_manager")
    if checkpoint_manager:
        checkpoint_manager.create_checkpoint(
            stage="knowledge_test",
            data=test_data,
            upload_to_cloud=False
        )
```

#### 4d. UEQ Survey Completion

After ueq_completed is set to True:

```python
if st.session_state.ueq_completed:
    # Collect UEQ data
    ueq_data = {
        "responses": st.session_state.get("ueq_responses", {}),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    
    checkpoint_manager = st.session_state.get("checkpoint_manager")
    if checkpoint_manager:
        checkpoint_manager.create_checkpoint(
            stage="ueq",
            data=ueq_data,
            upload_to_cloud=False
        )
```

### Step 5: Add Continuous Backup (Already Running in Background)

The background thread starts automatically when initialized in Step 2. You can add monitoring in sidebar:

```python
# Optional: Show backup status in sidebar (debug mode)
if DEBUG_MODE:
    with st.sidebar.expander("🔄 Backup Status"):
        backup_manager = st.session_state.get("backup_manager")
        if backup_manager:
            status = backup_manager.get_backup_status()
            st.write(f"Running: {status['running']}")
            st.write(f"Last backup: {status['last_backup_time']}")
            st.write(f"Checkpoints: {status['checkpoints_available']}")
            
            if st.button("⚡ Force Backup Now"):
                success = backup_manager.force_backup_now()
                st.info(f"Backup {'succeeded' if success else 'failed'}")
```

### Step 6: Final Completion with Force Backup

Modify the completion page upload section:

```python
# Before uploading final files, force backup all checkpoints
try:
    backup_manager = st.session_state.get("backup_manager")
    if backup_manager:
        backup_manager.force_backup_now()
        st.info("✓ Final backup completed")
except Exception as e:
    st.warning(f"Final backup failed: {e}")

# Then proceed with existing upload logic
success = storage.upload_session_files(sm, DEV_MODE)
```

### Step 7: Cleanup on Session Exit

Modify the atexit handlers in main.py:

```python
def cleanup_session():
    """Clean up on session exit."""
    try:
        # Save final logs
        get_learning_logger().save_logs(force=True)
        
        # Final checkpoint for incomplete session
        checkpoint_manager = st.session_state.get("checkpoint_manager")
        if checkpoint_manager:
            checkpoint_manager.create_checkpoint(
                stage="exit",
                data={"exit_timestamp": datetime.now(timezone.utc).isoformat()},
                upload_to_cloud=True
            )
        
        # Stop continuous backup
        backup_manager = st.session_state.get("backup_manager")
        if backup_manager:
            backup_manager.force_backup_now()  # Final backup
            backup_manager.stop_periodic_backup()
        
        # Page dump
        page_dump(Path(get_session_manager().session_dir))
    
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

atexit.register(cleanup_session)
```

## Research-Related Logging

### Recovery Event Logging

All recovery events are logged to `{session_dir}/recovery_logs/recovery_events.jsonl` for analysis:

```json
{
  "session_id": "abc123",
  "timestamp": "2026-01-15T10:30:00Z",
  "recovery_type": "user_initiated",
  "success": true,
  "details": {"restored_stages": ["profile", "learning"]}
}
```

### Checkpoint Metadata

Each checkpoint saves metadata:
- `fake_name`: Pseudonymized name
- `language_code`: Language used
- `credentials_folder`: Cohort information
- `timestamp`: When checkpoint was created

## Testing the System

### Manual Testing in Dev Mode

1. **Start a session normally** → Complete profile survey
2. **Check checkpoints**: Look in `output/{date}__{name}/checkpoints/profile_checkpoint.json`
3. **Simulate abandonment**: Close browser without completing the study
4. **Login again**: Should see recovery prompt
5. **Resume session**: Should restore profile data and skip to learning

### Testing Continuous Backup

Add to main.py for testing:

```python
if DEV_MODE and st.sidebar.checkbox("Testing: Trigger Backup"):
    backup_manager = st.session_state.get("backup_manager")
    if backup_manager:
        success = backup_manager.force_backup_now()
        result = backup_manager.get_backup_status()
        st.write(result)
```

## FAQ

**Q: Will this cause performance issues?**
A: No - backups run in background thread. Database operations are batched.

**Q: What if Supabase is down?**
A: Local backups continue. Data syncs to cloud when connection restores.

**Q: Can users restart from the middle?**
A: Yes - recovery allows resuming from any completed stage.

**Q: Does this affect research bias?**
A: No - recovery is optional ("resume" vs "start fresh" choice).

**Q: What data is saved?**
A: User interactions, responses, timestamps, but NOT sensitive profile info (marked as excluded).

## Troubleshooting

**Checkpoints not saving?**
- Check session_dir permissions
- Verify CheckpointManager is initialized
- Look in logs for checkpoint creation errors

**Recovery not appearing?**
- Ensure recovery_detector is initialized
- Check credentials_folder matches directory name
- Verify incomplete session exists in output/

**Continuous backup not working?**
- Check Supabase connection in storage initialization
- Verify table `session_checkpoints` exists in database
- Enable DEBUG_MODE to see backup logs

## Next Steps

1. Integrate all components into main.py
2. Test with dev mode enabled
3. Deploy to production
4. Monitor recovery_logs for usage patterns
5. Adjust backup interval if needed (currently 5 mins)
