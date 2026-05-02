import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services.auth_service import auth_service


def test_validate_employee_email_accepts_allowed_domains(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "EMPLOYEE_EMAIL_DOMAINS", "stackyon.com,amzur.com")

    normalized = auth_service._validate_employee_email(" User@Stackyon.com ")

    assert normalized == "user@stackyon.com"


def test_validate_employee_email_rejects_bad_format(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "EMPLOYEE_EMAIL_DOMAINS", "stackyon.com")

    with pytest.raises(HTTPException) as exc:
        auth_service._validate_employee_email("bad-email")

    assert exc.value.status_code == 400


def test_validate_employee_email_rejects_non_employee_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "EMPLOYEE_EMAIL_DOMAINS", "stackyon.com")

    with pytest.raises(HTTPException) as exc:
        auth_service._validate_employee_email("user@gmail.com")

    assert exc.value.status_code == 403
