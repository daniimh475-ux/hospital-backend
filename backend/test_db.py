
import asyncio
from sqlalchemy import text
from .db import engine  # Ejecutar SIEMPRE con: python -m backend.test_db

async def test():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT * FROM paciente"))
        for row in result:
            print(row)

if __name__ == "__main__":
    asyncio.run(test())
