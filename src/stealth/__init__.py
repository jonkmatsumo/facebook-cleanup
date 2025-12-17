"""
Stealth and anti-detection modules.
"""
from src.stealth.fingerprint import (
    create_stealth_context,
    apply_stealth_patches,
    get_browser_args,
    get_context_options
)

__all__ = [
    'create_stealth_context',
    'apply_stealth_patches',
    'get_browser_args',
    'get_context_options'
]

