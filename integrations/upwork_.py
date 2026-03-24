"""
Upwork Messaging Module for Tradier Copy Bot

This module provides functions for interacting with the Upwork API to send,
read, and search messages. Uses the official python-upwork-oauth2 library
with GraphQL.

Setup:
    1. Go to Upwork Developer Portal:
        - View existing keys: https://www.upwork.com/developer/keys
        - Create new app: https://www.upwork.com/developer/keys/apply
    2. Create a new API application:
        - App Name: Your app name
        - App Description: Brief description
        - Callback URL: http://localhost:8080/callback (for local dev)
    3. Request permissions (select from available scopes):
        Required for this module:
            - Messaging - Read and Write Access (rooms and messages)
        Optional:
            - Common Entities - Read-Only Access (for sender filter & get_user_info)

        All available scopes:
            - Activity Entities - Read-Only Access
            - Activity Entities - Read and Write Access
            - Client Proposals - Read And Write Access
            - Common Entities - Read-Only Access (City, Country, Organization, User, Money)
            - Common Functionality - Read And Write Access
            - Contract - Read and Write Access
            - Freelancer Profile - Read And Write Access
            - Management Job Postings (client side)
            - Job Postings - Read-Only Access (client view)
            - Job Postings - Read and Write Access
            - Organization - Read and Write Access
            - Read marketplace Job Postings (public)
            - Messaging - Read-Only Access (rooms and messages)
            - Messaging - Read and Write Access (rooms and messages)
            - Offer - Read-Only Access
            - Offer - Read And Write Access
            - Ontology - Read-Only Access
            - Payments - Read and Write Access
            - Snapshots - Read-Only Access (public)
            - Submit Proposal (coming soon)
            - Talent Profile - Read And Write Access
            - Talent Workhistory - Read Only Access
            - TimeSheet - Read-Only Access
            - Transaction Data - Read-Only Access (history info)
            - Common Entities - Read-Only Access (public user)
            - Work Diary Company - Read-Only Access (snapshots for company)
    4. Once approved, copy your credentials to .env file:
        UPWORK_API=your_client_id
        UPWORK_SECRET=your_client_secret
        UPWORK_CALLBACK=http://localhost:8080/callback
    5. Run OAuth flow to get tokens:
        python scripts/upwork_manager.py --auth
    6. Add tokens to .env:
        UPWORK_ACCESS_TOKEN=your_access_token
        UPWORK_REFRESH_TOKEN=your_refresh_token

    Required packages: pip install python-upwork-oauth2 python-dotenv

Key Functions:
    Authentication:
        - get_authorization_url()
            Generate OAuth2 authorization URL
            Returns: (authorization_url, state)

        - exchange_code_for_token(authorization_response_url)
            Exchange auth code for access tokens
            Params: authorization_response_url (str) - Full callback URL with code

        - run_oauth_flow()
            Interactive OAuth flow with local server (opens browser)

    Messaging:
        - send_message(room_ids=None, message="", send_time=None, attachment=None, client_name=None)
            Send messages to one or more rooms
            Params: room_ids (list, optional) - Room IDs to send to
                    message (str) - Message content or path to .txt file
                    send_time (datetime/int, optional) - When to send:
                        None = send now, datetime = specific time, int = X minutes from now
                    attachment (str, optional) - Path to file to attach
                    client_name (str, optional) - Find room by client name if room_ids not provided

        - read_messages(room_id, limit=10, start_date=None, end_date=None, sender=None, order="desc")
            Read message history with filtering
            Params: room_id (str) - Room identifier
                    limit (int) - Max messages to retrieve
                    start_date (datetime, optional) - Filter from date
                    end_date (datetime, optional) - Filter to date
                    sender (str, optional) - Filter by sender name
                    order (str) - Sort order: "desc" (newest first) or "asc" (oldest first)

        - search_messages(query, room_id=None, limit=10, case_sensitive=False, match_all=False, start_date=None, end_date=None)
            Search for messages by keyword/phrase (single or multiple)
            Params: query (str or list) - Search text or list of keywords
                    room_id (str, optional) - Room to search (None=all rooms)
                    limit (int) - Max matches to return
                    case_sensitive (bool) - Case-sensitive search
                    match_all (bool) - For multiple queries: True=ALL, False=ANY
                    start_date (datetime, optional) - Filter from date
                    end_date (datetime, optional) - Filter to date

    Rooms:
        - get_rooms(room_ids=None)
            Retrieve message rooms/conversations
            Params: room_ids (str/list, optional) - Room ID(s) to get (None = all rooms)
            Returns: list (all/multiple) or dict (single) or None

        - find_rooms(client_name)
            Find room IDs by client name (case-insensitive partial match)

        - get_user_info()
            Get current authenticated user info (requires Common Entities - Read-Only Access scope)

        - get_client_info(client_name)
            Get client information by name (from room data and messages)
            Params: client_name (str) - Client name to search for (case-insensitive partial match)
            Returns: dict with name, room_id, room_topic, last_message or None

    Scheduling:
        - clear_scheduled_messages(message_ids=None)
            Clear messages from the scheduled queue
            Params: message_ids (list, optional) - IDs to clear (None = clear all)

        - get_scheduled_messages(message_ids=None)
            Get pending scheduled messages
            Params: message_ids (str/list, optional) - Message ID(s) (None = all)

        - run_scheduler(max_runtime=None)
            Run the scheduler loop (sends messages at top of each minute)

        - process_scheduled_messages()
            Check and send any messages that are due

    Utilities:
        - get_config()
            Get API configuration dict from environment variables

        - get_client()
            Get or create authenticated Upwork client

        - get_graphql()
            Get or create GraphQL API instance

API Documentation:
    https://developers.upwork.com/

Environment Variables:
    - UPWORK_API: Client ID
    - UPWORK_SECRET: Client secret
    - UPWORK_CALLBACK: OAuth callback URL (default: http://localhost:8080/callback)
    - UPWORK_ACCESS_TOKEN: OAuth access token
    - UPWORK_REFRESH_TOKEN: OAuth refresh token

Testing:
    46 tests across 8 categories (NO real messages are sent).
    See tests/test_upwork.py for test suite.

    Run tests:
        python tests/test_upwork.py           # Run basic tests (no API calls)
        python tests/test_upwork.py --api     # Run all tests including API calls

    Run CLI commands:
        python scripts/upwork_manager.py --auth       # Run OAuth flow to get tokens
        python scripts/upwork_manager.py --rooms      # List all message rooms
        python scripts/upwork_manager.py --scheduler  # Run message scheduler
        python scripts/upwork_manager.py --help       # Show all options

Note: The REST Messages API is deprecated. This module uses GraphQL.

"""

# ==============================================================================
# IMPORTS
# ==============================================================================

from datetime import datetime, timedelta, timezone
import json
import os

from dotenv import load_dotenv
from requests_oauthlib import OAuth2Session
import pytz


# Allow OAuth over HTTP for localhost development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

import upwork
from upwork.routers import graphql

# Load environment variables
load_dotenv()

# Upwork OAuth token endpoint
UPWORK_TOKEN_URL = 'https://www.upwork.com/api/v3/oauth2/token'

# ==============================================================================
# GLOBAL CONFIGURATION
# ==============================================================================

_client = None
_graphql_api = None
_scheduler_running = False

# File to store scheduled messages (in assets folder)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEDULED_MESSAGES_FILE = os.path.join(PROJECT_ROOT, 'assets', 'scheduled_messages.json')

# ==============================================================================
# API AUTHENTICATION
# ==============================================================================

def get_config():
    """
    Get Upwork API configuration from environment variables.

    Returns:
        dict: Configuration dictionary for upwork.Config

    Example:
        >>> config = get_config()
        >>> client = upwork.Client(upwork.Config(config))
    """
    config = {
        'client_id': os.getenv('UPWORK_API'),
        'client_secret': os.getenv('UPWORK_SECRET'),
        'redirect_uri': os.getenv('UPWORK_CALLBACK', 'http://localhost:8080/callback'),
    }

    # Add token if we have one
    access_token = os.getenv('UPWORK_ACCESS_TOKEN')
    refresh_token = os.getenv('UPWORK_REFRESH_TOKEN')

    if access_token:
        config['token'] = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
        }

    return config


def refresh_access_token(update_env_file=True):
    """
    Refresh the Upwork access token using the refresh token.

    Uses OAuth2Session to obtain a new access token when the current one expires.
    Automatically updates environment variables and optionally the .env file.

    Args:
        update_env_file (bool): Whether to update the .env file with new tokens.
            Defaults to True.

    Returns:
        dict: New token dictionary with 'access_token' and 'refresh_token',
              or None if refresh failed.
    """
    global _client, _graphql_api

    client_id = os.getenv('UPWORK_API')
    client_secret = os.getenv('UPWORK_SECRET')
    refresh_token = os.getenv('UPWORK_REFRESH_TOKEN')

    if not all([client_id, client_secret, refresh_token]):
        print("Error: Missing Upwork API credentials for token refresh")
        return None

    # Create token dict for OAuth2Session
    token = {
        'access_token': os.getenv('UPWORK_ACCESS_TOKEN'),
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
    }

    try:
        oauth = OAuth2Session(client_id, token=token)
        new_token = oauth.refresh_token(
            UPWORK_TOKEN_URL,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token
        )

        # Update environment variables in memory
        os.environ['UPWORK_ACCESS_TOKEN'] = new_token['access_token']
        os.environ['UPWORK_REFRESH_TOKEN'] = new_token['refresh_token']

        # Reset cached client and graphql instances to use new token
        _client = None
        _graphql_api = None

        # Update .env file if requested
        if update_env_file:
            _update_env_file(new_token['access_token'], new_token['refresh_token'])

        print("Upwork access token refreshed successfully")
        return new_token

    except Exception as e:
        print(f"Error refreshing Upwork token: {e}")
        return None


def _update_env_file(access_token, refresh_token):
    """
    Update the .env file with new Upwork tokens.

    Args:
        access_token (str): New access token
        refresh_token (str): New refresh token
    """
    env_path = os.path.join(PROJECT_ROOT, '.env')

    if not os.path.exists(env_path):
        print(f"Warning: .env file not found at {env_path}")
        return

    try:
        with open(env_path, 'r') as f:
            lines = f.readlines()

        updated_lines = []
        access_updated = False
        refresh_updated = False

        for line in lines:
            if line.startswith('UPWORK_ACCESS_TOKEN='):
                updated_lines.append(f'UPWORK_ACCESS_TOKEN={access_token}\n')
                access_updated = True
            elif line.startswith('UPWORK_REFRESH_TOKEN='):
                updated_lines.append(f'UPWORK_REFRESH_TOKEN={refresh_token}\n')
                refresh_updated = True
            else:
                updated_lines.append(line)

        # Add tokens if they weren't in the file
        if not access_updated:
            updated_lines.append(f'UPWORK_ACCESS_TOKEN={access_token}\n')
        if not refresh_updated:
            updated_lines.append(f'UPWORK_REFRESH_TOKEN={refresh_token}\n')

        with open(env_path, 'w') as f:
            f.writelines(updated_lines)

        print(f"Updated .env file with new Upwork tokens")

    except Exception as e:
        print(f"Warning: Could not update .env file: {e}")


def _is_auth_error(result):
    """
    Check if an API result indicates an authentication error.

    Args:
        result (dict): API response dictionary

    Returns:
        bool: True if the result indicates authentication failure
    """
    if not isinstance(result, dict):
        return False

    # Check for 'message' field with auth error
    message = result.get('message', '').lower()
    if 'authentication' in message or 'unauthorized' in message:
        return True

    # Check for 'errors' field with auth-related errors
    errors = result.get('errors', [])
    if isinstance(errors, list):
        for error in errors:
            error_str = str(error).lower()
            if 'authentication' in error_str or 'unauthorized' in error_str or 'token' in error_str:
                return True

    return False


def get_client():
    """
    Get or create the Upwork API client.

    Returns:
        upwork.Client: Authenticated Upwork client

    Example:
        >>> client = get_client()
        >>> # Use client for API calls
    """
    global _client

    if _client is None:
        config = get_config()
        _client = upwork.Client(upwork.Config(config))

    return _client


def get_graphql():
    """
    Get or create the GraphQL API instance.

    Returns:
        upwork.routers.graphql.Api: GraphQL API instance

    Example:
        >>> gql = get_graphql()
        >>> result = gql.execute({"query": "..."})
    """
    global _graphql_api

    if _graphql_api is None:
        client = get_client()
        _graphql_api = graphql.Api(client)

    return _graphql_api


def execute_graphql(query_data, retry_on_auth_error=True):
    """
    Execute a GraphQL query with automatic token refresh on authentication errors.

    This is the recommended way to execute GraphQL queries as it handles
    token expiration automatically.

    Args:
        query_data (dict): GraphQL query dictionary with 'query' and optional 'variables'
        retry_on_auth_error (bool): Whether to refresh token and retry on auth error.
            Defaults to True.

    Returns:
        dict: GraphQL response dictionary

    Example:
        >>> result = execute_graphql({
        ...     "query": "query { roomList { edges { node { id } } } }"
        ... })
    """
    gql = get_graphql()
    result = gql.execute(query_data)

    # Check for authentication error and retry with refreshed token
    if retry_on_auth_error and _is_auth_error(result):
        print("Authentication error detected, refreshing token...")
        new_token = refresh_access_token()

        if new_token:
            # Get fresh graphql instance with new token
            gql = get_graphql()
            result = gql.execute(query_data)
        else:
            print("Token refresh failed, cannot retry request")

    return result


# ==============================================================================
# OAUTH FLOW
# ==============================================================================

def get_authorization_url():
    """
    Generate the OAuth2 authorization URL for user login.

    Returns:
        tuple: (authorization_url, state) for OAuth flow

    Example:
        >>> url, state = get_authorization_url()
        >>> print(f"Visit this URL to authorize: {url}")
    """
    client = get_client()
    return client.get_authorization_url()


def exchange_code_for_token(authorization_response_url):
    """
    Exchange authorization response URL for access and refresh tokens.

    Args:
        authorization_response_url (str): The full callback URL with code parameter

    Returns:
        dict: Token dictionary containing access_token, refresh_token, etc.
    """
    global _client

    client = get_client()
    config = get_config()
    redirect_uri = config.get("redirect_uri", "http://localhost:8080/callback")

    # Set redirect_uri on the OAuth session (library omits it when a token
    # already exists in config, causing "Missing parameters: redirect_uri")
    oauth_session = client._Client__oauth
    oauth_session.redirect_uri = redirect_uri

    token = client.get_access_token(authorization_response = authorization_response_url)

    print("\nTokens received successfully!")
    print(f"Add these to your .env file:\n")
    print(f"UPWORK_ACCESS_TOKEN={token.get('access_token')}")
    print(f"UPWORK_REFRESH_TOKEN={token.get('refresh_token')}")

    # Update .env file automatically
    _update_env_file(token.get("access_token"), token.get("refresh_token"))

    return token


def run_oauth_flow():
    """
    Run interactive OAuth flow to obtain access token.

    Starts a simple HTTP server to capture the OAuth callback,
    then exchanges the code for tokens.

    Returns:
        dict: Token response or None if failed
    """
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import webbrowser
    import threading

    callback_url = None
    server_done = threading.Event()

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal callback_url
            # Store the full callback URL
            callback_url = f"http://localhost:8080{self.path}"

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization successful!</h1><p>You can close this window.</p></body></html>")
            server_done.set()

        def log_message(self, format, *args):
            pass  # Suppress logging

    # Start server
    server = HTTPServer(('localhost', 8080), CallbackHandler)
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.start()

    # Open browser
    auth_url, state = get_authorization_url()
    print(f"\nOpening browser for authorization...")
    print(f"If browser doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for callback
    print("Waiting for authorization...")
    server_done.wait(timeout=120)
    server.server_close()

    if callback_url:
        return exchange_code_for_token(callback_url)
    else:
        print("Authorization timed out or failed")
        return None


# ==============================================================================
# GRAPHQL QUERIES
# ==============================================================================

# Query to get all rooms
QUERY_GET_ROOMS = """
query getRooms {
    roomList {
        totalCount
        edges {
            node {
                id
                topic
                roomName
                favorite
            }
        }
    }
}
"""

# Query to get messages from a room (basic - no date filter)
QUERY_GET_MESSAGES = """
query getMessages($roomId: ID!, $first: Int!) {
    room(id: $roomId) {
        id
        roomName
        topic
        stories(filter: {pagination: {first: $first}}) {
            totalCount
            edges {
                node {
                    id
                    message
                    createdDateTime
                }
            }
        }
    }
}
"""

# Query to get messages with date range filter (uses roomStories)
QUERY_GET_MESSAGES_WITH_DATE = """
query getMessages($roomId: ID!, $first: Int!, $rangeStart: String, $rangeEnd: String) {
    roomStories(filter: {
        roomId_eq: $roomId,
        storyFilter: {
            pagination: {first: $first},
            storyCreatedDateTime_bt: {rangeStart: $rangeStart, rangeEnd: $rangeEnd}
        }
    }) {
        totalCount
        edges {
            node {
                id
                message
                createdDateTime
            }
        }
    }
}
"""

# Query to get messages with date range filter AND sender info
QUERY_GET_MESSAGES_WITH_DATE_AND_SENDER = """
query getMessages($roomId: ID!, $first: Int!, $rangeStart: String, $rangeEnd: String) {
    roomStories(filter: {
        roomId_eq: $roomId,
        storyFilter: {
            pagination: {first: $first},
            storyCreatedDateTime_bt: {rangeStart: $rangeStart, rangeEnd: $rangeEnd}
        }
    }) {
        totalCount
        edges {
            node {
                id
                message
                createdDateTime
                user {
                    name
                }
            }
        }
    }
}
"""

# Query to get messages with sender info (requires broader OAuth permissions)
QUERY_GET_MESSAGES_WITH_SENDER = """
query getMessages($roomId: ID!, $first: Int!) {
    room(id: $roomId) {
        id
        roomName
        topic
        stories(filter: {pagination: {first: $first}}) {
            totalCount
            edges {
                node {
                    id
                    message
                    createdDateTime
                    user {
                        name
                    }
                }
            }
        }
    }
}
"""

# Mutation to send a message (createRoomStoryV2)
MUTATION_SEND_MESSAGE = """
mutation sendMessage($roomId: ID!, $message: String!) {
    createRoomStoryV2(input: {roomId: $roomId, message: $message}) {
        id
        message
        createdDateTime
    }
}
"""

# Query to get current user info (requires Common Entities - Read-Only Access scope)
# Note: This query may not work with limited message-only OAuth scopes
QUERY_GET_USER = """
query {
    user {
        id
        nid
    }
}
"""

# ==============================================================================
# MESSAGE OPERATIONS
# ==============================================================================

def get_user_info():
    """
    Get current authenticated user info.

    Note: This requires Common Entities - Read-Only Access OAuth scope which may not be available
    with message-only scopes.

    Returns:
        dict: User information or None if permissions insufficient

    Example:
        >>> info = get_user_info()
        >>> if info:
        ...     print(f"User ID: {info['id']}")
    """
    result = execute_graphql({
        "query": QUERY_GET_USER
    })

    if 'errors' in result:
        # Check if it's a permission error
        error_msg = str(result['errors'])
        if 'permissions' in error_msg.lower() or 'scope' in error_msg.lower():
            return None  # Silent fail for permission issues
        print(f"Error: {result['errors']}")
        return None

    return result.get('data', {}).get('user')


def get_client_info(client_name):
    """
    Get information about a client by name.

    Looks up client info from room data and recent messages.

    Args:
        client_name (str): Client name to search for (case-insensitive partial match)

    Returns:
        dict or None: Client information if found, containing:
            - name (str): Client's name (from room)
            - room_id (str): Room ID for this client
            - room_topic (str): Room topic/subject
            - last_message (dict, optional): Most recent message info
        Returns None if client not found.

    Example:
        >>> client = get_client_info("Ian")
        >>> print(client['name'])
    """
    # Find the room for this client
    result = find_rooms(client_name)
    if result.get('error') or not result.get('rooms'):
        return None

    # If multiple matches, use the first one
    room = result['rooms'][0]
    room_id = room['id']
    room_name = room['roomName']

    # Get full room details
    full_room = get_rooms(room_ids=room_id)

    client_info = {
        'name': room_name,
        'room_id': room_id,
        'room_topic': full_room.get('topic') if full_room else None,
    }

    # Try to get last message info
    try:
        messages = read_messages(room_id, limit=1)
        if messages:
            last_msg = messages[0]
            client_info['last_message'] = {
                'text': last_msg.get('message', '')[:100],
                'timestamp': last_msg.get('timestamp'),
                'sender': last_msg.get('sender')
            }
    except Exception:
        pass  # Skip if can't get messages

    return client_info


def get_rooms(room_ids=None):
    """
    Retrieve message rooms (conversations) for the authenticated user.

    Args:
        room_ids (str, list, optional): Room ID(s) to retrieve.
            - None: Returns all rooms
            - str: Returns single room dict
            - list: Returns list of room dicts for specified IDs

    Returns:
        list or dict:
            - If room_ids is None: list of all room dictionaries
            - If room_ids is str: single room dict or None if not found
            - If room_ids is list: list of room dicts (only found rooms)

        Room dict contains:
            - id (str): Unique room identifier
            - roomName (str): Name of the conversation
            - topic (str): Topic/subject of the room
            - favorite (bool): Whether room is favorited

    Example:
        >>> # Get all rooms
        >>> rooms = get_rooms()
        >>> for room in rooms:
        ...     print(f"{room['id']}: {room['roomName']}")

        >>> # Get specific room
        >>> room = get_rooms(room_ids="room_123")
        >>> print(room['roomName'])

        >>> # Get multiple rooms
        >>> rooms = get_rooms(room_ids=["room_123", "room_456"])
    """
    # Handle single room ID (string)
    if isinstance(room_ids, str):
        query = """
        query getRoom($roomId: ID!) {
            room(id: $roomId) {
                id
                topic
                roomName
                favorite
            }
        }
        """
        result = execute_graphql({
            "query": query,
            "variables": {"roomId": room_ids}
        })

        if 'errors' in result:
            print(f"Error: {result['errors']}")
            return None

        room_data = result.get('data', {}).get('room')
        if room_data:
            return {
                'id': room_data.get('id'),
                'roomName': room_data.get('roomName'),
                'topic': room_data.get('topic'),
                'favorite': room_data.get('favorite'),
            }
        return None

    # Handle list of room IDs
    if isinstance(room_ids, list) and room_ids:
        rooms = []
        query = """
        query getRoom($roomId: ID!) {
            room(id: $roomId) {
                id
                topic
                roomName
                favorite
            }
        }
        """
        for room_id in room_ids:
            result = execute_graphql({
                "query": query,
                "variables": {"roomId": room_id}
            })

            if 'errors' not in result:
                room_data = result.get('data', {}).get('room')
                if room_data:
                    rooms.append({
                        'id': room_data.get('id'),
                        'roomName': room_data.get('roomName'),
                        'topic': room_data.get('topic'),
                        'favorite': room_data.get('favorite'),
                    })
        return rooms

    # Get all rooms (room_ids is None or empty list)
    result = execute_graphql({
        "query": QUERY_GET_ROOMS
    })

    if 'errors' in result:
        print(f"Error: {result['errors']}")
        return []

    rooms_data = result.get('data', {}).get('roomList', {}).get('edges', [])

    rooms = []
    for edge in rooms_data:
        node = edge.get('node', {})
        rooms.append({
            'id': node.get('id'),
            'roomName': node.get('roomName'),
            'topic': node.get('topic'),
            'favorite': node.get('favorite'),
        })

    return rooms


def find_rooms(client_name):
    """
    Find room IDs by client name.

    Args:
        client_name (str): Client name to search for (case-insensitive partial match)

    Returns:
        dict: Result containing matching rooms or error
            - rooms (list): List of matching rooms with 'id' and 'roomName'
            - error (str): Error message if no rooms found
    """
    rooms = get_rooms()
    matching_rooms = [
        {'id': r['id'], 'roomName': r['roomName']}
        for r in rooms
        if r.get('roomName') and client_name.lower() in r['roomName'].lower()
    ]

    if not matching_rooms:
        return {'rooms': [], 'error': f"No room found for client: {client_name}"}

    return {'rooms': matching_rooms, 'error': None}


def send_message(room_ids=None, message="", send_time=None, attachment=None, client_name=None):
    """
    Send a message to one or more rooms.

    Sends the specified message to each room in the provided list. Messages
    can be scheduled for a future time or sent immediately.

    Args:
        room_ids (list, optional): List of room IDs to send message to.
            If not provided, client_name must be specified.
        message (str): The message content to send. Can be:
            - Plain text string
            - Path to a .txt file (content will be read from file)
        send_time (datetime, int, optional): When to send the message.
            - None: Send immediately (default)
            - datetime: Send at specific time
            - int: Send in X minutes from now (rounded to top of minute)
        attachment (str, optional): Path to file to attach. Defaults to None.
            Note: Attachment support depends on Upwork API permissions.
        client_name (str, optional): Client name to search for (case-insensitive partial match).
            Used to find room_id if room_ids not provided.

    Returns:
        dict: Results of send operations
            - success (list): List of room IDs where message was sent successfully
            - failed (list): List of room IDs where message failed to send
            - scheduled (list): List of room IDs where message was scheduled
            - message_content (str): The actual message content sent
            - error (str): Error message if client lookup failed

    Example:
        >>> # Send plain text by room ID
        >>> result = send_message(
        ...     room_ids=["room_123", "room_456"],
        ...     message="Hello! Here's your weekly update.",
        ... )

        >>> # Send by client name
        >>> result = send_message(
        ...     client_name="Ian",
        ...     message="Hello! Here's your weekly update.",
        ... )

        >>> # Schedule message for 5 minutes from now
        >>> result = send_message(
        ...     client_name="Ian",
        ...     message="I'll start working on that now.",
        ...     send_time=5,  # 5 minutes from now
        ... )

        >>> # Send content from a text file
        >>> result = send_message(
        ...     room_ids=["room_123"],
        ...     message="templates/weekly_update.txt",
        ... )

        >>> # Send with attachment
        >>> result = send_message(
        ...     room_ids=["room_123"],
        ...     message="Please see attached report.",
        ...     attachment="reports/monthly_report.pdf",
        ... )
    """
    # If no room_ids provided, try to find by client_name
    if not room_ids and client_name:
        result = find_rooms(client_name)
        if result['error']:
            return {
                'success': [],
                'failed': [],
                'scheduled': [],
                'message_content': None,
                'error': result['error']
            }
        room_ids = [r['id'] for r in result['rooms']]
        room_names = [r['roomName'] for r in result['rooms']]
        print(f"Found {len(room_ids)} room(s) for '{client_name}': {room_names}")

    # Ensure room_ids is a list
    if room_ids is None:
        room_ids = []

    results = {
        'success': [],
        'failed': [],
        'scheduled': [],
        'message_content': None,
        'attachment': None
    }

    # Check if message is a file path (.txt file)
    message_content = message
    if isinstance(message, str) and message.endswith('.txt'):
        try:
            if os.path.isfile(message):
                with open(message, 'r', encoding='utf-8') as f:
                    message_content = f.read()
                print(f"Loaded message content from: {message}")
            # If file doesn't exist, treat as plain text
        except Exception as e:
            print(f"Warning: Could not read file {message}: {e}")
            # Fall back to using message as plain text

    results['message_content'] = message_content

    # Handle attachment
    if attachment:
        if os.path.isfile(attachment):
            results['attachment'] = attachment
            print(f"Attachment queued: {attachment}")
            # Note: Actual attachment upload requires additional Upwork API support
        else:
            print(f"Warning: Attachment file not found: {attachment}")

    # Handle send_time parameter
    if send_time is None:
        send_time = datetime.now()
    elif isinstance(send_time, int):
        # Integer = minutes from now, round to top of minute
        send_time = datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=send_time)

    # Check if message should be scheduled for later
    # Compare using naive datetimes (strip timezone for comparison)
    send_time_naive = send_time.replace(tzinfo=None) if send_time.tzinfo else send_time
    if send_time_naive > datetime.now() + timedelta(seconds=30):
        print(f"Message scheduled for: {send_time}")
        # Get timezone string if available
        tz_str = None
        if send_time.tzinfo:
            tz_str = str(send_time.tzinfo)
        for room_id in room_ids:
            # Save to scheduled messages file (keep full ISO with timezone)
            entry = save_scheduled_message(
                room_id=room_id,
                message=message_content,
                scheduled_time=send_time.isoformat(),
                attachment=attachment,
                client_name=client_name,
                timezone_str=tz_str
            )
            results['scheduled'].append({
                'id': entry['id'],
                'room_id': room_id,
                'message': message_content,
                'attachment': attachment,
                'scheduled_time': send_time.isoformat()
            })
            print(f"  Saved to queue: {entry['id']}")
        return results

    # Send immediately to each room
    for room_id in room_ids:
        try:
            result = execute_graphql({
                "query": MUTATION_SEND_MESSAGE,
                "variables": {
                    "roomId": room_id,
                    "message": message_content
                }
            })

            if 'errors' in result:
                results['failed'].append({
                    'room_id': room_id,
                    'error': str(result['errors'])
                })
                print(f"Failed to send message to {room_id}: {result['errors']}")
            else:
                story = result.get('data', {}).get('createRoomStoryV2', {})
                results['success'].append({
                    'room_id': room_id,
                    'message_id': story.get('id') if story else None
                })
                print(f"Message sent to {room_id}")

        except Exception as e:
            results['failed'].append({
                'room_id': room_id,
                'error': str(e)
            })
            print(f"Error sending to {room_id}: {e}")

    return results


# ==============================================================================
# MESSAGE SCHEDULING
# ==============================================================================

def save_scheduled_message(room_id, message, scheduled_time, attachment=None, client_name=None, timezone_str=None, message_file=None):
    """
    Save a message to the scheduled messages queue.

    Args:
        room_id (str): Room ID to send to
        message (str): Message content (used if message_file not provided)
        scheduled_time (str): ISO format datetime string
        attachment (str, optional): Path to attachment
        client_name (str, optional): Client name for reference
        timezone_str (str, optional): Timezone string (e.g., 'CST', 'UTC-6')
        message_file (str, optional): Path to file containing message content.
            If provided, the file will be read at send time (not at schedule time).
            This allows editing the message content before it's sent.

    Returns:
        dict: The saved scheduled message entry
    """
    messages = load_scheduled_messages()

    entry = {
        'id': f"sched_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(messages)}",
        'room_id': room_id,
        'message': message,
        'message_file': message_file,  # Store file path for reading at send time
        'scheduled_time': scheduled_time,
        'timezone': timezone_str,
        'attachment': attachment,
        'client_name': client_name,
        'created_at': datetime.now().isoformat()
    }

    messages.append(entry)

    with open(SCHEDULED_MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, indent=2)

    return entry


def load_scheduled_messages():
    """
    Load all scheduled messages from the queue file.

    Returns:
        list: List of scheduled message entries
    """
    if not os.path.exists(SCHEDULED_MESSAGES_FILE):
        return []

    try:
        with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def clear_scheduled_messages(message_ids=None):
    """
    Clear messages from the scheduled queue.

    Args:
        message_ids (str, list, optional): Message ID(s) to remove.
            - None: Clears entire queue
            - str: Clears single message by ID
            - list: Clears all specified IDs

    Returns:
        int: Number of messages that were cleared
    """
    messages = load_scheduled_messages()

    if message_ids is None:
        # Clear entire queue
        count = len(messages)
        if os.path.exists(SCHEDULED_MESSAGES_FILE):
            os.remove(SCHEDULED_MESSAGES_FILE)
    else:
        # Convert single ID to list
        if isinstance(message_ids, str):
            message_ids = [message_ids]

        # Clear only specified IDs
        original_count = len(messages)
        messages = [m for m in messages if m.get('id') not in message_ids]
        count = original_count - len(messages)

        with open(SCHEDULED_MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2)

    if count > 0:
        print(f"Cleared {count} scheduled message(s) from queue")
    return count


def get_scheduled_messages(message_ids=None):
    """
    Get pending scheduled messages.

    Args:
        message_ids (str, list, optional): Message ID(s) to retrieve.
            - None: Returns all scheduled messages
            - str: Returns single message dict or None
            - list: Returns list of matching messages

    Returns:
        list or dict: Scheduled messages with parsed times
            - If message_ids is None: list of all messages
            - If message_ids is str: single message dict or None
            - If message_ids is list: list of matching messages
    """
    messages = load_scheduled_messages()

    # Add parsed datetime to all messages
    for msg in messages:
        msg['scheduled_datetime'] = datetime.fromisoformat(msg['scheduled_time'])

    # Return all messages
    if message_ids is None:
        return messages

    # Return single message by ID
    if isinstance(message_ids, str):
        for msg in messages:
            if msg.get('id') == message_ids:
                return msg
        return None

    # Return list of messages by IDs
    if isinstance(message_ids, list):
        return [msg for msg in messages if msg.get('id') in message_ids]

    return messages


def process_scheduled_messages():
    """
    Check for and send any messages that are due.

    Returns:
        dict: Results of processing
            - sent (list): Messages that were sent
            - failed (list): Messages that failed to send
            - pending (int): Number of messages still pending
    """
    results = {
        'sent': [],
        'failed': [],
        'pending': 0
    }

    messages = load_scheduled_messages()

    # Use pytz for proper timezone handling
    local_tz = pytz.timezone('US/Central')  # Default to Central time
    now = datetime.now(local_tz)

    for msg in messages:
        scheduled_time = datetime.fromisoformat(msg['scheduled_time'])

        # Handle timezone-aware comparison
        if scheduled_time.tzinfo is None:
            # Naive datetime - assume local timezone
            scheduled_time = local_tz.localize(scheduled_time)
        else:
            # Convert to local timezone for comparison
            scheduled_time = scheduled_time.astimezone(local_tz)

        if scheduled_time <= now:
            # Time to send this message
            print(f"Sending scheduled message to {msg.get('client_name', msg['room_id'])}...")

            # Get message content - read from file if message_file is specified
            message_content = msg['message']
            message_file = msg.get('message_file')
            if message_file and os.path.isfile(message_file):
                try:
                    with open(message_file, 'r', encoding='utf-8') as f:
                        message_content = f.read()
                    print(f"  Read message content from file: {message_file}")
                except Exception as e:
                    print(f"  Warning: Could not read message file {message_file}: {e}")
                    # Fall back to stored message content

            send_result = send_message(
                room_ids=[msg['room_id']],
                message=message_content,
                attachment=msg.get('attachment')
            )

            if send_result.get('success'):
                results['sent'].append({
                    'id': msg['id'],
                    'room_id': msg['room_id'],
                    'client_name': msg.get('client_name'),
                    'message_id': send_result['success'][0].get('message_id')
                })
                clear_scheduled_messages(msg['id'])
                print(f"  Sent successfully!")
            else:
                error = send_result.get('failed', [{}])[0].get('error', 'Unknown error')
                results['failed'].append({
                    'id': msg['id'],
                    'room_id': msg['room_id'],
                    'client_name': msg.get('client_name'),
                    'error': error
                })
                print(f"  Failed: {error}")
        else:
            results['pending'] += 1

    return results


def run_scheduler(max_runtime=None, exit_on_empty=False):
    """
    Run the message scheduler in a loop.

    Messages are sent at the top of each minute when their scheduled time arrives.
    Status updates are printed at the top of each minute.

    Args:
        max_runtime (int, optional): Maximum seconds to run. None = run forever.
        exit_on_empty (bool, optional): If True, exit when queue becomes empty after
            sending all messages. If False (default), keep running even if queue is empty.

    Returns:
        dict: Final results when scheduler stops
    """
    global _scheduler_running
    import time

    _scheduler_running = True
    start_time = datetime.now()
    last_minute = -1
    total_sent = 0
    total_failed = 0

    print(f"Scheduler started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("Messages send at top of minute. Status updates every minute.")
    if exit_on_empty:
        print("Will exit when queue is empty after sending all messages.")
    print("Press Ctrl+C to stop\n")

    # Show initial status
    _print_queue_status()

    try:
        while _scheduler_running:
            now = datetime.now()
            current_minute = now.minute

            # At top of each minute (when minute changes)
            if current_minute != last_minute:
                last_minute = current_minute

                # Process any due messages
                messages = load_scheduled_messages()
                if messages:
                    results = process_scheduled_messages()
                    total_sent += len(results['sent'])
                    total_failed += len(results['failed'])

                    # Check if we should exit after sending all messages
                    if exit_on_empty and results['pending'] == 0:
                        remaining = load_scheduled_messages()
                        if not remaining:
                            print(f"\nAll messages sent. Queue is empty. Exiting.")
                            break

                # Show status update
                _print_queue_status()

                # Check exit_on_empty when queue was already empty at start
                if exit_on_empty and not messages:
                    print(f"\nQueue is empty. Nothing to send. Exiting.")
                    break

            # Check max runtime
            if max_runtime:
                elapsed = (now - start_time).total_seconds()
                if elapsed >= max_runtime:
                    print(f"\nMax runtime ({max_runtime}s) reached")
                    break

            # Sleep until next second to check for minute change
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nScheduler stopped by user")
    finally:
        _scheduler_running = False

    print(f"\nScheduler summary: {total_sent} sent, {total_failed} failed")
    return {
        'total_sent': total_sent,
        'total_failed': total_failed,
        'runtime': str(datetime.now() - start_time).split('.')[0]
    }


def _print_queue_status():
    """Print current queue status."""
    messages = load_scheduled_messages()
    now = datetime.now()

    print(f"\n{'='*50}")
    print(f"Queue Status at {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    if not messages:
        print("No messages in queue")
        return

    print(f"{len(messages)} message(s) scheduled:\n")
    for msg in messages:
        scheduled = datetime.fromisoformat(msg['scheduled_time'])
        scheduled_naive = scheduled.replace(tzinfo=None) if scheduled.tzinfo else scheduled
        time_until = scheduled_naive - now

        if time_until.total_seconds() > 0:
            mins, secs = divmod(int(time_until.total_seconds()), 60)
            hours, mins = divmod(mins, 60)
            if hours > 0:
                time_str = f"{hours}h {mins}m {secs}s"
            elif mins > 0:
                time_str = f"{mins}m {secs}s"
            else:
                time_str = f"{secs}s"
        else:
            time_str = "SENDING NOW"

        client = msg.get('client_name', msg['room_id'][:20])
        print(f"  To: {client}")
        print(f"  At: {scheduled_naive.strftime('%H:%M:%S')} (in {time_str})")
        print(f"  Msg: {msg['message'][:60]}{'...' if len(msg['message']) > 60 else ''}")
        print()


def start_scheduler_background():
    """
    Start the scheduler in a background thread.

    Returns:
        threading.Thread: The scheduler thread
    """
    import threading

    thread = threading.Thread(
        target=run_scheduler,
        daemon=True
    )
    thread.start()
    print("Scheduler started in background (processes at top of each minute)")
    return thread


def stop_scheduler():
    """Stop the running scheduler."""
    global _scheduler_running
    _scheduler_running = False
    print("Scheduler stop requested")


def read_messages(room_id, limit=10, start_date=None, end_date=None, sender=None, order="desc"):
    """
    Read messages from a conversation room.

    Retrieves message history from the specified room.
    Can filter by number of messages, date range, or sender.

    Args:
        room_id (str): Room identifier
        limit (int, optional): Maximum number of messages to retrieve. Defaults to 10.
        start_date (datetime, optional): Start of date range filter. Defaults to None.
        end_date (datetime, optional): End of date range filter. Defaults to None.
        sender (str, optional): Filter by sender name (case-insensitive partial match).
            Requires broader OAuth permissions. Defaults to None.
        order (str, optional): Sort order for messages. Defaults to "desc".
            - "desc": Newest messages first (default)
            - "asc": Oldest messages first

    Returns:
        dict: Message retrieval results
            - messages (list): List of message dictionaries
                - id (str): Message ID
                - message (str): Message content
                - timestamp (str): When message was sent
                - sender (str): Sender name (if permissions allow)
            - room_id (str): The room ID messages were retrieved from
            - room_name (str): The room name
            - topic (str): The room topic
            - total_count (int): Total messages in room
            - count (int): Number of messages retrieved
            - order (str): Sort order used
            - error (str or None): Error message if retrieval failed

    Example:
        >>> result = read_messages("room_123", limit=5)
        >>> for msg in result['messages']:
        ...     print(f"{msg['timestamp']}: {msg['message']}")

        >>> # Get oldest messages first
        >>> result = read_messages("room_123", limit=10, order="asc")

        >>> # Filter by sender (requires OAuth permissions)
        >>> result = read_messages("room_123", limit=10, sender="Ian")
    """
    # Validate order parameter
    order = order.lower() if order else "desc"
    if order not in ("asc", "desc"):
        order = "desc"

    result_data = {
        'messages': [],
        'room_id': room_id,
        'room_name': None,
        'topic': None,
        'total_count': 0,
        'count': 0,
        'order': order,
        'error': None
    }

    # Determine which query to use
    use_date_filter = start_date is not None or end_date is not None

    if sender:
        query = QUERY_GET_MESSAGES_WITH_SENDER
    elif use_date_filter:
        query = QUERY_GET_MESSAGES_WITH_DATE
    else:
        query = QUERY_GET_MESSAGES

    # If filtering by sender, fetch more messages to filter client-side
    fetch_limit = limit * 5 if sender else limit

    try:
        # Build variables based on query type
        if use_date_filter and not sender:
            variables = {
                "roomId": room_id,
                "first": fetch_limit,
                "rangeStart": start_date.strftime('%Y-%m-%dT%H:%M:%S.000Z') if start_date else None,
                "rangeEnd": end_date.strftime('%Y-%m-%dT%H:%M:%S.000Z') if end_date else None
            }
        else:
            variables = {
                "roomId": room_id,
                "first": fetch_limit
            }

        result = execute_graphql({
            "query": query,
            "variables": variables
        })

        if 'errors' in result:
            # If sender query fails due to permissions, fall back to basic query
            if sender and 'permissions' in str(result['errors']):
                result_data['error'] = "Sender filtering requires broader OAuth permissions. Re-authorize with 'Common Entities - Read-Only Access' scope."
                return result_data
            result_data['error'] = str(result['errors'])
            return result_data

        # Parse response based on query type
        if use_date_filter and not sender:
            # roomStories query returns different structure
            stories_data = result.get('data', {}).get('roomStories', {})
            result_data['total_count'] = stories_data.get('totalCount', 0)
            stories = stories_data.get('edges', [])
            # Get room info separately for date-filtered queries
            result_data['room_name'] = None
            result_data['topic'] = None
        else:
            room_data = result.get('data', {}).get('room', {})
            if not room_data:
                result_data['error'] = "Room not found"
                return result_data
            result_data['room_name'] = room_data.get('roomName')
            result_data['topic'] = room_data.get('topic')
            stories_data = room_data.get('stories', {})
            result_data['total_count'] = stories_data.get('totalCount', 0)
            stories = stories_data.get('edges', [])

        for edge in stories:
            node = edge.get('node', {})
            user = node.get('user', {}) or {}
            msg = {
                'id': node.get('id'),
                'message': node.get('message', ''),
                'timestamp': node.get('createdDateTime', ''),
                'sender': user.get('name') if user else None
            }
            result_data['messages'].append(msg)

        # Apply sender filtering if specified (client-side)
        if sender:
            sender_lower = sender.lower()
            result_data['messages'] = [
                msg for msg in result_data['messages']
                if msg.get('sender') and sender_lower in msg['sender'].lower()
            ]
            # Apply limit after sender filtering
            if len(result_data['messages']) > limit:
                result_data['messages'] = result_data['messages'][:limit]

        # Sort messages by timestamp
        if result_data['messages']:
            reverse_sort = (order == "desc")
            result_data['messages'] = sorted(
                result_data['messages'],
                key=lambda m: m.get('timestamp', ''),
                reverse=reverse_sort
            )

        result_data['count'] = len(result_data['messages'])

    except Exception as e:
        result_data['error'] = str(e)
        print(f"Error reading messages: {e}")

    return result_data


def search_messages(query, room_id=None, limit=10, case_sensitive=False, match_all=False, start_date=None, end_date=None):
    """
    Search for messages containing specific keywords or phrases.

    Searches within a single room or across all rooms for messages
    matching the query. Supports single keyword/phrase or multiple keywords.

    Args:
        query (str or list): The search query - either a single string or list of keywords
        room_id (str, optional): Room ID to search within. If None, searches all rooms.
        limit (int, optional): Maximum number of matching messages to return. Defaults to 10.
        case_sensitive (bool, optional): Whether search is case-sensitive. Defaults to False.
        match_all (bool, optional): For multiple queries - if True, message must contain ALL queries.
            If False, message must contain ANY query. Defaults to False. Ignored for single query.
        start_date (datetime, optional): Only search messages after this date. Defaults to None.
        end_date (datetime, optional): Only search messages before this date. Defaults to None.

    Returns:
        dict: Search results
            - matches (list): List of matching messages with room info
                - room_id (str): Room ID where message was found
                - room_name (str): Room name
                - message (str): Message content
                - timestamp (str): When message was sent
                - id (str): Message ID
                - matched_queries (list): Which queries matched (for multi-query search)
            - query (str or list): The search query used
            - rooms_searched (int): Number of rooms searched
            - total_matches (int): Total matches found
            - error (str or None): Error message if search failed

    Example:
        >>> # Single keyword search
        >>> result = search_messages("profit", room_id="room_123", limit=5)

        >>> # Search across all rooms
        >>> result = search_messages("trading bot", limit=10)

        >>> # Multiple keywords - ANY match
        >>> result = search_messages(["profit", "loss", "trade"], limit=10)

        >>> # Multiple keywords - ALL must match
        >>> result = search_messages(["position", "cancelled"], match_all=True)

        >>> # Search within date range
        >>> from datetime import datetime, timedelta
        >>> start = datetime.now() - timedelta(days=7)
        >>> result = search_messages("error", start_date=start, limit=10)
    """
    result_data = {
        'matches': [],
        'query': query,
        'rooms_searched': 0,
        'total_matches': 0,
        'error': None
    }

    # Normalize query to list format
    if isinstance(query, str):
        if not query or not query.strip():
            result_data['error'] = "Search query cannot be empty"
            return result_data
        queries = [query]
    elif isinstance(query, list):
        if not query or len(query) == 0:
            result_data['error'] = "Search queries list cannot be empty"
            return result_data
        queries = [q for q in query if q and q.strip()]
        if not queries:
            result_data['error'] = "No valid search queries provided"
            return result_data
    else:
        result_data['error'] = "Query must be a string or list of strings"
        return result_data

    # Normalize for case sensitivity
    if case_sensitive:
        queries_normalized = queries
    else:
        queries_normalized = [q.lower() for q in queries]

    is_multi_query = len(queries_normalized) > 1

    try:
        # Determine which rooms to search
        if room_id:
            rooms_to_search = [{'id': room_id, 'roomName': None}]
        else:
            rooms_to_search = get_rooms()
            if not rooms_to_search:
                result_data['error'] = "No rooms found to search"
                return result_data

        result_data['rooms_searched'] = len(rooms_to_search)

        # Search each room
        for room in rooms_to_search:
            current_room_id = room['id']
            room_name = room.get('roomName', 'Unknown')

            # Fetch messages from this room
            messages_result = read_messages(current_room_id, limit=50, start_date=start_date, end_date=end_date)

            if messages_result.get('error'):
                continue

            if messages_result.get('room_name'):
                room_name = messages_result['room_name']

            # Search through messages
            for msg in messages_result.get('messages', []):
                message_text = msg.get('message') or ''
                if not message_text:
                    continue
                text_to_search = message_text if case_sensitive else message_text.lower()

                # Check if message matches query criteria
                if is_multi_query:
                    if match_all:
                        matches = all(q in text_to_search for q in queries_normalized)
                    else:
                        matches = any(q in text_to_search for q in queries_normalized)
                else:
                    matches = queries_normalized[0] in text_to_search

                if matches:
                    match_data = {
                        'room_id': current_room_id,
                        'room_name': room_name,
                        'message': message_text,
                        'timestamp': msg.get('timestamp', ''),
                        'id': msg.get('id', '')
                    }
                    # Add matched_queries for multi-query searches
                    if is_multi_query:
                        match_data['matched_queries'] = [q for q in queries_normalized if q in text_to_search]

                    result_data['matches'].append(match_data)

                    if len(result_data['matches']) >= limit:
                        break

            if len(result_data['matches']) >= limit:
                break

        result_data['total_matches'] = len(result_data['matches'])

    except Exception as e:
        result_data['error'] = str(e)
        print(f"Error searching messages: {e}")

    return result_data


def export_chat_history(client_name, days=14, output_path=None):
    """
    Export chat history for a client to a text file with timestamps and senders.

    Fetches messages from the past specified number of days and saves them
    to a file with timestamps and sender names.

    Args:
        client_name (str): Client name to search for (case-insensitive partial match)
        days (int, optional): Number of days of history to export. Defaults to 14.
        output_path (str, optional): Path to save the output file.
            Defaults to client_resources/chat_history.txt

    Returns:
        dict: Export results
            - success (bool): Whether export was successful
            - file_path (str): Path to the exported file
            - message_count (int): Number of messages exported
            - date_range (tuple): (start_date, end_date) of messages
            - error (str or None): Error message if export failed

    Example:
        >>> result = export_chat_history("Joe Weissinger", days=14)
        >>> print(f"Exported {result['message_count']} messages to {result['file_path']}")
    """
    result_data = {
        'success': False,
        'file_path': None,
        'message_count': 0,
        'date_range': None,
        'error': None
    }

    # Find the room for this client
    room_result = find_rooms(client_name)
    if room_result.get('error') or not room_result.get('rooms'):
        result_data['error'] = room_result.get('error', f"No room found for client: {client_name}")
        return result_data

    room = room_result['rooms'][0]
    room_id = room['id']
    room_name = room['roomName']

    print(f"Found room for '{client_name}': {room_name}")

    # Calculate date range (use UTC to match API timestamps)
    from datetime import timezone as tz
    end_date_utc = datetime.now(tz.utc).replace(tzinfo=None)
    start_date_utc = end_date_utc - timedelta(days=days)
    # For display purposes, use local time
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Fetch messages day by day to work around null user issues
    # Days with problematic messages will fall back to no sender info
    gql = get_graphql()

    all_stories = []
    current_date = start_date

    while current_date <= end_date + timedelta(days=1):
        day_start = current_date.strftime('%Y-%m-%dT00:00:00.000Z')
        day_end = current_date.strftime('%Y-%m-%dT23:59:59.000Z')

        # Try with sender info first (fetch up to 500 per day)
        result = execute_graphql({
            "query": QUERY_GET_MESSAGES_WITH_DATE_AND_SENDER,
            "variables": {
                "roomId": room_id,
                "first": 500,
                "rangeStart": day_start,
                "rangeEnd": day_end
            }
        })

        day_stories = []
        has_sender_info = True

        if 'errors' in result:
            # Fall back to no sender info for this day
            has_sender_info = False
            result = execute_graphql({
                "query": QUERY_GET_MESSAGES_WITH_DATE,
                "variables": {
                    "roomId": room_id,
                    "first": 500,
                    "rangeStart": day_start,
                    "rangeEnd": day_end
                }
            })

        if 'errors' not in result:
            stories_data = result.get('data', {}).get('roomStories', {})
            day_stories = stories_data.get('edges', [])

        if day_stories:
            status = "with sender" if has_sender_info else "no sender"
            print(f"  {current_date.strftime('%Y-%m-%d')}: {len(day_stories)} messages ({status})")
            all_stories.extend(day_stories)

        current_date += timedelta(days=1)

    stories = all_stories
    print(f"Total: {len(stories)} messages")

    if not stories:
        result_data['error'] = "No messages found in date range"
        return result_data

    # Parse messages and filter by date
    messages = []
    for edge in stories:
        node = edge.get('node', {})
        timestamp_str = node.get('createdDateTime', '')

        # Parse timestamp and filter by date range
        if timestamp_str:
            try:
                # Handle various timestamp formats
                if 'T' in timestamp_str:
                    if timestamp_str.endswith('Z'):
                        msg_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    else:
                        msg_time = datetime.fromisoformat(timestamp_str)
                    # Convert to naive datetime for comparison
                    msg_time = msg_time.replace(tzinfo=None)
                else:
                    msg_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')

                # Skip messages outside date range (use UTC for comparison)
                if msg_time < start_date_utc or msg_time > end_date_utc:
                    continue
            except ValueError:
                # If parsing fails, include the message anyway
                msg_time = None

        user = node.get('user', {}) or {}
        sender_name = user.get('name', 'Unknown')

        msg_entry = {
            'timestamp': timestamp_str,
            'timestamp_parsed': msg_time,
            'sender': sender_name,
            'message': node.get('message', '')
        }
        messages.append(msg_entry)

    # Sort messages by timestamp (oldest first for chronological order)
    messages = sorted(
        messages,
        key=lambda m: m.get('timestamp_parsed') or datetime.min,
        reverse=False
    )

    # Set default output path
    if output_path is None:
        output_path = os.path.join(PROJECT_ROOT, 'client_resources', 'chat_history.txt')

    # Ensure directory exists
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Format and write to file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"Upwork Chat History - {room_name}\n")
            f.write(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            # Write messages
            for msg in messages:
                timestamp = msg.get('timestamp_parsed')
                if timestamp:
                    time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    time_str = msg.get('timestamp', 'Unknown time')

                sender = msg.get('sender', 'Unknown')
                message_text = msg.get('message', '')

                f.write(f"[{time_str}] {sender}:\n")
                f.write(f"{message_text}\n\n")

        result_data['success'] = True
        result_data['file_path'] = output_path
        result_data['message_count'] = len(messages)
        result_data['date_range'] = (start_date, end_date)

        print(f"Exported {len(messages)} messages to {output_path}")

    except Exception as e:
        result_data['error'] = f"Failed to write file: {e}"
        print(f"Error writing file: {e}")

    return result_data


if __name__ == "__main__":
    import sys

    if '--help' in sys.argv or '-h' in sys.argv:
        print("Upwork Manager (using python-upwork-oauth2 library)")
        print("\nUsage: python scripts/upwork_manager.py [options]")
        print("\nOptions:")
        print("  --auth       Run OAuth flow to get access token")
        print("  --rooms      Fetch and display all message rooms")
        print("  --user       Fetch and display current user info")
        print("  --scheduler  Run the message scheduler (sends at top of minute)")
        print("               Use with --wait to exit when queue is empty")
        print("  --wait       Exit scheduler when all messages are sent (use with --scheduler)")
        print("  --queue      Show pending scheduled messages")
        print("  --clear      Clear all scheduled messages from queue")
        print("  --chat-history  Export chat history for a client (past 2 weeks)")
        print("      --client=NAME  Client name to export (default: Joe Weissinger)")
        print("      --days=N       Number of days of history (default: 14)")
        print("  --help, -h   Show this help message")
        print("\nFor tests, run: python tests/test_upwork.py")

    elif '--scheduler' in sys.argv:
        # Run the scheduler
        exit_on_empty = '--wait' in sys.argv
        print("Starting message scheduler...")
        run_scheduler(exit_on_empty=exit_on_empty)

    elif '--queue' in sys.argv:
        # Show scheduled messages
        messages = load_scheduled_messages()
        if messages:
            print(f"\n{len(messages)} scheduled message(s):\n")
            now = datetime.now()
            for msg in messages:
                scheduled = datetime.fromisoformat(msg['scheduled_time'])
                scheduled_naive = scheduled.replace(tzinfo=None) if scheduled.tzinfo else scheduled
                time_until = scheduled_naive - now
                time_str = str(time_until).split('.')[0] if time_until.total_seconds() > 0 else 'OVERDUE'
                print(f"  ID: {msg['id']}")
                print(f"  To: {msg.get('client_name', msg['room_id'])}")
                print(f"  At: {scheduled_naive.strftime('%Y-%m-%d %H:%M:%S')} (in {time_str})")
                # Show message_file if present, otherwise show message content
                if msg.get('message_file'):
                    print(f"  File: {msg['message_file']}")
                else:
                    print(f"  Msg: {msg['message'][:50]}..." if len(msg['message']) > 50 else f"  Msg: {msg['message']}")
                print()
        else:
            print("\nNo scheduled messages in queue")

    elif '--clear' in sys.argv:
        # Clear scheduled messages
        count = clear_scheduled_messages()
        if count == 0:
            print("Queue was already empty")

    elif '--auth' in sys.argv:
        # Check for manual URL entry
        url_idx = None
        for i, arg in enumerate(sys.argv):
            if arg.startswith('--url='):
                url_idx = arg.split('=', 1)[1]
                break
            elif arg == '--url' and i + 1 < len(sys.argv):
                url_idx = sys.argv[i + 1]
                break

        # Check for --mode=auto or --mode=manual
        mode = None
        for arg in sys.argv:
            if arg.startswith('--mode='):
                mode = arg.split('=', 1)[1]
                break

        if url_idx:
            exchange_code_for_token(url_idx)
        elif mode == 'manual' or mode == '2':
            url, state = get_authorization_url()
            print(f"\nVisit this URL:\n{url}\n")
            print("After authorizing, copy the FULL redirect URL from your browser")
            print("(It will look like: http://localhost:8080/callback?code=XXXXX&state=YYYYY)")
            print("\nThen re-run with: --auth --url=\"<callback_url>\"")
        elif mode == 'auto' or mode == '1':
            run_oauth_flow()
        else:
            print("\nOption 1: Automatic (opens browser)")
            print("Option 2: Manual (copy URL, paste callback URL back)")
            print("\nUsage: --auth --mode=auto  OR  --auth --mode=manual")
            print("Then:  --auth --url=\"<callback_url>\"")
            try:
                choice = input("\nEnter 1 or 2: ").strip()
                if choice == '2':
                    url, state = get_authorization_url()
                    print(f"\nVisit this URL:\n{url}\n")
                    print("After authorizing, copy the FULL redirect URL from your browser")
                    print("(It will look like: http://localhost:8080/callback?code=XXXXX&state=YYYYY)")
                    print("\nThen re-run with: --auth --url=\"<callback_url>\"")
                else:
                    run_oauth_flow()
            except EOFError:
                print("\nNo interactive input available. Use --mode=auto or --mode=manual")

    elif '--rooms' in sys.argv:
        rooms = get_rooms()
        if rooms:
            print(f"\nFound {len(rooms)} rooms:\n")
            for room in rooms:
                name = room.get('roomName', 'Unknown')
                topic = room.get('topic', '')
                topic_str = f" - {topic}" if topic else ""
                print(f"  {room['id']}")
                print(f"    {name}{topic_str}\n")
        else:
            print("No rooms found or error occurred")

    elif '--user' in sys.argv:
        user = get_user_info()
        if user:
            print(f"\nUser: {user.get('name')}")
            print(f"ID: {user.get('id')}")
        else:
            print("Could not get user info")

    elif '--chat-history' in sys.argv:
        # Export chat history with usernames
        # Parse --client and --days arguments
        client_name = "Joe Weissinger"  # Default client
        days = 14  # Default days

        for arg in sys.argv:
            if arg.startswith('--client='):
                client_name = arg.split('=', 1)[1]
            elif arg.startswith('--days='):
                try:
                    days = int(arg.split('=', 1)[1])
                except ValueError:
                    print(f"Invalid days value, using default: {days}")

        print(f"\nExporting chat history for '{client_name}' (past {days} days)...")
        result = export_chat_history(client_name, days=days)

        if result['success']:
            print(f"\nExport complete!")
            print(f"  Messages: {result['message_count']}")
            print(f"  Date range: {result['date_range'][0].strftime('%Y-%m-%d')} to {result['date_range'][1].strftime('%Y-%m-%d')}")
            print(f"  File: {result['file_path']}")
        else:
            print(f"\nExport failed: {result['error']}")

    else:
        print("Upwork Manager - use --help for options")
        print("For tests, run: python tests/test_upwork.py")

# END
