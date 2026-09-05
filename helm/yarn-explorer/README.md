# Helm Chart: YARN Queue Explorer

Production-ready Helm-чарт для развертывания веб-приложения **YARN Queue Explorer** (Apache Hadoop Capacity Scheduler UI) в кластере Kubernetes.

## 🚀 Возможности чарта

- **Безопасность (Non-root)**: запуск контейнера от непривилегированного пользователя (UID 10001) с настраиваемым `securityContext`.
- **Интеграция с Kerberos / SPNEGO**:
  - Монтирование пользовательского файла конфигурации `krb5.conf` через ConfigMap.
  - Поддержка создания K8s Secret с base64-кодированным keytab (`keytabBase64`) или использование существующего секрета (`existingSecret`).
- **Персистентность SQLite**: автоматическое создание `PersistentVolumeClaim` для хранения базы данных заявок (`/app/data/yarn_explorer.db`). При включенном PVC стратегия деплоя автоматически переключается на `Recreate` для исключения блокировок базы данных.
- **Корпоративная аутентификация**: полная поддержка конфигурации LDAP/Active Directory и сопоставления групп с ролями (ADMIN, WRITER, READER).
- **Ingress & TLS**: интеграция с Ingress-контроллерами (`ingress-nginx`, Traefik и др.) и автоматическая TLS-терминация.
- **Health Probes**: Liveness и Readiness пробы по эндпоинту `/health`.
- **Автоматический перезапуск подов**: аннотации с контрольными суммами конфигурации (`checksum/config`, `checksum/krb5`) для автоматического бесшовного перезапуска подов при обновлении ConfigMap/Secret.

---

## 📦 Установка чарта

### 1. Добавление репозитория или локальная установка
```bash
# Клонирование репозитория
git clone https://github.com/balookrd/yarn-explorer.git
cd yarn-explorer

# Установка чарта в namespace yarn-system
helm install yarn-explorer ./helm/yarn-explorer \
  --namespace yarn-system \
  --create-namespace
```

### 2. Установка с пользовательскими параметрами (`custom-values.yaml`)
```bash
helm upgrade --install yarn-explorer ./helm/yarn-explorer \
  -f custom-values.yaml \
  --namespace yarn-system \
  --create-namespace
```

### 3. Удаление релиза
```bash
helm uninstall yarn-explorer --namespace yarn-system
```

---

## ⚙️ Параметры конфигурации (`values.yaml`)

### Основные параметры

| Параметр | Описание | Значение по умолчанию |
|---|---|---|
| `replicaCount` | Количество реплик Deployment | `1` |
| `image.repository` | Docker-образ приложения | `ghcr.io/balookrd/yarn-explorer` |
| `image.tag` | Тег Docker-образа | `latest` (или `appVersion`) |
| `image.pullPolicy` | Политика скачивания образа | `IfNotPresent` |
| `imagePullSecrets` | Секреты для скачивания из приватных реестров | `[]` |
| `nameOverride` | Переопределение короткого имени релиза | `""` |
| `fullnameOverride` | Переопределение полного имени релиза | `""` |

### Сеть и Ingress

| Параметр | Описание | Значение по умолчанию |
|---|---|---|
| `service.type` | Тип Kubernetes Service | `ClusterIP` |
| `service.port` | Внешний порт сервиса | `80` |
| `service.targetPort` | Порт контейнера | `8080` |
| `ingress.enabled` | Включение создания Ingress | `false` |
| `ingress.className` | Имя IngressClass (например `nginx`) | `""` |
| `ingress.annotations` | Дополнительные аннотации Ingress | `{}` |
| `ingress.hosts` | Список виртуальных хостов и путей | `[{host: "yarn-explorer.local", paths: [{path: "/", pathType: "Prefix"}]}]` |
| `ingress.tls` | Настройки TLS сертификатов | `[]` |

### Ресурсы и Probes

| Параметр | Описание | Значение по умолчанию |
|---|---|---|
| `resources.limits.cpu` | Лимит CPU | `1000m` |
| `resources.limits.memory` | Лимит оперативной памяти | `1Gi` |
| `resources.requests.cpu` | Гарантированный CPU | `100m` |
| `resources.requests.memory` | Гарантированная память | `256Mi` |
| `livenessProbe.httpGet.path` | Путь Liveness пробы | `/health` |
| `readinessProbe.httpGet.path` | Путь Readiness пробы | `/health` |

### Персистентное хранилище (SQLite)

| Параметр | Описание | Значение по умолчанию |
|---|---|---|
| `persistence.enabled` | Включение PersistentVolumeClaim | `true` |
| `persistence.storageClassName` | StorageClass тома (null — дефолтный) | `null` |
| `persistence.accessMode` | Режим доступа тома | `ReadWriteOnce` |
| `persistence.size` | Размер постоянного тома | `1Gi` |
| `persistence.mountPath` | Точка монтирования тома в контейнере | `/app/data` |
| `persistence.dbName` | Имя файла SQLite базы данных | `yarn_explorer.db` |

### Kerberos / SPNEGO

| Параметр | Описание | Значение по умолчанию |
|---|---|---|
| `kerberos.enabled` | Включение монтирования Kerberos конфигурации | `false` |
| `kerberos.keytab.keytabBase64` | Base64-строка keytab файла (создаст K8s Secret) | `""` |
| `kerberos.keytab.existingSecret` | Имя уже созданного K8s Secret с keytab | `""` |
| `kerberos.keytab.secretKey` | Ключ внутри Secret, содержащий keytab | `yarn-explorer.keytab` |
| `kerberos.keytab.mountPath` | Директория монтирования keytab в контейнере | `/etc/security/keytabs` |
| `kerberos.krb5Conf` | Текстовое содержимое файла `krb5.conf` | `""` |

---

## 📝 Пример production `custom-values.yaml`

```yaml
replicaCount: 1

image:
  repository: my-registry.company.local/bigdata/yarn-explorer
  tag: "1.0.0"
  pullPolicy: IfNotPresent

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/proxy-body-size: "32m"
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
  storageClassName: "fast-rbd"
  size: 10Gi

kerberos:
  enabled: true
  keytab:
    keytabBase64: "BQIAAABUAAI..."
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
        kdc = kdc1.company.local:88
        kdc = kdc2.company.local:88
        admin_server = kdc1.company.local:749
      }

config:
  auth:
    mode: ldap
    jwt_secret: "super-secure-production-jwt-token-key-2026"
    token_expiry_hours: 12
    ldap:
      server: "ldaps://corp-ad.company.local:636"
      base_dn: "DC=company,DC=local"
      bind_dn: "CN=svc-yarn-explorer,OU=ServiceAccounts,DC=company,DC=local"
      bind_password: "ProdServicePasswordHere"
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
