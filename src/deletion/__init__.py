"""
Deletion handlers and orchestration engine.
"""
from src.deletion.deletion_engine import DeletionEngine
from src.deletion.item_extractor import ItemExtractor
from src.deletion.handlers import (
    DeletionHandler,
    PostDeletionHandler,
    CommentDeletionHandler,
    ReactionRemovalHandler,
    get_all_handlers,
)

__all__ = [
    'DeletionEngine',
    'ItemExtractor',
    'DeletionHandler',
    'PostDeletionHandler',
    'CommentDeletionHandler',
    'ReactionRemovalHandler',
    'get_all_handlers',
]

