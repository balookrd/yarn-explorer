import time
from typing import Optional
from fastapi import Request, HTTPException, status

from app.services.storage import storage_service


class RateLimiter:
    """
    Ограничитель частоты запросов на базе скользящего окна (sliding window),
    сохраняющий состояние в SQLite (yarn_explorer.db).
    
    Поддерживает совместную работу между процессами/воркерами Uvicorn
    и переживает перезапуск приложения.
    """
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def _get_client_ip(self, request: Request) -> str:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        elif request.client:
            return request.client.host
        return "unknown"

    def is_allowed(self, key: str, now: Optional[float] = None) -> tuple[bool, int]:
        """Проверяет лимит и записывает попытку. Возвращает (is_allowed, retry_after)."""
        return storage_service.check_and_record_rate_limit(
            key=key,
            max_requests=self.max_requests,
            window_seconds=self.window_seconds,
            now=now,
        )

    def __call__(self, request: Request):
        client_ip = self._get_client_ip(request)
        allowed, retry_after = self.is_allowed(key=f"ip:{client_ip}")

        if not allowed:
            from app.core.audit import audit_log
            audit_log(
                action="RATE_LIMIT_EXCEEDED",
                username="anonymous",
                client_ip=client_ip,
                details={"path": request.url.path, "retry_after": retry_after},
                status="WARNING",
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Слишком много попыток. Пожалуйста, повторите через {retry_after} сек.",
                headers={"Retry-After": str(retry_after)},
            )


auth_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)

