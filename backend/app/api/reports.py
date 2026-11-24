from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import Place, Report, User, UserRole
from app.schemas.report import ReportCreate, ReportRead

router = APIRouter(tags=["reports"])


async def _owned_report(report_id: int, user: User, session) -> Report:
    """Редагувати/видаляти відгук може лише автор або адмін (захист від IDOR)."""
    report = await session.get(Report, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if report.author_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your report")
    return report


@router.post(
    "/places/{place_id}/reports",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_report(
    place_id: int, data: ReportCreate, user: CurrentUser, session: DbSession
):
    if await session.get(Place, place_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Place not found")
    report = Report(place_id=place_id, author_id=user.id, text=data.text)
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


@router.get("/places/{place_id}/reports", response_model=list[ReportRead])
async def list_reports(place_id: int, session: DbSession):
    result = await session.scalars(
        select(Report).where(Report.place_id == place_id).order_by(Report.id)
    )
    return list(result)


@router.patch("/reports/{report_id}", response_model=ReportRead)
async def update_report(
    report_id: int, data: ReportCreate, user: CurrentUser, session: DbSession
):
    report = await _owned_report(report_id, user, session)
    report.text = data.text
    await session.commit()
    return report


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: int, user: CurrentUser, session: DbSession):
    report = await _owned_report(report_id, user, session)
    await session.delete(report)
    await session.commit()
