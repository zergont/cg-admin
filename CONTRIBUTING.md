# CONTRIBUTING.md — CG Admin Panel

## Общие принципы

- **Единый конфиг** — все настройки проекта хранятся в `config.yaml` (один файл, без `.env`).
- **Версионирование** — каждый компонент (backend, frontend, deploy-скрипты) содержит номер версии для контроля. Backend: `__version__` в `app/main.py` + `config.yaml`. Frontend: `package.json`.
- **Будущая интеграция** — админ-панель в перспективе будет встроена в раздел настроек UI-telemetry (единый фронт). Код писать с учётом возможного переезда. Самостоятельный фронт админки будет убран.
- **Self-update** — обновление cg-admin выполняется через бэкенд UI-telemetry (не через саму себя).
- **Авторизация** — только LAN auto-admin (Bearer token + X-Real-IP проверка подсети). Cookie не используются.

## Стек

### Backend
- Python 3.12, FastAPI, Uvicorn
- aiosqlite (локальная SQLite для audit/update логов)
- asyncpg (read-only подключение к PostgreSQL для метрик)
- psutil (OS health)
- Конфиг: Pydantic модели + YAML

### Frontend
- React 19, TypeScript, Vite
- Tailwind CSS 4 (OKLch цветовая модель)
- shadcn/ui (new-york стиль), lucide-react
- TanStack React Query

## Стиль кода

- Backend: Python — PEP 8, типизация (type hints), async/await.
- Frontend: TypeScript strict, функциональные компоненты, хуки.
- Дизайн: тёмная тема, те же CSS-переменные и компоненты что в UI Dashboard.

## Git

- Основная ветка: `main`.
- Коммиты: осмысленные сообщения на русском или английском.
- Теги: `v0.1.0`, `v0.2.0` и т.д.

## Архитектурные решения

- **Авторизация** — Bearer token + LAN auto-admin (по X-Real-IP). Cookie `cg_session` не используется.
- **Self-update** — админка НЕ обновляет сама себя. Обновление cg-admin производится через бэкенд UI-telemetry.
- **Этапность** — разработка по этапам. MVP (Этап 1): Overview, ServicePage, Updates, AuditLog, Deploy.
- **Переносимость фронта** — компоненты пишутся без жёстких привязок к роутингу, чтобы в будущем встроить в UI-telemetry.
- **Стартовая версия** — `v0.1.0`.