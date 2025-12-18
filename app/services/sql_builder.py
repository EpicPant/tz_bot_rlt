from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from nlp.spec import QuerySpec, Table, Aggregation, ConditionOp


# Какие поля можно агрегировать в каких таблицах
ALLOWED_FIELDS_BY_TABLE: Dict[Table, List[str]] = {
    Table.videos: [
        "id",
        "views_count",
        "likes_count",
        "comments_count",
        "reports_count",
    ],
    Table.video_snapshots: [
        "id",
        "video_id",
        "views_count",
        "likes_count",
        "comments_count",
        "reports_count",
        "delta_views_count",
        "delta_likes_count",
        "delta_comments_count",
        "delta_reports_count",
    ],
}

# По каким колонкам в принципе разрешаем фильтровать
ALLOWED_FILTER_COLUMNS = {
    "creator_id",
    "video_created_at",
    "views_count",
    "created_at",
    "delta_views_count",
}

# Какие колонки считаем datetime-полями
DATETIME_COLUMNS = {"video_created_at", "created_at"}


def _parse_iso_datetime(value: str) -> datetime:
    """Ждём строку формата 'YYYY-MM-DDTHH:MM:SS+ZZ:ZZ' или 'YYYY-MM-DDTHH:MM:SS'."""
    return datetime.fromisoformat(value)


def build_sql_and_params(spec: QuerySpec) -> Tuple[str, Dict[str, Any]]:
    """
    Собирает SQL-строку и словарь параметров из QuerySpec.
    Возвращает (sql, params), где sql — SELECT с одним агрегатом и псевдонимом value.
    """
    # 1. Проверяем поле, по которому считаем
    allowed_fields = ALLOWED_FIELDS_BY_TABLE.get(spec.table)
    if not allowed_fields or spec.field not in allowed_fields:
        raise ValueError(
            f"Field '{spec.field}' is not allowed for table '{spec.table.value}'"
        )

    # 2. Строим часть SELECT
    if spec.aggregation == Aggregation.count_rows:
        select_expr = "COUNT(*)"
    elif spec.aggregation == Aggregation.sum_field:
        select_expr = f"COALESCE(SUM({spec.field}), 0)"
    elif spec.aggregation == Aggregation.count_distinct:
        select_expr = f"COUNT(DISTINCT {spec.field})"
    else:
        raise ValueError(f"Unknown aggregation '{spec.aggregation}'")

    table_name = spec.table.value

    where_clauses: List[str] = []
    params: Dict[str, Any] = {}
    param_index = 0

    # 3. Перебираем фильтры и строим WHERE
    for cond in spec.filters:
        if cond.column not in ALLOWED_FILTER_COLUMNS:
            raise ValueError(f"Column '{cond.column}' is not allowed in filters")

        col = cond.column

        if cond.op == ConditionOp.eq:
            pname = f"p{param_index}"
            param_index += 1
            where_clauses.append(f"{col} = :{pname}")
            params[pname] = cond.value

        elif cond.op == ConditionOp.gt:
            pname = f"p{param_index}"
            param_index += 1
            where_clauses.append(f"{col} > :{pname}")
            params[pname] = cond.value

        elif cond.op == ConditionOp.between_datetime:
            if cond.value2 is None:
                raise ValueError("between_datetime requires value2")
            p1, p2 = f"p{param_index}", f"p{param_index + 1}"
            param_index += 2

            start = _parse_iso_datetime(str(cond.value))
            end = _parse_iso_datetime(str(cond.value2))

            where_clauses.append(f"{col} >= :{p1} AND {col} < :{p2}")
            params[p1] = start
            params[p2] = end

        elif cond.op == ConditionOp.date_eq:
            if col not in DATETIME_COLUMNS:
                raise ValueError(
                    f"date_eq is only applicable to datetime columns, got '{col}'"
                )

            # value: 'YYYY-MM-DD'
            day = datetime.fromisoformat(str(cond.value)).date()
            start = datetime.combine(day, datetime.min.time())
            end = start + timedelta(days=1)

            p1, p2 = f"p{param_index}", f"p{param_index + 1}"
            param_index += 2

            where_clauses.append(f"{col} >= :{p1} AND {col} < :{p2}")
            params[p1] = start
            params[p2] = end

        else:
            raise ValueError(f"Unsupported ConditionOp '{cond.op}'")

    where_sql = ""
    if where_clauses:
        where_sql = " WHERE " + " AND ".join(where_clauses)

    sql = f"SELECT {select_expr} AS value FROM {table_name}{where_sql};"
    return sql, params


async def execute_query_spec(session: AsyncSession, spec: QuerySpec) -> int:
    """
    Выполняет QuerySpec через переданный AsyncSession.
    Возвращает одно число (int). Пустой результат -> 0.
    """
    sql, params = build_sql_and_params(spec)
    stmt = text(sql)
    result = await session.execute(stmt, params)
    row = result.first()
    if row is None:
        return 0

    value = row[0]
    # На случай, если вернётся Decimal / None
    if value is None:
        return 0
    return int(value)
