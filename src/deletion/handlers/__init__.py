"""
Deletion handlers registry.
"""
from src.deletion.handlers.base_handler import DeletionHandler
from src.deletion.handlers.comment_handler import CommentDeletionHandler
from src.deletion.handlers.post_handler import PostDeletionHandler
from src.deletion.handlers.reaction_handler import ReactionRemovalHandler
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Registry of all handlers
_registered_handlers: list[DeletionHandler] = []


def get_all_handlers() -> list[DeletionHandler]:
    """
    Get list of all registered deletion handlers.

    Returns:
        List of DeletionHandler instances
    """
    if not _registered_handlers:
        # Initialize default handlers
        _registered_handlers.extend(
            [
                PostDeletionHandler(),
                CommentDeletionHandler(),
                ReactionRemovalHandler(),
            ]
        )
        logger.debug(f"Initialized {len(_registered_handlers)} default handlers")

    return _registered_handlers.copy()


def register_handler(handler: DeletionHandler) -> None:
    """
    Register a custom deletion handler.

    Args:
        handler: DeletionHandler instance to register
    """
    if handler not in _registered_handlers:
        _registered_handlers.append(handler)
        logger.info(f"Registered custom handler: {type(handler).__name__}")
    else:
        logger.debug(f"Handler already registered: {type(handler).__name__}")


def clear_handlers() -> None:
    """Clear all registered handlers (useful for testing)."""
    _registered_handlers.clear()
    logger.debug("Cleared all handlers")


__all__ = [
    "DeletionHandler",
    "PostDeletionHandler",
    "CommentDeletionHandler",
    "ReactionRemovalHandler",
    "get_all_handlers",
    "register_handler",
    "clear_handlers",
]
