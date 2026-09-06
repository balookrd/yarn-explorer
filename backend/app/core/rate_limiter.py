import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException, status


class RateLimiter:
    """
    Легковесный ограничитель частоты запросов на базе скользящего окна по IP.
    """
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def _cleanup(self, now: float):
        cutoff = now - self.window_seconds
        for ip in list(self._requests.keys()):
            self._requests[ip] = [ts for ts in self._requests[ip] if ts > cutoff]
            if not self._requests[ip]:
                del self._requests[ip]

    def __call__(self, request: Request):
        # Определение IP клиента (с учетом возможных reverse proxy заголовков)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "unknown"

        now = time.time()
        self._cleanup(now)

        timestamps = self._requests[client_ip]
        if len(timestamps) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - timestamps[0]))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Слишком много попыток. Пожалуйста, повторите через {max(1, retry_after)} сек.",
                headers={"Retry-After": str(max(1, retry_after))},
            )

        self._requests[client_ip].append(now)


auth_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
