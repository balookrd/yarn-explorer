import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from app.models.change_requests import ChangeRequestSummary, ChangeRequestResponse
from app.models.yarn import DraftQueueItem, DiffItem

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.environ.get("DB_PATH", "data/yarn_explorer.db")


class StorageService:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout=30000;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS change_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cluster_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'SUBMITTED',
                    author TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    reviewer TEXT,
                    review_comment TEXT,
                    reviewed_at TEXT,
                    changes_json TEXT NOT NULL,
                    diffs_json TEXT NOT NULL,
                    xml_content TEXT
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS revoked_tokens (
                    jti TEXT PRIMARY KEY,
                    expires_at TEXT NOT NULL
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cr_cluster ON change_requests(cluster_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cr_status ON change_requests(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_revoked_exp ON revoked_tokens(expires_at);")
            conn.commit()
            logger.info(f"SQLite база данных инициализирована: {self.db_path}")

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

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO change_requests (
                    cluster_id, title, description, status, author,
                    created_at, updated_at, changes_json, diffs_json
                ) VALUES (?, ?, ?, 'SUBMITTED', ?, ?, ?, ?, ?)
                """,
                (cluster_id, title, description, author, now, now, changes_json, diffs_json),
            )
            conn.commit()
            return cursor.lastrowid

    def list_change_requests(
        self,
        cluster_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[ChangeRequestSummary]:
        query = "SELECT id, cluster_id, title, status, author, created_at, updated_at, reviewer, reviewed_at, changes_json FROM change_requests WHERE 1=1"
        params = []
        if cluster_id:
            query += " AND cluster_id = ?"
            params.append(cluster_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY id DESC"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM change_requests WHERE id = ?", (cr_id,))
            r = cursor.fetchone()
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE change_requests
                SET status = 'APPROVED', reviewer = ?, review_comment = ?, reviewed_at = ?, xml_content = ?, updated_at = ?
                WHERE id = ? AND status = 'SUBMITTED'
                """,
                (reviewer, comment, now, xml_content, now, cr_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def reject_change_request(
        self,
        cr_id: int,
        reviewer: str,
        comment: str,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE change_requests
                SET status = 'REJECTED', reviewer = ?, review_comment = ?, reviewed_at = ?, updated_at = ?
                WHERE id = ? AND status = 'SUBMITTED'
                """,
                (reviewer, comment, now, now, cr_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def cancel_change_request(
        self,
        cr_id: int,
        author: str,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE change_requests
                SET status = 'CANCELLED', updated_at = ?
                WHERE id = ? AND status = 'SUBMITTED' AND author = ?
                """,
                (now, cr_id, author),
            )
            conn.commit()
            return cursor.rowcount > 0

    def count_pending(self, cluster_id: Optional[str] = None) -> int:
        query = "SELECT COUNT(*) FROM change_requests WHERE status = 'SUBMITTED'"
        params = []
        if cluster_id:
            query += " AND cluster_id = ?"
            params.append(cluster_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    def revoke_token(self, jti: str, expires_at: str) -> bool:
        """Помещает токен (jti) в список отозванных токенов."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO revoked_tokens (jti, expires_at) VALUES (?, ?)",
                    (jti, expires_at),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при отзыве токена {jti}: {e}")
            return False

    def is_token_revoked(self, jti: str) -> bool:
        """Проверяет, отозван ли токен."""
        if not jti:
            return False
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM revoked_tokens WHERE jti = ?", (jti,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Ошибка проверки отзыва токена {jti}: {e}")
            return False

    def cleanup_expired_tokens(self):
        """Удаляет из базы устаревшие отозванные токены."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM revoked_tokens WHERE expires_at < ?", (now,))
                conn.commit()
        except Exception as e:
            logger.warning(f"Ошибка очистки устаревших отозванных токенов: {e}")


storage_service = StorageService()
