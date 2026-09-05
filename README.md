# YARN Queue Explorer

**YARN Queue Explorer** — веб-приложение для мониторинга, интерактивной визуализации, моделирования и генерации конфигураций иерархии очередей **Apache Hadoop YARN Capacity Scheduler** в защищенных корпоративных мультикластерных средах.

---

## 📑 Содержание

- [Ключевые возможности](#-ключевые-возможности)
- [Архитектура решения](#-архитектура-решения)
- [Быстрый старт: Демо-стенд в Docker](#-быстрый-старт-демонстрационный-стенд-в-docker)
- [Тестовые учетные записи LDAP](#-тестовые-учетные-записи-ldap)
- [Локальная разработка](#-локальная-разработка)
- [Конфигурация (`config.yaml`)](#️-конфигурация-configyaml)
- [Развертывание в Kubernetes (Helm)](#️-развертывание-в-kubernetes-helm)
- [Тестирование](#-тестирование)
- [Структура проекта](#-структура-проекта)
- [Специализированная документация](#-дополнительная-документация)

---

## 📚 Дополнительная документация

| Документ | Содержание |
|---|---|
| 🎪 **[DEMO.md](DEMO.md)** | Подробное руководство по керберизированному демонстрационному стенду и 6 пошаговых сценариев работы |
| ☸️ **[helm/yarn-explorer/README.md](helm/yarn-explorer/README.md)** | Описание параметров `values.yaml` и инструкция по Helm-деплою в Kubernetes |
| ⚙️ **[backend/README.md](backend/README.md)** | Спецификация REST API, архитектура бэкенда (FastAPI), модели и запуск тестов |
| 🎨 **[frontend/README.md](frontend/README.md)** | Описание архитектуры клиентской части на Svelte 5 (Runes), компонентов и сборки |

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
- **Точечная модификация существующего файла конфигурации**:
  - Приложение получает текущий `capacity-scheduler.xml` из YARN ResourceManager (через REST API `/ws/v1/cluster/scheduler-conf` или локальный файл конфигурации кластера).
  - **Гарантированное сохранение всех необрабатываемых параметров**: такие параметры, как `yarn.scheduler.capacity.resource-calculator`, `schedule-asynchronously.enable`, `node-locality-delay`, права доступа ACL (`acl_submit_applications`, `acl_administer_queue`), приоритеты, а также пользовательские комментарии внутри XML, остаются нетронутыми.
  - Изменяются, добавляются и удаляются исключительно те параметры, которыми управляет YARN Queue Explorer.
- **Поддержка форматов ресурсов**:
  - Процентный формат: `yarn.scheduler.capacity.<queue>.capacity = 60.0`
  - Абсолютный формат YARN 3.x: `yarn.scheduler.capacity.<queue>.capacity = [memory=1258291,vcores=614]`
- Встроенные пошаговые инструкции по применению конфигурации на кластере с помощью `yarn rmadmin -refreshQueues`.

---

### 6. Расширенные параметры и лимиты приложений очередей
- **Политика планирования внутри очереди (`ordering-policy`)**:
  - `FIFO` — классическая очередь в порядке поступления приложений.
  - `FAIR` — справедливое разделение ресурсов между активными приложениями очереди.
- **Коэффициент лимита пользователя (`user-limit-factor`)**:
  - Плавная настройка коэффициента от `0.1` до `10.0` (значения $\le 1.0$ ограничивают пользователя частью гарантированной емкости очереди; значения $> 1.0$ позволяют пользователю утилизировать свободные burst-ресурсы кластера).
- **Лимиты приложений (Application Limits)**:
  - **`maximum-applications`**: лимит суммарного числа приложений в очереди (активных и ожидающих запуска).
  - **`maximum-am-resource-percent`**: максимальная доля ресурсов очереди, выделяемая под Application Masters (в процентах).
  - **`max-parallel-apps`**: лимит одновременно запущенных (running) приложений в очереди.
  - **`maximum-application-lifetime`**: максимальное время жизни приложения в секундах (`-1` — бессрочно).
- **Визуализация и управление**:
  - Интерактивный блок настроек в карточке редактирования очереди (`QueueEditDrawer`) и окне создания очереди (`AddQueueModal`).
  - Отображение дельт изменений лимитов в панели сравнения (`DiffPanel`).
  - Компактный столбец **Policy** в таблице с кликабельным бейджем политики и лимита (`FAIR · 0.2x` / `FIFO · 1.0x`), открывающий панель быстрой настройки.

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
./demo/start-demo.sh
```
*(или из папки `demo/`: `cd demo && docker compose up -d`)*

Подробное руководство со сценариями демонстрации и архитектурой стенда доступно в документе **[DEMO.md](DEMO.md)**.

### Остановка:
```bash
./demo/stop-demo.sh
```
*(или `cd demo && docker compose down -v`)*


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

## ☸️ Развертывание в Kubernetes (Helm)

Для развертывания YARN Queue Explorer в кластере Kubernetes подготовлен готовый к production Helm-чарт в директории `helm/yarn-explorer`.

### Возможности чарта:
- **Безопасность**: Запуск от непривилегированного пользователя (`non-root`, UID 10001, `readOnlyRootFilesystem: false`).
- **Персистентность**: Поддержка `PersistentVolumeClaim` для хранения локальной базы данных заявок SQLite (`/app/data/yarn_explorer.db`). При включенном PVC стратегия деплоя автоматически переключается на `Recreate`.
- **Kerberos / SPNEGO**:
  - Монтирование пользовательского `krb5.conf` через ConfigMap.
  - Поддержка создания K8s Secret с `keytab` (из base64-строки) или подключение уже существующего секрета (`existingSecret`).
- **Ingress**: Поддержка Ingress-контроллеров (включая `ingress-nginx`) с TLS-терминацией.
- **Health Probes**: Настроенные Liveness и Readiness пробы по эндпоинту `/health`.
- **Автоматический перезапуск подов**: При обновлении содержимого `config.yaml` или `krb5.conf` контроллер Deployment перезапускает поды за счет контрольных сумм в аннотациях (`checksum/config`, `checksum/krb5`).

### Быстрая установка:

```bash
# 1. Клонирование репозитория
git clone https://github.com/balookrd/yarn-explorer.git
cd yarn-explorer

# 2. Установка чарта со стандартными настройками
helm install yarn-explorer ./helm/yarn-explorer --namespace yarn-system --create-namespace
```

### Пример пользовательского `custom-values.yaml`:

```yaml
replicaCount: 1

image:
  repository: ghcr.io/balookrd/yarn-explorer
  tag: "latest"
  pullPolicy: IfNotPresent

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: yarn-explorer.company.local
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: yarn-explorer-tls
      hosts:
        - yarn-explorer.company.local

persistence:
  enabled: true
  size: 5Gi
  storageClassName: "fast-storage"

kerberos:
  enabled: true
  keytab:
    # Можно передать base64-содержимое keytab-файла:
    keytabBase64: "BQIAAABUAAI..."
    # Или использовать предварительно созданный K8s Secret:
    # existingSecret: "my-custom-keytab-secret"
    # secretKey: "yarn-explorer.keytab"
  krb5Conf: |
    [libdefaults]
      default_realm = COMPANY.LOCAL
      dns_lookup_realm = false
      dns_lookup_kdc = false
      ticket_lifetime = 24h
      renew_lifetime = 7d
      forwardable = true
    [realms]
      COMPANY.LOCAL = {
        kdc = kdc.company.local:88
        admin_server = kdc.company.local:749
      }

config:
  auth:
    mode: ldap
    jwt_secret: "prod-ultra-secure-random-jwt-secret-key"
    token_expiry_hours: 12
    ldap:
      server: "ldaps://corp-ad.company.local:636"
      base_dn: "DC=company,DC=local"
      bind_dn: "CN=svc-yarn-explorer,OU=ServiceAccounts,DC=company,DC=local"
      bind_password: "ServiceAccountPassword123"
      user_search_base: "OU=Users,DC=company,DC=local"
      group_search_base: "OU=Groups,DC=company,DC=local"
      role_mapping:
        admin_groups: ["CN=Hadoop-Admins,OU=Groups,DC=company,DC=local"]
        writer_groups: ["CN=Hadoop-Operators,OU=Groups,DC=company,DC=local"]
        reader_groups: ["CN=Hadoop-Analysts,OU=Groups,DC=company,DC=local"]
  kerberos:
    service_principal: "yarn-explorer@COMPANY.LOCAL"
    keytab_path: "/etc/security/keytabs/yarn-explorer.keytab"
    krb5_conf_path: "/etc/krb5.conf"
  clusters:
    - id: "prod-yarn"
      name: "Production Hadoop"
      description: "Hadoop 3.3 Production YARN Cluster"
      rm_hosts:
        - "rm1.company.local:8088"
        - "rm2.company.local:8088"
      kerberos_enabled: true
      default_partition: "DEFAULT"
```

Применение параметров:
```bash
helm upgrade --install yarn-explorer ./helm/yarn-explorer -f custom-values.yaml -n yarn-system
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
├── backend/                     # Бэкенд FastAPI (см. backend/README.md)
│   ├── app/
│   │   ├── api/                 # REST API роутеры (auth, clusters, queues, change_requests)
│   │   ├── core/                # Конфигурация, безопасность, токены, база SQLite
│   │   ├── models/              # Pydantic модели (QueueNode, Cluster, Balance, ChangeRequest)
│   │   └── services/            # Бизнес-логика (YarnClient, CapacityScheduler, XmlGenerator)
│   ├── tests/                   # Юнит-тесты на pytest
│   ├── requirements.txt         # Зависимости Python
│   └── README.md                # Документация бэкенда и REST API
├── frontend/                    # Фронтенд Svelte 5 (см. frontend/README.md)
│   ├── src/
│   │   ├── components/          # Svelte-компоненты (таблица, drawer, модалки, QueueMappings, Diff)
│   │   ├── utils/               # Утилиты форматирования RAM и vCPU
│   │   ├── api/                 # Клиентский HTTP-сервис
│   │   ├── App.svelte           # Корневой компонент приложения
│   │   └── types.ts             # TypeScript интерфейсы
│   ├── package.json             # Зависимости и скрипты сборки
│   ├── vite.config.ts           # Конфигурация сборщика Vite
│   └── README.md                # Документация фронтенда и компонентов
├── demo/                        # Полный демонстрационный стенд (Kerberos KDC, OpenLDAP, 2x Hadoop RM)
│   ├── docker-compose.yml       # Спецификация сервисов демо-стенда
│   ├── start-demo.sh            # Скрипт быстрого запуска стенда
│   ├── stop-demo.sh             # Скрипт остановки и очистки томов
│   ├── cluster-1/               # Hadoop RM 1 конфигурации (Production)
│   ├── cluster-2/               # Hadoop RM 2 конфигурации (Analytics & ML)
│   ├── kdc/                     # Kerberos KDC Dockerfile и скрипт инициализации
│   ├── ldap/                    # OpenLDAP конфигурация и пользователи
│   ├── config.yaml              # Конфиг YARN Explorer для демо-стенда
│   └── README.md                # Ссылка на руководство DEMO.md
├── helm/yarn-explorer/          # Production-ready Helm-чарт для развертывания в Kubernetes
│   ├── Chart.yaml               # Описание и метаданные чарта
│   ├── values.yaml              # Параметры по умолчанию (resources, ingress, kerberos, db)
│   ├── templates/               # Манифесты K8s (Deployment, Service, Ingress, PVC, ConfigMap, Secret)
│   └── README.md                # Документация чарта и таблица параметров
├── Dockerfile                   # Production Dockerfile YARN Explorer
├── DEMO.md                      # Подробное руководство по демонстрационному стенду
└── README.md                    # Главная документация проекта



```

---

## 📄 Лицензия

Распространяется под лицензией Apache License 2.0.
