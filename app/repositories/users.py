from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: UserCreate) -> User:
        user = User(**data.model_dump())
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        return await self.session.scalar(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
