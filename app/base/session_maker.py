from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from loguru import logger
from app.base.database import async_session


class DBSessionManager:

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self.session_maker = session_maker

    @asynccontextmanager
    async def create_session(self) -> AsyncGenerator[AsyncSession, None]:
        """context manager for sessions"""
        async with self.session_maker() as session:
            try:
                yield session
            except Exception as e:
                logger.error(f"Error with create session:{e}")
                await session.rollback()
                raise
            finally:
                await session.close()

    @asynccontextmanager
    async def create_transaction(
        self, session: AsyncSession
    ) -> AsyncGenerator[None, None]:
        """Context manager for use transactions"""
        async with session.begin():
            try:
                yield
                await session.commit()
            except Exception as e:
                logger.error(f"Error with transaction {e}")
                await session.rollback()
                raise

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.create_session() as session:
            yield session

    async def get_transaction(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.create_session() as session:
            async with self.create_transaction(session):
                yield session


database_manager = DBSessionManager(async_session)

TransactionDep = database_manager.get_transaction
