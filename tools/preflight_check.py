"""Preflight check script for multilingual fairness study platform.

Run before each pilot session to validate environment, dependencies, and configuration.
Exit code 0 = all checks passed, 1 = issues found.

Usage:
    python tools/preflight_check.py
"""

import sys
import os
import json
import importlib
import pathlib
import hashlib

REQUIRED = {
    "streamlit": "1.39.0",
    "pandas": "2.2.3",
    "numpy": "2.1.2",
    "Pillow": "10.4.0",
    "google-genai": "1.3.0",
    "supabase": "2.6.0",
    "langid": "1.1.6",
}

def _ok(msg): print(f"✅ {msg}")
def _warn(msg): print(f"⚠️  {msg}")
def _err(msg): print(f"❌ {msg}")

def check_python():
    """Verify Python version >= 3.10"""
    maj, minv = sys.version_info[:2]
    if (maj, minv) < (3, 10):
        _err(f"Python >=3.10 required, found {maj}.{minv}")
        return False
    _ok(f"Python {maj}.{minv}")
    return True

def check_packages():
    """Verify all required packages are installed with correct versions"""
    ok = True
    try:
        import pkg_resources
    except Exception:
        _warn("pkg_resources missing; skipping version checks")
        return True
    
    installed = {d.project_name.lower(): d.version for d in pkg_resources.working_set}
    for name, ver in REQUIRED.items():
        key = name.lower()
        if key not in installed:
            _err(f"Package missing: {name}=={ver}")
            ok = False
            continue
        if installed[key] != ver:
            _warn(f"{name} version {installed[key]} != pinned {ver}")
        else:
            _ok(f"{name}=={ver}")
    return ok

def check_keys_and_env():
    """Verify API keys and environment variables are configured"""
    ok = True
    # Streamlit secrets OR env
    api_key = os.getenv("GEMINI_API_KEY")
    secrets_toml = pathlib.Path(".streamlit/secrets.toml")
    if not api_key and not secrets_toml.exists():
        _err("No GEMINI_API_KEY and no .streamlit/secrets.toml with [google].api_key")
        ok = False
    else:
        _ok("Gemini API key source present (env or secrets.toml)")

    for var in ["SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_BUCKET"]:
        if not os.getenv(var):
            _warn(f"{var} not set (only needed for cloud mirror)")
        else:
            _ok(f"{var} is set")
    return ok

def check_content_paths():
    """Verify course content (slides, transcript) exists"""
    try:
        import config  # your module
        paths = config.get_file_paths()
        slides_dir = pathlib.Path(paths["slides_dir"])
        transcript = pathlib.Path(paths["transcription_file"])
        ok = True
        if not slides_dir.exists():
            _err(f"Slides dir missing: {slides_dir}")
            ok = False
        else:
            _ok(f"Slides dir OK: {slides_dir}")
        if not transcript.exists():
            _err(f"Transcript missing: {transcript}")
            ok = False
        else:
            _ok(f"Transcript OK: {transcript}")
        return ok
    except Exception as e:
        _err(f"config.get_file_paths() check failed: {e}")
        return False

def try_import_gemini():
    """Test google.genai import"""
    try:
        import google.genai as genai  # new SDK
        _ok("google.genai import OK")
        return True
    except Exception as e:
        _err(f"google.genai import failed: {e}")
        return False

def check_langid():
    """Test langid language detection"""
    try:
        import langid
        code, score = langid.classify("This is a short English test sentence.")
        _ok(f"langid OK (sample -> {code}, {score:.2f})")
        return True
    except Exception as e:
        _err(f"langid failed: {e}")
        return False

def main():
    """Run all preflight checks and report results"""
    sections = [
        ("Python", check_python),
        ("Packages", check_packages),
        ("Keys/Env", check_keys_and_env),
        ("Content paths", check_content_paths),
        ("Gemini SDK", try_import_gemini),
        ("langid", check_langid),
    ]
    overall = True
    print("=== Preflight Check ===")
    for title, fn in sections:
        print(f"\n-- {title} --")
        ok = fn()
        overall = overall and ok
    print("\nResult:", "✅ ALL GOOD" if overall else "❌ FIX ISSUES ABOVE")
    sys.exit(0 if overall else 1)

if __name__ == "__main__":
    main()
