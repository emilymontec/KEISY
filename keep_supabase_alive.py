import os
import signal
import sys
import time
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

RUNNING = True
DEFAULT_INTERVAL_SECONDS = 900
MIN_INTERVAL_SECONDS = 60


def stop_handler(signum, frame):
    del signum, frame
    global RUNNING
    RUNNING = False


def get_interval_seconds():
    raw_value = os.getenv(
        "KEEPALIVE_INTERVAL_SECONDS",
        str(DEFAULT_INTERVAL_SECONDS),
    ).strip()
    try:
        interval = int(raw_value)
    except ValueError:
        interval = DEFAULT_INTERVAL_SECONDS
    return max(interval, MIN_INTERVAL_SECONDS)


def ping_database(database_url):
    with psycopg2.connect(database_url, connect_timeout=10) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()


def main():
    database_url = os.getenv("SUPABASE_DB_URL", "").strip()
    if not database_url:
        print("Falta SUPABASE_DB_URL en el archivo .env")
        return 1

    interval_seconds = get_interval_seconds()
    print(
        "Keepalive liviano para Supabase "
        f"cada {interval_seconds} segundos. Ctrl+C para salir."
    )

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    while RUNNING:
        started_at = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            ping_database(database_url)
            print(f"[{started_at}] OK")
        except Exception as exc:
            print(f"[{started_at}] ERROR: {exc}")

        for _ in range(interval_seconds):
            if not RUNNING:
                break
            time.sleep(1)

    print("Keepalive detenido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
