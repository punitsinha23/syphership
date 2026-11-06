from pydantic import BaseModel


class CodeExchange(BaseModel):
    code: str

class RefreshToken(BaseModel):
    refresh_token: str


class DeleteAccount(BaseModel):
    confirm_username: str
