from pydantic import BaseModel
from typing import Optional

class SiteBase(BaseModel):
    domain: str
    type: str # php, node, python

class SiteCreate(SiteBase):
    pass # Nanti bisa ditambah config lain

class SiteResponse(SiteBase):
    id: int
    user_id: int
    app_port: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True