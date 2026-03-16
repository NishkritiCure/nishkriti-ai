import logging
import json
import os
import re
from datetime import datetime, timezone

PHONE_RE = re.compile(r'\+91\d{10}')
NAME_RE = re.compile(r'"name":\s*"[^"]*"')

class PIIFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.msg)
        if '+91' in msg or '"name"' in msg:
            msg = PHONE_RE.sub('+91***', msg)
            msg = NAME_RE.sub('"name": "***"', msg)
        record.msg = msg
        return True

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "level": record.levelname.lower(),
            "event": record.getMessage(),
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        if record.exc_info:
            log_record["exc"] = self.formatException(record.exc_info)
        # merge any extra fields passed via extra={}
        for key, val in record.__dict__.items():
            if key not in (
                "msg", "args", "levelname", "levelno", "pathname", "filename",
                "module", "exc_info", "exc_text", "stack_info", "lineno",
                "funcName", "created", "msecs", "relativeCreated", "thread",
                "threadName", "processName", "process", "name", "message",
                "taskName",
            ):
                log_record[key] = val
        return json.dumps(log_record)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
        logger.setLevel(level)
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        handler.addFilter(PIIFilter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger
