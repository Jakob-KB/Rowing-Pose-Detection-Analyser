# /src/api/schemas.py

from pydantic import BaseModel

from src.models import SessionView

# Requests
class SessionRequest(BaseModel):
    name: str
    original_filepath: str

# Responses
class SessionResponse(SessionView):
    pass
