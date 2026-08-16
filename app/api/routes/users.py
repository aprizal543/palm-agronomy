from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep
from app.repositories.users import UserRepository
from app.schemas.user import UserCreate, UserRead

router = APIRouter()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, session: SessionDep):
    try:
        user = await UserRepository(session).create(payload)
        await session.commit()
        return user
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Identitas Telegram/telepon sudah terdaftar") from exc


@router.get("/telegram/{telegram_user_id}", response_model=UserRead)
async def get_user_by_telegram(telegram_user_id: int, session: SessionDep):
    user = await UserRepository(session).get_by_telegram_id(telegram_user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")
    return user

