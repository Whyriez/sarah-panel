from pydantic import BaseModel
from typing import List, Optional

# --- Panel Schemas ---
class PanelBase(BaseModel):
    name: str
    url: str
    username: str
    password: str

class PanelCreate(PanelBase):
    pass

class PanelResponse(PanelBase):
    id: int
    project_id: int

    class Config:
        from_attributes = True

# --- Project Schemas ---
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: int
    name: str
    description: Optional[str] = None
    # Nested Panel di dalam Project
    panels: List[PanelResponse] = []

    class Config:
        from_attributes = True