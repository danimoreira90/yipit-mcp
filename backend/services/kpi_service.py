"""Application facade: a session-bound service over the query functions.

Owns session lifecycle so the transports (MCP tools, REST routes) never open a
session or run SQL — they call these session-free methods. One facade, two
transports (the spine). RED stub: methods return [] until GREEN.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.services import companies
from backend.services.models import Company


class KpiService:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def list_sectors(self) -> list[str]:
        async with self._sessionmaker() as session:
            return await companies.list_sectors(session)

    async def list_companies(
        self, sector: str | None = None, query: str | None = None
    ) -> list[Company]:
        async with self._sessionmaker() as session:
            return await companies.list_companies(session, sector, query)
