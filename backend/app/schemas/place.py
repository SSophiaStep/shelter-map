from pydantic import BaseModel, Field, model_validator

from app.models import PlaceType


class PlaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: PlaceType
    address: str = Field(min_length=1, max_length=500)
    capacity: int = Field(default=0, ge=0)
    is_available: bool = True
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class PlaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: PlaceType | None = None
    address: str | None = Field(default=None, min_length=1, max_length=500)
    capacity: int | None = Field(default=None, ge=0)
    is_available: bool | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def coordinates_together(self):
        if (self.lat is None) != (self.lon is None):
            raise ValueError("lat and lon must be provided together")
        return self


class PlaceRead(BaseModel):
    id: int
    name: str
    type: PlaceType
    address: str
    capacity: int
    is_available: bool
    lat: float
    lon: float
    distance_m: float | None = None
