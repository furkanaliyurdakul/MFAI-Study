#!/usr/bin/env python3
"""Auto-deploy: Copy SQL to clipboard and show instructions"""

import subprocess
from pathlib import Path


def copy_file_to_clipboard(filepath):
    """Copy file contents to clipboard"""
    try:
        content = Path(filepath).read_text()
        p = subprocess.Popen(['clip'], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        p.communicate(content.encode('utf-8'))
        return True
    except:
        return False


def main():
    print("\n" + "="*70)
    print("AUTO-DEPLOY: COPY & PASTE TO SUPABASE")
    print("="*70)
    print("\nExecution order (do NOT skip, NOT in parallel):\n")
    
    steps = [1, 2, 3]
    
    for step in steps:
        filepath = Path.cwd() / "output" / f"STEP_{step}.sql"
        size = filepath.stat().st_size if filepath.exists() else 0
        
        print(f"\n▶️  STEP {step} ({size} bytes)")
        print(f"    File: output/STEP_{step}.sql")
        
        if not filepath.exists():
            print(f"    ❌ File missing!")
            continue
        
        print(f"\n    1. File ready to copy")
        
        if copy_file_to_clipboard(str(filepath)):
            print(f"    ✅ COPIED TO CLIPBOARD")
            print(f"\n    2. Go to Supabase:")
            print(f"       https://supabase.com/dashboard")
            print(f"\n    3. Select project → SQL Editor → New Query")
            print(f"\n    4. Paste (Ctrl+V) the SQL")
            print(f"\n    5. Click RUN")
            print(f"\n    6. Click SAVE (name it: STEP_{step})")
        else:
            print(f"    📋 Cannot auto-copy - manually open file")
        
        if step < 3:
            input(f"\n    Press Enter after STEP {step} is SAVED...")
        else:
            input(f"\n    Press Enter after STEP {step} is SAVED...")
    
    print("\n" + "="*70)
    print("✅ ALL STEPS DEPLOYED")
    print("="*70)
    print("\nVerify deployment:")
    print("  python tools/verify_deployment.py\n")


if __name__ == "__main__":
    main()
