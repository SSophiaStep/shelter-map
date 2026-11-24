# Лабораторна робота №3. Розділення середовищ, конфігурація та CI/CD

## 1. Конфігурація за середовищами

Налаштування читає `app/core/config.py` (pydantic-settings). Середовище вибирає змінна `APP_ENV` (`sandbox` за замовчуванням або `production`). Файли читаються в порядку: `backend/.env` → `backend/.env.<APP_ENV>`, пізніший файл має пріоритет, а змінні процесу (Docker, CI) — найвищий.

| Параметр | sandbox | production |
|---|---|---|
| Файл | `.env.sandbox` | `.env.production` |
| База даних | `shelter_sandbox` | `shelter_production` |
| `DEBUG` | `true` дозволено | примусово `false` |
| `SQL_ECHO` | за потреби | `false` |
| `SECRET_KEY` | тестовий | унікальний, ≥32 символи |

Шаблони без секретів: `.env.sandbox.example`, `.env.production.example`. Реальні `.env.*` додані до `.gitignore`.

### Захисні правила (валідатор Settings)

Застосунок **не стартує**, якщо:
- у `production` ключ коротший за 32 символи або містить `change-me`;
- у `production` назва БД містить `sandbox` (і навпаки, у `sandbox` — `production`), тобто неможливо випадково підключити «не ту» базу;
- `production` з `DEBUG=true` — значення примусово скидається у `false`.

### Приховування stack trace

Глобальний обробник `Exception` пише повну помилку тільки в лог (`logger.exception`), клієнт отримує `500 {"detail":"Internal server error"}` без шляхів файлів і SQL. Перевіряє тест `test_errors_and_observability.py`.

## 2. Інструкція запуску

```powershell
cd backend
# sandbox (за замовчуванням)
copy .env.sandbox.example .env.sandbox
alembic upgrade head
uvicorn app.main:app --reload

# production (окрема БД!)
copy .env.production.example .env.production      # вписати свій SECRET_KEY та пароль БД
$env:APP_ENV = "production"
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Згенерувати ключ: `python -c "import secrets; print(secrets.token_hex(32))"`.

У Docker: `infra/.env` (sandbox) або `infra/.env.production`; запуск
`docker compose --env-file .env.production -p shelter-prod up -d --build` — окремий проєкт має окремі контейнери й томи, тому дані середовищ не змішуються.

## 3. Додаткове: CI/CD (GitHub Actions)

Файл `.github/workflows/ci.yml` запускається на кожен PR і push у `main`:
1. піднімає сервіси PostGIS та Redis;
2. встановлює Python 3.12 і залежності;
3. `ruff check` та `ruff format --check`;
4. `alembic upgrade head` (перевірка міграцій);
5. `pytest` (48 тестів).

Merge у `main` можна заборонити без зеленого CI: *Settings → Branches → Branch protection → Require status checks*.

## 4. Перевірка

- `pytest backend/tests/test_config.py` — правила середовищ (ключ, назви БД, DEBUG).
- Скриншот зеленого запуску: вкладка **Actions** у GitHub після push.
