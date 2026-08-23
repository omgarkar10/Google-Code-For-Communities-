import asyncio
import os
import sys
import bcrypt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spin_agents.db import AsyncSessionLocal, engine, Base
from spin_agents.models import User

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

async def create_admin():
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        stmt = select(User).where(User.email == "admin@government.gov.in")
        result = await db.execute(stmt)
        existing = result.scalars().first()
        
        hashed = hash_password("SecureSPIN2026!")

        if existing:
            existing.password_hash = hashed
            existing.role = "admin"
            existing.department = "All Departments"
            await db.commit()
            print("Admin user updated with fresh password hash!")
            return

        user = User(
            email="admin@government.gov.in",
            password_hash=hashed,
            name="System Administrator",
            department="All Departments",
            role="admin",
            is_verified=True
        )
        db.add(user)
        await db.commit()
        print("Admin user created successfully!")

if __name__ == "__main__":
    asyncio.run(create_admin())
