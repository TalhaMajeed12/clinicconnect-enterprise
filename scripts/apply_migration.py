"""Apply one reviewed SQL migration to the configured PostgreSQL database."""

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402


APPROVED_MIGRATIONS = {'001_add_clinician_time_off.sql'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('migration', choices=sorted(APPROVED_MIGRATIONS))
    args = parser.parse_args()

    migration_path = PROJECT_ROOT / 'migrations' / args.migration
    sql = migration_path.read_text(encoding='utf-8')
    app = create_app('development')
    with app.app_context():
        with db.engine.begin() as connection:
            connection.exec_driver_sql(sql)
    print(f'Applied migration: {args.migration}')


if __name__ == '__main__':
    main()
