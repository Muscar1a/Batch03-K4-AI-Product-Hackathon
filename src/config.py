import os
from dotenv import load_dotenv

load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

# LLM & Graph Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Data Paths
DATA_DIR = os.getenv("DATA_DIR", "data")
MEMORY_STORE_PATH = os.path.join(DATA_DIR, "memory_store.json")
KG_DB_PATH = os.path.join(DATA_DIR, "kg_database.json")
