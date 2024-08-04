from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest  # type: ignore
import requests  # type: ignore
import requests_mock  # type: ignore

from pre_commit_hooks.jira_ticket_check import get_commit_message
from pre_commit_hooks.jira_ticket_check import main
from pre_commit_hooks.jira_ticket_check import validate_jira_ticket


@pytest.fixture  # type: ignore [misc]
def mock_commit_message_file(tmp_path: Path) -> Generator[Path]:
    file = tmp_path / "COMMIT_MSG"
    file.write_text("ABC-123\n")
    yield file


@pytest.fixture  # type: ignore [misc]
def set_env_vars(
    monkeypatch: pytest.MonkeyPatch,
    change_request_required: str = "False",
) -> None:
    monkeypatch.setenv("JIRA_URL", "https://your-jira-instance.atlassian.net")
    monkeypatch.setenv("JIRA_API_TOKEN", "fake_api_token")
    monkeypatch.setenv("JIRA_USERNAME", "fake_username")
    monkeypatch.setenv("CHANGE_REQUEST_REQUIRED", change_request_required)


def test_get_commit_message(mock_commit_message_file: Path) -> None:
    import sys

    sys.argv = [sys.argv[0], str(mock_commit_message_file)]

    commit_message = get_commit_message()
    assert commit_message == "ABC-123"


def test_validate_jira_ticket_success(
    requests_mock: requests_mock.Mocker,
    set_env_vars: None,
) -> None:
    ticket_id = "ABC-123"
    jira_api_url = f"{os.getenv('JIRA_URL')}/rest/api/2/issue/{ticket_id}"

    requests_mock.get(
        jira_api_url,
        json={
            "fields": {
                "status": {
                    "name": "In Progress",
                },
            },
        },
    )

    is_valid = validate_jira_ticket(ticket_id, ["In Progress"])
    assert is_valid is True


def test_validate_jira_ticket_invalid_status(
    requests_mock: requests_mock.Mocker,
    set_env_vars: None,
) -> None:
    ticket_id = "ABC-123"
    jira_api_url = f"{os.getenv('JIRA_URL')}/rest/api/2/issue/{ticket_id}"

    requests_mock.get(
        jira_api_url,
        json={
            "fields": {
                "status": {
                    "name": "To Do",
                },
            },
        },
    )

    is_valid = validate_jira_ticket(ticket_id, ["In Progress"])
    assert is_valid is False


def test_main_valid_ticket(
    monkeypatch: pytest.MonkeyPatch,
    mock_commit_message_file: Path,
    requests_mock: requests_mock.Mocker,
) -> None:
    # Set CHANGE_REQUEST_REQUIRED to "False" for this test
    monkeypatch.setenv("CHANGE_REQUEST_REQUIRED", "False")

    ticket_id = "ABC-123"
    jira_api_url = f"{os.getenv('JIRA_URL')}/rest/api/2/issue/{ticket_id}"

    requests_mock.get(
        jira_api_url,
        json={
            "fields": {
                "status": {
                    "name": "In Progress",
                },
            },
        },
    )

    import sys

    monkeypatch.setattr(sys, "argv", [sys.argv[0], str(mock_commit_message_file)])

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 0


def test_main_no_ticket(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    set_env_vars: None,
) -> None:
    file = tmp_path / "COMMIT_MSG"
    file.write_text("No JIRA ticket\n")

    import sys

    monkeypatch.setattr(sys, "argv", [sys.argv[0], str(file)])

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1


def test_main_change_request_required(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    requests_mock: requests_mock.Mocker,
) -> None:
    file = tmp_path / "COMMIT_MSG"
    file.write_text("ABC-123\nCR-456\n")

    ticket_id_project = "ABC-123"
    ticket_id_cr = "CR-456"
    jira_api_url_project = (
        f"{os.getenv('JIRA_URL')}/rest/api/2/issue/{ticket_id_project}"
    )
    jira_api_url_cr = f"{os.getenv('JIRA_URL')}/rest/api/2/issue/{ticket_id_cr}"

    requests_mock.get(
        jira_api_url_project,
        json={
            "fields": {
                "status": {
                    "name": "In Progress",
                },
            },
        },
    )
    requests_mock.get(
        jira_api_url_cr,
        json={
            "fields": {
                "status": {
                    "name": "Approved",
                },
            },
        },
    )

    import sys

    monkeypatch.setattr(sys, "argv", [sys.argv[0], str(file)])

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 0


def test_validate_jira_ticket_network_failure(
    requests_mock: requests_mock.Mocker,
    set_env_vars: None,
) -> None:
    ticket_id = "ABC-123"
    jira_api_url = f"{os.getenv('JIRA_URL')}/rest/api/2/issue/{ticket_id}"

    requests_mock.get(jira_api_url, exc=requests.exceptions.ConnectionError)

    is_valid = validate_jira_ticket(ticket_id, ["In Progress"])
    assert is_valid is False


def test_validate_jira_ticket_invalid_response(
    requests_mock: requests_mock.Mocker,
    set_env_vars: None,
) -> None:
    ticket_id = "ABC-123"
    jira_api_url = f"{os.getenv('JIRA_URL')}/rest/api/2/issue/{ticket_id}"

    requests_mock.get(jira_api_url, status_code=500)

    is_valid = validate_jira_ticket(ticket_id, ["In Progress"])
    assert is_valid is False


def test_main_network_failure(
    monkeypatch: pytest.MonkeyPatch,
    mock_commit_message_file: Path,
    requests_mock: requests_mock.Mocker,
    set_env_vars: None,
) -> None:
    ticket_id = "ABC-123"
    jira_api_url = f"{os.getenv('JIRA_URL')}/rest/api/2/issue/{ticket_id}"

    requests_mock.get(jira_api_url, exc=requests.exceptions.ConnectionError)

    import sys

    monkeypatch.setattr(sys, "argv", [sys.argv[0], str(mock_commit_message_file)])

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1


def test_main_invalid_response(
    monkeypatch: pytest.MonkeyPatch,
    mock_commit_message_file: Path,
    requests_mock: requests_mock.Mocker,
    set_env_vars: None,
) -> None:
    ticket_id = "ABC-123"
    jira_api_url = f"{os.getenv('JIRA_URL')}/rest/api/2/issue/{ticket_id}"

    requests_mock.get(jira_api_url, status_code=500)

    import sys

    monkeypatch.setattr(sys, "argv", [sys.argv[0], str(mock_commit_message_file)])

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1


def test_invalid_jira_ticket_format(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    set_env_vars: None,
) -> None:
    file = tmp_path / "COMMIT_MSG"
    file.write_text("Invalid ticket format 123-ABC\n")

    import sys

    monkeypatch.setattr(sys, "argv", [sys.argv[0], str(file)])

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1


def test_multiple_tickets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    requests_mock: requests_mock.Mocker,
    set_env_vars: None,
) -> None:
    file = tmp_path / "COMMIT_MSG"
    file.write_text("ABC-123 CR-456\n")

    ticket_id_1 = "ABC-123"
    ticket_id_2 = "CR-456"
    jira_api_url_1 = f"{os.getenv('JIRA_URL')}/rest/api/2/issue/{ticket_id_1}"
    jira_api_url_2 = f"{os.getenv('JIRA_URL')}/rest/api/2/issue/{ticket_id_2}"

    requests_mock.get(
        jira_api_url_1,
        json={
            "fields": {
                "status": {
                    "name": "In Progress",
                },
            },
        },
    )
    requests_mock.get(
        jira_api_url_2,
        json={
            "fields": {
                "status": {
                    "name": "Approved",
                },
            },
        },
    )

    import sys

    monkeypatch.setattr(sys, "argv", [sys.argv[0], str(file)])

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 0
