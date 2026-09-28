import enum

from geoalchemy2 import Geography
from sqlalchemy import Boolean, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlaceType(str, enum.Enum):
    SHELTER = "shelter"
    HEATING = "heating"


class Place(Base):
    __tablename__ = "places"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[PlaceType] = mapped_column(Enum(PlaceType), index=True)
    address: Mapped[str] = mapped_column(String(500))
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    location = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=True)
    )