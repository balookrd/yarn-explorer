# Backend: YARN Queue Explorer

Бэкенд-сервис приложения **YARN Queue Explorer**, реализованный на базе **FastAPI (Python 3.12)**. Сервис обеспечивает взаимодействие с кластерами Apache Hadoop YARN через Kerberos SPNEGO, аутентификацию пользователей через OpenLDAP / Active Directory, персистентное хранение заявок на согласование в SQLite и генерацию конфигурации `capacity-scheduler.xml`.

---

## 🏛 Архитектура компонентов бэкенда

```
backend/
├── app/
│   ├── api/                     # REST API контроллеры
│   │   ├── auth.py              # Аутентификация (/api/auth/login, /api/auth/me, /api/auth/logout)
│   │   ├── clusters.py          # Список кластеров и метаданные (/api/clusters)
│   │   ├── queues.py            # Дерево очередей, балансировка, экспорт (/api/queues)
│   │   └── change_requests.py   # Заявки на согласование (/api/queues/{cluster_id}/change-requests)
│   ├── core/                    # Ядро сервиса
│   │   ├── config.py            # Загрузка и валидация config.yaml (Pydantic Settings)
│   │   ├── security.py          # Хеширование паролей, JWT-токены
│   │   └── database.py          # SQLite база данных (таблицы change_requests, audits)
│   ├── models/                  # Pydantic-модели и схемы данных
│   │   ├── queue.py             # QueueNode, QueueMetrics, QueuePartitionInfo
│   │   ├── cluster.py           # ClusterConfig, TotalResources
│   │   ├── balance.py           # BalanceValidationResult, AutoBalanceRequest
│   │   └── change_request.py    # ChangeRequest, ChangeRequestStatus, DiffPayload
│   ├── services/                # Бизнес-логика
│   │   ├── auth_service.py      # LDAP / Local гибридная аутентификация
│   │   ├── yarn_client.py       # REST API клиент YARN с поддержкой Kerberos SPNEGO
│   │   ├── capacity_service.py  # Парсинг и валидация иерархий очередей
│   │   ├── xml_generator.py     # Точечная модификация capacity-scheduler.xml
│   │   └── change_request_service.py # Управление жизненным циклом заявок (Submit -> Approve/Reject)
│   └── main.py                  # Входная точка приложения FastAPI, роутинг, CORS, /health
└── tests/                       # Автоматические тесты на pytest
```

---

## 🌐 Спецификация REST API

### Аутентификация (`/api/auth`)
- `POST /api/auth/login` — аутентификация по логину и паролю (LDAP / Local). Возвращает JWT Bearer токен.
- `GET /api/auth/me` — получение профиля текущего пользователя и его роли (ADMIN, WRITER, READER).
- `POST /api/auth/logout` — завершение сессии.

### Кластеры (`/api/clusters`)
- `GET /api/clusters` — список доступных YARN-кластеров с описаниями и типами безопасности.
- `GET /api/clusters/{cluster_id}` — детальная конфигурация кластера (ресурсы, партиции).

### Очереди и балансировка (`/api/queues`)
- `GET /api/queues/{cluster_id}` — получение полного дерева очередей (Live состояние из YARN RM).
- `POST /api/queues/{cluster_id}/balance` — валидация инварианта 100% и расчет автобалансировки веток очередей.
- `POST /api/queues/{cluster_id}/xml` — точечная генерация `capacity-scheduler.xml` с сохранением сторонних параметров кластера.

### Заявки на согласование (`/api/queues/{cluster_id}/change-requests`)
- `GET /api/queues/{cluster_id}/change-requests` — получение списка заявок с фильтрами по статусу (`SUBMITTED`, `APPROVED`, `REJECTED`).
- `POST /api/queues/{cluster_id}/change-requests` — создание новой заявки оператором (WRITER) с обоснованием.
- `PUT /api/queues/{cluster_id}/change-requests/{request_id}` — согласование (Approve) или отклонение (Reject) заявки администратором.

### Системные эндпоинты
- `GET /health` — проверка жизнеспособности сервиса (`{"status": "ok"}`) для Kubernetes Liveness/Readiness probes (без авторизации).

---

## 💻 Локальный запуск и разработка

### 1. Подготовка окружения
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Переменные окружения
| Переменная | Описание | Значение по умолчанию |
|---|---|---|
| `CONFIG_PATH` | Путь к файлу конфигурации `config.yaml` | `config/config.yaml` |
| `DB_PATH` | Путь к файлу SQLite базы данных | `backend/yarn_explorer.db` |
| `KRB5_CONFIG` | Путь к файлу `krb5.conf` | `/etc/krb5.conf` |
| `PYTHONUNBUFFERED` | Отключение буферизации вывода логов | `1` |

### 3. Запуск сервера разработки
```bash
export CONFIG_PATH=../demo/config.yaml
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

---

## 🧪 Тестирование

Запуск набора юнит-тестов с помощью `pytest`:
```bash
pytest backend/tests -v
```

Тестирование покрывает:
- Парсинг древовидной иерархии очередей и извлечение метрик RAM/vCPU.
- Алгоритм автоматической балансировки ветки до 100%.
- Точечную модификацию XML с сохранением необрабатываемых свойств и комментариев.
- Генерацию правил `yarn.scheduler.capacity.queue-mappings`.
- Ролевую модель доступа (RBAC) и генерацию JWT-токенов.
