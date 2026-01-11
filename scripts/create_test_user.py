import uuid
from datetime import datetime

from app.db import SessionLocal
from app.models.db_models import User

def main():
    db = SessionLocal()

    test_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    user = db.get(User, test_user_id)
    if user:
        print(" Test user already exists")
        return

    user = User(
        id=test_user_id,
        email="test@example.com",
        name=" Test User",
        hashed_password="dev",
        created_at=datetime.utcnow(),
    )

    db.add(user)
    db.commit()
    print(" Test user created")

if __name__ == "__main__":
    main()
