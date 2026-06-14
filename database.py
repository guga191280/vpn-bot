from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Base, Tariff
from config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(Tariff))
        if not result.scalars().first():
            session.add_all([
                Tariff(name="1 месяц", slug="1m", price=153, days=30, traffic_gb=0),
                Tariff(name="3 месяца", slug="3m", price=450, days=90, traffic_gb=0),
                Tariff(name="Тест 500MB", slug="test", price=0, days=30, traffic_gb=0.5),
            ])
            await session.commit()

async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
