"""Core modules for Auto Code Web Backend"""


def sanitize_log(value: str) -> str:
    """Sanitize value for safe logging (prevent log injection).

    Replaces newline and carriage-return characters so that user-controlled
    data cannot forge multi-line log entries.
    """
    return str(value).replace("\n", "\\n").replace("\r", "\\r")
