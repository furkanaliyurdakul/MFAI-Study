# Data Loss Prevention Implementation Checklist

## Phase 1: Setup (Database & Configuration)

- [ ] **Create Supabase Table**
  ```sql
  CREATE TABLE session_checkpoints (
    id serial primary key,
    session_id text not null,
    stage text not null,
    checkpoint_data jsonb not null,
    saved_at timestamp not null,
    created_at timestamp default now()
  );
  
  CREATE INDEX idx_session_checkpoint 
  ON session_checkpoints(session_id, stage);
  ```
  *(Optional table for recovered_data_backup for emergency recovery)*

- [ ] **Verify Supabase service_key permissions**
  - Need INSERT on session_checkpoints
  - Need SELECT for recovery detection

- [ ] **Migrate existing sessions to use Supabase**
  - Run emergency recovery scan to assess existing data
  - Backup output directory before changes

## Phase 2: Code Integration

### Step 1: Add to main.py (Imports)
- [ ] Add imports for all 4 new modules at top of main.py
  ```python
  from checkpoint_manager import CheckpointManager
  from session_recovery_detector import SessionRecoveryDetector
  from continuous_backup_manager import get_continuous_backup_manager
  from recovery_utils import (...)
  ```

### Step 2: Session State Initialization
- [ ] Add manager initialization in `ensure_session_state_initialized()`
  ```python
  if "checkpoint_manager" not in st.session_state:
      # Initialize all three managers
  ```

### Step 3: Recovery Prompt (Login)
- [ ] Add recovery detection after `require_authentication()`
  ```python
  if credential_config and "language_code" in st.session_state:
      recovery_choice = show_recovery_prompt(...)
  ```

### Step 4: Add Checkpoints (4 Places)

After each page completion, add:

- [ ] **Profile Survey** (after `st.session_state.profile_completed = True`)
  ```python
  checkpoint_manager.create_checkpoint(
      stage="profile",
      data={...},
      upload_to_cloud=True
  )
  ```

- [ ] **Learning Session** (after `st.session_state.learning_completed = True`)
  ```python
  checkpoint_manager.create_checkpoint(
      stage="learning",
      data={...},
      upload_to_cloud=False
  )
  ```

- [ ] **Knowledge Test** (after `st.session_state.test_completed = True`)
  ```python
  checkpoint_manager.create_checkpoint(
      stage="knowledge_test",
      data={...},
      upload_to_cloud=False
  )
  ```

- [ ] **UEQ Survey** (after `st.session_state.ueq_completed = True`)
  ```python
  checkpoint_manager.create_checkpoint(
      stage="ueq",
      data={...},
      upload_to_cloud=False
  )
  ```

### Step 5: Cleanup Handler
- [ ] Modify `atexit` handlers to stop backup manager
  ```python
  backup_manager.stop_periodic_backup()
  backup_manager.force_backup_now()  # Final backup
  ```

## Phase 3: Testing

### Manual Testing
- [ ] **Test 1: Normal Flow**
  - [ ] Start session, complete profile
  - [ ] Check: profile_checkpoint.json exists in checkpoints/
  - [ ] Check: Data can be read from checkpoint
  
- [ ] **Test 2: Abandonment & Recovery**
  - [ ] Start session, complete profile, close browser
  - [ ] Login again with same language
  - [ ] Should see recovery prompt
  - [ ] Click "Resume"
  - [ ] Should skip profile, go to learning
  
- [ ] **Test 3: Crash Recovery**
  - [ ] Start learning session
  - [ ] Manually delete profile_checkpoint.json
  - [ ] Wait for continuous backup (5 min)
  - [ ] Restore from cloud backup using emergency_recovery.py
  - [ ] Verify checkpoint restored

- [ ] **Test 4: Continuous Backup**
  - [ ] Enable DEBUG_MODE
  - [ ] Add "Force Backup" button in sidebar
  - [ ] Verify backup runs without errors
  - [ ] Check backup_manager.get_backup_status()

### Automated Testing (pytest)
```bash
# Would add unit tests for:
pytest tests/test_checkpoint_manager.py
pytest tests/test_session_recovery_detector.py
pytest tests/test_continuous_backup.py
pytest tests/test_recovery_utils.py
```

## Phase 4: Deployment

- [ ] **Pre-deployment**
  - [ ] Run emergency_recovery.py --scan-only on production backup
  - [ ] Generate recovery report
  - [ ] Review any incomplete sessions

- [ ] **Deployment Steps**
  1. [ ] Copy new modules to production server
  2. [ ] Update main.py with all integration points
  3. [ ] Test in dev/staging environment first
  4. [ ] Create Supabase table
  5. [ ] Deploy to production during maintenance window

- [ ] **Post-deployment Verification**
  - [ ] Test full session completion flow
  - [ ] Check Supabase table has data
  - [ ] Monitor logs for backup errors
  - [ ] Verify recovery detector works on next login

## Phase 5: Monitoring & Maintenance

- [ ] **Monitor First Week**
  - [ ] Check recovery_logs for any errors
  - [ ] Review session_checkpoints table growth
  - [ ] Monitor backup thread for crashes
  - [ ] Track recovery success rate

- [ ] **Ongoing Maintenance**
  - [ ] Archive old checkpoints monthly (older than 90 days)
  - [ ] Review recovery metrics for improvements
  - [ ] Update checkpoint_manager based on feedback
  - [ ] Adjust backup interval if needed

- [ ] **Document**
  - [ ] Add data loss prevention to deployment guide
  - [ ] Train team on emergency recovery procedures
  - [ ] Create runbook for recovery operations

## Phase 6: Performance Optimization

- [ ] **Monitor Resource Usage**
  - [ ] Check disk space for local_backups/
  - [ ] Monitor Supabase storage quota
  - [ ] Check CPU/memory of backup thread

- [ ] **Adjustments** (if needed)
  - [ ] Increase backup interval if too frequent
  - [ ] Reduce checkpoint history if disk space issue
  - [ ] Compress old backups if needed

## Rollback Plan (If Issues)

If problems arise after deployment:

1. [ ] Stop continuous backup: Edit main.py, disable `start_periodic_backup()`
2. [ ] Disable recovery UI: Comment out `show_recovery_prompt()` 
3. [ ] Fall back to manual checkpoints only (local save still works)
4. [ ] Use emergency_recovery.py to recover any missed data
5. [ ] Deploy fix and re-enable

## Estimated Timeline

- **Setup**: 15 min (Supabase table)
- **Integration**: 1-2 hours (modify main.py)
- **Testing**: 1-2 hours (manual tests)
- **Deployment**: 30 min (deploy code + verify)
- **Monitoring**: Ongoing (first week)

**Total: ~4-5 hours from start to production**

## Support & Troubleshooting

If checkpoint not saving:
1. Check checkpoint_dir exists: `Path(session_dir) / "checkpoints"`
2. Check file permissions
3. Verify CheckpointManager initialized
4. Check logs for exceptions

If recovery not appearing:
1. Verify credentials_folder matches directory name
2. Check incomplete session exists
3. Verify recovery_detector initialized
4. Check language_code matches

If cloud upload failing:
1. Verify Supabase connection
2. Check session_checkpoints table exists  
3. Review Supabase error logs
4. Fallback to local backup (still safe)

## Questions to Answer

- [ ] What backup interval is appropriate? (default: 5 min)
- [ ] How long to keep recovery memory? (default: 24 hours)
- [ ] Should all stages force-upload or only important ones? (default: profile only)
- [ ] Need to add disk space limits? (will need to discuss based on user count)

## Final Checklist for Production

- [ ] All imports added ✓
- [ ] All 3 managers initialized ✓
- [ ] Recovery prompt implemented ✓
- [ ] 4 checkpoints added (profile, learning, test, ueq) ✓
- [ ] Cleanup handlers updated ✓
- [ ] Manual testing passed ✓
- [ ] Supabase table created ✓
- [ ] Backup interval appropriate ✓
- [ ] Logging configured ✓
- [ ] Documentation updated ✓
- [ ] Team trained ✓
- [ ] Deployment plan ready ✓
- [ ] Rollback plan ready ✓
