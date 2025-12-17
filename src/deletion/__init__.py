"""
Deletion handlers and orchestration engine.
"""
from src.deletion.deletion_engine import DeletionEngine
from src.deletion.handlers import (
    CommentDeletionHandler,
    DeletionHandler,
    PostDeletionHandler,
    ReactionRemovalHandler,
    get_all_handlers,
)
from src.deletion.item_extractor import ItemExtractor
from src.deletion.trash_cleanup import TrashCleanup

__all__ = [
    "DeletionEngine",
    "ItemExtractor",
    "TrashCleanup",
    "DeletionHandler",
    "PostDeletionHandler",
    "CommentDeletionHandler",
    "ReactionRemovalHandler",
    "get_all_handlers",
]
