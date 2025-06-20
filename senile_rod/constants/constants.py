from enum import Enum
import os
from dotenv import load_dotenv

from pathlib import Path

load_dotenv()


class Constants(Enum):
    """
    Shared constants
    """

    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    ROD_USER_ID = os.environ.get("ROD_USER_ID", "")
    GUILD_ID = os.environ.get("GUILD_ID", "")
    CHANNEL_ID = os.environ.get("CHANNEL_ID", "")
    CONFIG_PATH = Path.home()
