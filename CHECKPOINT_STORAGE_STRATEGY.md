# Checkpoint Storage Strategy - Limited Cloud Resources

## Problem
Checkpoints can accumulate storage quickly on limited cloud plans:
- Learning interactions can be 100 KB - 1 MB each
- Multiple checkpoints per session (after each stage)
- Continuous backups every 5 minutes = rapid multiplication
- Many concurrent users = large total storage footprint

## Solution: Smart Backup Strategy

### Storage Tiers

**Tier 1: Local Filesystem (All Checkpoints)**
- Location: `output/{cohort}/{session}/checkpoints/`
- Files: All stage checkpoints (profile, learning, test, UEQ)
- Frequency: Continuously (as user completes stages)
- Size: Full data preserved
- Cost: Free (your server disk space)
- Recovery: Instant (if server available)

**Tier 2: Local Backup Directory (Periodic)**
- Location: `output/{cohort}/{session}/local_backups/`
- Frequency: Every 5 minutes (background thread)
- Files: Full checkpoint copies
- Size: Duplicates of Tier 1 (filesystem-level redundancy)
- Cost: Free (your server disk space)
- Recovery: Fallback if Tier 1 corrupted

**Tier 3: Cloud Database (On Completion Only)**
- Location: Supabase `session_checkpoints` table
- Frequency: Only on page completion (not every 5 min!)
- Files: Final checkpoints for each stage
- Size: ~50-100 KB per session (compression via JSONB)
- Cost: Minimal Supabase storage usage
- Recovery: Available if server crashed

### How It Works

**During Session (No Cloud Upload):**
```
User completes page
  ↓
Local checkpoint created
  ↓
5-minute background backup
  ↓
Copies checkpoint locally (Tier 2)
  ↓
NO cloud upload yet
```

**On Session Completion (Cloud Upload):**
```
User completes final stage
  ↓
Force backup triggered
  ↓
ALL checkpoints uploaded to Supabase
  ↓
Cloud now has final session data
```

**On Crash Before Completion:**
```
Session abandoned
  ↓
User logs in again
  ↓
Recovery detector finds incomplete session
  ↓
Loads from local Tier 1/2 checkpoints
  ↓
Session fully restored
```

## Storage Estimates

### Per Session
- Profile checkpoint: ~20 KB
- Learning checkpoint: ~200-500 KB (depends on chat length)
- Test checkpoint: ~30 KB
- UEQ checkpoint: ~15 KB
- **Total per session: ~300-600 KB**

### Cloud Storage (Supabase)
- **Periodic backups:** 0 KB (disabled for limited resources)
- **On completion:** ~300-600 KB per session
- **For 100 completed sessions:** ~30-60 MB

### Server Storage (Local)
- Same data stored locally (filesystem is typically cheap/unlimited)
- **For 100 sessions:** ~30-60 MB

## Configuration

### To Reduce Cloud Storage Further

**Option 1: Only Use Local (Recommended)**
```python
# In main.py, don't call force_backup_now() on completion
# Just let local backups handle it
# If server crashes, recovery still works locally
```

**Option 2: Compress Before Upload**
```python
# Add gzip compression before storing in Supabase
checkpoint_data_compressed = gzip.compress(
    json.dumps(checkpoint_data).encode()
)
# Uploads ~3x smaller
```

**Option 3: Cleanup Old Sessions**
```python
# Add cleanup script to delete checkpoints older than 30 days
# Run daily to save space
```

## What's Protected?

✅ **Protected (No Data Loss):**
- User completes survey → immediately saved locally → recovered
- User completes interview → immediately backup → recovered if crash
- Server crashes → full recovery from local filesystem

✅ **Semi-Protected (Can Recover):**
- Cloud database corrupted → recover from local backups
- Server disk corrupted → recover from Supabase cloud

❌ **At Risk:**
- Both local AND cloud corrupted simultaneously → unrecoverable
  (But this is extremely unlikely)

## Recommendations

1. **For Hackathon/Short Study:**
   - Use current setup (Tier 1 + 2 only, no cloud uploads)
   - Zero cloud storage cost
   - Full recovery capability
   - ✅ Recommended

2. **For Long-Term Production:**
   - Enable cloud uploads (force_backup_now() on completion)
   - Costs ~30-100 MB per 100 sessions
   - Adds redundancy for critical data
   - ✅ Worth it

3. **For Unlimited Storage:**
   - Keep current setup (everything uploaded)
   - Maximum redundancy
   - Can disable background backups if needed

## Monitor Storage Usage

Check storage with:
```bash
# Local checkpoint size
du -sh output/

# Cloud checkpoint size (Supabase dashboard)
# → Tables → session_checkpoints → Storage info
```

## Summary

**Current Configuration:**
- ✅ Local backups only (periodic)
- ✅ Cloud uploads on completion only
- ✅ Minimal Supabase storage cost
- ✅ Full data recovery capability
- ✅ Optimized for limited cloud resources
