import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("DASHBOARD_SECRET", "change_this_in_production")
DISCORD_CLIENT_ID = os.getenv("CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.getenv("DASHBOARD_URL", "http://localhost:5000") + "/callback"
DISCORD_API_ENDPOINT = "https://discord.com/api/v10"
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:5000")
