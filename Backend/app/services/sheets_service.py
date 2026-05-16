from __future__ import annotations

import hashlib
import io
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import gspread
import pandas as pd
from cachetools import TTLCache
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build

from app.core.config import settings

# --- Cache structures ---

@dataclass
class SheetCacheEntry:
    """A cached Google Sheet DataFrame with revision metadata."""
    df: pd.DataFrame
    modified_time: str  # ISO 8601 from Drive API
    cached_at: str  # ISO 8601 when cached
    source_type: str = "google_sheet"
    sheet_id: str = ""


# Short TTL for Google Sheets (60s safety net)
_sheet_cache: TTLCache = TTLCache(maxsize=20, ttl=60)

# Long TTL for uploaded files (content never changes)
_file_cache: TTLCache = TTLCache(maxsize=20, ttl=3600)


def _get_credentials_dict() -> dict:
    """Parse and return the service account credentials dict."""
    raw = settings.GOOGLE_SERVICE_ACCOUNT_JSON
    if not raw:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON is not set. "
            "Provide the full service-account JSON string in .env."
        )
    return json.loads(raw)


def _extract_sheet_id(sheet_url: str) -> str:
    """Extract the spreadsheet ID from a Google Sheets URL."""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not match:
        raise ValueError(f"Cannot extract sheet ID from URL: {sheet_url}")
    return match.group(1)


def _get_drive_modified_time(sheet_id: str, creds_dict: dict) -> str:
    """Fetch the modifiedTime of a Google Sheet via Drive API (lightweight metadata call)."""
    try:
        credentials = ServiceAccountCredentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/drive.metadata.readonly"],
        )
        service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        file_meta = service.files().get(fileId=sheet_id, fields="modifiedTime").execute()
        return file_meta["modifiedTime"]
    except Exception:
        # If Drive API fails, return empty string to force re-fetch
        return ""


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Infer types and strip whitespace from string columns."""
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().any() and converted.notna().sum() > len(df) * 0.5:
            df[col] = converted
            continue
        try:
            df[col] = pd.to_datetime(df[col], format="mixed", dayfirst=False)
            continue
        except (ValueError, TypeError):
            pass
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()
    return df


def _fetch_sheet_data(sheet_url: str, creds_dict: dict) -> pd.DataFrame:
    """Fetch the actual sheet data from Google Sheets API."""
    gc = gspread.service_account_from_dict(creds_dict)
    try:
        spreadsheet = gc.open_by_url(sheet_url)
    except gspread.exceptions.SpreadsheetNotFound:
        raise ValueError(
            "Spreadsheet not found. Make sure the sheet is shared with "
            "the service account: id-am-azur-chatbot-sheets@micro-territory-495005-j4.iam.gserviceaccount.com"
        )
    worksheet = spreadsheet.sheet1
    all_values = worksheet.get_all_values()
    if not all_values or len(all_values) < 2:
        raise ValueError("The Google Sheet is empty or has no data rows.")
    headers = all_values[0]
    rows = all_values[1:]
    df = pd.DataFrame(rows, columns=headers)
    df = _clean_dataframe(df)
    return df


def load_google_sheet(sheet_url: str, refresh: bool = False) -> tuple[pd.DataFrame, str, str]:
    """Load a Google Sheet with revision-based cache invalidation.

    Returns: (DataFrame, modifiedTime ISO string, cache_status: "HIT"|"MISS"|"FORCED-MISS")
    """
    sheet_id = _extract_sheet_id(sheet_url)
    creds_dict = _get_credentials_dict()

    # Force refresh bypasses cache entirely
    if refresh:
        df = _fetch_sheet_data(sheet_url, creds_dict)
        modified_time = _get_drive_modified_time(sheet_id, creds_dict)
        entry = SheetCacheEntry(
            df=df,
            modified_time=modified_time,
            cached_at=datetime.now(timezone.utc).isoformat(),
            sheet_id=sheet_id,
        )
        _sheet_cache[sheet_id] = entry
        return df, modified_time, "FORCED-MISS"

    # Check cache
    cached: Optional[SheetCacheEntry] = _sheet_cache.get(sheet_id)
    if cached is not None:
        # Revision-based invalidation: compare modifiedTime
        current_modified = _get_drive_modified_time(sheet_id, creds_dict)
        if current_modified and current_modified == cached.modified_time:
            return cached.df, cached.modified_time, "HIT"
        # Sheet was updated — invalidate and re-fetch
        # (fall through to MISS path)

    # Cache MISS — fetch fresh data
    df = _fetch_sheet_data(sheet_url, creds_dict)
    modified_time = _get_drive_modified_time(sheet_id, creds_dict)
    entry = SheetCacheEntry(
        df=df,
        modified_time=modified_time,
        cached_at=datetime.now(timezone.utc).isoformat(),
        sheet_id=sheet_id,
    )
    _sheet_cache[sheet_id] = entry
    return df, modified_time, "MISS"


def load_csv(file_bytes: bytes) -> pd.DataFrame:
    """Load CSV from bytes into a cleaned DataFrame."""
    md5 = hashlib.md5(file_bytes).hexdigest()
    if md5 in _file_cache:
        return _file_cache[md5]
    df = pd.read_csv(io.BytesIO(file_bytes))
    if df.empty:
        raise ValueError("The CSV file is empty or could not be parsed.")
    df = _clean_dataframe(df)
    _file_cache[md5] = df
    return df


def load_xlsx(file_bytes: bytes) -> pd.DataFrame:
    """Load Excel from bytes into a cleaned DataFrame."""
    md5 = hashlib.md5(file_bytes).hexdigest()
    if md5 in _file_cache:
        return _file_cache[md5]
    df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    if df.empty:
        raise ValueError("The Excel file is empty or could not be parsed.")
    df = _clean_dataframe(df)
    _file_cache[md5] = df
    return df


# --- Cache management functions ---

def clear_sheet_cache(sheet_id: Optional[str] = None) -> int:
    """Clear cache entries. Returns number of entries removed."""
    if sheet_id:
        if sheet_id in _sheet_cache:
            del _sheet_cache[sheet_id]
            return 1
        return 0
    else:
        count = len(_sheet_cache)
        _sheet_cache.clear()
        return count


def get_cache_status() -> list[dict]:
    """Return info about all current cache entries."""
    entries = []
    for key, entry in _sheet_cache.items():
        if isinstance(entry, SheetCacheEntry):
            entries.append({
                "key": key,
                "source_type": entry.source_type,
                "cached_at": entry.cached_at,
                "modified_time": entry.modified_time,
                "rows": len(entry.df),
                "columns": list(entry.df.columns),
            })
    # Also include file cache entries
    for key in _file_cache:
        df = _file_cache[key]
        entries.append({
            "key": key,
            "source_type": "uploaded_file",
            "cached_at": None,
            "modified_time": None,
            "rows": len(df),
            "columns": list(df.columns),
        })
    return entries


def load_sheet_as_dataframe(sheet_url: str) -> pd.DataFrame:
    """Backward-compatible alias."""
    df, _, _ = load_google_sheet(sheet_url)
    return df
