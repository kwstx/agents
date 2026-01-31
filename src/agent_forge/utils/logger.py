import logging
import json
import sys
from contextvars import ContextVar
import uuid

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="SYSTEM")

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "correlation_id": correlation_id.get(),
            "module": record.module,
            "function": record.funcName,
            "lineno": record.lineno,
        }
        
        # Merge extra fields if any
        if hasattr(record, "extra_fields"):
            log_record.update(record.extra_fields)

        if record.exc_info:
             log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_logger(name="AgentForge"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    # logger.propagate = False # Prevent double logging if root logger is active
    
    # Check if already setup to avoid duplicates
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        
    return logger

class StructuredAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        if "extra_fields" not in extra:
            kwargs["extra"] = {"extra_fields": extra}
        else:
             # If extra_fields is already there, don't nest it again hopefully
             pass
        return msg, kwargs

def get_logger(name):
    logger = setup_logger(name)
    return StructuredAdapter(logger, {})
