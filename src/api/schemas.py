from pydantic import BaseModel


class SessionRequest(BaseModel):
    name: str
    original_filepath: str
