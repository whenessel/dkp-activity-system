from pathlib import Path

import environ

env = environ.Env()

BASE_DIR = Path(__file__).resolve().parent.parent

env.read_env(BASE_DIR / ".." / ".env")
