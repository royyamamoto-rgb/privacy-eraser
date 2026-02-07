"""Database configuration and session management."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    # Import all models to register them with Base.metadata
    from app.models import user, broker, exposure, request, alert

    async with engine.begin() as conn:
        # Create tables if they don't exist (preserves data)
        await conn.run_sync(Base.metadata.create_all)

    # Seed brokers if empty
    await seed_brokers()


async def seed_brokers():
    """Seed initial data brokers if none exist."""
    from app.models.broker import DataBroker
    from sqlalchemy import select, func

    async with async_session() as session:
        # Check if brokers exist
        result = await session.execute(select(func.count(DataBroker.id)))
        count = result.scalar()

        if count > 0:
            return  # Already seeded

        # Add common data brokers
        brokers = [
            DataBroker(
                name="Spokeo",
                domain="spokeo.com",
                category="people_search",
                opt_out_url="https://www.spokeo.com/optout",
                opt_out_method="form",
                processing_days=14,
                can_automate=True,
                difficulty=2,
            ),
            DataBroker(
                name="WhitePages",
                domain="whitepages.com",
                category="people_search",
                opt_out_url="https://www.whitepages.com/suppression-requests",
                opt_out_method="form",
                processing_days=14,
                can_automate=True,
                difficulty=2,
            ),
            DataBroker(
                name="BeenVerified",
                domain="beenverified.com",
                category="background_check",
                opt_out_url="https://www.beenverified.com/opt-out",
                opt_out_method="form",
                processing_days=14,
                can_automate=False,
                difficulty=3,
            ),
            DataBroker(
                name="Intelius",
                domain="intelius.com",
                category="people_search",
                opt_out_url="https://www.intelius.com/opt-out",
                opt_out_method="form",
                processing_days=14,
                can_automate=True,
                difficulty=2,
            ),
            DataBroker(
                name="TruePeopleSearch",
                domain="truepeoplesearch.com",
                category="people_search",
                opt_out_url="https://www.truepeoplesearch.com/removal",
                opt_out_method="form",
                processing_days=7,
                can_automate=True,
                difficulty=1,
            ),
            DataBroker(
                name="FastPeopleSearch",
                domain="fastpeoplesearch.com",
                category="people_search",
                opt_out_url="https://www.fastpeoplesearch.com/removal",
                opt_out_method="form",
                processing_days=7,
                can_automate=True,
                difficulty=1,
            ),
            DataBroker(
                name="ThatsThem",
                domain="thatsthem.com",
                category="people_search",
                opt_out_url="https://thatsthem.com/optout",
                opt_out_method="form",
                processing_days=14,
                can_automate=True,
                difficulty=2,
            ),
            DataBroker(
                name="Radaris",
                domain="radaris.com",
                category="people_search",
                opt_out_url="https://radaris.com/control/privacy",
                opt_out_method="form",
                processing_days=30,
                can_automate=False,
                difficulty=4,
            ),
            DataBroker(
                name="PeopleFinder",
                domain="peoplefinder.com",
                category="people_search",
                opt_out_url="https://www.peoplefinder.com/optout.php",
                opt_out_method="form",
                processing_days=14,
                can_automate=True,
                difficulty=2,
            ),
            DataBroker(
                name="USSearch",
                domain="ussearch.com",
                category="people_search",
                opt_out_url="https://www.ussearch.com/opt-out/submit/",
                opt_out_method="form",
                processing_days=14,
                can_automate=True,
                difficulty=2,
            ),
        ]

        for broker in brokers:
            session.add(broker)

        await session.commit()
