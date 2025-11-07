import argparse
import asyncio
import sys
import tomllib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.user import User
from app.services.password import hash_password


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create new admin accounts for onewAy")

    parser.add_argument(
        "-u", "--username", help="Username for new admin", required=True
    )
    parser.add_argument(
        "-p", "--password", help="Password for new admin", required=True
    )

    return parser.parse_args()


def get_config(file_name: str) -> dict[str, Any]:
    with open(file_name, "rb") as f:
        return tomllib.load(f)


def db_url_exists(config: dict[str, Any]) -> bool:
    if config.get("database").get("url"):
        return True
    return False


async def add_admin(username: str, password: str, db_url: str) -> None:
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(
        bind=engine, class_=AsyncSession, autoflush=False, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"[-] User '{username}' already exists")
                await engine.dispose()
                sys.exit(1)

            hashed_password = hash_password(password)
            new_admin = User(
                username=username,
                hashed_password=hashed_password,
                is_admin=True,
                last_login=datetime.now(UTC),
                created_at=datetime.now(UTC),
            )

            session.add(new_admin)
            await session.commit()

            print(f"[+] Admin user '{username}' created successfully")

        except Exception as e:
            await session.rollback()
            print(f"[-] Failed to create admin user: {e}")
            await engine.dispose()
            sys.exit(1)

        finally:
            await engine.dispose()


if __name__ == "__main__":
    file = "config.toml"
    args = parse_args()
    conf = get_config(file)
    if not db_url_exists(conf):
        print(f"[-] No database URL found in {file}")
        sys.exit(1)

    asyncio.run(
        add_admin(args.username, args.password, conf.get("database").get("url"))
    )
