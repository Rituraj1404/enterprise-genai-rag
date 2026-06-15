"""
Bulk-import users from a CSV file into users.db.

CSV format (header required):
    username,password,role

role must be one of: intern, manager, admin

Usage:
    python add_users_csv.py users.csv
"""
import sys
import csv
from database.users_db import init_users_db, create_user, get_user

VALID_ROLES = {"intern", "manager", "admin"}


def main(csv_path: str):
    init_users_db()

    created, skipped, errors = 0, 0, 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required_cols = {"username", "password", "role"}
        if not required_cols.issubset(set(reader.fieldnames or [])):
            print(f"CSV must have columns: {required_cols}")
            sys.exit(1)

        for row in reader:
            username = row["username"].strip()
            password = row["password"].strip()
            role = row["role"].strip().lower()

            if role not in VALID_ROLES:
                print(f"[SKIP] '{username}': invalid role '{role}'")
                errors += 1
                continue

            if get_user(username):
                print(f"[SKIP] '{username}': already exists")
                skipped += 1
                continue

            create_user(username, password, role)
            print(f"[OK]   '{username}' ({role}) created")
            created += 1

    print(f"\nDone. Created={created}, Skipped(existing)={skipped}, Errors={errors}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python add_users_csv.py <users.csv>")
        sys.exit(1)
    main(sys.argv[1])