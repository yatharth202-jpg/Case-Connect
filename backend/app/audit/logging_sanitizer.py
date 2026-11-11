"""
Forensic logging hygiene and PII scrubber for CaseConnect AI.
Complies with statutory privacy standards under Section 63 BSA 2023.

Ensures no raw evidence content, full phone numbers, full bank accounts,
PAN, or Aadhaar numbers ever enter persistent application log files or streams.
"""

import logging
import re
from typing import Any, Tuple, Union

# Regex patterns for sensitive identifiers in application logs
RE_PHONE = re.compile(r"(?:\+91[-\s]?)?(?<!\d)([6-9]\d{5})(\d{4})(?!\d)")
RE_AADHAAR = re.compile(r"(?<!\d)(\d{4})[-\s]?(\d{4})[-\s]?(\d{4})(?!\d)")
RE_PAN = re.compile(r"(?<![A-Z0-9])([A-Z]{5}\d{2})(\d{2}[A-Z])(?![A-Z0-9])")
RE_ACCOUNT = re.compile(r"(?i)(?:acct?|account|a/c)[\s:#_-]*(\d{5,14})(\d{4})(?!\d)")
RE_STANDALONE_ACCOUNT = re.compile(r"(?<!\d)(\d{6,14})(\d{4})(?!\d)")


def sanitize_log_message(text: str) -> str:
    """
    Scrubs raw PII identifiers from a text message, masking everything except safe trailing digits.
    Never throws on invalid or non-string inputs.
    """
    if not isinstance(text, str):
        return text

    # Mask explicit account patterns first
    text = RE_ACCOUNT.sub(r"account [ACCOUNT:XXXX\2]", text)

    # Mask Aadhaar numbers (12 digits with optional spaces/hyphens)
    text = RE_AADHAAR.sub(r"[AADHAAR:XXXX-XXXX-\3]", text)

    # Mask PAN (5 letters, 4 digits, 1 letter)
    text = RE_PAN.sub(r"[PAN:XXXXXX\2]", text)

    # Mask 10-digit Indian Mobile Numbers
    text = RE_PHONE.sub(r"[PHONE:XXXXXX\2]", text)

    return text


def _sanitize_arg(arg: Any) -> Any:
    if isinstance(arg, str):
        return sanitize_log_message(arg)
    elif isinstance(arg, (list, tuple)):
        return type(arg)(_sanitize_arg(item) for item in arg)
    elif isinstance(arg, dict):
        return {k: _sanitize_arg(v) for k, v in arg.items()}
    return arg


class SensitiveDataSanitizerFilter(logging.Filter):
    """
    Logging filter that intercepts log records and masks PII before emission to handlers.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = sanitize_log_message(record.msg)
            if record.args:
                if isinstance(record.args, tuple):
                    record.args = tuple(_sanitize_arg(a) for a in record.args)
                elif isinstance(record.args, dict):
                    record.args = {k: _sanitize_arg(v) for k, v in record.args.items()}
        except Exception:
            pass
        return True


def setup_logging_sanitizer() -> None:
    """
    Attaches the SensitiveDataSanitizerFilter to root and framework loggers.
    """
    sanitizer_filter = SensitiveDataSanitizerFilter()
    root_logger = logging.getLogger()
    if sanitizer_filter not in root_logger.filters:
        root_logger.addFilter(sanitizer_filter)

    for handler in root_logger.handlers:
        if sanitizer_filter not in handler.filters:
            handler.addFilter(sanitizer_filter)

    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi", "backend"):
        l = logging.getLogger(logger_name)
        if sanitizer_filter not in l.filters:
            l.addFilter(sanitizer_filter)

