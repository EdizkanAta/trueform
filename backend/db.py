"""MongoDB connection (Motor async). Single shared client for the app."""
import os
from motor.motor_asyncio import AsyncIOMotorClient

_mongo_url = os.environ["MONGO_URL"]
_db_name = os.environ["DB_NAME"]

client = AsyncIOMotorClient(_mongo_url)
db = client[_db_name]


async def ensure_indexes() -> None:
    """Create indexes required by the app (idempotent)."""
    await db.users.create_index("email", unique=True)
    await db.health_profiles.create_index("user_id", unique=True)
    await db.goals.create_index("user_id")
    await db.plans.create_index("user_id")
    await db.daily_logs.create_index([("user_id", 1), ("date", 1)], unique=True)
    await db.progress_photos.create_index("user_id")
    await db.coach_messages.create_index([("user_id", 1), ("created_at", 1)])
    await db.jobs.create_index("user_id")
    await db.exercises.create_index("slug", unique=True)
    await db.ai_cost_log.create_index("created_at")
