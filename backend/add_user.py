"""
Run this from inside `backend/` to add new users to users.db.

Usage:
    python add_user.py <username> <password> <role>

Example:
    python add_user.py rishu mypassword123 manager
"""
import sys
from database.users_db import init_users_db, create_user, get_user

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python add_user.py <username> <password> <role>")
        print("role must be one of: intern, manager, admin")
        sys.exit(1)

    username, password, role = sys.argv[1], sys.argv[2], sys.argv[3]

    if role not in ("intern", "manager", "admin"):
        print("Error: role must be intern, manager, or admin")
        sys.exit(1)

    init_users_db()

    if get_user(username):
        print(f"User '{username}' already exists.")
        sys.exit(1)

    create_user(username, password, role)
    print(f"Created user '{username}' with role '{role}'.")