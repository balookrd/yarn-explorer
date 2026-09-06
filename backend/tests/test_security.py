import pytest
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.yarn import QueueDraftItem, PartitionResourceConfig
from app.models.cluster import ClusterConfig, ClusterResources, ClusterAcl
from app.models.auth import UserSession, Role
from app.services.xml_generator import generate_capacity_scheduler_xml, _sanitize_xml_comment
from app.core.ldap_auth import ldap_service
from app.core.acl import check_ui_access
from app.core.security import get_current_user
from app.api.auth import _mock_authenticate
from app.api.change_requests import get_change_request, list_change_requests, get_pending_count
from app.services.storage import StorageService


@pytest.fixture
def sample_cluster():
    return ClusterConfig(
        id="test-cluster-sec",
        name="Security Test Cluster",
        resource_manager_urls=["http://rm:8088"],
        resource_mode="percentage",
        default_partition="DEFAULT",
        partitions=["DEFAULT"],
        total_resources=ClusterResources(memory_mb=1048576, vcores=512),
        acl=ClusterAcl(
            allowed_users=["allowed_user"],
            allowed_groups=[],
        ),
    )


def test_xml_comment_injection_sanitized(sample_cluster):
    """Проверяет, что разделители комментария '-->' и спецсимволы нейтрализуются."""
    malicious_comment = 'test --> <property><name>injected.property</name><value>true</value></property><!--'
    malicious_author = 'attacker --!>'

    xml = generate_capacity_scheduler_xml(
        queues=[],
        cluster=sample_cluster,
        generated_by=malicious_author,
        comment=malicious_comment,
        base_xml=None,
    )

    # XML должен быть синтаксически валидным
    root = ET.fromstring(xml)

    # Проверяем, что внедренное свойство НЕ появилось среди тегов <property>
    property_names = [p.find("name").text for p in root.findall("property") if p.find("name") is not None]
    assert "injected.property" not in property_names
    # Проверяем, что в шапке разрыв комментария был нейтрализован
    assert "--> <property>" not in xml


def test_ldap_input_escaping():
    """Проверяет, что спецсимволы в имени пользователя экранируются перед подстановкой в LDAP-фильтр."""
    malicious_username = "admin)(|(cn=*"
    with patch("app.core.ldap_auth.Connection") as mock_conn_cls, \
         patch.object(ldap_service.config, "enabled", True), \
         patch.object(ldap_service.config, "user_filter", "(&(objectClass=user)(sAMAccountName={username}))"):
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn_cls.return_value = mock_conn
        mock_conn.entries = []

        ldap_service.authenticate(malicious_username, "password")

        # Проверяем, с каким фильтром был вызван search
        search_calls = mock_conn.search.call_args_list
        assert len(search_calls) > 0
        actual_filter = search_calls[0][1]["search_filter"]

        # Круглые скобки и звездочка должны быть экранированы в безопасные hex-последовательности
        assert "admin\\29\\28|\\28cn=\\2a" in actual_filter
        assert "admin)(|(cn=*" not in actual_filter


def test_queue_draft_item_validation():
    """Проверяет regex-валидацию имен и путей очередей."""
    part = PartitionResourceConfig(capacity=100.0, max_capacity=100.0)

    # Корректная очередь
    valid_q = QueueDraftItem(
        path="root.valid_queue-1",
        name="valid_queue-1",
        parent_path="root",
        partitions={"DEFAULT": part},
    )
    assert valid_q.name == "valid_queue-1"

    # Некорректное имя (пробелы, спецсимволы)
    with pytest.raises(ValidationError):
        QueueDraftItem(
            path="root.invalid queue",
            name="invalid queue",
            parent_path="root",
            partitions={"DEFAULT": part},
        )

    # Некорректный путь (перевод строки или path traversal)
    with pytest.raises(ValidationError):
        QueueDraftItem(
            path="root.queue\ninjection",
            name="queue",
            parent_path="root",
            partitions={"DEFAULT": part},
        )

    with pytest.raises(ValidationError):
        QueueDraftItem(
            path="../root.queue",
            name="queue",
            parent_path="..",
            partitions={"DEFAULT": part},
        )


@pytest.mark.asyncio
async def test_change_request_bola_protection(tmp_path, sample_cluster):
    """Проверяет защиту BOLA / IDOR в эндпоинтах Change Requests."""
    db_file = str(tmp_path / "sec_test.db")
    test_storage = StorageService(db_path=db_file)

    with patch("app.api.change_requests.storage_service", test_storage), \
         patch("app.api.change_requests.settings.clusters", [sample_cluster]):

        cr_id = test_storage.create_change_request(
            cluster_id=sample_cluster.id,
            title="Secret changes",
            description="Private info",
            author="allowed_user",
            changes=[],
            diffs=[],
        )

        allowed_user = UserSession(
            username="allowed_user",
            display_name="Allowed",
            groups=[],
            auth_method="mock",
            is_admin=False,
            system_role=Role.READER,
        )

        unauthorized_user = UserSession(
            username="unauthorized_user",
            display_name="Attacker",
            groups=[],
            auth_method="mock",
            is_admin=False,
            system_role=Role.READER,
        )

        # 1. Авторизованный пользователь получает заявку
        res = await get_change_request(cr_id=cr_id, current_user=allowed_user)
        assert res.id == cr_id

        # 2. Неавторизованный пользователь получает 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            await get_change_request(cr_id=cr_id, current_user=unauthorized_user)
        assert exc_info.value.status_code == 403

        # 3. В общем списке заявок неавторизованный пользователь не видит заявку
        unauth_list = await list_change_requests(cluster_id=None, status_filter=None, current_user=unauthorized_user)
        assert len(unauth_list) == 0

        auth_list = await list_change_requests(cluster_id=None, status_filter=None, current_user=allowed_user)
        assert len(auth_list) == 1

        # 4. В pending_count неавторизованный видит 0
        unauth_count = await get_pending_count(cluster_id=None, current_user=unauthorized_user)
        assert unauth_count["pending_count"] == 0

        auth_count = await get_pending_count(cluster_id=None, current_user=allowed_user)
        assert auth_count["pending_count"] == 1


def test_ui_access_acl_enforcement():
    """Проверяет применение политик ui_access."""
    with patch("app.core.acl.settings.acl.ui_access.allowed_users", ["allowed_admin"]), \
         patch("app.core.acl.settings.acl.ui_access.allowed_groups", []):

        allowed = UserSession(
            username="allowed_admin",
            display_name="Allowed",
            groups=[],
            auth_method="mock",
            is_admin=False,
            system_role=Role.READER,
        )
        blocked = UserSession(
            username="blocked_user",
            display_name="Blocked",
            groups=[],
            auth_method="mock",
            is_admin=False,
            system_role=Role.READER,
        )

        assert check_ui_access(allowed) is True
        assert check_ui_access(blocked) is False


def test_mock_auth_timing_safe():
    """Проверяет корректность безопасной проверки паролей mock-пользователей."""
    user = _mock_authenticate("admin_user", "password123")
    assert user is not None
    assert user.username == "admin_user"

    wrong_pw = _mock_authenticate("admin_user", "wrongpassword")
    assert wrong_pw is None

    wrong_user = _mock_authenticate("nonexistent", "password123")
    assert wrong_user is None


def test_security_headers_and_cors():
    """Проверяет наличие защитных заголовков и настройки CORS."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in response.headers
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_token_revocation_on_logout():
    """Проверяет серверный отзыв токена при выходе и очистку cookie."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 1. Логин
    login_resp = client.post("/api/auth/login", json={"username": "admin_user", "password": "password123"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    assert "access_token" in login_resp.cookies

    # 2. Проверяем, что токен работает
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "admin_user"

    # 3. Выход с отзывом токена
    logout_resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200

    # 4. Повторный запрос с тем же токеном должен вернуть 401 Unauthorized
    me_after_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_after_resp.status_code == 401


def test_rate_limiter_blocks_excessive_logins():
    """Проверяет ограничение частоты запросов Rate Limiter в SQLite."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.storage import storage_service

    client = TestClient(app)
    # Очищаем таблицу перед тестом
    with storage_service._get_connection() as conn:
        conn.cursor().execute("DELETE FROM rate_limits")
        conn.commit()

    # Делаем 10 запросов (разрешенный лимит)
    for _ in range(10):
        resp = client.post("/api/auth/login", json={"username": "admin_user", "password": "wrongpassword"})
        assert resp.status_code == 401

    # 11-й запрос должен быть заблокирован с HTTP 429
    blocked_resp = client.post("/api/auth/login", json={"username": "admin_user", "password": "wrongpassword"})
    assert blocked_resp.status_code == 429
    assert "Слишком много попыток" in blocked_resp.json()["detail"]
    assert "Retry-After" in blocked_resp.headers

    # Очищаем после теста
    with storage_service._get_connection() as conn:
        conn.cursor().execute("DELETE FROM rate_limits")
        conn.commit()


def test_mock_auth_bcrypt_hash():
    """Проверяет аутентификацию mock-пользователя через password_hash (bcrypt)."""
    import bcrypt
    from app.core.config import MockUserConfig, settings

    hashed = bcrypt.hashpw(b"secret_bcrypt_123", bcrypt.gensalt()).decode("utf-8")
    mock_bcrypt_user = MockUserConfig(
        username="bcrypt_user",
        password=None,
        password_hash=hashed,
        display_name="Bcrypt User",
        groups=["hadoop-admins"],
    )

    with patch.object(settings.auth, "mock_users", [mock_bcrypt_user]):
        # Успешный вход
        user = _mock_authenticate("bcrypt_user", "secret_bcrypt_123")
        assert user is not None
        assert user.username == "bcrypt_user"

        # Неверный пароль
        failed = _mock_authenticate("bcrypt_user", "wrong_secret")
        assert failed is None


def test_env_variable_overrides():
    """Проверяет переопределение JWT_SECRET_KEY и LDAP_BIND_PASSWORD из переменных окружения."""
    from app.core.config import Settings
    import os

    with patch.dict(os.environ, {
        "JWT_SECRET_KEY": "env-custom-jwt-secret-xyz",
        "LDAP_BIND_PASSWORD": "env-ldap-custom-password",
        "SERVER_DEBUG": "false",
        "CORS_ORIGINS": "https://yarn.company.com,https://yarn-internal.company.com",
    }):
        loaded_settings = Settings.load_from_yaml("nonexistent-path.yaml")
        assert loaded_settings.auth.jwt.secret_key == "env-custom-jwt-secret-xyz"
        assert loaded_settings.auth.ldap.bind_password == "env-ldap-custom-password"
        assert loaded_settings.server.debug is False
        assert "https://yarn.company.com" in loaded_settings.server.cors_origins
        assert "https://yarn-internal.company.com" in loaded_settings.server.cors_origins


def test_audit_logging(tmp_path):
    """Проверяет запись структурированного JSON аудита в логгер и файл."""
    import json
    import os
    from unittest.mock import patch
    from app.core.audit import audit_log

    audit_file = str(tmp_path / "audit_test.log")
    with patch.dict(os.environ, {"AUDIT_LOG_FILE": audit_file}):
        with patch("app.core.audit.AUDIT_LOG_FILE", audit_file):
            audit_log(
                action="TEST_ACTION",
                username="admin_user",
                client_ip="192.168.1.100",
                details={"cluster_id": "prod-cluster", "status_code": 200},
                status="SUCCESS",
            )

    assert os.path.exists(audit_file)
    with open(audit_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["action"] == "TEST_ACTION"
    assert event["username"] == "admin_user"
    assert event["client_ip"] == "192.168.1.100"
    assert event["status"] == "SUCCESS"
    assert event["details"]["cluster_id"] == "prod-cluster"
    assert "timestamp" in event
