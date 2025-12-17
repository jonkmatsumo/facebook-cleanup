"""
Stealth and anti-detection modules.
"""
from src.stealth.fingerprint import (
    create_stealth_context,
    apply_stealth_patches,
    get_browser_args,
    get_context_options
)
from src.stealth.behavior import (
    human_delay,
    wait_before_action,
    micro_pause
)

__all__ = [
    'create_stealth_context',
    'apply_stealth_patches',
    'get_browser_args',
    'get_context_options',
    'human_delay',
    'wait_before_action',
    'micro_pause',
]

