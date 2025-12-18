# Video Info Bot

Телеграм-бот, который отвечает на аналитические вопросы по базе видео **одним числом**.  
Вопрос — на русском, ответ — агрегат по PostgreSQL (COUNT, SUM и т.п.).

## Стек

- Python 3.12
- PostgreSQL + asyncpg
- SQLAlchemy (async)
- Alembic (миграции)
- aiogram (Telegram-бот)
- langchain-openai (LLM → JSON-DSL)
- Pydantic / pydantic-settings

---

## Запуск локально (без Docker)

> При желании всё это легко оборачивается в Docker (Postgres + приложение),
> но ниже — упрощённый вариант без контейнеров.

### 1. Клонирование и зависимости

```bash
git clone <repo-url> tz_bot_rlt
cd tz_bot_rlt

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2. PostgreSQL

Нужна база, например:

- хост: `localhost`
- порт: `5432`
- БД: `video_info_bot_db`
- пользователь: `admin`
- пароль: `admin123`

Поднять можно как угодно (локально, Docker и т.д.), главное — чтобы DSN совпадал с тем, что в `.env`.

### 3. Файл `.env`

В корне проекта (`tz_bot_rlt/.env`):

```env
# PostgreSQL
postgres_host=localhost
postgres_port=5432
postgres_db=video_info_bot_db
postgres_user=admin
postgres_password=admin123

# Telegram
BOT_TOKEN=ваш_telegram_bot_token

# OpenAI / LLM
openai_api_key=sk-...ваш_ключ...
```

Эти переменные читаются через `app/core/config.py`:

- `DBSettings` — alias для `postgres_*`
- `BotSettings` — `BOT_TOKEN`
- `LLMSettings` — `openai_api_key`

### 4. Миграции

Создание таблиц через Alembic:

```bash
alembic upgrade head
```

После этого в БД появятся таблицы:

- `videos`
- `video_snapshots`

### 5. Загрузка данных из JSON

В корне лежит файл `videos.json` (из ТЗ).  
Для первичного заполнения БД используется скрипт `fill_db_script.py`:

```bash
export PYTHONPATH=.
python fill_db_script.py videos.json
```

Скрипт:

- читает JSON;
- валидирует записи через Pydantic-модели;
- конвертирует их в ORM-модели `Video` и `VideoSnapshot`;
- делает bulk-insert в Postgres.

В конце в логах будет видно примерно:

```text
батч: видео=358, снапы=35946
ГОТОВО. видео=358, снапы=35946
```

### 6. Запуск бота

Точка входа:

```bash
export PYTHONPATH=.
python app/main.py
```

После запуска бот начинает опрашивать Telegram API.  
Можно писать боту, например:

- `Сколько всего видео есть в системе?`
- `Сколько видео у креатора с id aca1061a9d324ecf8c3fa2bb32d7be63 вышло с 1 по 5 ноября 2025 года?`
- `Сколько видео набрало больше 100000 просмотров?`
- `На сколько просмотров в сумме выросли все видео 28 ноября 2025?`
- `Сколько разных видео получали новые просмотры 28 ноября 2025 года?`

Бот всегда отвечает **одним числом** (строкой).

---

## Архитектура

Упрощённая структура проекта:

```text
app/
  base/
    database.py        # engine, async_session, Base
    models.py          # ORM-модели Video, VideoSnapshot
    session_maker.py   # DBSessionManager (async contextmanager)
  core/
    config.py          # DBSettings, BotSettings, LLMSettings
  nlp/
    spec.py            # DSL QuerySpec (описание запроса)
    prompts.py         # системный промпт для LLM
    llm_parser.py      # текст -> JSON -> QuerySpec
  services/
    sql_builder.py     # QuerySpec -> SQL + params -> execute_query_spec
    executor.py        # answer_query_spec(spec) -> int
    text_query.py      # answer_text_query(text) -> int
  bot/
    handlers.py        # aiogram Router: текст -> answer_text_query -> ответ
    main.py            # запуск бота
fill_db_script.py      # заливка JSON в БД
migrations/            # Alembic миграции
```

### Модель данных

**videos**

- `id` (UUID PK) — идентификатор видео
- `creator_id` (TEXT) — идентификатор автора
- `video_created_at` (TIMESTAMPTZ) — когда видео появилось
- `views_count`, `likes_count`, `comments_count`, `reports_count` (BIGINT) — итоговые цифры
- `created_at`, `updated_at` (TIMESTAMPTZ) — служебные поля

**video_snapshots**

- `id` (UUID PK)
- `video_id` (UUID FK → videos.id)
- `views_count`, `likes_count`, `comments_count`, `reports_count` — значения на момент снапшота
- `delta_views_count`, `delta_likes_count`, `delta_comments_count`, `delta_reports_count` — прирост с прошлого снапшота
- `created_at`, `updated_at` — время снапшота и обновления

---

## Как текстовый запрос превращается в обращение к БД

Пайплайн:

1. **Пользовательский текст** → `answer_text_query(text)`.
2. `answer_text_query` вызывает `build_spec_from_text(text)`:
   - LLM получает описание схемы и формат JSON;
   - LLM возвращает JSON-объект в формате `QuerySpec`.
3. `QuerySpec` валидируется через Pydantic (`app/nlp/spec.py`).
4. `QuerySpec` передаётся в `execute_query_spec(session, spec)`:
   - собирается SQL с параметрами;
   - запрос выполняется к Postgres;
   - возвращается одно число (`int`).
5. Бот отправляет это число пользователю.

### DSL: QuerySpec

Чтобы LLM не писала сырые SQL-запросы, используется небольшой **DSL** в виде JSON.  
Он описан в `app/nlp/spec.py` и включает:

```python
class Table(str, Enum):
    videos = "videos"
    video_snapshots = "video_snapshots"

class Aggregation(str, Enum):
    count_rows = "count_rows"          # COUNT(*)
    sum_field = "sum_field"            # SUM(field)
    count_distinct = "count_distinct"  # COUNT(DISTINCT field)

class ConditionOp(str, Enum):
    eq = "eq"                   # col = value
    gt = "gt"                   # col > value
    between_datetime = "between_datetime"  # col >= value AND col < value2
    date_eq = "date_eq"         # один день: [day; day+1)
```

`QuerySpec`:

```python
class Condition(BaseModel):
    column: str          # ограничен whitelists: creator_id, video_created_at, views_count, created_at, delta_views_count
    op: ConditionOp
    value: str | int
    value2: str | int | None = None  # только для between_datetime

class QuerySpec(BaseModel):
    table: Table
    aggregation: Aggregation
    field: str           # только разрешённые метрики для каждой таблицы
    filters: List[Condition] = []
```

Примеры `QuerySpec`:

- «Сколько всего видео?»:

```json
{"table": "videos", "aggregation": "count_rows", "field": "id", "filters": []}
```

- «На сколько просмотров выросли все видео 28 ноября 2025?»:

```json
{
  "table": "video_snapshots",
  "aggregation": "sum_field",
  "field": "delta_views_count",
  "filters": [
    {"column": "created_at", "op": "date_eq", "value": "2025-11-28"}
  ]
}
```

### SQL-слой

В `app/services/sql_builder.py`:

- по `QuerySpec` строится SQL вида:

```sql
SELECT COUNT(*) AS value
FROM videos
WHERE creator_id = :p0
  AND video_created_at >= :p1
  AND video_created_at < :p2;
```

или:

```sql
SELECT COALESCE(SUM(delta_views_count), 0) AS value
FROM video_snapshots
WHERE created_at >= :p0
  AND created_at < :p1;
```

- используются только whitelisted поля и колонки;
- фильтры `date_eq` разворачиваются в диапазон `[дата 00:00; дата+1 день 00:00)`.

`execute_query_spec(session, spec)` выполняет запрос через async SQLAlchemy и возвращает одно число.

---

## LLM и промпт

Используется `langchain-openai`:

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
    api_key=llm_settings.OPENAI_API_KEY,
)
```

В `app/nlp/prompts.py` описан системный промпт `SPEC_SYSTEM_PROMPT`, который:

1. Подробно описывает схему таблиц `videos` и `video_snapshots`.
2. Жёстко задаёт формат JSON-ответа:

   ```jsonc
   {
     "table": "videos" | "video_snapshots",
     "aggregation": "count_rows" | "sum_field" | "count_distinct",
     "field": "...",
     "filters": [
       {
         "column": "creator_id" | "video_created_at" | "views_count" | "created_at" | "delta_views_count",
         "op": "eq" | "gt" | "between_datetime" | "date_eq",
         "value": "...",
         "value2": "..."
       }
     ]
   }
   ```

3. Ограничивает допустимые значения (`table`, `field`, `column`, форматы даты/времени).
4. Приводит примеры вопросов и корректных JSON-ответов в духе ТЗ.
5. Отдельно требует:
   - **не писать SQL**;
   - возвращать **только чистый JSON-объект**, без Markdown, комментариев и лишних полей.

`build_spec_from_text`:

```python
raw = await call_llm(SPEC_SYSTEM_PROMPT, user_text)
raw_str = raw.strip()
# защита от ```json ... ```
data = json.loads(raw_str)
spec = QuerySpec.model_validate(data)
```

Далее `spec` уходит в SQL-слой, а результат — в Телеграм.
