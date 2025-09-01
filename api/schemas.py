from pydantic import BaseModel
from typing import Optional, Literal

class PostModerationCreate(BaseModel):
    url: str
    post_type: Literal["img", "video", "audio", "text"]
    table_name: str
    reason: Optional[str] = None
    user_id: Optional[int] = 24   
    status: Optional[Literal["reported", "request", "reviewd", "disclined", "success"]] = "reported"

class PostModerationResponse(PostModerationCreate):
    id: int

    class Config:
        orm_mode = True
