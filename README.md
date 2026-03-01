# CG Admin Panel

Админ-панель сервера «Честная Генерация» — независимый сервис для мониторинга и управления всей инфраструктурой проекта.

**Версия:** `v0.1.0` (MVP)

## Возможности (Этап 1 — MVP)

- **Overview** — состояние сервера (CPU, RAM, Disk, Uptime) + список всех служб с индикаторами
- **Service Details** — systemd-статус, journald-логи, restart с подтверждением
- **Updates** — проверка и установка обновлений модулей (git pull + rebuild + restart)
- **Audit Log** — журнал всех административных действий

## Архитектура

┌─────────────────────────────────────────────────┐
│  Nginx :9443 (HTTPS)                            │
│  ┌──────────────┐  ┌─────────────────────────┐  │
│  │ /      → SPA │  │ /admin/      → SPA      │  │
│  │ /api/  → :5555│  │ /admin/api/ → :5556    │  │
│  │ UI Dashboard  │  │ CG Admin Panel          │  │
│  └──────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────┘
         │                        │
   UI Backend :5555        Admin Backend :5556
   (cg-dashboard)          (cg-admin)
         │                        │
    PostgreSQL :5432        SQLite (admin.db)
    (телеметрия)            (audit + update logs)

## Стек

| Слой     | Технологии                                      |
|----------|--------------------------------------------------|
| Backend  | Python 3.12, FastAPI, Uvicorn, aiosqlite, psutil |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4       |
| UI Kit   | shadcn/ui (new-york), lucide-react               |
| Data     | TanStack React Query                             |
| Deploy   | systemd, nginx, Ubuntu 24.04                     |

## Структура проекта

```
cg-admin/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI, __version__ = "0.1.0"
│   │   ├── config.py         # Pydantic + YAML
│   │   ├── auth.py           # Bearer token + LAN auto-admin
│   │   ├── database.py       # SQLite (aiosqlite)
│   │   ├── models.py         # Pydantic-схемы ответов
│   │   ├── routers/
│   │   │   ├── overview.py   # GET /admin/api/overview
│   │   │   ├── services.py   # GET/POST /admin/api/services/*
│   │   │   ├── updates.py    # GET/POST /admin/api/updates/*
│   │   │   └── audit.py      # GET /admin/api/audit
│   │   └── services/
│   │       ├── systemd.py    # systemctl, journalctl
│   │       ├── os_health.py  # CPU/RAM/Disk/Uptime (psutil)
│   │       └── updater.py    # git fetch/pull + build + restart
│   └── requirements.txt
├── frontend/
│   ├── package.json          # version: "0.1.0"
│   ├── vite.config.ts
│   ├── components.json       # shadcn/ui (new-york)
│   └── src/
│       ├── pages/
│       │   ├── OverviewPage.tsx
│       │   ├── ServicePage.tsx
│       │   ├── UpdatesPage.tsx
│       │   └── AuditPage.tsx
│       ├── components/
│       │   ├── Layout.tsx
│       │   ├── ServiceCard.tsx
│       │   ├── OsHealthBar.tsx
│       │   └── LogViewer.tsx
│       └── lib/
│           ├── api.ts
│           └── utils.ts
├── deploy/
│   ├── install.sh            # v0.1.0
│   ├── cg-admin.service
│   └── cg-admin-nginx.conf
├── config.yaml.example       # версия конфига: 0.1.0
├── .gitignore
├── CONTRIBUTING.md
└── README.md
```

## Доступ к панели

| Метод | URL |
|-------|-----|
| Через браузер (LAN/VPN) | **https://192.168.0.130:9443/admin/** |
| Из UI Dashboard | Шестерёнка ⚙️ в шапке (только для admin) |
| API docs (Swagger) | https://192.168.0.130:9443/admin/api/docs |

> Панель доступна **только из LAN** (192.168.0.0/16) и **Wireguard VPN** (10.0.0.0/8).  
> Nginx ограничивает доступ по IP — извне не откроется.

## Установка на сервер

### Требования
- Ubuntu 24.04 LTS
- Python 3.12+, Node.js 20+, git
- Пользователь `cg` (будет создан автоматически)

### Первая установка

```bash
# 1. Клонируем репозиторий
sudo git clone https://github.com/zergont/cg-admin.git /opt/cg-admin

# 2. Запускаем установщик
sudo bash /opt/cg-admin/deploy/install.sh

# 3. Проверяем конфиг (токен подтянется автоматически из UI Dashboard)
cat /opt/cg-admin/config.yaml
```

> `install.sh` автоматически находит `token` и `postgres_password`  
> из `/opt/cg-dashboard/config.yaml` и подставляет в конфиг админки.  
> Если Dashboard не установлен — укажите значения вручную:  
> `sudo nano /opt/cg-admin/config.yaml`

После установки сервис **автоматически запускается при загрузке сервера** (`systemctl enable`).

### Обновление

```bash
# На сервере: install.sh сам подтянет текущую ветку и пересоберёт
cd /opt/cg-admin
sudo bash deploy/install.sh
```

Скрипт `install.sh` идемпотентен — определяет, что репо уже есть, и выполняет обновление:
- `pip install -r requirements.txt` (если зависимости изменились)
- `npm run build` (пересборка фронта)
- `systemctl restart cg-admin`

### Управление сервисом

```bash
# Статус
sudo systemctl status cg-admin

# Логи (live)
journalctl -u cg-admin -f

# Перезапуск
sudo systemctl restart cg-admin

# Остановка
sudo systemctl stop cg-admin
```

### Разработка (локально)

```bash
# Backend
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
CG_ADMIN_CONFIG=../config.yaml uvicorn app.main:app --reload --port 5556
```

```bash
# Frontend (в отдельном терминале)
cd frontend
npm install
npm run dev
```

Dev-сервер Vite проксирует `/admin/api/*` → `http://127.0.0.1:5556`.

## API (Этап 1)

Все эндпоинты: `/admin/api/*`.
Авторизация:
- `GET` — `Bearer token` или LAN auto-admin
- `POST` — только `Bearer token`

| Метод | Эндпоинт                          | Описание                    |
|-------|------------------------------------|-----------------------------|
| GET   | /admin/api/overview                | OS health + список служб    |
| GET   | /admin/api/services                | Все службы                  |
| GET   | /admin/api/services/{unit}/status  | Детали службы               |
| GET   | /admin/api/services/{unit}/logs    | Журнал (journald)           |
| POST  | /admin/api/services/{unit}/restart | Перезапуск службы           |
| GET   | /admin/api/updates                 | Проверка обновлений         |
| POST  | /admin/api/updates/{module}        | Запуск обновления           |
| GET   | /admin/api/updates/{module}/status | Статус обновления           |
| GET   | /admin/api/audit                   | Журнал аудита               |

## Конфигурация

Единый файл `config.yaml` — см. `config.yaml.example`.

## Дорожная карта

- [x] Этап 1 — MVP (overview, services, updates, audit)
- [ ] Этап 2 — Database page, VPN peers, Chrony
- [ ] Этап 3 — Share Links, RBAC, 2FA
- [ ] Интеграция фронта в UI-telemetry

## Лицензия

Внутренний проект. Все права защищены.

## Тегирование релиза

```bash
git tag v0.1.0
git push origin v0.1.0