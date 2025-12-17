"""
Deletion engine for orchestrating item extraction, handler selection, and deletion.
"""
from typing import Optional
from datetime import datetime
from playwright.sync_api import Page
from config import settings
from src.deletion.item_extractor import ItemExtractor
from src.deletion.handlers import get_all_handlers, DeletionHandler
from src.utils.logging import get_logger

logger = get_logger(__name__)


class DeletionEngine:
    """Orchestrates deletion of items from Activity Log pages."""
    
    def __init__(
        self,
        page: Page,
        target_date: Optional[datetime] = None,
        handlers: Optional[list[DeletionHandler]] = None,
        logger_instance=None
    ):
        """
        Initialize DeletionEngine.
        
        Args:
            page: Playwright Page object
            target_date: Date threshold for deletion (defaults to settings.TARGET_YEAR)
            handlers: Optional list of handlers (defaults to all registered handlers)
            logger_instance: Optional logger instance
        """
        self.page = page
        self.target_date = target_date or datetime(settings.TARGET_YEAR, 1, 1)
        self.handlers = handlers or get_all_handlers()
        self.logger = logger_instance or logger
        
        self.item_extractor = ItemExtractor(self.target_date)
        
        self.logger.info(
            f"DeletionEngine initialized with {len(self.handlers)} handlers, "
            f"target_date={self.target_date.date()}"
        )
    
    def process_page(self, page: Optional[Page] = None) -> dict:
        """
        Process all deletable items on the current page.
        
        Args:
            page: Optional Page object (uses self.page if None)
        
        Returns:
            Dictionary with statistics: {'deleted': int, 'failed': int, 'skipped': int, 'errors': list}
        """
        page = page or self.page
        
        stats = {
            'deleted': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        # Extract items from page
        self.logger.info("Extracting items from page...")
        items = self.item_extractor.extract_items(page)
        
        if not items:
            self.logger.info("No deletable items found on page")
            return stats
        
        self.logger.info(f"Found {len(items)} deletable items, processing...")
        
        # Process each item
        for i, item in enumerate(items, 1):
            self.logger.debug(f"Processing item {i}/{len(items)}: {item.get('type')} from {item.get('date_string')}")
            
            result = self.delete_item(page, item)
            
            if result[0]:  # Success
                stats['deleted'] += 1
                self.logger.info(f"Successfully deleted item {i}/{len(items)}")
            else:
                stats['failed'] += 1
                error_msg = result[1]
                stats['errors'].append({
                    'item': item.get('type', 'unknown'),
                    'date': item.get('date_string', 'unknown'),
                    'error': error_msg
                })
                self.logger.warning(f"Failed to delete item {i}/{len(items)}: {error_msg}")
        
        self.logger.info(
            f"Page processing complete: {stats['deleted']} deleted, "
            f"{stats['failed']} failed, {stats['skipped']} skipped"
        )
        
        return stats
    
    def delete_item(self, page: Page, item: dict) -> tuple[bool, str]:
        """
        Delete a single item using the appropriate handler.
        
        Args:
            page: Playwright Page object
            item: Item dictionary to delete
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Select appropriate handler
        handler = self._select_handler(item)
        
        if not handler:
            return False, f"No handler found for item type: {item.get('type')}"
        
        # Execute deletion
        try:
            return handler.delete(page, item)
        except Exception as e:
            self.logger.error(f"Unexpected error during deletion: {e}")
            return False, f"Unexpected error: {str(e)}"
    
    def _select_handler(self, item: dict) -> Optional[DeletionHandler]:
        """
        Select appropriate handler for item.
        
        Args:
            item: Item dictionary
        
        Returns:
            DeletionHandler instance or None if no handler found
        """
        for handler in self.handlers:
            try:
                if handler.can_handle(item):
                    self.logger.debug(f"Selected handler: {type(handler).__name__}")
                    return handler
            except Exception as e:
                self.logger.debug(f"Handler {type(handler).__name__} error in can_handle: {e}")
                continue
        
        return None

