from pydantic import BaseModel


class DatabaseCreate(BaseModel):
    name: str  # Input user: "toko"


class DatabaseResponse(BaseModel):
    id: int
    name: str
    db_user: str
    db_password: str
    type: str

    class Config:
        from_attributes = True