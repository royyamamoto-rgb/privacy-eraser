"""Database configuration and session management."""

from sqlalchemy import text
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

        # Add search_url_pattern column if it doesn't exist (for existing installations)
        await conn.execute(
            text("""
                ALTER TABLE data_brokers
                ADD COLUMN IF NOT EXISTS search_url_pattern VARCHAR(500)
            """)
        )

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
            # Update existing brokers with search URL patterns
            await update_broker_search_urls(session)
            return

        # Add common data brokers with search URLs
        brokers = [
            DataBroker(
                name="Spokeo",
                domain="spokeo.com",
                category="people_search",
                search_url_pattern="https://www.spokeo.com/{first_name}-{last_name}",
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
                search_url_pattern="https://www.whitepages.com/name/{first_name}-{last_name}/{state}",
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
                search_url_pattern="https://www.beenverified.com/people/{first_name}-{last_name}/",
                opt_out_url="https://www.beenverified.com/opt-out",
                opt_out_method="form",
                processing_days=14,
                can_automate=False,
                difficulty=3,
            ),
            DataBroker(
                name="TruePeopleSearch",
                domain="truepeoplesearch.com",
                category="people_search",
                search_url_pattern="https://www.truepeoplesearch.com/results?name={first_name}%20{last_name}",
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
                search_url_pattern="https://www.fastpeoplesearch.com/name/{first_name}-{last_name}",
                opt_out_url="https://www.fastpeoplesearch.com/removal",
                opt_out_method="form",
                processing_days=7,
                can_automate=True,
                difficulty=1,
            ),
            DataBroker(
                name="Intelius",
                domain="intelius.com",
                category="people_search",
                search_url_pattern="https://www.intelius.com/people-search/{first_name}-{last_name}",
                opt_out_url="https://www.intelius.com/opt-out",
                opt_out_method="form",
                processing_days=14,
                can_automate=True,
                difficulty=2,
            ),
            DataBroker(
                name="ThatsThem",
                domain="thatsthem.com",
                category="people_search",
                search_url_pattern="https://thatsthem.com/name/{first_name}-{last_name}",
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
                search_url_pattern="https://radaris.com/p/{first_name}/{last_name}",
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
                search_url_pattern="https://www.peoplefinder.com/results?name={first_name}+{last_name}",
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
                search_url_pattern="https://www.ussearch.com/search/results?firstName={first_name}&lastName={last_name}",
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


async def update_broker_search_urls(session):
    """Update existing brokers with search URL patterns."""
    from app.models.broker import DataBroker
    from sqlalchemy import select, update

    # Mapping of broker domains to their search URL patterns
    search_patterns = {
        "spokeo.com": "https://www.spokeo.com/{first_name}-{last_name}",
        "whitepages.com": "https://www.whitepages.com/name/{first_name}-{last_name}/{state}",
        "beenverified.com": "https://www.beenverified.com/people/{first_name}-{last_name}/",
        "truepeoplesearch.com": "https://www.truepeoplesearch.com/results?name={first_name}%20{last_name}",
        "fastpeoplesearch.com": "https://www.fastpeoplesearch.com/name/{first_name}-{last_name}",
        "intelius.com": "https://www.intelius.com/people-search/{first_name}-{last_name}",
        "thatsthem.com": "https://thatsthem.com/name/{first_name}-{last_name}",
        "radaris.com": "https://radaris.com/p/{first_name}/{last_name}",
        "peoplefinder.com": "https://www.peoplefinder.com/results?name={first_name}+{last_name}",
        "ussearch.com": "https://www.ussearch.com/search/results?firstName={first_name}&lastName={last_name}",
    }

    for domain, pattern in search_patterns.items():
        await session.execute(
            update(DataBroker)
            .where(DataBroker.domain == domain)
            .values(search_url_pattern=pattern)
        )

    await session.commit()
