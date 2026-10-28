"""Query strategy, preview, import, and diffing API endpoints."""

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.query import (
    QueryCreate,
    QueryDiffResponse,
    QueryImportResponse,
    QueryPreviewResponse,
    QueryResponse,
    QueryRevertResponse,
)
from app.services.import_pipeline import run_import_in_background
from app.services.query_service import QueryService

router = APIRouter(tags=["Queries"])


@router.post(
    "/reviews/{review_id}/queries",
    response_model=QueryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new query version",
)
def create_query(review_id: str, payload: QueryCreate, db: Session = Depends(get_db)):
    service = QueryService(db)
    return service.create_query(review_id, payload)


@router.get(
    "/reviews/{review_id}/queries",
    response_model=list[QueryResponse],
    summary="List all query versions for a review",
)
def list_queries(review_id: str, db: Session = Depends(get_db)):
    service = QueryService(db)
    return service.list_queries(review_id)


@router.get(
    "/queries/{query_id}",
    response_model=QueryResponse,
    summary="Get details for a specific query version",
)
def get_query(query_id: str, db: Session = Depends(get_db)):
    service = QueryService(db)
    return service.get_query(query_id)


@router.post(
    "/queries/{query_id}/preview",
    response_model=QueryPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview query hits and freeze query specification",
)
def preview_query(query_id: str, db: Session = Depends(get_db)):
    service = QueryService(db)
    return service.preview_query(query_id)


@router.post(
    "/queries/{query_id}/import",
    response_model=QueryImportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Approve query and trigger asynchronous ingestion pipeline",
)
def import_query(query_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Starts a live import run: fetch, store, deduplicate, screen, PICO.

    Returns at once with the run id; poll `GET /api/runs/{run_id}` for progress.
    Re-posting returns the active or completed run; after a failure it retries.
    """
    response = QueryService(db).import_query(query_id)
    if response.status == "queued":
        background_tasks.add_task(run_import_in_background, response.run_id)
    return response


@router.get(
    "/queries/{query_id}/diff",
    response_model=QueryDiffResponse,
    summary="Compute mathematical set difference between query versions",
)
def diff_query(
    query_id: str,
    against: str = Query(..., description="Parent or comparison query version ID"),
    db: Session = Depends(get_db),
):
    service = QueryService(db)
    return service.compute_diff(query_id=query_id, against_id=against)


@router.post(
    "/queries/{query_id}/revert",
    response_model=QueryRevertResponse,
    status_code=status.HTTP_200_OK,
    summary="Exact, zero-API revert to query version workspace snapshot",
)
def revert_query(query_id: str, db: Session = Depends(get_db)):
    """Restores workspace to the exact state captured in GroupSnapshot for this query version."""
    service = QueryService(db)
    return service.revert_query(query_id)
