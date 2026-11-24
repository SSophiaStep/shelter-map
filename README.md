# Shelter Map

Інтерактивна мапа укриттів та пунктів обігріву.
Високонавантажена система з пікоподібними read-запитами.

## Стек

FastAPI · PostgreSQL/PostGIS · SQLAlchemy 2 · Alembic · Redis · Nginx · Docker Compose

## Структура

- `backend/` — код застосунку та тести
- `docs/` — документація й архітектурні схеми
- `infra/` — Docker Compose, конфіги Nginx/PostgreSQL
- `scripts/` — допоміжні скрипти

## Архітектура

Див. [docs/architecture.md](docs/architecture.md).
Обґрунтування рішень лаби №2 (користувачі, ролі, доступ): [docs/lab2-architecture.md](docs/lab2-architecture.md).

## Запуск

```powershell
# 1. База даних (з папки infra)
docker compose up -d

# 2. Середовище та залежності (з папки backend)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt

# 3. Налаштування: скопіювати .env.example у .env і задати власний SECRET_KEY
copy .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"

# 4. Створити таблиці
alembic upgrade head

# 5. Створити адміністратора
python -m app.cli admin@example.com StrongPass123 --name "Admin"

# 6. Запустити сервер (обов'язково з папки backend)
uvicorn app.main:app --reload
```

Swagger: http://127.0.0.1:8000/docs (кнопка **Authorize** для входу).

## Середовища (лаба 3)

`APP_ENV=sandbox|production` вибирає файл `backend/.env.<середовище>` (шаблони `*.example`). У production `DEBUG` вимкнений, ключ ≥ 32 символи, база не може називатись `sandbox`. Деталі: [docs/lab3.md](docs/lab3.md).

## Docker (лаби 5–6, 8)

```powershell
cd infra
copy .env.example .env                                   # впишіть паролі та SECRET_KEY
docker compose up --build                                # db + redis + міграції + backend
docker compose --profile lb up --build -d                # + 3 репліки і Nginx на :8080
docker compose --profile lb --profile monitoring up -d   # + Prometheus :9090 та Grafana :3000
docker compose -f docker-compose.yml -f docker-compose.dev.yml up   # hot-reload
```

Звіти: [lab5](docs/lab5.md) · [lab6](docs/lab6.md).

## Навантажувальне тестування (лаби 4, 7, 8)

```powershell
cd backend
pip install -r loadtest/requirements.txt
psql ... -f loadtest/seed.sql ; python loadtest/seed_users.py   # 100 000 укриттів і 100 користувачів
bash loadtest/run_test.sh baseline 100 10 120s http://127.0.0.1:8000
python loadtest/analyze.py compare ../docs/img/cmp before=loadtest/results/baseline after=loadtest/results/optC
```

Звіти: [lab4](docs/lab4.md) · [lab7](docs/lab7.md) · [lab8](docs/lab8.md). Кеш Redis вмикається `CACHE_ENABLED=true`.

## CI

`.github/workflows/ci.yml`: ruff + міграції + pytest на кожен PR і push у `main`.

## Тести

Потрібна запущена БД (`docker compose up -d`). Тести самі створюють базу `shelter_map_test`.

```powershell
cd backend
pytest
```

## Основні маршрути

| Метод і шлях | Доступ |
|---|---|
| `POST /auth/register`, `POST /auth/login` | публічно |
| `GET /auth/me`, `GET /home/user` | авторизований користувач |
| `GET /home/admin`, `GET /admin/users`, `PATCH /admin/users/{id}/role` | лише адмін |
| `GET /places/nearby`, `GET /places/{id}`, `GET /places/{id}/reports` | публічно |
| `POST/PATCH/DELETE /places` | лише адмін |
| `POST /places/{id}/reports` | авторизований користувач |
| `PATCH/DELETE /reports/{id}` | автор відгуку або адмін |
| `PATCH /users/{id}` | власник профілю або адмін |
