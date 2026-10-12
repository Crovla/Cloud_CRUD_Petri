import os
from datetime import datetime
from zoneinfo import ZoneInfo


SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only")

MAX_CONTENT_LENGTH = 5 * 1024 * 1024

SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL", "sqlite:///samples.db"
).replace("postgres://", "postgresql://", 1)

APP_TIMEZONE = ZoneInfo(
    os.environ.get("APP_TIMEZONE", "Europe/Vilnius")
)

STATUSES = ("Incubating", "Need to check", "Done")

ALLOWED = {"png", "jpg", "jpeg"}


def today():
    return datetime.now(APP_TIMEZONE).date()