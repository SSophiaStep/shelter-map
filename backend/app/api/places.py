from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from geoalchemy2 import Geography, Geometry
from geoalchemy2.elements import WKTElement
from pydantic import TypeAdapter
from sqlalchemy import cast, func, select

from app.api.deps import AdminUser, DbSession
from app.core import cache
from app.core.config import settings
from app.models import Place, PlaceType
from app.schemas.place import PlaceCreate, PlaceRead, PlaceUpdate

router = APIRouter(prefix="/places", tags=["places"])
_places_adapter = TypeAdapter(list[PlaceRead])

_lon = func.ST_X(cast(Place.location, Geometry)).label("lon")
_lat = func.ST_Y(cast(Place.location, Geometry)).label("lat")


# Вибираємо лише потрібні колонки: без зайвої геоколонки (WKB) на кожен рядок
_columns = (
    Place.id,
    Place.name,
    Place.type,
    Place.address,
    Place.capacity,
    Place.is_available,
    _lon,
    _lat,
)


def _to_read(row, distance_m: float | None = None) -> PlaceRead:
    return PlaceRead(
        id=row.id,
        name=row.name,
        type=row.type,
        address=row.address,
        capacity=row.capacity,
        is_available=row.is_available,
        lat=row.lat,
        lon=row.lon,
        distance_m=distance_m,
    )


def _point(lat: float, lon: float) -> WKTElement:
    return WKTElement(f"POINT({lon} {lat})", srid=4326)


async def _get_or_404(session, place_id: int) -> PlaceRead:
    row = (await session.execute(select(*_columns).where(Place.id == place_id))).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Place not found")
    return _to_read(row)


@router.get("/nearby", response_model=list[PlaceRead])
async def nearby(
    session: DbSession,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius_m: Annotated[int, Query(ge=1, le=50000)] = 1000,
    place_type: Annotated[PlaceType | None, Query(alias="type")] = None,
    only_available: bool = True,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """Публічний геопошук: у надзвичайній ситуації логін не потрібен."""
    cache_key = None
    if settings.cache_enabled:
        # З кешем шукаємо від центру клітинки сітки, щоб відповідь збігалася з ключем
        lat, lon = cache.snap(lat), cache.snap(lon)
        cache_key, cached = await cache.nearby_lookup(
            lat,
            lon,
            radius_m,
            place_type.value if place_type else None,
            only_available,
            limit,
        )
        if cached is not None:
            return Response(
                cached, media_type="application/json", headers={"X-Cache": "HIT"}
            )
    point = cast(func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326), Geography)
    # use_spheroid=false: відстань по сфері замість еліпсоїда. Похибка до ~0,3%,
    # але обчислення помітно швидші, а для пошуку найближчого укриття це неважливо.
    distance = func.ST_Distance(Place.location, point, False).label("distance_m")
    stmt = (
        select(*_columns, distance)
        .where(func.ST_DWithin(Place.location, point, float(radius_m), False))
        .order_by(distance)
        .limit(limit)
    )
    if place_type is not None:
        stmt = stmt.where(Place.type == place_type)
    if only_available:
        stmt = stmt.where(Place.is_available.is_(True))
    rows = (await session.execute(stmt)).all()
    items = [_to_read(row, distance_m=row.distance_m) for row in rows]
    if not settings.cache_enabled:
        return items
    payload = _places_adapter.dump_json(items)
    if cache_key is not None:
        await cache.nearby_store(cache_key, payload)
    status_header = "MISS" if cache_key is not None else "BYPASS"
    return Response(
        payload, media_type="application/json", headers={"X-Cache": status_header}
    )


@router.get("/{place_id}", response_model=PlaceRead)
async def get_place(place_id: int, session: DbSession):
    return await _get_or_404(session, place_id)


@router.post("", response_model=PlaceRead, status_code=status.HTTP_201_CREATED)
async def create_place(data: PlaceCreate, _admin: AdminUser, session: DbSession):
    place = Place(
        name=data.name,
        type=data.type,
        address=data.address,
        capacity=data.capacity,
        is_available=data.is_available,
        location=_point(data.lat, data.lon),
    )
    session.add(place)
    await session.commit()
    await cache.invalidate_nearby()
    return await _get_or_404(session, place.id)


@router.patch("/{place_id}", response_model=PlaceRead)
async def update_place(
    place_id: int, data: PlaceUpdate, _admin: AdminUser, session: DbSession
):
    place = await session.get(Place, place_id)
    if place is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Place not found")
    values = data.model_dump(exclude_unset=True)
    lat, lon = values.pop("lat", None), values.pop("lon", None)
    for field, value in values.items():
        setattr(place, field, value)
    if lat is not None and lon is not None:
        place.location = _point(lat, lon)
    await session.commit()
    await cache.invalidate_nearby()
    return await _get_or_404(session, place_id)


@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_place(place_id: int, _admin: AdminUser, session: DbSession):
    place = await session.get(Place, place_id)
    if place is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Place not found")
    await session.delete(place)
    await session.commit()
    await cache.invalidate_nearby()
