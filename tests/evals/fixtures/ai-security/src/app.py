# src/app.py
from os import getenv

password = getenv("DB_PASS", "root")
