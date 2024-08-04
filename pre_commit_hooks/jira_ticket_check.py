#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Any

import requests  # type: ignore [import-untyped]

JIRA_URL = os.getenv("JIRA_URL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
CHANGE_REQUEST_REQUIRED = os.getenv("CHANGE_REQUEST_REQUIRED", "True").lower() in (
    "true",
    "1",
    "t",
)

if not JIRA_API_TOKEN or not JIRA_USERNAME:
    print("JIRA_API_TOKEN and JIRA_USERNAME must be set as environment variables.")
    print("Exiting with code 1")
    sys.exit(1)


def get_commit_message() -> str:
    """
    Reads the commit message from the file specified in the command-line arguments.

    Returns:
        str: The content of the commit message.
    """
    with open(sys.argv[1]) as file:
        return file.read().strip()


def jira_api_request(endpoint: str) -> Any:
    """
    Makes a GET request to the JIRA API to retrieve data for a given endpoint.

    Args:
        endpoint (str): The JIRA API endpoint to query.

    Returns:
        Dict[str, Any]: The JSON response from the JIRA API as a dictionary.

    Raises:
        Exception: If the request to the JIRA API fails.
    """
    url = f"{JIRA_URL}/rest/api/2/{endpoint}"
    response = requests.get(url, auth=(JIRA_USERNAME, JIRA_API_TOKEN))
    if response.status_code != 200:
        raise Exception(
            f"Failed to connect to JIRA API: {response.status_code} {response.text}",
        )
    return response.json()


def validate_jira_ticket(ticket_id: str, valid_statuses: list[str]) -> bool:
    """
    Validates a JIRA ticket by checking if it exists and is in one of the valid statuses.

    Args:
        ticket_id (str): The JIRA ticket ID to validate.
        valid_statuses (List[str]): A list of valid statuses.

    Returns:
        bool: True if the ticket is valid and in one of the valid statuses, False otherwise.
    """
    try:
        issue = jira_api_request(f"issue/{ticket_id}")
        status_name = issue["fields"]["status"]["name"]
        if ticket_id.startswith("CR-"):
            if status_name != "Approved":
                print(f"CR ticket {ticket_id} is not in the 'Approved' status.")
                return False
        else:
            if status_name not in valid_statuses:
                print(
                    f"Ticket {ticket_id} is not in one of the valid statuses: {valid_statuses}",
                )
                return False
        return True
    except Exception as e:
        print(f"Failed to validate JIRA ticket {ticket_id}: {e}")
        return False


def main() -> None:
    """
    Main function to check the commit message for valid JIRA tickets and ensure they are in the correct stage.

    It reads the commit message, extracts JIRA tickets, validates them, and checks for required change request tickets
    if applicable. Exits with status 0 if all checks pass, otherwise exits with status 1.
    """

    parser = argparse.ArgumentParser(description="Check JIRA ticket requirements.")
    parser.add_argument(
        "--change-request-required",
        action="store_true",
        help="Specify if a change request is required.",
    )
    args, unknown = parser.parse_known_args()

    change_request_required = args.change_request_required or CHANGE_REQUEST_REQUIRED

    # Your existing logic here, using the change_request_required variable as needed
    print(f"Change request required: {change_request_required}")

    commit_message = get_commit_message()

    ticket_regex = re.compile(r"\b[A-Z]+-\d+\b")
    tickets = ticket_regex.findall(commit_message)

    if not tickets:
        print("No JIRA ticket found in commit message.")
        print("Exiting with code 1")
        sys.exit(1)

    valid_statuses = ["In Progress"]
    cr_ticket_found = False

    if change_request_required:
        if len(tickets) < 2:
            print(
                "Two tickets are required in the commit message when change request is required.",
            )
            sys.exit(1)

        for ticket in tickets:
            if ticket.startswith("CR-"):
                cr_ticket_found = True
                if not validate_jira_ticket(ticket, ["Approved"]):
                    sys.exit(1)
            else:
                if not validate_jira_ticket(ticket, valid_statuses):
                    sys.exit(1)

        if not cr_ticket_found:
            print(
                "Change request ticket (CR-) is required but not found in commit message.",
            )
            sys.exit(1)
    else:
        for ticket in tickets:
            if not validate_jira_ticket(ticket, valid_statuses):
                sys.exit(1)

    print("JIRA ticket(s) validated successfully.")
    print("Exiting with code 0")
    sys.exit(0)


if __name__ == "__main__":
    main()
