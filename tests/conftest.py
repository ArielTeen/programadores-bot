import os, sys, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DISCORD_TOKEN"] = "test_token"
os.environ["CLIENT_ID"] = "123"
os.environ["CLIENT_SECRET"] = "test_secret"
os.environ["DASHBOARD_SECRET"] = "test_secret_32_chars_long_abcd"
os.environ["OWNER_ID"] = "123"
os.environ["DEBUG"] = "false"

from database.db import Database
import tempfile, aiosqlite

@pytest.fixture
async def db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()
    db = Database(db_path)
    await db.connect()
    yield db
    await db.close()
    os.unlink(db_path)

@pytest.fixture
def sample_guild_id():
    return 123456789

@pytest.fixture
def sample_user_id():
    return 987654321
