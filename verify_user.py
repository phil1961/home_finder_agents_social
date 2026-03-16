# v20260309-1
"""Run from your home_finder_agents directory: python verify_user.py"""
from app import create_app
from app.models import db, User

app = create_app()
with app.app_context():
    users = User.query.all()
    if not users:
        print("No users found in the database.")
    else:
        for u in users:
            print(f"  {u.id}: {u.username} ({u.email}) verified={u.is_verified}")
            u.is_verified = True
        db.session.commit()
        print("\nAll accounts verified! You can now log in.")
