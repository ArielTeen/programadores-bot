from .db import Database

db = Database()

async def get_db() -> Database:
    return db
