# HiTalent API

REST API для управления иерархией подразделений и сотрудниками компании.

## Стек

| Компонент | Версия |
|-----------|--------|
| Python | 3.12 |
| FastAPI | 0.111 |
| PostgreSQL | 16 |
| SQLAlchemy | 2.0 |
| Alembic | 1.13 |
| Docker / Docker Compose | — |

---

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone <repo_url>
cd hitalent_test
```

### 2. Создать `.env` (уже есть в репозитории, при необходимости отредактировать)

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=hitalent_db
DATABASE_URL=postgresql://postgres:postgres@db:5432/hitalent_db
```

### 3. Запустить

```bash
docker compose up --build
```

При старте контейнер автоматически:
1. Применяет все Alembic-миграции (`alembic upgrade head`)
2. Запускает uvicorn с hot-reload на порту **8000**

### 4. Проверить

| URL | Описание |
|-----|----------|
| http://localhost:8000/docs | Swagger UI (интерактивная документация) |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/ | Health-check |

---

## API

### Подразделения

| Метод | URL | Описание |
|-------|-----|----------|
| `POST` | `/departments/` | Создать подразделение |
| `GET` | `/departments/{id}` | Получить подразделение с поддеревом и сотрудниками |
| `PATCH` | `/departments/{id}` | Переименовать или переместить |
| `DELETE` | `/departments/{id}` | Удалить (cascade или reassign) |
| `POST` | `/departments/{id}/employees/` | Добавить сотрудника |

### Query-параметры GET `/departments/{id}`

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|-------------|----------|
| `depth` | int | `1` | Глубина вложенных подразделений (1–5) |
| `include_employees` | bool | `true` | Включить список сотрудников |
| `sort_by` | string | `full_name` | Сортировка сотрудников: `full_name` или `created_at` |

### Режимы удаления `DELETE /departments/{id}`

| `mode` | Поведение |
|--------|-----------|
| `cascade` | Удалить подразделение, всех сотрудников и все дочерние подразделения рекурсивно (ON DELETE CASCADE на уровне БД) |
| `reassign` | Удалить подразделение; сотрудников перевести в `reassign_to_department_id`; дочерние подразделения поднять на уровень выше |

---

## Миграции

```bash
# Создать новую миграцию после изменения моделей
docker compose exec app alembic revision --autogenerate -m "описание"

# Применить
docker compose exec app alembic upgrade head

# Откатить
docker compose exec app alembic downgrade -1
```

---

## Тесты

```bash
docker compose exec app pytest -v
```

34 теста на SQLite in-memory. Покрывают:
- валидацию полей (длина, пустые значения, trim)
- уникальность имён в рамках одного родителя
- построение дерева с разной глубиной
- защиту от циклов и self-parent
- режимы удаления cascade / reassign

---

## Структура проекта

```
hitalent_test/
├── app/
│   ├── main.py          # FastAPI приложение, настройка логгирования
│   ├── config.py        # Настройки (pydantic-settings)
│   ├── database.py      # SQLAlchemy engine, Base, get_db
│   ├── models/
│   │   ├── department.py
│   │   └── employee.py
│   ├── schemas/
│   │   ├── department.py
│   │   └── employee.py
│   └── routers/
│       └── departments.py
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── tests/
│   ├── conftest.py
│   └── test_departments.py
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```
