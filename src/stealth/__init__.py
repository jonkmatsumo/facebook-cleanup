"""
Stealth and anti-detection modules.
"""
from src.stealth.behavior import human_delay, micro_pause, wait_before_action
from src.stealth.fingerprint import (
    apply_stealth_patches,
    create_stealth_context,
    get_browser_args,
    get_context_options,
)

__all__ = [
    "create_stealth_context",
    "apply_stealth_patches",
    "get_browser_args",
    "get_context_options",
    "human_delay",
    "wait_before_action",
    "micro_pause",
]
