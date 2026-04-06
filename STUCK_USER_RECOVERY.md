# Emergency: User Stuck on Blank Page After UEQ Finalize

## ⚠️ IMMEDIATE SITUATION
User is **LIVE on the deployed Streamlit app** and stuck on a blank page after clicking "Finish Interview" on the UEQ survey. Their data is ONLY in the browser session—not saved to Supabase yet.

## 🔴 WHAT JUST HAPPENED
When they clicked "Finish Interview":
1. ✅ The validation checked all 26 questions
2. ✅ The validation checked the feedback comment  
3. ✅ The UEQ scores were calculated
4. ✅ **The data was SAVED to a JSON file** (but only locally to the app's file system)
5. ❌ **THE ERROR:** After saving, `st.rerun()` was called without telling Streamlit to navigate to the completion page
6. ❌ Result: Blank page with confused user

## 🆘 FOR THE STUCK USER (DO THIS NOW)

### Option 1: Make them Refresh (First Try)
Tell them:
> "Can you press **F5** or **Ctrl+R** to refresh the page? This might trigger the navigation logic to move you forward."

If that doesn't work → Option 2

### Option 2: Examine Browser Console (Diagnostic)
Have them:
1. Open **Developer Tools** (F12)
2. Go to **Console** tab
3. Look for red error messages
4. Screenshot any errors and send to you
5. **DO NOT CLOSE THE TAB** - their session is still alive there

### Option 3: Last Resort - Manual Data Extraction
If they still want to proceed without refreshing:
1. Have them open **DevTools → Application → Session Storage**
2. Look for the Streamlit session key that contains `responses`
3. Copy the raw data and save to a text file
4. **Then you can manually create the session JSON if needed**

**But realistically:**  Once you deploy the fix (see below), they can close and reopen the app fresh and try again—their data won't be lost because you'll have properly handled navigation.

---

## 🚀 DEPLOY THE FIX (This is in your code now)

The bug is fixed in `testui_ueqsurvey.py`:
- Added error handling around `save_ueq()` to catch failures
- **CRITICAL FIX:** Changed `st.rerun()` → `st.session_state["current_page"] = "completion"` + `st.rerun()`
- Added console logging so you can debug in the future

### Steps to deploy:
1. **Stage the changes:**
   ```powershell
   git add testui_ueqsurvey.py
   git commit -m "Fix: UEQ survey blank page after finalize - added proper navigation and error handling"
   ```

2. **Push to GitHub:**
   ```powershell
   git push origin main
   ```

3. **Streamlit Cloud should auto-deploy** within 1-2 minutes (check your Streamlit Cloud dashboard)

4. **Tell the stuck user:** "You can now refresh the page and try again—we fixed the issue!"

---

## 📋 FUTURE PREVENTION

The fixes now in place:

### 1. **Better Error Messages**
If something fails during save, user sees:
```
❌ Error saving your responses. Please contact support.
Technical details: [actual error]
```
Instead of a blank page.

### 2. **Proper Navigation**
After successful save, explicitly sets:
```python
st.session_state["current_page"] = "completion"
```
Then reruns—so they **will** see the completion page.

### 3. **Console Logging**
Check your app logs/terminal output:
```
✅ UEQ responses saved to /path/to/ueq_responses.json
```
or
```
❌ ERROR saving UEQ responses: [details]
```

---

## 🔍 HOW TO DEBUG IN THE FUTURE

If this happens again:

1. **Check app logs/terminal** for the error messages (the `print()` statements)
2. **Check if the JSON file was created:**
   ```powershell
   # Look for recent UEQ files in output directories
   Get-ChildItem "output\*_cohort" -Recurse -Filter "ueq_responses.json" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 5
   ```
3. If file exists = data was saved, just a navigation issue
4. If file doesn't exist = database/file system error during save

---

## ✅ CHECKLIST

- [ ] User knows to NOT close their browser tab yet
- [ ] (Optional) Have them check console for error details
- [ ] You've pushed the fix to GitHub  
- [ ] Streamlit Cloud has deployed the fix (check dashboard)
- [ ] Tell user to refresh and try again
- [ ] After they complete, verify JSON file was created in output/*/ueq/ 
- [ ] Moving forward, monitor console logs when users finalize UEQ

---

## 📞 IF THIS STILL DOESN'T WORK

The `save_ueq()` method in `session_manager.py` might be failing. Check:
1. File permissions on the output directory
2. Whether `analytics.sync_ueq()` is throwing an error (this shouldn't stop the save, but check logs)
3. Whether the `ueq_dir` is being created properly

Run:
```powershell
python -c "from session_manager import SessionManager; sm = SessionManager('test_session', 'en'); sm.ueq_dir"
```
to verify the directory path is accessible.
