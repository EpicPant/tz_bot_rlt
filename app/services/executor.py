from sqlalchemy.ext.asyncio import AsyncSession

from app.base.session_maker import database_manager
from app.nlp.spec import QuerySpec
from app.services.sql_builder import execute_query_spec


async def answer_query_spec(spec: QuerySpec) -> int:
    """
    Фасад: взять QuerySpec, сходить в БД, вернуть одно число.
    Открывает и закрывает сессию сам.
    """
    async with database_manager.create_session() as session:
        return await execute_query_spec(session, spec)
