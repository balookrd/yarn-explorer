# YARN Queue Explorer

**YARN Queue Explorer** — веб-приложение для мониторинга, интерактивной визуализации, моделирования и генерации конфигураций иерархии очередей **Apache Hadoop YARN Capacity Scheduler** в защищенных корпоративных мультикластерных средах.

---

## 🚀 Ключевые возможности

### 1. Мультикластерность и безопасность
- **Поддержка множества кластеров**: единая точка управления для Production, Analytics, ML и других YARN-кластеров с переключением в реальном времени.
- **Kerberos & SPNEGO**: аутентификация запросов к YARN ResourceManager REST API через защищенный Kerberos SPNEGO (с поддержкой keytab и `krb5.conf`).
- **Корпоративный RBAC & LDAP**:
  - Аутентификация пользователей через корпоративный каталог OpenLDAP / Active Directory или локальный список пользователей.
  - Ролевая модель доступа:
    - **ADMIN** — просмотр, добавление/удаление очередей, редактирование, балансировка, генерация `capacity-scheduler.xml`.
    - **WRITER** — просмотр, редактирование параметров очередей, моделирование изменений и просмотр diff.
    - **READER** — безопасный режим только для чтения топологии и метрик утилизации очередей.

---

### 2. Разделение квот на RAM и vCPU
- **Раздельный учет ресурсов**: раздельное задание гарантированной емкости (Capacity) и максимального лимита (Max Capacity / Burst) для **RAM** (MB, GB, TB) и **vCPU** (Cores).
- **Переключение режимов отображения**:
  - **Проценты (%)**: классическое распределение долей кластера.
  - **Абсолютные величины (GB / CPU)**: физический объем оперативной памяти и ядер процессора.
- **Двусторонний автопересчет**:
  - Ввод в гигабайтах автоматически пересчитывает проценты от суммарной емкости кластера.
  - Ввод в процентах автоматически вычисляет доступный объем памяти и ядер.
- **Связывание ресурсов**:
  - Режим **«Связаны (RAM = vCPU)»**: синхронное пропорциональное выделение памяти и вычислительных ядер.
  - Режим **«Раздельно»**: независимая настройка памяти и ядер для memory-bound или compute-heavy очередей.

---

### 3. Интерактивное моделирование (Draft Sandbox & Diff)
- **Безопасная песочница**: все изменения квот, добавление новых и удаление существующих очередей производятся в изолированном клиентском черновике (draft) без риска повредить боевую конфигурацию.
- **Визуализация изменений на лету**: подсветка измененных очередей в дереве с отображением исходных и новых значений, а также дельты изменения.
- **Панель сравнения (Diff Panel)**: структурированное отображение всех изменений в формате Unified Diff перед подтверждением и генерацией XML.

---

### 4. Валидация баланса веток (Capacity Balancer)
- Автоматический контроль инварианта Capacity Scheduler: сумма емкостей дочерних очередей на каждом уровне иерархии должна составлять ровно 100% (или соответствовать емкости родителя).
- Раздельная валидация баланса для **RAM** и **vCPU**.
- Предупреждения о недораспределении (underallocated) и перераспределении (overallocated) ресурсов с точностью до десятых долей.

---

### 5. Экспорт и генерация `capacity-scheduler.xml`
- Генерация синтаксически корректного конфигурационного файла Hadoop XML с форматированием и метаданными (кем и когда сгенерирован файл).
- **Поддержка двух форматов ресурсов**:
  - Процентный формат: `yarn.scheduler.capacity.<queue>.capacity = 60.0`
  - Абсолютный формат YARN 3.x: `yarn.scheduler.capacity.<queue>.capacity = [memory=1258291,vcores=614]`
- Встроенные пошаговые инструкции по применению конфигурации на кластере с помощью `yarn rmadmin -refreshQueues`.

---

### 6. Расширенные параметры очередей (Ordering Policy & User Limit Factor)
- **Политика планирования внутри очереди (`ordering-policy`)**:
  - `FIFO` — классическая очередь в порядке поступления приложений.
  - `FAIR` — справедливое разделение ресурсов между активными приложениями очереди.
- **Коэффициент лимита пользователя (`user-limit-factor`)**:
  - Плавная настройка коэффициента от `0.1` до `10.0` (значения $\le 1.0$ ограничивают пользователя частью гарантированной емкости очереди; значения $> 1.0$ позволяют пользователю утилизировать свободные burst-ресурсы кластера).
- **Визуализация в таблице**:
  - Отдельный компактный столбец **Policy** с кликабельным бейджем политики и лимита (`FAIR · 0.2x` / `FIFO · 1.0x`), открывающий панель быстрой настройки.

---

### 7. Управление сопоставлением пользователей и очередей (Queue Mappings)
- **Конструктор правил `yarn.scheduler.capacity.queue-mappings`**:
  - Назначение очередей для пользователей (`u:`) и групп (`g:`).
  - Поддержка динамических макроподстановок: `%user` (по имени пользователя) и `%group` (по имени первичной группы).
  - Выбор целевой очереди из выпадающего дерева очередей кластера.
  - Управление приоритетом правил с помощью перемещения вверх/вниз (Move Up / Down).
  - Режим **Raw-текста** для быстрого копирования и редактирования строки маппингов через запятую.
- **Флаг принудительного переопределения (`queue-mappings-override.enable`)**:
  - Переключатель разрешения переопределения очереди, запрошенной приложением.
- **Моделирование и Diff**:
  - Сохранение правил в черновик, сравнение Live vs Draft конфигурации в Diff Panel и автоматический экспорт в `capacity-scheduler.xml`.

---

### 8. Процесс согласования изменений (Change Requests / Approval Workflow)
- **Серверное хранение заявок (SQLite)**: операторы (роль **WRITER**) могут отправлять смоделированные изменения на согласование с указанием обоснования. Заявки персистентно сохраняются на сервере.
- **Входящие заявки у администратора**: бейдж в шапке с количеством ожидающих рассмотрения заявок (`SUBMITTED`).
- **Интерактивный центр согласования**:
  - Просмотр списка заявок с фильтрами («Все», «Ожидают», «Одобрены», «Отклонены»).
  - Детальный Side-by-side Diff изменений по каждой очереди (Capacity, Max Capacity, RAM MB, vCPU Cores).
  - Возможность загрузить предложенные изменения в интерактивный редактор очереди.
  - Одобрение (**Approve**) с автоматической генерацией `capacity-scheduler.xml` или отклонение (**Reject**) с указанием причины.

---

## 🏛 Архитектура решения

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Svelte 5 + Vite)                   │
│  - QueueTreeTable (Дерево очередей, RAM/vCPU, утилизация)      │
│  - QueueEditDrawer (Редактирование, автопересчет, связка)       │
│  - AddQueueModal / DiffPanel / XmlExportModal                   │
└────────────────────────────────┬────────────────────────────────┘
                                 │ HTTP REST API (Bearer JWT)
┌────────────────────────────────▼────────────────────────────────┐
│                    Backend (FastAPI + Python 3.12)              │
│  - /api/auth       (LDAP / Local JWT аутентификация)            │
│  - /api/clusters   (Список кластеров, переключение)             │
│  - /api/queues     (Дерево очередей, парсинг, балансировка)     │
│  - /api/xml        (Генерация capacity-scheduler.xml)           │
└───────┬────────────────────────┬────────────────────────┬───────┘
        │                        │                        │
        │ Kerberos SPNEGO        │ Kerberos SPNEGO        │ LDAP Search
┌───────▼──────────────┐ ┌───────▼──────────────┐ ┌───────▼──────────────┐
│ YARN RM Cluster 1    │ │ YARN RM Cluster 2    │ │ OpenLDAP / AD        │
│ (Production Hadoop)  │ │ (Analytics & ML)     │ │ (Пользователи/Группы)│
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘
```

---

## 🐳 Быстрый старт: Демонстрационный стенд в Docker

В репозиторий включен полностью автономный керберизированный демо-стенд, разворачиваемый одной командой.

### Состав стенда:
| Контейнер | Назначение | Адрес / Порт |
|---|---|---|
| **`yarn-demo-explorer`** | Сервис YARN Explorer (Backend + UI) | **[http://localhost:8003](http://localhost:8003)** |
| **`yarn-demo-rm-1`** | YARN RM 1 («Production Hadoop Cluster») | [http://localhost:8088](http://localhost:8088) |
| **`yarn-demo-rm-2`** | YARN RM 2 («Analytics & ML Cluster») | [http://localhost:8089](http://localhost:8089) |
| **`yarn-demo-ldap`** | Сервер каталогов OpenLDAP | `localhost:389` |
| **`yarn-demo-kdc`** | Kerberos KDC (`COMPANY.LOCAL`) | `localhost:88` |

### Запуск:
```bash
./start-demo.sh
```
*(или напрямую через `docker compose -f docker-compose.demo.yml up -d`)*

### Остановка:
```bash
./stop-demo.sh
```

---

## 🔐 Тестовые учетные записи (LDAP)

| Логин | Пароль | Роль | Группа LDAP | Доступные действия |
|---|---|---|---|---|
| **`admin_user`** | `password123` | **ADMIN** | `hadoop-admins` | Полный доступ: редактирование, добавление, балансировка, генерация XML |
| **`writer_user`** | `password123` | **WRITER** | `yarn-operators` | Просмотр, редактирование параметров, просмотр diff |
| **`reader_user`** | `password123` | **READER** | `bi-analysts` | Только просмотр состояния и очередей |

---

## 💻 Локальная разработка

### Требования:
- Python 3.11+
- Node.js 20+ и npm
- Библиотеки Kerberos (`krb5-devel` в Linux или Xcode Command Line Tools в macOS)

### 1. Запуск Backend:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Запуск сервера разработки
export CONFIG_PATH=../demo/config.yaml
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 2. Запуск Frontend:
```bash
cd frontend
npm install
npm run dev
```
Фронтенд будет доступен по адресу: `http://localhost:5173` (с автоматическим проксированием API-запросов на бэкенд `localhost:8080`).

### 3. Сборка Frontend в production:
```bash
cd frontend
npm run build
```
Статические файлы компилируются в директорию `frontend/dist` и автоматически раздаются FastAPI бэкендом в production-режиме.

---

## ⚙️ Конфигурация (`config.yaml`)

Сервис настраивается через YAML-файл (путь задается переменной окружения `CONFIG_PATH`):

```yaml
auth:
  mode: hybrid          # ldap, local или hybrid
  jwt_secret: "your-secret-key"
  token_expiry_hours: 8
  ldap:
    server: "ldap://ldap:389"
    base_dn: "dc=company,dc=local"
    bind_dn: "cn=admin,dc=company,dc=local"
    bind_password: "adminpassword"
    user_search_base: "ou=users,dc=company,dc=local"
    group_search_base: "ou=groups,dc=company,dc=local"
    role_mapping:
      admin_groups: ["hadoop-admins"]
      writer_groups: ["yarn-operators"]
      reader_groups: ["bi-analysts"]

kerberos:
  service_principal: "yarn-explorer@COMPANY.LOCAL"
  keytab_path: "/etc/security/keytabs/yarn-explorer.keytab"
  krb5_conf_path: "/etc/krb5.conf"

clusters:
  - id: "prod-yarn"
    name: "Production Hadoop Cluster"
    description: "Основной производственный YARN кластер"
    rm_hosts:
      - "yarn-rm-1:8088"
    kerberos_enabled: true
    default_partition: "DEFAULT"
    total_resources:
      memory_mb: 2097152   # 2048 GB RAM
      vcores: 1024          # 1024 Cores
```

---

## 🧪 Тестирование

Запуск набора автоматических тестов бэкенда:
```bash
# В виртуальном окружении:
pytest backend/tests

# Или внутри запущенного Docker контейнера:
docker exec yarn-demo-explorer pytest backend/tests
```

Проверка типов и синтаксиса фронтенда:
```bash
cd frontend
npm run check
```

---

## 📁 Структура проекта

```
yarn-explorer/
├── backend/
│   ├── app/
│   │   ├── api/                 # REST API роутеры (auth, clusters, queues)
│   │   ├── core/                # Конфигурация, безопасность, токены
│   │   ├── models/              # Pydantic модели (QueueNode, Cluster, Balance)
│   │   └── services/            # Бизнес-логика (YarnClient, CapacityScheduler, XmlGenerator)
│   ├── tests/                   # Юнит-тесты на pytest
│   └── requirements.txt         # Зависимости Python
├── frontend/
│   ├── src/
│   │   ├── components/          # Svelte-компоненты (таблица, drawer, модалки, QueueMappingsModal)
│   │   ├── utils/               # Утилиты форматирования RAM и vCPU
│   │   ├── api/                 # Клиентский HTTP-сервис
│   │   ├── App.svelte           # Корневой компонент приложения
│   │   └── types.ts             # TypeScript интерфейсы
│   ├── package.json             # Зависимости и скрипты сборки
│   └── vite.config.ts           # Конфигурация сборщика Vite
├── demo/                        # Конфигурации демонстрационного стенда
│   ├── cluster-1/               # Hadoop RM 1 конфигурации
│   ├── cluster-2/               # Hadoop RM 2 конфигурации
│   ├── kdc/                     # Kerberos KDC Dockerfile и генерация keytabs
│   ├── ldap/                    # OpenLDAP конфигурация и пользователи
│   └── config.yaml              # Конфиг YARN Explorer для демо-стенда
├── docker-compose.demo.yml      # Docker Compose демо-стенда
├── Dockerfile                   # Production Dockerfile YARN Explorer
├── start-demo.sh                # Скрипт быстрого запуска стенда
└── stop-demo.sh                 # Скрипт остановки стенда
```

---

## 📄 Лицензия

Распространяется под лицензией Apache License 2.0.
