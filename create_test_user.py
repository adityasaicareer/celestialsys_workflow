#!/usr/bin/env python3
"""Create a test user for the visitor management system."""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from backend.models import Base, User, Role
from backend.security import hash_password

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./backend/visitor_access.db")


async def create_test_user():
    """Create a test admin user."""
    print("Creating test user...")
    print(f"Database: {DATABASE_URL}")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created/verified")
    
    # Create a test admin user
    async with SessionLocal() as session:
        # Check if user exists
        result = await session.execute(select(User).where(User.email == "admin@example.com"))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print("\n✅ Admin user already exists!")
            print("=" * 60)
            print("📧 Email:    admin@example.com")
            print("🔑 Password: admin123")
            print("👤 Role:     admin")
            print("=" * 60)
        else:
            user = User(
                email="admin@example.com",
                full_name="Admin User",
                password_hash=hash_password("admin123"),
                role=Role.ADMIN.value,
                organization="Test Organization",
                location="Headquarters",
                active=True
            )
            session.add(user)
            await session.commit()
            
            print("\n✅ Admin user created successfully!")
            print("=" * 60)
            print("📧 Email:    admin@example.com")
            print("🔑 Password: admin123")
            print("👤 Role:     admin")
            print("=" * 60)
            print("\nYou can now log in to the frontend with these credentials!")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_test_user())
