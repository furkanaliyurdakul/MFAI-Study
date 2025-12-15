# SPDX-License-Identifier: MIT
"""Platform constants - single source of truth for configuration values.

This module centralizes all platform constants to ensure consistency across
the multilingual fairness study platform.
"""

import re

# ── Language Configuration ──────────────────────────────────────────────
# Supported language codes for the multilingual fairness study
LANGUAGE_CODES = {
    "en": "en",  # English
    "de": "de",  # German
    "nl": "nl",  # Dutch
    "tr": "tr",  # Turkish
    "sq": "sq",  # Albanian
    "hi": "hi",  # Hindi
}

# ── Page Keys ───────────────────────────────────────────────────────────
# Canonical page identifiers used throughout the platform
PAGE_KEYS = (
    "login",
    "home",
    "profile_survey",
    "learning",
    "knowledge_test",
    "ueq_survey",
    "completion",
)

# ── Slide File Pattern ──────────────────────────────────────────────────
# Regular expression to extract slide numbers from filenames
# Matches: Slide_001.png, Slide_023.png, etc.
# Use with: SLIDE_FILENAME_RE.search(path.stem).group(1)
SLIDE_FILENAME_RE = re.compile(r"Slide_(\d+)$")  # match stem (without .png)

# ── Analytics Filenames (Canonical) ─────────────────────────────────────
# Standard filenames for analytics and test result files
KNOWLEDGE_JSON = "knowledge_test_results.json"
UEQ_JSON = "ueq_responses.json"
EXPERIMENT_META = "experiment_meta.json"
INTERACTION_COUNTS = "interaction_counts.json"
PAGE_DURATIONS = "page_durations.json"
FINAL_ANALYTICS = "final_analytics.json"

# ── Interaction Types ───────────────────────────────────────────────────
# Canonical interaction type identifiers for logging
INTERACTION_SLIDE = "slide_explanation"  # User-requested slide explanation
INTERACTION_CHAT = "manual_chat"         # User manual chat input
INTERACTION_PRIME = "prime_context"      # System context initialization
