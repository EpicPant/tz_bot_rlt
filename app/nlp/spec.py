from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel


class Table(str, Enum):
    """Имя таблицы, по которой считаем агрегаты."""

    videos = "videos"
    video_snapshots = "video_snapshots"


class Aggregation(str, Enum):
    """Какую агрегатную функцию применяем."""

    count_rows = "count_rows"  # COUNT(*)
    sum_field = "sum_field"  # SUM(field)
    count_distinct = "count_distinct"  # COUNT(DISTINCT field)


class ConditionOp(str, Enum):
    """Операции для WHERE."""

    eq = "eq"  # col = value
    gt = "gt"  # col > value
    between_datetime = (
        "between_datetime"  # col >= value AND col < value2 (оба ISO datetime)
    )
    date_eq = "date_eq"  # col ∈ [day, day+1) по дню (value = 'YYYY-MM-DD')


class Condition(BaseModel):
    """Одно условие в WHERE."""

    column: str
    op: ConditionOp
    value: Union[str, int]
    value2: Optional[Union[str, int]] = None


class QuerySpec(BaseModel):
    """
    Спецификация запроса: что считаем и по каким фильтрам.
    Это то, из чего потом собирается SQL.
    """

    table: Table
    aggregation: Aggregation
    field: str
    filters: List[Condition] = []
