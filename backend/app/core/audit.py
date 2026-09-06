import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("yarn_explorer.audit")

# Путь к файлу audit log при необходимости локального сохранения
AUDIT_LOG_FILE = os.environ.get("AUDIT_LOG_FILE", "")


def audit_log(
    action: str,
    username: str,
    client_ip: str,
    details: Optional[Dict[str, Any]] = None,
    status: str = "SUCCESS",
):
    """
    Записывает структурированное событие аудита безопасности в JSON.
    События отправляются в логгер 'yarn_explorer.audit' и опционально в файл.
    """
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "username": username or "anonymous",
        "client_ip": client_ip or "unknown",
        "status": status,
        "details": details or {},
    }

    log_line = json.dumps(event, ensure_ascii=False)

    if status == "SUCCESS":
        logger.info(f"[AUDIT] {log_line}")
    elif status == "WARNING":
        logger.warning(f"[AUDIT] {log_line}")
    else:
        logger.error(f"[AUDIT] {log_line}")

    if AUDIT_LOG_FILE:
        try:
            os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)
            with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception as e:
            logger.warning(f"Не удалось записать в audit log файл {AUDIT_LOG_FILE}: {e}")
