"""
Date parser for Facebook fuzzy date strings.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, cast

import dateparser  # type: ignore[import-untyped]

from src.utils.logging import get_logger

logger = get_logger(__name__)


class DateParser:
    """Parses fuzzy date strings from Facebook into datetime objects."""

    def __init__(self, default_timezone: Optional[str] = None):
        """
        Initialize DateParser.

        Args:
            default_timezone: Default timezone (e.g., 'UTC', 'America/New_York')
                            If None, uses local timezone
        """
        self.default_timezone = default_timezone

    def parse_facebook_date(
        self, date_string: str, reference_date: Optional[datetime] = None
    ) -> Optional[datetime]:
        """
        Parse a Facebook date string into a datetime object.

        Args:
            date_string: Date string from Facebook (e.g., "2 years ago", "November 3")
            reference_date: Reference date for relative dates (defaults to now)

        Returns:
            Parsed datetime object, or None if parsing fails
        """
        if not date_string or not date_string.strip():
            logger.warning("Empty date string provided")
            return None

        date_string = date_string.strip()

        if reference_date is None:
            reference_date = datetime.now()

        # Try relative date parsing first
        parsed = self._parse_relative_date(date_string, reference_date)
        if parsed is not None:
            return parsed

        # Try absolute date parsing
        parsed = self._parse_absolute_date(date_string, reference_date)
        if parsed is not None:
            return parsed

        # Fallback to dateparser library
        try:
            parsed = dateparser.parse(
                date_string,
                settings={
                    "RELATIVE_BASE": reference_date,
                    "TIMEZONE": self.default_timezone,
                    "PREFER_DATES_FROM": "past",  # Prefer past dates for ambiguous cases
                },
            )
            if parsed:
                logger.debug(f"Parsed '{date_string}' as {parsed}")
                return cast(datetime, parsed)
        except Exception as e:
            logger.debug(f"dateparser failed for '{date_string}': {e}")

        logger.warning(f"Could not parse date string: '{date_string}'")
        return None

    def _parse_relative_date(
        self, date_string: str, reference_date: datetime
    ) -> Optional[datetime]:
        """
        Parse relative dates like "2 years ago", "3 months ago", etc.

        Args:
            date_string: Date string to parse
            reference_date: Reference date for calculation

        Returns:
            Parsed datetime or None
        """
        date_string_lower = date_string.lower()

        # Handle "today"
        if date_string_lower == "today":
            return reference_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Handle "yesterday"
        if date_string_lower == "yesterday":
            yesterday = reference_date - timedelta(days=1)
            return yesterday.replace(hour=0, minute=0, second=0, microsecond=0)

        # Pattern: "X years/months/days ago"
        patterns = [
            (r"(\d+)\s+years?\s+ago", "years"),
            (r"(\d+)\s+months?\s+ago", "months"),
            (r"(\d+)\s+weeks?\s+ago", "weeks"),
            (r"(\d+)\s+days?\s+ago", "days"),
            (r"(\d+)\s+hours?\s+ago", "hours"),
        ]

        for pattern, unit in patterns:
            match = re.search(pattern, date_string_lower)
            if match:
                value = int(match.group(1))

                # Calculate delta
                if unit == "years":
                    delta = timedelta(days=value * 365)  # Approximate
                elif unit == "months":
                    delta = timedelta(days=value * 30)  # Approximate
                elif unit == "weeks":
                    delta = timedelta(weeks=value)
                elif unit == "days":
                    delta = timedelta(days=value)
                elif unit == "hours":
                    delta = timedelta(hours=value)
                else:
                    continue

                parsed = reference_date - delta

                # Extract time if present (e.g., "2 years ago at 4:00pm")
                time_match = re.search(r"at\s+(\d{1,2}):(\d{2})\s*(am|pm)", date_string_lower)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    am_pm = time_match.group(3)

                    if am_pm == "pm" and hour != 12:
                        hour += 12
                    elif am_pm == "am" and hour == 12:
                        hour = 0

                    parsed = parsed.replace(hour=hour, minute=minute, second=0, microsecond=0)

                logger.debug(f"Parsed relative date '{date_string}' as {parsed}")
                return parsed

        return None

    def _parse_absolute_date(
        self, date_string: str, reference_date: datetime
    ) -> Optional[datetime]:
        """
        Parse absolute dates like "November 3", "Nov 3, 2020", etc.

        Args:
            date_string: Date string to parse
            reference_date: Reference date for year inference

        Returns:
            Parsed datetime or None
        """
        # Extract time if present (will apply later)
        time_match = re.search(r"at\s+(\d{1,2}):(\d{2})\s*(am|pm)", date_string.lower())
        date_str_without_time = date_string
        if time_match:
            # Remove time from original string (case-sensitive) by finding the position
            time_pattern = time_match.group(0)
            date_lower = date_string.lower()
            time_pos = date_lower.find(time_pattern)
            if time_pos != -1:
                date_str_without_time = date_string[:time_pos].strip()

        # Try manual parsing for common formats first (more reliable)
        parsed = self._parse_absolute_date_manual(date_str_without_time, reference_date)
        if parsed is not None:
            # Apply time if present
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                am_pm = time_match.group(3)

                if am_pm == "pm" and hour != 12:
                    hour += 12
                elif am_pm == "am" and hour == 12:
                    hour = 0

                parsed = parsed.replace(hour=hour, minute=minute, second=0, microsecond=0)

            logger.debug(f"Parsed absolute date '{date_string}' as {parsed}")
            return parsed

        # Fallback to dateparser for absolute dates
        try:
            parsed = dateparser.parse(
                date_string,
                settings={
                    "RELATIVE_BASE": reference_date,
                    "TIMEZONE": self.default_timezone,
                    "PREFER_DATES_FROM": "past",
                    "STRICT_PARSING": False,
                },
            )

            if parsed:
                # If no year specified and date is in the future, assume previous year
                if parsed.year == reference_date.year and parsed > reference_date:
                    parsed = parsed.replace(year=parsed.year - 1)

                # Extract time if present (e.g., "November 3 at 4:00pm")
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    am_pm = time_match.group(3)

                    if am_pm == "pm" and hour != 12:
                        hour += 12
                    elif am_pm == "am" and hour == 12:
                        hour = 0

                    parsed = parsed.replace(hour=hour, minute=minute, second=0, microsecond=0)

                logger.debug(f"Parsed absolute date '{date_string}' as {parsed}")
                return cast(datetime, parsed)
        except Exception as e:
            logger.debug(f"Error parsing absolute date '{date_string}': {e}")

        return None

    def _parse_absolute_date_manual(
        self, date_string: str, reference_date: datetime
    ) -> Optional[datetime]:
        """
        Manually parse common absolute date formats without dateparser.

        Args:
            date_string: Date string to parse (without time)
            reference_date: Reference date for year inference

        Returns:
            Parsed datetime or None
        """
        date_string_lower = date_string.lower().strip()

        # Month names mapping
        months = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "sept": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }

        # Pattern 1: "November 3, 2020" or "Nov 3, 2020"
        pattern1 = r"(\w+)\s+(\d+),\s*(\d{4})"
        match = re.match(pattern1, date_string_lower)
        if match:
            month_name = match.group(1)
            day = int(match.group(2))
            year = int(match.group(3))

            if month_name in months:
                try:
                    return datetime(year, months[month_name], day, 0, 0, 0)
                except ValueError:
                    pass

        # Pattern 2: "November 3" or "Nov 3" (no year)
        pattern2 = r"(\w+)\s+(\d+)"
        match = re.match(pattern2, date_string_lower)
        if match:
            month_name = match.group(1)
            day = int(match.group(2))

            if month_name in months:
                # Use reference year, but if date is in future, use previous year
                year = reference_date.year
                try:
                    parsed = datetime(year, months[month_name], day, 0, 0, 0)
                    if parsed > reference_date:
                        parsed = parsed.replace(year=year - 1)
                    return parsed
                except ValueError:
                    pass

        return None

    def is_before_target(
        self, date_string: str, target_date: datetime, reference_date: Optional[datetime] = None
    ) -> bool:
        """
        Check if a date string represents a date before the target date.

        Args:
            date_string: Date string to parse
            target_date: Target date for comparison
            reference_date: Reference date for relative dates

        Returns:
            True if parsed date is before target_date, False otherwise
        """
        parsed = self.parse_facebook_date(date_string, reference_date)

        if parsed is None:
            logger.warning(f"Could not parse date '{date_string}', assuming not before target")
            return False

        return parsed < target_date
