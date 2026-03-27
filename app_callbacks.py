"""
Application Callbacks Module for Tradier Copy Bot

This module contains all Dash callbacks for the application including
page routing, authentication, account management, settings, and order actions.

Key Callback Groups:
    - Page routing / navigation
    - Login / Logout
    - Account CRUD (add, delete, set master)
    - Settings updates
    - Order cancellation
    - Position closing
    - Color mode toggle
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import json
import traceback

from dash import Input, Output, State, callback_context, no_update, ALL, MATCH
from dash import html, dcc
from flask import redirect
from flask_login import login_user, logout_user, current_user

from constants import *
from helper import verify_password
from pages import *
from scripts.database_manager import connect_mongo, print_store
from scripts.style_manager import *
from services.accounts_service import do_post_account, do_delete_account, do_set_master
from services.orders_service import do_delete_order
from integrations.tradier_ import get_orders_trd
from services.settings_service import do_put_setting


# ==============================================================================
# CALLBACK REGISTRATION
# ==============================================================================

def register_app_callbacks(app):
    """Register all Dash callbacks for the application."""

    # ==================================================================
    # PAGE ROUTING
    # ==================================================================

    @app.callback(
        [Output('page-content', 'children'),
         Output({"type_": "links", "_id": ALL}, "active")],
        [Input('url', 'pathname'),
         Input({"type_": "links", "_id": ALL}, "href")],
        State('color-mode-store', 'data'),
        prevent_initial_call=False,
    )
    def route_page(pathname, all_pages, color_data):
        """Route URL to appropriate page with active link tracking."""
        color_mode = (color_data or {}).get("color_mode", default_color_mode)

        # Build active link list
        active_list = []
        for page_href in all_pages:
            if page_href == pathname:
                active_list.append(True)
            elif pathname == "/" and page_href == f"/{homepage}":
                active_list.append(True)
            else:
                active_list.append(False)

        if not current_user.is_authenticated:
            return serve_login(color_mode), active_list

        if pathname in ["/", f"/{homepage}", "/accounts"]:
            return serve_accounts(color_mode), active_list
        elif pathname == "/activity":
            return serve_activity(color_mode), active_list
        elif pathname == "/orders":
            return serve_orders(color_mode), active_list
        elif pathname == "/positions":
            return serve_positions(color_mode), active_list
        elif pathname == "/settings":
            return serve_settings(color_mode), active_list
        elif pathname == "/login":
            return serve_login(color_mode), active_list
        else:
            return serve_accounts(color_mode), active_list

    # ==================================================================
    # LOGIN / LOGOUT
    # ==================================================================

    @app.callback(
        Output('login-alert', 'children'),
        Output('url', 'pathname', allow_duplicate=True),
        Input('login-button', 'n_clicks'),
        State('login-username', 'value'),
        State('login-password', 'value'),
        prevent_initial_call=True,
    )
    def handle_login(n_clicks, username, password):
        """Handle login form submission."""
        if not n_clicks or not username or not password:
            return no_update, no_update

        try:
            db = connect_mongo()
            user_dict = db.get_collection("users").find_one({"username": username})

            if not user_dict:
                return create_error_alert("Invalid username or password"), no_update

            # Check password (plain text or hashed)
            stored_password = user_dict.get("password", "")
            stored_hash = user_dict.get("password_hash", "")

            valid = False
            if use_hashed_passwords and stored_hash:
                valid = verify_password(password, stored_hash)
            else:
                valid = (password == stored_password)

            if valid:
                user = User(
                    id=user_dict.get("username", ""),
                    username=user_dict.get("username", ""),
                )
                login_user(user)
                db2 = connect_mongo()
                print_store(db2, username, f"Info: [{username}] Logged in")
                from dash import dcc
                fixed_alert_style = {"position": "fixed", "top": "80px", "left": "50%", "transform": "translateX(-50%)", "zIndex": "9999", "width": "400px"}
                return [
                    html.Div(
                        create_success_alert(f"Welcome back, {username}! Redirecting..."),
                        style=fixed_alert_style,
                    ),
                    dcc.Interval(id="login-redirect", interval=1500, max_intervals=1),
                ], no_update
            else:
                return create_error_alert("Invalid username or password"), no_update

        except Exception as e:
            print(f"Login error: {traceback.format_exc()}")
            return create_error_alert("Login error occurred"), no_update

    @app.callback(
        Output('url', 'pathname', allow_duplicate=True),
        Input('login-redirect', 'n_intervals'),
        prevent_initial_call=True,
    )
    def redirect_after_login(n):
        """Redirect to homepage after login alert has been shown."""
        if n:
            return f"/{homepage}"
        return no_update

    @app.callback(
        Output('logout-content', 'children'),
        Input('signout-button', 'n_clicks'),
        prevent_initial_call=True,
    )
    def handle_logout(n_clicks):
        """Handle logout — show alert, then redirect after delay."""
        if n_clicks:
            username = current_user.username if current_user.is_authenticated else ""
            db = connect_mongo()
            print_store(db, username, f"Info: [{username}] Logged out")
            logout_user()
            from dash import dcc
            alert_style = {
                "position": "fixed", "top": "80px", "left": "50%",
                "transform": "translateX(-50%)", "zIndex": "9999", "width": "400px",
            }
            fixed_alert_style = {"position": "fixed", "top": "80px", "left": "50%", "transform": "translateX(-50%)", "zIndex": "9999", "width": "400px"}
            return [
                html.Div(
                    create_success_alert("Logout successful, redirecting...", duration=3000),
                    style=fixed_alert_style,
                ),
                dcc.Interval(id="logout-redirect", interval=1500, max_intervals=1),
            ]
        return no_update

    @app.callback(
        Output('url2', 'pathname'),
        Input('logout-redirect', 'n_intervals'),
        prevent_initial_call=True,
    )
    def redirect_after_logout(n):
        """Redirect to login after logout alert has been shown."""
        if n:
            return "/login"
        return no_update

    # ==================================================================
    # ACCOUNT MANAGEMENT
    # ==================================================================

    @app.callback(
        Output('accounts-alert', 'children', allow_duplicate=True),
        Output('url', 'pathname', allow_duplicate=True),
        Input('add-account-button', 'n_clicks'),
        State('add-alias', 'value'),
        State('add-account-number', 'value'),
        State('add-api-key', 'value'),
        prevent_initial_call=True,
    )
    def handle_add_account(n_clicks, alias, account_number, api_key):
        """Handle add account form submission."""
        if not n_clicks:
            return no_update, no_update

        if not alias or not account_number or not api_key:
            return create_error_alert("All fields are required"), no_update

        username = current_user.username if current_user.is_authenticated else ""
        success, message = do_post_account(alias, account_number, api_key, username=username)
        if success:
            db = connect_mongo()
            print_store(db, username, f"Info: [{username}] Added account '{alias}' ({account_number})")
            return create_success_alert(message), "/accounts"
        return create_error_alert(message), no_update

    @app.callback(
        Output('delete-account-modal', 'opened'),
        Output('delete-account-message', 'children'),
        Output('delete-account-pending', 'data'),
        Input({"type": "delete-account", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def show_delete_account_modal(n_clicks_list):
        """Open confirmation modal for account deletion."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update
        trigger = ctx.triggered[0]
        if not trigger["value"]:
            return no_update, no_update, no_update
        prop_id = json.loads(trigger["prop_id"].split(".")[0])
        account_number = prop_id["index"]
        db = connect_mongo()
        account = db.get_collection("accounts").find_one({"account_number": account_number}) or {}
        alias = account.get("alias", account_number)
        username = current_user.username if current_user.is_authenticated else ""
        msg = f"Are you sure you want to delete account '{alias}' ({account_number})? This will also remove all associated trades and history."
        return True, msg, account_number

    @app.callback(
        Output('delete-account-modal', 'opened', allow_duplicate=True),
        Output('accounts-alert', 'children', allow_duplicate=True),
        Output('url', 'pathname', allow_duplicate=True),
        Input('delete-account-confirm', 'n_clicks'),
        Input('delete-account-cancel', 'n_clicks'),
        State('delete-account-pending', 'data'),
        prevent_initial_call=True,
    )
    def handle_delete_account_confirm(confirm, cancel, account_number):
        """Handle delete account confirm/cancel."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if trigger_id == "delete-account-confirm" and account_number:
            success, message = do_delete_account(account_number)
            if success:
                db = connect_mongo()
                username = current_user.username if current_user.is_authenticated else ""
                print_store(db, username, f"Info: [{username}] Deleted account {account_number}")
                return False, create_success_alert(message), "/accounts"
            return False, create_error_alert(message), no_update
        return False, no_update, no_update

    @app.callback(
        Output('accounts-alert', 'children', allow_duplicate=True),
        Output('url', 'pathname', allow_duplicate=True),
        Input({"type": "master-radio", "index": ALL}, "checked"),
        prevent_initial_call=True,
    )
    def handle_set_master(checked_list):
        """Handle master radio toggle."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update

        trigger = ctx.triggered[0]
        if not trigger["value"]:
            return no_update, no_update

        prop_id = json.loads(trigger["prop_id"].split(".")[0])
        account_number = prop_id["index"]

        # Skip if this account is already master (prevents firing on page load)
        db = connect_mongo()
        existing = db.get_collection("accounts").find_one({"account_number": account_number})
        if existing and existing.get("is_master", False):
            return no_update, no_update

        success, message = do_set_master(account_number)
        if success:
            username = current_user.username if current_user.is_authenticated else ""
            print_store(db, username, f"Info: [{username}] Set master account to {account_number}")
            return create_success_alert(message), "/accounts"
        return create_error_alert(message), no_update

    # ==================================================================
    # SETTINGS
    # ==================================================================

    @app.callback(
        Output('automation-modal', 'opened'),
        Output('automation-modal-message', 'children'),
        Output('automation-previous-value', 'data'),
        Input('settings-use-automation', 'checked'),
        State('automation-previous-value', 'data'),
        prevent_initial_call=True,
    )
    def show_automation_modal(new_value, previous_value):
        """Open confirmation modal when automation switch changes."""
        if new_value == previous_value:
            return no_update, no_update, no_update

        if new_value:
            msg = "Are you sure you want to ENABLE automated trade execution? This will allow the system to copy trades automatically to all follower accounts."
        else:
            msg = "Are you sure you want to DISABLE automated trade execution? This will stop all automated trade copying immediately."
        return True, msg, previous_value

    @app.callback(
        Output('settings-use-automation', 'checked', allow_duplicate=True),
        Output('automation-modal', 'opened', allow_duplicate=True),
        Output('automation-previous-value', 'data', allow_duplicate=True),
        Output('settings-alert', 'children', allow_duplicate=True),
        Input('automation-confirm', 'n_clicks'),
        Input('automation-cancel', 'n_clicks'),
        State('settings-use-automation', 'checked'),
        State('automation-previous-value', 'data'),
        prevent_initial_call=True,
    )
    def handle_automation_confirm(confirm_clicks, cancel_clicks, switch_checked, previous_value):
        """Handle automation modal confirm/cancel."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == "automation-confirm":
            do_put_setting("use_automation", switch_checked)
            status = "enabled" if switch_checked else "disabled"
            db = connect_mongo()
            username = current_user.username if current_user.is_authenticated else ""
            print_store(db, username, f"Info: [{username}] Updated setting 'use_automation' to '{switch_checked}'")
            return switch_checked, False, switch_checked, create_success_alert(f"Automation {status}")
        else:
            # Cancel — revert switch to previous value
            return previous_value, False, previous_value, no_update

    @app.callback(
        Output('settings-alert', 'children', allow_duplicate=True),
        Output('poll-interval-container', 'style'),
        Input('settings-use-streaming', 'checked'),
        prevent_initial_call=True,
    )
    def handle_streaming_toggle(checked):
        """Handle streaming switch toggle — hides poll interval when streaming enabled."""
        do_put_setting("use_streaming", checked)
        status = "enabled" if checked else "disabled"
        db = connect_mongo()
        username = current_user.username if current_user.is_authenticated else ""
        print_store(db, username, f"Info: [{username}] Updated setting 'use_streaming' to '{checked}'")
        poll_style = {"display": "none"} if checked else {"display": "block"}
        return create_success_alert(f"Streaming {status}"), poll_style

    @app.callback(
        Output('settings-alert', 'children', allow_duplicate=True),
        Input('settings-poll-interval', 'value'),
        prevent_initial_call=True,
    )
    def handle_poll_interval(value):
        """Handle poll interval change."""
        if value and value > 0:
            do_put_setting("poll_interval", int(value))
            db = connect_mongo()
            username = current_user.username if current_user.is_authenticated else ""
            print_store(db, username, f"Info: [{username}] Updated setting 'poll_interval' to '{int(value)}'")
            return create_success_alert(f"Poll interval set to {value}s")
        return no_update

    @app.callback(
        Output('settings-alert', 'children', allow_duplicate=True),
        Input('settings-stale-timeout', 'value'),
        prevent_initial_call=True,
    )
    def handle_stale_timeout(value):
        """Handle stale timeout change."""
        if value and value > 0:
            do_put_setting("stale_timeout", int(value))
            db = connect_mongo()
            username = current_user.username if current_user.is_authenticated else ""
            print_store(db, username, f"Info: [{username}] Updated setting 'stale_timeout' to '{int(value)}'")
            return create_success_alert(f"Stale timeout set to {value} min")
        return no_update

    @app.callback(
        Output('settings-alert', 'children', allow_duplicate=True),
        Input({"type": "settings-multiplier", "index": ALL}, "value"),
        State({"type": "settings-multiplier", "index": ALL}, "id"),
        prevent_initial_call=True,
    )
    def handle_multiplier_change(values, ids):
        """Handle multiplier input changes."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update

        # Get current multipliers
        db = connect_mongo()
        settings = db.get_collection("settings").find_one({"type": "global"}) or {}
        multipliers = settings.get("multipliers", {})

        # Update changed multiplier
        trigger = ctx.triggered[0]
        prop_id = json.loads(trigger["prop_id"].split(".")[0])
        account_number = prop_id["index"]
        new_value = trigger["value"]

        if new_value is not None and new_value >= 0:
            multipliers[account_number] = round(float(new_value), 2)
            do_put_setting("multipliers", multipliers)
            username = current_user.username if current_user.is_authenticated else ""
            print_store(db, username, f"Info: [{username}] Updated multiplier for {account_number} to {round(float(new_value), 2)}")
            return create_success_alert(f"Multiplier for {account_number} set to {int(new_value)}")
        return no_update

    @app.callback(
        [Output('color-mode-store', 'data'),
         Output('main_page', 'style'),
         Output('page-content', 'style', allow_duplicate=True),
         Output('navbar', 'dark'),
         Output('footer-content', 'children'),
         Output('mantine-provider', 'forceColorScheme'),
         Output({"type": "settings_card", "_id": ALL}, 'style')],
        Input('settings-color-mode', 'value'),
        State({"type": "settings_card", "_id": ALL}, 'id'),
        prevent_initial_call=True,
    )
    def handle_color_mode(color_mode, card_ids):
        """Handle color mode toggle — updates all themed components in-place."""
        if not color_mode:
            return [no_update] * 7

        from app import create_footer

        do_put_setting("color_mode", color_mode)
        db = connect_mongo()
        username = current_user.username if current_user.is_authenticated else ""
        print_store(db, username, f"Info: [{username}] Updated setting 'color_mode' to '{color_mode}'")

        styles = get_settings_callback_styles(color_mode)
        main_page = {
            "background": dark_page_gradient if color_mode == "Dark" else light_page_gradient,
            "backgroundColor": dark_hex if color_mode == "Dark" else light_hex,
            "minHeight": "100vh",
        }
        page_content = {
            "minHeight": "100vh",
            "paddingTop": "70px",
        }
        navbar_dark = True  # Always dark text on brand-colored navbar
        footer = create_footer(color_mode=color_mode)
        mantine_scheme = "dark" if color_mode == "Dark" else "light"
        card_styles = [styles["card_style"] for _ in card_ids]

        return (
            {"color_mode": color_mode},
            main_page,
            page_content,
            navbar_dark,
            footer,
            mantine_scheme,
            card_styles,
        )

    # Sync data-bs-theme attribute when color mode changes
    app.clientside_callback(
        """
        function(color_mode) {
            if (color_mode) {
                var theme = color_mode === 'Dark' ? 'dark' : 'light';
                document.body.setAttribute('data-bs-theme', theme);
                var mainPage = document.getElementById('main_page');
                if (mainPage) { mainPage.setAttribute('data-bs-theme', theme); }
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('settings-color-mode', 'className'),
        Input('settings-color-mode', 'value'),
        prevent_initial_call=True,
    )

    # ==================================================================
    # DEFERRED PAGE LOADS
    # ==================================================================

    @app.callback(
        Output('orders-page-content', 'children'),
        Input('orders_initial_load', 'n_intervals'),
        State('color-mode-store', 'data'),
        prevent_initial_call=True,
    )
    def initial_load_orders(n, color_data):
        """Load real orders content after skeleton renders."""
        if not n:
            return no_update
        color_mode = (color_data or {}).get("color_mode", default_color_mode)
        return update_orders(color_mode)

    @app.callback(
        Output('positions-page-content', 'children'),
        Input('positions_initial_load', 'n_intervals'),
        State('color-mode-store', 'data'),
        prevent_initial_call=True,
    )
    def initial_load_positions(n, color_data):
        """Load real positions content after skeleton renders."""
        if not n:
            return no_update
        color_mode = (color_data or {}).get("color_mode", default_color_mode)
        return update_positions(color_mode)

    # ==================================================================
    # ORDER CANCELLATION
    # ==================================================================

    @app.callback(
        Output('cancel-order-modal', 'opened'),
        Output('cancel-order-message', 'children'),
        Output('cancel-order-pending', 'data'),
        Input({"type": "cancel-order", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def show_cancel_order_modal(n_clicks_list):
        """Open confirmation modal for order cancellation."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update
        trigger = ctx.triggered[0]
        if not trigger["value"]:
            return no_update, no_update, no_update
        prop_id = json.loads(trigger["prop_id"].split(".")[0])
        index = prop_id["index"]
        parts = index.split(":")
        account_number, order_id = parts[0], parts[1]
        return True, f"Are you sure you want to cancel order {order_id} on account {account_number}?", index

    @app.callback(
        Output('cancel-order-modal', 'opened', allow_duplicate=True),
        Output('orders-alert', 'children'),
        Output('url', 'pathname', allow_duplicate=True),
        Input('cancel-order-confirm', 'n_clicks'),
        Input('cancel-order-cancel', 'n_clicks'),
        State('cancel-order-pending', 'data'),
        prevent_initial_call=True,
    )
    def handle_cancel_order_confirm(confirm, cancel, pending):
        """Handle order cancel confirm/cancel."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if trigger_id == "cancel-order-confirm" and pending:
            parts = pending.split(":")
            account_number, order_id = parts[0], parts[1]
            success, message = do_delete_order(account_number, order_id)
            if success:
                db = connect_mongo()
                username = current_user.username if current_user.is_authenticated else ""
                print_store(db, username, f"Info: [{username}] Canceled order {order_id} on account {account_number}")
                return False, create_success_alert(message), "/orders"
            return False, create_error_alert(message), no_update
        return False, no_update, no_update

    # ==================================================================
    # FOLLOWER ORDER DETAILS MODAL
    # ==================================================================

    @app.callback(
        Output("follower-details-modal", "opened"),
        Output("follower-details-content", "children"),
        Input({"type": "master-order-id", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def show_follower_details(n_clicks_list):
        """Show follower order details when a master order ID is clicked."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update
        trigger = ctx.triggered[0]
        if not trigger["value"]:
            return no_update, no_update

        prop_id = json.loads(trigger["prop_id"].split(".")[0])
        master_order_id = int(prop_id["index"])

        # Get master order info
        db = connect_mongo()
        accounts = list(db.get_collection("accounts").find())
        master_account = None
        follower_accounts = []
        for acct in accounts:
            if acct.get("is_master"):
                master_account = acct
            else:
                follower_accounts.append(acct)

        if not master_account:
            return True, html.P("No master account configured.", style={"color": "var(--text-secondary)"})

        # Get master order details
        master_orders = get_orders_trd(
            trd_account=master_account.get("account_number"),
            trd_api=master_account.get("api_key"),
        )
        master_order = next((o for o in master_orders if o.get("id") == master_order_id), None)

        if not master_order:
            return True, html.P(f"Master order {master_order_id} not found.", style={"color": "var(--text-secondary)"})

        master_status = master_order.get("status", "")
        master_symbol = master_order.get("symbol", "")
        master_class = master_order.get("class", "equity")
        master_side = master_order.get("side", "")
        master_type = master_order.get("type", "")

        # Option symbol display
        option_symbol = master_order.get("option_symbol", "")
        legs = master_order.get("leg", [])
        symbol_display = master_symbol
        if option_symbol:
            symbol_display = f"{master_symbol} ({option_symbol})"
        elif legs:
            leg_symbols = [leg.get("option_symbol", "") for leg in legs]
            symbol_display = f"{master_symbol} ({', '.join(leg_symbols)})"

        # Master order summary
        content = [
            html.H6(f"Master Order #{master_order_id}", style={"color": purple_hex, "marginBottom": "0.5rem"}),
            html.P(f"{master_side.upper()} {master_order.get('quantity', '')} {symbol_display} ({master_type})",
                   style={"color": "var(--text-primary)", "marginBottom": "1rem"}),
        ]

        # If rejected, it never made it to followers — show explanation and return early
        if master_status in ["rejected", "REJ"]:
            content.append(
                html.Div([
                    html.P(
                        f"This order was rejected and never made it to follower accounts.",
                        style={"color": DANGER, "fontWeight": "500", "marginBottom": "0.5rem"},
                    ),
                ], style={"marginBottom": "1rem", "padding": "0.75rem",
                          "backgroundColor": "rgba(220, 53, 69, 0.1)", "borderRadius": "6px"})
            )
            return True, html.Div(content)

        # Look up follower copies from trades/history
        follower_rows = []
        for f_acct in follower_accounts:
            f_alias = f_acct.get("alias", f_acct.get("account_number", ""))
            f_number = f_acct.get("account_number", "")

            # Check trades collection for this master order
            f_trades_doc = db.get_collection("trades").find_one({"account_number": f_number})
            f_history_doc = db.get_collection("history").find_one({"account_number": master_account.get("account_number")})

            follower_order_id = None

            # Search active trades
            if f_trades_doc:
                for t in f_trades_doc.get("trades", []):
                    if t and t.get("master_order_id") == master_order_id:
                        follower_order_id = t.get("follower_order_id", t.get("order_id"))
                        break

            # Search history if not found in trades
            if not follower_order_id and f_history_doc:
                for h in f_history_doc.get("history", []):
                    if not h:
                        continue
                    if h.get("id") == master_order_id:
                        # Check follower orders by tag
                        f_orders = get_orders_trd(trd_account=f_number, trd_api=f_acct.get("api_key"))
                        tag_prefix = f"follower-{master_symbol}-{master_order_id}"
                        for fo in f_orders:
                            if str(fo.get("tag", "")).startswith(f"follower-") and str(master_order_id) in str(fo.get("tag", "")):
                                follower_order_id = fo.get("id")
                                break
                        break

            # Get follower order status
            if follower_order_id:
                f_orders = get_orders_trd(trd_account=f_number, trd_api=f_acct.get("api_key"))
                f_order = next((o for o in f_orders if o.get("id") == follower_order_id), None)
                f_status = f_order.get("status", "unknown") if f_order else "unknown"

                if f_status in filled_statuses:
                    badge_color = "green"
                elif f_status in open_statuses:
                    badge_color = "blue"
                elif f_status in bad_statuses:
                    badge_color = "red"
                else:
                    badge_color = "gray"

                follower_rows.append(
                    html.Tr([
                        html.Td(f_alias, style={"color": "var(--text-primary)", "fontWeight": "500"}),
                        html.Td(str(follower_order_id), style={"color": "var(--text-secondary)"}),
                        html.Td(dmc.Badge(f_status, color=badge_color, variant="filled", size="sm"),
                                style={"minWidth": "90px"}),
                    ])
                )
            else:
                follower_rows.append(
                    html.Tr([
                        html.Td(f_alias, style={"color": "var(--text-primary)", "fontWeight": "500"}),
                        html.Td("—", style={"color": "var(--text-secondary)"}),
                        html.Td("Not copied", style={"color": "var(--text-secondary)", "fontStyle": "italic"}),
                    ])
                )

        if follower_rows:
            follower_table = html.Table(
                children=[
                    html.Thead(html.Tr([
                        html.Th("Follower", style={"color": "var(--text-secondary)", "fontWeight": "600", "paddingBottom": "0.5rem"}),
                        html.Th("Order ID", style={"color": "var(--text-secondary)", "fontWeight": "600", "paddingBottom": "0.5rem"}),
                        html.Th("Status", style={"color": "var(--text-secondary)", "fontWeight": "600", "paddingBottom": "0.5rem"}),
                    ])),
                    html.Tbody(follower_rows),
                ],
                className="app-table",
                style={"width": "100%"},
            )
            content.append(follower_table)
        else:
            content.append(html.P("No follower accounts configured.", style={"color": "var(--text-secondary)"}))

        return True, html.Div(content)

    # ==================================================================
    # ACTIVITY LOG DELETE
    # ==================================================================

    @app.callback(
        Output({"type": "activity_tr", "row": MATCH}, "children"),
        Input({"type": "activity_delete_div", "row": MATCH}, "n_clicks"),
        [State({"type": "activity_log", "row": MATCH}, "children"),
         State({"type": "activity_datetime", "row": MATCH}, "children")],
        prevent_initial_call=True,
    )
    def handle_delete_log(n_clicks, log_text, datetime_text):
        """Delete a single log entry and remove the row."""
        if n_clicks is None:
            return no_update

        username = current_user.username if current_user.is_authenticated else master_username
        from services.activity_service import do_delete_log
        do_delete_log(username, datetime_text)
        return ""

    @app.callback(
        Output('clear-logs-modal', 'opened'),
        Input('clear-all-logs', 'n_clicks'),
        prevent_initial_call=True,
    )
    def show_clear_logs_modal(n_clicks):
        """Open confirmation modal for clearing logs."""
        if n_clicks:
            return True
        return no_update

    @app.callback(
        Output('clear-logs-modal', 'opened', allow_duplicate=True),
        Output('url', 'pathname', allow_duplicate=True),
        Input('clear-logs-confirm', 'n_clicks'),
        Input('clear-logs-cancel', 'n_clicks'),
        prevent_initial_call=True,
    )
    def handle_clear_logs_confirm(confirm, cancel):
        """Handle clear logs confirm/cancel."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if trigger_id == "clear-logs-confirm":
            username = current_user.username if current_user.is_authenticated else master_username
            db = connect_mongo()
            db.get_collection("logs").update_many(
                {},
                {"$set": {"logs": []}},
            )
            print_store(db, username, f"Info: [{username}] Cleared all activity logs")
            return False, "/activity"
        else:
            return False, no_update

    # ==========================================================================
    # ACTIVITY - EXPORT LOGS
    # ==========================================================================

    @app.callback(
        Output("download-logs", "data"),
        Input("export-logs-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def export_activity_logs(n_clicks):
        """Export all activity logs to CSV."""
        if not n_clicks:
            return no_update

        import datetime as dt
        import io

        db = connect_mongo()
        log_docs = list(db.get_collection("logs").find({}))

        rows = []
        for doc in log_docs:
            username = doc.get("username", "system")
            for log in doc.get("logs", []):
                rows.append({
                    "datetime": log.get("datetime", ""),
                    "username": username,
                    "log": log.get("log", ""),
                })

        rows.sort(key=lambda x: x.get("datetime", ""), reverse=True)

        # Build CSV
        output = io.StringIO()
        output.write("datetime,username,log\n")
        for row in rows:
            log_escaped = row["log"].replace('"', '""')
            output.write(f'"{row["datetime"]}","{row["username"]}","{log_escaped}"\n')

        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        return dcc.send_string(output.getvalue(), f"activity_logs_{timestamp}.csv")

    # ==========================================================================
    # ORDERS - EXPORT CSV
    # ==========================================================================

    @app.callback(
        Output("export-orders-csv-download", "data"),
        Input("export-orders-csv-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def export_orders_csv(n_clicks):
        """Export all orders across accounts to CSV."""
        if not n_clicks:
            return no_update

        import datetime as dt
        import io

        from services.orders_service import do_get_orders

        account_data = do_get_orders()

        rows = []
        for account, orders in account_data:
            for order in orders:
                if order.get("_error"):
                    continue
                # Convert timestamp to Eastern
                create_date = order.get("create_date", "")
                try:
                    naive = dt.datetime.fromisoformat(str(create_date).replace("Z", "+00:00"))
                    if naive.tzinfo is None:
                        naive = utc_timezone.localize(naive)
                    eastern = naive.astimezone(market_timezone)
                    create_date = eastern.strftime("%Y-%m-%d %H:%M:%S ET")
                except Exception:
                    create_date = str(create_date)[:19]
                legs = order.get("leg", [])
                rows.append({
                    "account": order.get("_account_alias", ""),
                    "id": order.get("id", ""),
                    "symbol": order.get("symbol", ""),
                    "class": order.get("class", ""),
                    "side": f"{len(legs)} legs" if legs else order.get("side", ""),
                    "quantity": order.get("quantity", ""),
                    "status": order.get("status", ""),
                    "type": order.get("type", ""),
                    "price": order.get("price", ""),
                    "created": create_date,
                    "tag": order.get("tag", ""),
                })

        output = io.StringIO()
        output.write("account,id,symbol,class,side,quantity,status,type,price,created,tag\n")
        for row in rows:
            line = ",".join(f'"{str(row[k]).replace(chr(34), chr(34)+chr(34))}"' for k in row)
            output.write(line + "\n")

        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        return dcc.send_string(output.getvalue(), f"orders_{timestamp}.csv")

    # ==========================================================================
    # CALLBACK REGISTRY
    # ==========================================================================

    registered_callbacks = {
        # Accounts page
        'handle_add_account': handle_add_account,                        # Accounts - Add account form
        'show_delete_account_modal': show_delete_account_modal,          # Accounts - Delete modal toggle
        'handle_delete_account_confirm': handle_delete_account_confirm,  # Accounts - Delete confirm
        'handle_set_master': handle_set_master,                          # Accounts - Master toggle

        # Activity page
        'handle_delete_log': handle_delete_log,                          # Activity - Delete single log
        'show_clear_logs_modal': show_clear_logs_modal,                  # Activity - Clear logs modal
        'handle_clear_logs_confirm': handle_clear_logs_confirm,          # Activity - Clear logs confirm
        'export_activity_logs': export_activity_logs,                      # Activity - Export CSV

        # Login page
        'handle_login': handle_login,                                    # Login - Form submit
        'redirect_after_login': redirect_after_login,                    # Login - Post-login redirect
        'handle_logout': handle_logout,                                  # Login - Logout button
        'redirect_after_logout': redirect_after_logout,                  # Login - Post-logout redirect

        # Orders page
        'initial_load_orders': initial_load_orders,                      # Orders - Deferred load
        'show_cancel_order_modal': show_cancel_order_modal,              # Orders - Cancel modal toggle
        'handle_cancel_order_confirm': handle_cancel_order_confirm,      # Orders - Cancel confirm
        'export_orders_csv': export_orders_csv,                          # Orders - Export CSV

        # Positions page
        'initial_load_positions': initial_load_positions,                # Positions - Deferred load

        # Routing (global)
        'route_page': route_page,                                        # Routing - Page nav / active state

        # Settings page
        'show_automation_modal': show_automation_modal,                  # Settings - Automation modal
        'handle_automation_confirm': handle_automation_confirm,          # Settings - Automation confirm
        'handle_color_mode': handle_color_mode,                          # Settings - Dark/Light toggle
        'handle_multiplier_change': handle_multiplier_change,            # Settings - Per-account multipliers
        'handle_poll_interval': handle_poll_interval,                    # Settings - Poll interval
        'handle_stale_timeout': handle_stale_timeout,                    # Settings - Stale timeout
        'handle_streaming_toggle': handle_streaming_toggle,              # Settings - Streaming on/off
    }

    return registered_callbacks

# END
