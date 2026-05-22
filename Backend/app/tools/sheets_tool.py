"""Sheets/CSV/Excel query tool — wraps existing sheets service and pandas agent."""
from __future__ import annotations

from typing import Any


async def execute_sheets_query(
    question: str,
    source_type: str,
    user_email: str = "system",
    sheet_url: str | None = None,
    attachment_id: str | None = None,
) -> dict[str, Any]:
    """Query spreadsheet data using natural language.

    Args:
        question: Natural language question about the data
        source_type: "google_sheet", "csv", or "xlsx"
        user_email: User's email for LLM metadata
        sheet_url: Google Sheets URL (for google_sheet source_type)
        attachment_id: Attachment ID (for csv/xlsx source_type)

    Returns:
        dict with keys: success, answer, source_type
    """
    if not question or not question.strip():
        return {"success": False, "error": "Question cannot be empty"}

    if source_type not in ("google_sheet", "csv", "xlsx"):
        return {"success": False, "error": f"Invalid source_type: {source_type}. Must be 'google_sheet', 'csv', or 'xlsx'"}

    if source_type == "google_sheet" and not sheet_url:
        return {"success": False, "error": "sheet_url is required for google_sheet source_type"}

    if source_type in ("csv", "xlsx") and not attachment_id:
        return {"success": False, "error": "attachment_id is required for csv/xlsx source_type"}

    try:
        from app.ai.chains.sheets_agent import run_dataframe_agent
        from app.services.sheets_service import load_csv, load_google_sheet, load_xlsx

        # Load the dataframe based on source type
        if source_type == "google_sheet":
            df = load_google_sheet(sheet_url)
        elif source_type == "csv":
            from app.services.sheets_service import _file_cache
            from pathlib import Path
            from app.core.config import settings

            # Build file path from attachment_id
            file_path = Path(settings.UPLOAD_DIR) / attachment_id
            df = load_csv(str(file_path))
        elif source_type == "xlsx":
            from pathlib import Path
            from app.core.config import settings

            file_path = Path(settings.UPLOAD_DIR) / attachment_id
            df = load_xlsx(str(file_path))
        else:
            return {"success": False, "error": f"Unsupported source_type: {source_type}"}

        # Run the pandas agent
        answer = await run_dataframe_agent(
            df=df,
            question=question.strip(),
            user_email=user_email,
        )

        return {
            "success": True,
            "answer": answer,
            "source_type": source_type,
            "question": question.strip(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Sheets query failed: {e}",
        }
