"""
Item extractor for parsing Activity Log pages and extracting deletable items.
"""
from typing import Optional, List
from datetime import datetime
from playwright.sync_api import Page, Locator
from src.traversal.date_parser import DateParser
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ItemExtractor:
    """Extracts deletable items from Activity Log pages."""
    
    def __init__(self, target_date: datetime):
        """
        Initialize ItemExtractor.
        
        Args:
            target_date: Date threshold - only extract items before this date
        """
        self.target_date = target_date
        self.date_parser = DateParser()
    
    def extract_items(self, page: Page) -> List[dict]:
        """
        Extract all deletable items from current page.
        
        Args:
            page: Playwright Page object
        
        Returns:
            List of item dictionaries
        """
        items = []
        
        try:
            # Wait for page to be ready
            page.wait_for_load_state('domcontentloaded', timeout=10000)
            
            # Find all potential activity items
            # Activity items on mbasic are typically in divs or articles
            item_selectors = [
                'div[role="article"]',
                'article',
                'div[id*="story"]',
                'div[class*="story"]',
                # Generic divs that might contain activity items
                'div > div > div',  # Nested divs (common structure)
            ]
            
            all_elements = []
            for selector in item_selectors:
                try:
                    locators = page.locator(selector).all()
                    all_elements.extend(locators)
                    if locators:
                        logger.debug(f"Found {len(locators)} elements with selector: {selector}")
                        break  # Use first selector that finds elements
                except Exception as e:
                    logger.debug(f"Selector '{selector}' failed: {e}")
                    continue
            
            if not all_elements:
                logger.warning("No activity items found on page")
                return items
            
            # Parse each element
            for element in all_elements:
                try:
                    item = self._parse_activity_item(element)
                    if item and self._is_deletable(item):
                        # Check if item is before target date
                        if item.get('date_parsed'):
                            if item['date_parsed'] < self.target_date:
                                items.append(item)
                            else:
                                logger.debug(f"Skipping item after target date: {item.get('date_string')}")
                        else:
                            # If date can't be parsed, include it (let handler decide)
                            logger.debug("Including item with unparseable date")
                            items.append(item)
                except Exception as e:
                    logger.debug(f"Error parsing item: {e}")
                    continue
            
            logger.info(f"Extracted {len(items)} deletable items from page")
            return items
        
        except Exception as e:
            logger.error(f"Error extracting items from page: {e}")
            return items
    
    def _parse_activity_item(self, element: Locator) -> Optional[dict]:
        """
        Parse a single activity item from DOM element.
        
        Args:
            element: Playwright Locator for the item element
        
        Returns:
            Item dictionary or None if parsing fails
        """
        try:
            # Extract date
            date_string = self._extract_date(element)
            
            # Parse date
            date_parsed = None
            if date_string:
                date_parsed = self.date_parser.parse_facebook_date(date_string)
            
            # Determine item type
            item_type = self._determine_item_type(element)
            
            # Find delete/unlike link
            delete_link = self._find_delete_link(element)
            
            # Extract item ID if available
            item_id = self._extract_item_id(element)
            
            if not item_type:
                logger.debug("Could not determine item type")
                return None
            
            return {
                'type': item_type,
                'date_string': date_string,
                'date_parsed': date_parsed,
                'delete_link': delete_link,
                'item_id': item_id,
                'element': element,
            }
        
        except Exception as e:
            logger.debug(f"Error parsing activity item: {e}")
            return None
    
    def _extract_date(self, element: Locator) -> Optional[str]:
        """
        Extract date string from activity item.
        
        Args:
            element: Locator for the item element
        
        Returns:
            Date string or None
        """
        # Common date selectors on mbasic
        date_selectors = [
            'abbr[title]',  # Facebook often uses abbr with title attribute
            'abbr',
            'time',
            'span[title*="20"]',  # Year in title
            # Look for text patterns that might be dates
        ]
        
        for selector in date_selectors:
            try:
                date_elem = element.locator(selector).first
                if date_elem.count() > 0:
                    # Try title attribute first (most reliable)
                    title = date_elem.get_attribute('title')
                    if title:
                        return title
                    
                    # Try text content
                    text = date_elem.text_content()
                    if text and text.strip():
                        return text.strip()
            except Exception:
                continue
        
        # Fallback: look for date-like text in the element
        try:
            text = element.text_content()
            if text:
                # Look for common date patterns
                import re
                # Patterns like "November 3, 2020" or "2 years ago"
                date_patterns = [
                    r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}',
                    r'\d{1,2}\s+(years?|months?|days?|hours?)\s+ago',
                    r'(Today|Yesterday)',
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        return match.group(0)
        except Exception:
            pass
        
        return None
    
    def _determine_item_type(self, element: Locator) -> Optional[str]:
        """
        Determine the type of activity item (post, comment, reaction).
        
        Args:
            element: Locator for the item element
        
        Returns:
            Item type string or None
        """
        try:
            text = element.text_content().lower() if element.text_content() else ""
            
            # Check for reaction indicators
            reaction_indicators = ['liked', 'reacted', 'unlike', 'remove reaction']
            if any(indicator in text for indicator in reaction_indicators):
                return 'reaction'
            
            # Check for comment indicators
            comment_indicators = ['commented', 'comment', 'view context']
            if any(indicator in text for indicator in comment_indicators):
                return 'comment'
            
            # Check for post indicators or default to post
            post_indicators = ['posted', 'shared', 'created a post']
            if any(indicator in text for indicator in post_indicators):
                return 'post'
            
            # Default: assume post if delete link exists
            if self._find_delete_link(element):
                return 'post'
            
            return None
        
        except Exception:
            return None
    
    def _find_delete_link(self, element: Locator) -> Optional[Locator]:
        """
        Find delete/unlike link within item element.
        
        Args:
            element: Locator for the item element
        
        Returns:
            Locator for delete link or None
        """
        delete_selectors = [
            'a:has-text("Delete")',
            'a:has-text("Remove")',
            'a:has-text("Unlike")',
            'a:has-text("Remove reaction")',
            'a[href*="delete"]',
            'a[href*="remove"]',
            'a[href*="unlike"]',
            'button:has-text("Delete")',
        ]
        
        for selector in delete_selectors:
            try:
                link = element.locator(selector).first
                if link.count() > 0 and link.is_visible():
                    return link
            except Exception:
                continue
        
        return None
    
    def _extract_item_id(self, element: Locator) -> Optional[str]:
        """
        Extract item ID from element if available.
        
        Args:
            element: Locator for the item element
        
        Returns:
            Item ID string or None
        """
        try:
            # Try ID attribute
            item_id = element.get_attribute('id')
            if item_id:
                return item_id
            
            # Try data attributes
            data_id = element.get_attribute('data-id')
            if data_id:
                return data_id
            
            # Try extracting from href if delete link exists
            delete_link = self._find_delete_link(element)
            if delete_link:
                href = delete_link.get_attribute('href')
                if href:
                    # Extract ID from URL if present
                    import re
                    match = re.search(r'[?&]id=(\d+)', href)
                    if match:
                        return match.group(1)
        
        except Exception:
            pass
        
        return None
    
    def _is_deletable(self, item: dict) -> bool:
        """
        Check if item can be deleted.
        
        Args:
            item: Item dictionary
        
        Returns:
            True if item appears deletable, False otherwise
        """
        # Must have a type
        if not item.get('type'):
            return False
        
        # Must have either a delete link or be a reaction (which may have unlike link)
        if not item.get('delete_link') and item.get('type') != 'reaction':
            return False
        
        return True

