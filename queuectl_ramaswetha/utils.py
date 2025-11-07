# QueueCTL_RamaSwetha — utilities
# Author: Rama Swetha

from datetime import datetime, timezone

def utcnow_iso():
    """Return current UTC time as ISO8601 string."""
    return datetime.now(timezone.utc).isoformat()

def iso_to_datetime(iso_str):
    from datetime import datetime
    if not iso_str:
        return None
    return datetime.fromisoformat(iso_str)

