import json
import logging
import os
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Text,
    Float,
    select,
    insert,
    update,
    delete,
    func,
    text,
)
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.models.change_requests import ChangeRequestSummary, ChangeRequestResponse
from app.models.yarn import DraftQueueItem, DiffItem

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.environ.get("DB_PATH", "data/yarn_explorer.db")


class StorageService:
    def __init__(self, db_path: Optional[str] = None, db_url: Optional[str] = None):
        if db_url:
            self.db_url = db_url
        elif db_path:
            if db_path == ":memory:":
                self.db_url = "sqlite:///:memory:"
            elif "://" in db_path:
                self.db_url = db_path
            else:
                self.db_url = f"sqlite:///{db_path}"
        else:
            self.db_url = settings.database.url

        self.db_path = db_path or DEFAULT_DB_PATH

        self._is_sqlite = "sqlite" in self.db_url
        self._is_memory = ":memory:" in self.db_url

        engine_kwargs = {}
        if self._is_sqlite:
            if self._is_memory:
                engine_kwargs = {
                    "connect_args": {"check_same_thread": False},
                    "poolclass": StaticPool,
                }
            else:
                engine_kwargs = {
                    "connect_args": {"check_same_thread": False, "timeout": 30.0},
                }
        else:
            engine_kwargs = {
                "pool_pre_ping": True,
                "pool_size": 10,
                "max_overflow": 20,
            }

        self.engine = create_engine(self.db_url, **engine_kwargs)
        self.metadata = MetaData()

        self.cr_table = Table(
            "change_requests",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("cluster_id", String(255), nullable=False, index=True),
            Column("title", String(500), nullable=False),
            Column("description", Text, nullable=False, default=""),
            Column("status", String(50), nullable=False, default="SUBMITTED", index=True),
            Column("author", String(255), nullable=False),
            Column("created_at", String(100), nullable=False),
            Column("updated_at", String(100), nullable=False),
            Column("reviewer", String(255), nullable=True),
            Column("review_comment", Text, nullable=True),
            Column("reviewed_at", String(100), nullable=True),
            Column("changes_json", Text, nullable=False),
            Column("diffs_json", Text, nullable=False),
            Column("xml_content", Text, nullable=True),
        )

        self.revoked_tokens_table = Table(
            "revoked_tokens",
            self.metadata,
            Column("jti", String(255), primary_key=True),
            Column("expires_at", String(100), nullable=False, index=True),
        )

        self.rate_limits_table = Table(
            "rate_limits",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("key", String(255), nullable=False, index=True),
            Column("timestamp", Float, nullable=False, index=True),
        )

        self._init_db()

    def _get_connection(self):
        """Возвращает DBAPI соединение для совместимости."""
        return self.engine.raw_connection()

    def _init_db(self):
        try:
            if self._is_sqlite and not self._is_memory:
                parsed = urllib.parse.urlparse(self.db_url)
                file_path = parsed.path
                if file_path:
                    db_file = Path(file_path.lstrip("/"))
                    db_file.parent.mkdir(parents=True, exist_ok=True)

            self.metadata.create_all(self.engine)

            if self._is_sqlite and not self._is_memory:
                with self.engine.begin() as conn:
                    conn.execute(text("PRAGMA journal_mode=WAL;"))
                    conn.execute(text("PRAGMA busy_timeout=30000;"))
            logger.info(f"База данных инициализирована: {self.db_url}")
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных ({self.db_url}): {e}")

    def create_change_request(
        self,
        cluster_id: str,
        title: str,
        description: str,
        author: str,
        changes: List[DraftQueueItem],
        diffs: List[DiffItem],
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        changes_json = json.dumps([c.model_dump() for c in changes], ensure_ascii=False)
        diffs_json = json.dumps([d.model_dump() for d in diffs], ensure_ascii=False)

        with self.engine.begin() as conn:
            stmt = insert(self.cr_table).values(
                cluster_id=cluster_id,
                title=title,
                description=description,
                status="SUBMITTED",
                author=author,
                created_at=now,
                updated_at=now,
                changes_json=changes_json,
                diffs_json=diffs_json,
            )
            result = conn.execute(stmt)
            return result.inserted_primary_key[0]

    def list_change_requests(
        self,
        cluster_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ChangeRequestSummary]:
        stmt = select(
            self.cr_table.c.id,
            self.cr_table.c.cluster_id,
            self.cr_table.c.title,
            self.cr_table.c.status,
            self.cr_table.c.author,
            self.cr_table.c.created_at,
            self.cr_table.c.updated_at,
            self.cr_table.c.reviewer,
            self.cr_table.c.reviewed_at,
            self.cr_table.c.changes_json,
        )
        if cluster_id:
            stmt = stmt.where(self.cr_table.c.cluster_id == cluster_id)
        if status:
            stmt = stmt.where(self.cr_table.c.status == status)
        stmt = stmt.order_by(self.cr_table.c.id.desc())

        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
            result = []
            for r in rows:
                changes = json.loads(r["changes_json"]) if r["changes_json"] else []
                result.append(
                    ChangeRequestSummary(
                        id=r["id"],
                        cluster_id=r["cluster_id"],
                        title=r["title"],
                        status=r["status"],
                        author=r["author"],
                        changes_count=len(changes),
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                        reviewer=r["reviewer"],
                        reviewed_at=r["reviewed_at"],
                    )
                )
            return result

    def get_change_request(self, cr_id: int) -> Optional[ChangeRequestResponse]:
        stmt = select(self.cr_table).where(self.cr_table.c.id == cr_id)
        with self.engine.connect() as conn:
            r = conn.execute(stmt).mappings().one_or_none()
            if not r:
                return None

            changes_raw = json.loads(r["changes_json"]) if r["changes_json"] else []
            diffs_raw = json.loads(r["diffs_json"]) if r["diffs_json"] else []

            changes = [DraftQueueItem(**item) for item in changes_raw]
            diffs = [DiffItem(**item) for item in diffs_raw]

            return ChangeRequestResponse(
                id=r["id"],
                cluster_id=r["cluster_id"],
                title=r["title"],
                description=r["description"],
                status=r["status"],
                author=r["author"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                reviewer=r["reviewer"],
                review_comment=r["review_comment"],
                reviewed_at=r["reviewed_at"],
                changes=changes,
                diffs=diffs,
                xml_content=r["xml_content"],
            )

    def approve_change_request(
        self,
        cr_id: int,
        reviewer: str,
        comment: str,
        xml_content: str,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        stmt = (
            update(self.cr_table)
            .where(self.cr_table.c.id == cr_id, self.cr_table.c.status == "SUBMITTED")
            .values(
                status="APPROVED",
                reviewer=reviewer,
                review_comment=comment,
                reviewed_at=now,
                xml_content=xml_content,
                updated_at=now,
            )
        )
        with self.engine.begin() as conn:
            result = conn.execute(stmt)
            return result.rowcount > 0

    def reject_change_request(
        self,
        cr_id: int,
        reviewer: str,
        comment: str,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        stmt = (
            update(self.cr_table)
            .where(self.cr_table.c.id == cr_id, self.cr_table.c.status == "SUBMITTED")
            .values(
                status="REJECTED",
                reviewer=reviewer,
                review_comment=comment,
                reviewed_at=now,
                updated_at=now,
            )
        )
        with self.engine.begin() as conn:
            result = conn.execute(stmt)
            return result.rowcount > 0

    def cancel_change_request(
        self,
        cr_id: int,
        author: str,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        stmt = (
            update(self.cr_table)
            .where(
                self.cr_table.c.id == cr_id,
                self.cr_table.c.status == "SUBMITTED",
                self.cr_table.c.author == author,
            )
            .values(
                status="CANCELLED",
                updated_at=now,
            )
        )
        with self.engine.begin() as conn:
            result = conn.execute(stmt)
            return result.rowcount > 0

    def count_pending(self, cluster_id: Optional[str] = None) -> int:
        stmt = select(func.count(self.cr_table.c.id)).where(self.cr_table.c.status == "SUBMITTED")
        if cluster_id:
            stmt = stmt.where(self.cr_table.c.cluster_id == cluster_id)
        with self.engine.connect() as conn:
            return conn.execute(stmt).scalar() or 0

    def revoke_token(self, jti: str, expires_at: str) -> bool:
        """Помещает токен (jti) в список отозванных токенов."""
        try:
            with self.engine.begin() as conn:
                existing = conn.execute(
                    select(self.revoked_tokens_table.c.jti).where(
                        self.revoked_tokens_table.c.jti == jti
                    )
                ).scalar_one_or_none()

                if existing:
                    conn.execute(
                        update(self.revoked_tokens_table)
                        .where(self.revoked_tokens_table.c.jti == jti)
                        .values(expires_at=expires_at)
                    )
                else:
                    conn.execute(
                        insert(self.revoked_tokens_table).values(jti=jti, expires_at=expires_at)
                    )
                return True
        except Exception as e:
            logger.error(f"Ошибка при отзыве токена {jti}: {e}")
            return False

    def is_token_revoked(self, jti: str) -> bool:
        """Проверяет, отозван ли токен."""
        if not jti:
            return False
        try:
            with self.engine.connect() as conn:
                stmt = select(self.revoked_tokens_table.c.jti).where(
                    self.revoked_tokens_table.c.jti == jti
                ).limit(1)
                result = conn.execute(stmt).scalar_one_or_none()
                return result is not None
        except Exception as e:
            logger.error(f"Ошибка проверки отзыва токена {jti}: {e}")
            return False

    def cleanup_expired_tokens(self):
        """Удаляет из базы устаревшие отозванные токены."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    delete(self.revoked_tokens_table).where(
                        self.revoked_tokens_table.c.expires_at < now
                    )
                )
        except Exception as e:
            logger.warning(f"Ошибка очистки устаревших отозванных токенов: {e}")

    def check_and_record_rate_limit(
        self, key: str, max_requests: int, window_seconds: int, now: Optional[float] = None
    ) -> tuple[bool, int]:
        """
        Проверяет и регистрирует попытку запроса в БД (sliding window).
        Возвращает (allowed, retry_after_seconds).
        """
        import time
        current_time = now if now is not None else time.time()
        cutoff = current_time - window_seconds
        try:
            with self.engine.begin() as conn:
                # Удаляем устаревшие записи для данного ключа
                conn.execute(
                    delete(self.rate_limits_table).where(
                        self.rate_limits_table.c.key == key,
                        self.rate_limits_table.c.timestamp < cutoff,
                    )
                )
                # Получаем временные метки
                stmt = (
                    select(self.rate_limits_table.c.timestamp)
                    .where(self.rate_limits_table.c.key == key)
                    .order_by(self.rate_limits_table.c.timestamp.asc())
                )
                rows = conn.execute(stmt).fetchall()
                count = len(rows)

                if count >= max_requests:
                    oldest_ts = rows[0][0]
                    retry_after = max(1, int(window_seconds - (current_time - oldest_ts)))
                    return False, retry_after

                conn.execute(
                    insert(self.rate_limits_table).values(key=key, timestamp=current_time)
                )
                return True, 0
        except Exception as e:
            logger.error(f"Ошибка проверки rate limit для {key}: {e}")
            return True, 0

    def cleanup_rate_limits(self, older_than_seconds: int = 3600):
        """Удаляет из базы все записи rate limit старше заданного времени."""
        import time
        cutoff = time.time() - older_than_seconds
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    delete(self.rate_limits_table).where(
                        self.rate_limits_table.c.timestamp < cutoff
                    )
                )
        except Exception as e:
            logger.warning(f"Ошибка очистки rate limits: {e}")


storage_service = StorageService()
