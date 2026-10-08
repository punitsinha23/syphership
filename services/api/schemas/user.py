from pydantic import BaseModel


class CodeExchange(BaseModel):
    code: str

class RefreshToken(BaseModel):
    refresh_token: str
