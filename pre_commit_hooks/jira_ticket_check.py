#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Any

import requests


def get_jira_issue_status(jira_url: str, ticket_id: str, token: str) -> str:
    url = f"{jira_url}/rest/api/2/issue/{ticket_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to get JIRA issue {ticket_id}: {response.status_code}")
        sys.exit(1)

    issue_data: dict[str, Any] = response.json()
    status: str = issue_data["fields"]["status"]["name"]
    return status


def main() -> None:
    parser = argparse.ArgumentParser(description="Check JIRA ticket status.")
    parser.add_argument(
        "--allowed-statuses",
        nargs="+",
        required=True,
        help="List of allowed JIRA statuses",
    )
    args = parser.parse_args()

    # Load configuration from the environment
    jira_url = os.getenv("JIRA_URL")
    jira_token = os.getenv("JIRA_TOKEN")
    if not jira_url or not jira_token:
        print("Please set the JIRA_URL and JIRA_TOKEN environment variables.")
        sys.exit(1)

    allowed_statuses: list[str] = args.allowed_statuses

    # Find JIRA ticket IDs in commit messages
    commit_message = sys.stdin.read()
    ticket_ids = re.findall(r"\b[A-Z]{2,}-\d+\b", commit_message)

    if not ticket_ids:
        print("No JIRA ticket IDs found in the commit message.")
        sys.exit(0)

    # Check each ticket ID
    for ticket_id in ticket_ids:
        status = get_jira_issue_status(jira_url, ticket_id, jira_token)
        if status not in allowed_statuses:
            print(
                f"JIRA ticket {ticket_id} is in status '{status}', which is not allowed.",
            )
            sys.exit(1)

    print("All JIRA tickets are in allowed statuses.")
    sys.exit(0)


if __name__ == "__main__":
    main()
