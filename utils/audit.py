"""
utils/audit.py
==============
Audit logging module to track all user interactions for security purposes.
Logs are stored in a dedicated file: logs/audit_security.log
"""

import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from config.config import LOGS_DIR

# Ensure logs directory exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)

audit_logger = logging.getLogger("audit_security")
audit_logger.setLevel(logging.INFO)

# File handler for audit logs
audit_file = LOGS_DIR / "audit_security.log"
file_handler = RotatingFileHandler(
    audit_file,
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5,
    encoding="utf-8",
)

formatter = logging.Formatter("[%(asctime)s] - UserID: %(userid)s - Username: %(username)s - Action: %(action)s")
file_handler.setFormatter(formatter)
audit_logger.addHandler(file_handler)

def log_action(chat_id: int, username: str, action: str):
    """
    Log an action performed by a user.
    """
    audit_logger.info(
        "Action logged",
        extra={
            "userid": str(chat_id),
            "username": username or "Unknown",
            "action": action
        }
    )
