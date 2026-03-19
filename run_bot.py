#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add current directory to path
BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

# Import and run the bot
from tg_bot.bot import run_bot

if __name__ == "__main__":
    run_bot()