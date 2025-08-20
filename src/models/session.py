# /src/models/session.py

from pydantic import BaseModel, Field

from src.utils.misc import new_id, now_s

class Session(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    status: str
    notes: str = ""
    created_at: int = Field(default_factory=now_s)
    updated_at: int = Field(default_factory=now_s)
