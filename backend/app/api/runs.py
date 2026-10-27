"""Pipeline Runs API endpoint."""

from backend.app.core.database import get_db
from backend.app.core.errors import NotFoundError
from backend.app.models.audit import PipelineRun
from backend.app.schemas.run import PipelineRunResponse
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

router = APIRouter(tags=["Pipeline Runs"])


@router.get(
    "/runs/{run_id}",
    response_model=PipelineRunResponse,
    summary="Get background pipeline run execution status and sub-steps",
)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = (
        db.query(PipelineRun)
        .options(joinedload(PipelineRun.steps))
        .filter(PipelineRun.id == run_id)
        .first()
    )
    if not run:
        raise NotFoundError(f"Pipeline run '{run_id}' was not found.")
    return PipelineRunResponse.model_validate(run)
