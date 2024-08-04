#!/bin/bash

export CHANGE_REQUEST_REQUIRED=False
export JIRA_URL="https://your-jira-instance.atlassian.net"
PYTHONPATH=$(pwd) pytest
