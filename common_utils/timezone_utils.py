"""
Timezone utilities for handling IST and UTC timestamps.
"""

from datetime import datetime, timedelta, timezone

# IST timezone (UTC+5:30)
IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30))


def get_utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


def get_ist_now() -> datetime:
    """Get current IST time."""
    return datetime.now(IST_TIMEZONE)


def utc_to_ist(utc_time: datetime) -> datetime:
    """Convert UTC time to IST."""
    if utc_time.tzinfo is None:
        # If naive datetime, assume it's UTC
        utc_time = utc_time.replace(tzinfo=timezone.utc)
    return utc_time.astimezone(IST_TIMEZONE)


def ist_to_utc(ist_time: datetime) -> datetime:
    """Convert IST time to UTC."""
    if ist_time.tzinfo is None:
        # If naive datetime, assume it's IST
        ist_time = ist_time.replace(tzinfo=IST_TIMEZONE)
    return ist_time.astimezone(timezone.utc)


def format_timestamp_for_display(
    timestamp: datetime, timezone_name: str = "IST"
) -> str:
    """Format timestamp for display in specified timezone."""
    if timezone_name.upper() == "IST":
        return utc_to_ist(timestamp).strftime("%Y-%m-%d %H:%M:%S IST")
    elif timezone_name.upper() == "UTC":
        return timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        return timestamp.isoformat()


def parse_timestamp_from_ist(ist_string: str) -> datetime:
    """Parse IST timestamp string to UTC datetime."""
    # Parse IST time and convert to UTC
    ist_time = datetime.fromisoformat(ist_string.replace("IST", "+05:30"))
    return ist_to_utc(ist_time)


def get_timestamp_for_mongo() -> datetime:
    """Get current UTC timestamp for MongoDB storage."""
    return get_utc_now()


def get_timestamp_for_display() -> str:
    """Get current IST timestamp formatted for display."""
    return format_timestamp_for_display(get_utc_now(), "IST")


def format_datetime_to_standard_format(dt: datetime) -> str:
    """
    Format datetime to standard ISO format with timezone offset.

    Args:
        dt: datetime object to format

    Returns:
        Formatted datetime string in standard format
    """
    from common_utils.constants import DateTimeFormats

    # Ensure datetime has timezone info
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.strftime(DateTimeFormats.ISO_FORMAT_WITH_TIMEZONE)


def parse_datetime_from_standard_format(dt_string: str) -> datetime:
    """
    Parse datetime string from standard ISO format with timezone offset.

    Args:
        dt_string: datetime string in standard format

    Returns:
        Parsed datetime object
    """
    # Handle ISO format with timezone
    if dt_string.endswith("Z"):
        dt_string = dt_string.replace("Z", "+00:00")

    return datetime.fromisoformat(dt_string)


def format_datetime_to_iso_with_timezone(dt: datetime) -> str:
    """
    Format datetime to ISO format with timezone offset.

    Args:
        dt: datetime object to format

    Returns:
        Formatted datetime string in ISO format with timezone
    """
    from common_utils.constants import DateTimeFormats

    # Ensure datetime has timezone info
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.strftime(DateTimeFormats.ISO_FORMAT_WITH_TIMEZONE)


def format_datetime_to_iso(dt: datetime) -> str:
    """
    Format datetime to ISO format without timezone.

    Args:
        dt: datetime object to format

    Returns:
        Formatted datetime string in ISO format
    """
    from common_utils.constants import DateTimeFormats

    return dt.strftime(DateTimeFormats.ISO_FORMAT)


def timestamp_ms_to_utc(timestamp_ms: int) -> datetime:
    """
    Convert Unix timestamp in milliseconds to UTC datetime.

    Args:
        timestamp_ms: Unix timestamp in milliseconds

    Returns:
        UTC datetime object with timezone info
    """
    # Convert milliseconds to seconds and create UTC datetime
    timestamp_seconds = timestamp_ms / 1000
    utc_datetime = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
    return utc_datetime


def timestamp_ms_to_ist(timestamp_ms: int) -> datetime:
    """
    Convert Unix timestamp in milliseconds to IST datetime.

    Args:
        timestamp_ms: Unix timestamp in milliseconds

    Returns:
        IST datetime object with timezone info
    """
    utc_datetime = timestamp_ms_to_utc(timestamp_ms)
    return utc_to_ist(utc_datetime)
