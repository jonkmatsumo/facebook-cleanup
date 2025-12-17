"""
Configuration constants for Facebook cleanup project.
"""
import os
from pathlib import Path

# Base directory (project root)
BASE_DIR = Path(__file__).parent.parent

# Rate Limiting
MAX_DELETIONS_PER_HOUR = 50
MEAN_DELAY_SECONDS = 5.0
DELAY_STD_DEV = 1.5
MIN_DELAY_SECONDS = 2.0

# Target Date
TARGET_YEAR = 2021  # Delete everything before this year
START_YEAR = 2020  # Start from this year and go backwards

# Safety
BLOCK_WAIT_HOURS = 24
BACKOFF_MULTIPLIER = 1.5

# Interface
TARGET_INTERFACE = "mbasic"  # Always use mbasic
USER_AGENT = "Mozilla/5.0 (Linux; U; Android 4.4.2; en-us; SCH-I535 Build/KOT49H) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30"

# Content Types
TARGET_CATEGORIES = [
    "cluster_11",   # Posts
    "cluster_116", # Comments
    "cluster_15"   # Likes/Reactions
]

# Paths (relative to BASE_DIR)
COOKIES_PATH = BASE_DIR / "data" / "cookies.json"
PROGRESS_PATH = BASE_DIR / "data" / "progress.json"
LOG_DIR = BASE_DIR / "data" / "logs"

# Environment Variables (with defaults)
FACEBOOK_USERNAME = os.getenv("FACEBOOK_USERNAME", "")
FACEBOOK_COOKIES_PATH = os.getenv("FACEBOOK_COOKIES_PATH", str(COOKIES_PATH))
FACEBOOK_PROGRESS_PATH = os.getenv("FACEBOOK_PROGRESS_PATH", str(PROGRESS_PATH))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"

# Ensure data directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)

