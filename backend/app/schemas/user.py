from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    full_name: str
    email: str
    phone: str | None = None
    address: str | None = None
    avatar_url: str | None = None


class UserRegisterResponse(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class UserMe(UserRegisterResponse):
    """Authenticated user's public profile."""

