from datetime import datetime, timezone, timedelta

def get_beijing_time():
    """
    Returns the current time in Beijing (UTC+8).
    """
    utc_now = datetime.now(timezone.utc)
    beijing_tz = timezone(timedelta(hours=8))
    return utc_now.astimezone(beijing_tz)

def get_beijing_time_iso():
    """
    Returns the current Beijing time as an ISO string.
    """
    return get_beijing_time().isoformat()
