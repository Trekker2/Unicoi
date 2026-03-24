"""
Stream Manager Module for Tradier Copy Bot

This module provides WebSocket-based account event streaming from Tradier.
Triggers immediate copy cycles on order events instead of relying solely on polling.

Key Classes:
    - TradierStreamManager: WebSocket client for account event streaming

Notes:
    - Uses websocket-client library
    - Auto-reconnects with exponential backoff on disconnect
    - Filters heartbeat messages, invokes callback for order events
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import json
import threading
import time
import traceback

import websocket

from integrations.tradier_ import create_streaming_session, get_streaming_url


# ==============================================================================
# STREAM MANAGER
# ==============================================================================

class TradierStreamManager:
    """
    WebSocket client for Tradier account event streaming.

    Args:
        account_id: Tradier account number to monitor
        api_key: Tradier API key
        on_order_event: Callback function invoked on order events
    """

    def __init__(self, account_id, api_key, on_order_event=None):
        self.account_id = account_id
        self.api_key = api_key
        self.on_order_event = on_order_event
        self._ws = None
        self._thread = None
        self._running = False
        self._reconnect_delay = 1

    def start(self):
        """Start the streaming connection in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._connect_loop, daemon=True)
        self._thread.start()
        print(f"Stream manager started for account {self.account_id}")

    def stop(self):
        """Stop the streaming connection."""
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        print(f"Stream manager stopped for account {self.account_id}")

    def _connect_loop(self):
        """Main connection loop with auto-reconnect."""
        while self._running:
            try:
                session_id = create_streaming_session(trd_api=self.api_key)
                if not session_id:
                    print("Failed to create streaming session, retrying...")
                    time.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(self._reconnect_delay * 2, 60)
                    continue

                ws_url = get_streaming_url()
                self._ws = websocket.WebSocketApp(
                    ws_url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=lambda ws: self._on_open(ws, session_id),
                )

                self._reconnect_delay = 1
                self._ws.run_forever()

            except Exception as e:
                print(f"Stream connection error: {e}")
                print(traceback.format_exc())

            if self._running:
                print(f"Reconnecting in {self._reconnect_delay}s...")
                time.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, 60)

    def _on_open(self, ws, session_id):
        """Handle WebSocket connection open."""
        payload = {
            "sessionid": session_id,
            "account": [self.account_id],
        }
        ws.send(json.dumps(payload))
        print(f"Stream connected for account {self.account_id}")

    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)

            # Skip heartbeats
            if data.get("type") == "heartbeat":
                return

            # Process order events
            event_type = data.get("type", "")
            if "order" in event_type.lower():
                print(f"Stream event: {event_type} - {data.get('id', '')}")
                if self.on_order_event:
                    self.on_order_event(data)

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"Stream message error: {e}")

    def _on_error(self, ws, error):
        """Handle WebSocket errors."""
        print(f"Stream error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        print(f"Stream closed: {close_status_code} - {close_msg}")

# END
