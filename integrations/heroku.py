"""
Heroku Platform Module for Tradier Copy Bot

This module provides functions for managing Heroku dynos via the Platform API.

Key Functions:
    - get_dynos: List all dynos
    - start: Start a detached worker dyno
    - stop: Stop a running dyno
    - restart: Restart a dyno
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import json
import os
import time

import requests


# ==============================================================================
# GLOBAL CONFIGURATION
# ==============================================================================

heroku_url = 'https://api.heroku.com'
apps_url = f'{heroku_url}/apps'
main_name = "main"

# ==============================================================================
# API AUTHENTICATION
# ==============================================================================

def dyno_headers():
    """Generate authentication headers for Heroku Platform API."""
    heroku_token = os.getenv("HEROKU_API_TOKEN", "")
    app_name = os.getenv("HEROKU_APP_NAME", "")
    headers = {
        "Accept": "application/vnd.heroku+json; version=3",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {heroku_token}",
    }
    return {"headers": headers, "name": app_name}

# ==============================================================================
# DYNO MANAGEMENT
# ==============================================================================

def get_dynos():
    """Retrieve list of all dynos for the application."""
    config = dyno_headers()
    headers = config['headers']
    app_name = config['name']
    url = f'{apps_url}/{app_name}/dynos'
    response = requests.get(url, headers=headers)
    if response.status_code in [200, 201]:
        return json.loads(response.content)
    return []


def start(main_name="main"):
    """Start a detached worker dyno if not already running."""
    dyno_content = get_dynos()
    detached = [d for d in dyno_content if d.get('command') == f'python {main_name}.py']

    if len(detached) == 0:
        config = dyno_headers()
        headers = config['headers']
        app_name = config['name']
        data = {"command": f"python {main_name}.py", "type": "run:detached"}
        url = f'{apps_url}/{app_name}/dynos'
        response = requests.post(url, data=json.dumps(data), headers=headers)
        content = json.loads(response.content)
        print(content)
        return content
    else:
        return detached


def stop(main_name="main"):
    """Stop a running detached worker dyno."""
    dyno_content = get_dynos()
    detached = [d for d in dyno_content if d.get('command') == f'python {main_name}.py']

    if len(detached) == 0:
        print("Dyno already stopped")
        return detached
    else:
        dyno_id = detached[0]['id']
        config = dyno_headers()
        headers = config['headers']
        app_name = config['name']
        url = f'{apps_url}/{app_name}/dynos/{dyno_id}/actions/stop'
        response = requests.post(url, headers=headers)
        content = json.loads(response.content)
        print(content)
        return content


def restart(main_name="main"):
    """Restart a detached worker dyno."""
    dyno_content = get_dynos()
    detached = [d for d in dyno_content if d.get('command') == f'python {main_name}.py']

    if len(detached) == 0:
        start(main_name)
    else:
        stop(main_name)
        time.sleep(5)
        start(main_name)
    return detached

# END
