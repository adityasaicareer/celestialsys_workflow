#!/usr/bin/env python3
"""Create a test user for the visitor management system."""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

# Import from backend
from database import Base
from models.entities import User, UserRole, UserStatus
from security import hash_password

# Get DATABASE_URL from backend/.env
from config import settings

async def create_test_user():
    """Create test users with different roles."""
    print("=" * 60)
    print("Creating test users...")
    print(f"Database: {settings.database_url}")
    print("=" * 60)
    
    engine = create_async_engine(settings.database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created/verified\n")
    
    # Define test users
    test_users = [
        {
            "email": "admin@example.com",
            "password": "admin123",
            "full_name": "Admin User",
            "role": UserRole.ADMIN,
            "status": UserStatus.ACTIVE
        },
        {
            "email": "user@example.com",
            "password": "user123",
            "full_name": "Regular User",
            "role": UserRole.USER,
            "status": UserStatus.ACTIVE
        },
        {
            "email": "superadmin@example.com",
            "password": "super123",
            "full_name": "Super Admin",
            "role": UserRole.SUPER_ADMIN,
            "status": UserStatus.ACTIVE
        }
    ]
    
    # Create users
    async with SessionLocal() as session:
        for user_data in test_users:
            # Check if user exists
            result = await session.execute(
                select(User).where(User.email == user_data["email"])
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                # Update existing user to be active
                existing_user.status = user_data["status"]
                existing_user.role = user_data["role"]
                existing_user.password_hash = hash_password(user_data["password"])
                print(f"✅ Updated: {user_data['email']}")
            else:
                # Create new user
                user = User(
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    password_hash=hash_password(user_data["password"]),
                    role=user_data["role"],
                    status=user_data["status"],
                    is_soft_deleted=False
                )
                session.add(user)
                print(f"✅ Created: {user_data['email']}")
        
        await session.commit()
    
    print("\n" + "=" * 60)
    print("📋 TEST USERS CREATED")
    print("=" * 60)
    print("\n1️⃣  SUPER ADMIN")
    print("   📧 Email:    superadmin@example.com")
    print("   🔑 Password: super123")
    print("   👤 Role:     Super Admin")
    print()
    print("2️⃣  ADMIN")
    print("   📧 Email:    admin@example.com")
    print("   🔑 Password: admin123")
    print("   👤 Role:     Admin")
    print()
    print("3️⃣  USER")
    print("   📧 Email:    user@example.com")
    print("   🔑 Password: user123")
    print("   👤 Role:     User")
    print("=" * 60)
    print("\n✨ You can now log in to the frontend!")
    print("   Frontend: http://localhost:3000/login")
    print("   Backend:  http://localhost:8000/docs")
    print("=" * 60)
    
    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(create_test_user())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure:")
        print("   1. PostgreSQL is running")
        print("   2. backend/.env has correct DATABASE_URL")
        print("   3. DATABASE_URL uses postgresql+asyncpg://")
        sys.exit(1)
