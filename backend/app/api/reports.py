from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import RequireViewer, get_report_generation_service
from app.services.report_generation import ReportGenerationService

router = APIRouter(tags=["reports"])


@router.get("/repositories/{repository_id}/report.json")
async def download_report_json(
    repository_id: str,
    context: RequireViewer,
    service: Annotated[ReportGenerationService, Depends(get_report_generation_service)],
) -> dict:
    try:
        data = await service.build_report_data(repository_id, context.organization_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")
    return data


@router.get("/repositories/{repository_id}/report.pdf")
async def download_report_pdf(
    repository_id: str,
    context: RequireViewer,
    service: Annotated[ReportGenerationService, Depends(get_report_generation_service)],
) -> Response:
    try:
        data = await service.build_report_data(repository_id, context.organization_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")

    pdf_bytes = service.render_pdf(data)
    repo_name = data["repository"].get("name") or repository_id
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in repo_name)
    filename = f"verion-report-{safe_name}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
