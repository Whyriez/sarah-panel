from pydantic import BaseModel
from typing import Optional

class SiteBase(BaseModel):
    domain: str
    type: str # php, node, python
    php_version: Optional[str] = "8.2" # Default PHP 8.2 jika type=php

class SiteCreate(SiteBase):
    pass

class SiteResponse(SiteBase):
    id: int
    user_id: int
    app_port: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True