from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "nemo_exam"
    google_client_id: str = ""
    google_client_secret: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days
    frontend_url: str = "http://localhost:5173"
    allowed_origins: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


class Database:
    client: AsyncIOMotorClient = None
    db = None


db_instance = Database()


async def connect_db():
    settings = get_settings()
    db_instance.client = AsyncIOMotorClient(settings.mongodb_uri)
    db_instance.db = db_instance.client[settings.mongodb_db]

    # Create indexes
    await db_instance.db.profiles.create_index("user_id", unique=True)
    await db_instance.db.exam_sessions.create_index([("user_id", 1), ("subject", 1)])
    await db_instance.db.exam_sessions.create_index("certificate_id", sparse=True)
    await db_instance.db.user_roles.create_index([("user_id", 1), ("role", 1)])
    await db_instance.db.voucher_codes.create_index("code", unique=True)
    await db_instance.db.admin_settings.create_index("id")
    print("✅ Connected to MongoDB")


async def close_db():
    if db_instance.client:
        db_instance.client.close()
        print("🔌 MongoDB connection closed")


def get_db():
    return db_instance.db
