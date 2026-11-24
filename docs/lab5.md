# Лабораторна робота №5. Контейнеризація (Docker)

## 1. Що створено

| Файл | Призначення |
|---|---|
| `backend/Dockerfile` | multi-stage збірка: `builder` (build-essential, wheels) → `runtime` (python:3.12-slim, користувач `app` без root, `HEALTHCHECK` на `/live`) |
| `backend/.dockerignore` | виключає `.git`, `.venv`, `__pycache__`, `.env*`, `tests`, `loadtest`, логи |
| `infra/docker-compose.yml` | сервіси `db`, `redis`, `migrate`, `backend` (+ профілі `lb`, `monitoring`) |
| `infra/docker-compose.dev.yml` | режим розробки: bind mount коду + `--reload` |
| `infra/.env.example`, `.env.production.example` | змінні оточення compose |

## 2. Як це влаштовано

- **БД:** образ `postgis/postgis:16-3.4`, дані в іменованому томі `pgdata` — переживають `docker compose down` (видаляє лише `down -v`). Порт БД відкритий тільки на `127.0.0.1:55432`.
- **Змінні:** паролі й ключі беруться з `infra/.env` (підстановка `${VAR}`), у образ не потрапляють (`.dockerignore`).
- **Мережі:** `internal` (db, redis, backend, migrate — без доступу ззовні) і `edge` (те, що публікується: backend/nginx/grafana).
- **Черговість запуску:** `db` та `redis` мають `healthcheck` (`pg_isready`, `redis-cli ping`) → `migrate` чекає `service_healthy`, виконує `alembic upgrade head` і завершується → `backend` стартує за умови `service_completed_successfully`.
- **Multi-stage:** компілятори лишаються в `builder`, у фінальний образ копіюються тільки зібрані пакунки — менший образ і менша поверхня атаки.
- **Hot-reload:** `docker-compose.dev.yml` монтує `../backend/app` у контейнер і запускає `uvicorn --reload` (з `WATCHFILES_FORCE_POLLING` для Windows) — перезбірка образу не потрібна.

## 3. Запуск (PowerShell, папка `infra`)

```powershell
copy .env.example .env            # впишіть свої паролі та SECRET_KEY
docker compose up --build         # вся система однією командою
docker compose ps                 # усі сервіси healthy, migrate — Exited (0)
curl.exe http://localhost:8000/health
```

Режим розробки: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`.

Перевірка збереження даних: створіть укриття → `docker compose down` → `docker compose up -d` → дані на місці.

Розмір образу: `docker images shelter-map-backend`.

## 4. Скриншоти для звіту (зробіть самі)

1. `docker compose up --build` — кінець логу з рядком Application startup complete.
2. `docker compose ps` — статуси healthy.
3. `http://localhost:8000/docs` у браузері та `/health`.
4. `docker volume ls` — том `shelter-map_pgdata`.

> **Чесна примітка.** У середовищі, де я готувала проєкт, Docker Hub був недоступний, тому `docker compose up` там не запускався: файли перевірені на синтаксис YAML, а сам застосунок, міграції й Nginx — запущені нативно (результати в лабах 4, 6–8). Фактичний запуск контейнерів і скриншоти потрібно зробити на вашому ПК.
