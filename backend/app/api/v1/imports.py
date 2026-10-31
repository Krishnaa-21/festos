# OWNER: P2
from typing import Optional

from app.core.change_service import ChangeResult
from app.core.db import get_session
from app.core.deps import get_actor
from app.core.errors import FestOSError
from app.engines.importer import MalformedCSVError, MissingColumnsError
from app.schemas.common import Actor, Envelope, Page
from app.schemas.imports import (
    ImportBatchItem,
    ImportBatchResponse,
    ImportPromoteRequest,
    QuarantineIssueItem,
)
from app.services.imports.service import (
    get_import_batch,
    get_import_issues,
    import_file,
    list_import_batches,
    promote_import_batch,
)
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from sqlmodel import Session

router = APIRouter(prefix="/imports", tags=["Imports"])


@router.post("", response_model=Envelope[ImportBatchResponse])
async def upload_import_file(
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(None),
    dry_run: bool = Form(False),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    filename = file.filename or "uploaded.csv"
    if not filename.lower().endswith((".csv", ".tsv", ".txt")):
        raise FestOSError(
            message=f"Unsupported file type for '{filename}'. Only CSV, TSV, or plain text tables are permitted.",
            code="UNSUPPORTED_MEDIA_TYPE",
            status_code=415,
        )

    try:
        content = await file.read()
        max_bytes = 15 * 1024 * 1024  # 15 MB
        if len(content) > max_bytes:
            raise FestOSError(
                message=f"File '{filename}' ({len(content)} bytes) exceeds the 15 MB maximum upload limit.",
                code="PAYLOAD_TOO_LARGE",
                status_code=413,
            )
        result = import_file(
            session=session,
            file_content=content,
            filename=filename,
            sheet_name=sheet_name,
            dry_run=dry_run,
            actor=actor,
        )
        warnings = []
        if result.quarantined_rows > 0:
            warnings.append(
                f"{result.quarantined_rows} rows were quarantined due to validation errors. Review issues before promotion."
            )
        return Envelope(
            data=result,
            meta={"filename": filename, "idempotency_key": idempotency_key},
            warnings=warnings,
        )
    except MalformedCSVError as e:
        raise FestOSError(message=str(e), code="MALFORMED_CSV", status_code=422)
    except MissingColumnsError as e:
        raise FestOSError(
            message=str(e),
            code="MISSING_COLUMNS",
            status_code=422,
            details={"missing_columns": e.missing_columns, "sheet_name": e.sheet_name},
        )
    except FestOSError:
        raise
    except Exception as e:
        raise FestOSError(message=f"Failed to process import: {e}", code="IMPORT_ERROR", status_code=500)


@router.get("", response_model=Envelope[Page[ImportBatchItem]])
def get_import_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Lists import batch history with pagination and status filtering."""
    items, total = list_import_batches(session=session, page=page, page_size=page_size, status=status)
    page_data = Page.create(items=items, total=total, page=page, page_size=page_size)
    return Envelope(data=page_data)


@router.get("/{id}", response_model=Envelope[ImportBatchItem])
def get_import_batch_details(
    id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Fetches details for a specific import batch."""
    batch = get_import_batch(session=session, batch_id=id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Import batch '{id}' not found")
    return Envelope(data=batch)


@router.get("/{id}/issues", response_model=Envelope[Page[QuarantineIssueItem]])
def get_import_batch_issues(
    id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Retrieves quarantined rows and validation reasons for an import batch."""
    items, total = get_import_issues(session=session, batch_id=id, page=page, page_size=page_size)
    page_data = Page.create(items=items, total=total, page=page, page_size=page_size)
    return Envelope(data=page_data)


@router.post("/{id}/promote", response_model=Envelope[ChangeResult])
def post_promote_import_batch(
    id: str,
    body: ImportPromoteRequest = ImportPromoteRequest(),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Promotes staged records to canonical tables through ChangeService handler imports.promote."""
    result = promote_import_batch(
        session=session,
        batch_id=id,
        actor=actor,
        reason=body.reason,
        dry_run=body.dry_run,
        expected_version=body.expected_version,
    )
    return Envelope(
        data=result,
        meta={"batch_id": id, "idempotency_key": idempotency_key},
        warnings=result.warnings,
    )
