from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportCreate(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    place_id: int
    author_id: int
    text: str
    created_at: datetime
