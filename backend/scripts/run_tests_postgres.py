"""Run Django tests against the dedicated local PostgreSQL service."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import dotenv_values


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
ENV_FILE = PROJECT_ROOT / ".env.test"
POSTGRES_ENGINE = "django.db.backends.postgresql"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
FORBIDDEN_DATABASES = {
    "carbono_zero",
    "proyecto_huella",
    "postgres",
    "production",
    "produccion",
}
REQUIRED = {
    "DATABASE_ENGINE",
    "DATABASE_NAME",
    "DATABASE_USER",
    "DATABASE_PASSWORD",
    "DATABASE_HOST",
    "DATABASE_PORT",
}


def load_test_environment() -> dict[str, str]:
    if not ENV_FILE.is_file():
        raise SystemExit(
            "Falta .env.test. Copia .env.test.example y conserva credenciales locales."
        )

    values = {
        key: str(value)
        for key, value in dotenv_values(ENV_FILE).items()
        if value is not None
    }
    missing = sorted(key for key in REQUIRED if not values.get(key))
    if missing:
        raise SystemExit(f"Faltan variables requeridas en .env.test: {', '.join(missing)}")

    engine = values["DATABASE_ENGINE"]
    host = values["DATABASE_HOST"].strip().lower()
    database = values["DATABASE_NAME"].strip().lower()

    if engine != POSTGRES_ENGINE:
        raise SystemExit("Ejecución abortada: DATABASE_ENGINE debe ser PostgreSQL.")
    if host not in LOCAL_HOSTS:
        raise SystemExit(
            "Ejecución abortada: DATABASE_HOST debe apuntar explícitamente a localhost."
        )
    if database in FORBIDDEN_DATABASES or not database.endswith("_test"):
        raise SystemExit(
            "Ejecución abortada: DATABASE_NAME debe ser una base local terminada en _test."
        )

    os.environ.update(values)
    return values


def verify_runtime() -> None:
    os.chdir(BACKEND_ROOT)
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django

    django.setup()

    from django.db import connection
    from django.db.utils import OperationalError

    last_error = None
    for attempt in range(15):
        try:
            connection.ensure_connection()
            break
        except OperationalError as error:
            last_error = error
            connection.close()
            if attempt == 14:
                raise SystemExit(
                    "PostgreSQL local no estuvo disponible después de 30 segundos."
                ) from last_error
            time.sleep(2)
    if connection.vendor != "postgresql":
        raise SystemExit(
            f"Ejecución abortada: Django resolvió el vendor {connection.vendor!r}."
        )
    print(f"Django connection.vendor: {connection.vendor}")
    connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta tests Django exclusivamente en PostgreSQL local."
    )
    parser.add_argument(
        "test_labels",
        nargs="*",
        help="Labels opcionales; sin labels ejecuta toda la suite.",
    )
    parser.add_argument(
        "--verbosity", choices=("0", "1", "2", "3"), default="1"
    )
    args = parser.parse_args()

    values = load_test_environment()
    print("PostgreSQL test target:")
    print(f"  ENGINE={values['DATABASE_ENGINE']}")
    print(f"  HOST={values['DATABASE_HOST']}")
    print(f"  PORT={values['DATABASE_PORT']}")
    print(f"  DATABASE_NAME={values['DATABASE_NAME']}")
    verify_runtime()

    command = [sys.executable, "manage.py", "test", *args.test_labels]
    command.extend(["--verbosity", args.verbosity])
    return subprocess.run(command, cwd=BACKEND_ROOT, env=os.environ.copy()).returncode


if __name__ == "__main__":
    raise SystemExit(main())
