# 📈 Tradier Copy Bot - Automated Trade Copier Platform

<div align="center">

  ![Python](https://img.shields.io/badge/python-v3.13+-blue.svg)
  ![Dash](https://img.shields.io/badge/Dash-Web%20Framework-green.svg)
  ![MongoDB](https://img.shields.io/badge/MongoDB-Database-brightgreen.svg)
  ![Tradier](https://img.shields.io/badge/Tradier-API-6f42c1.svg)
  ![Heroku](https://img.shields.io/badge/Heroku-Cloud%20Deploy-purple.svg)

  *A Python-based automated trade copier that monitors a master Tradier brokerage account and replicates equity and option orders to follower accounts in real time, with per-account multipliers, multi-leg spread support, modification sync, cancellation sync, WebSocket streaming, and a full Dash web dashboard for management*

</div>

## 📋 Overview

The Tradier Copy Bot is an automated trade replication system built with Python and Dash that monitors a designated master Tradier brokerage account and instantly copies all orders — equities, options, and multi-leg spreads — to one or more follower accounts. The platform supports both polling (2-second default) and WebSocket streaming for near-instant order detection, with intelligent features like stale order filtering, modification sync, cancellation sync, and per-account quantity multipliers.

### 🏦 Supported Broker
- 📊 **Tradier** - Full REST API + WebSocket streaming integration for equities and options trading

### ☁️ Deployment Platform
- **Heroku** - Optimized for cloud deployment with web + worker dyno architecture

### ✨ Key Features

- 📡 **Polling + Streaming** - 2-second polling by default, with optional WebSocket streaming for instant order detection
- 🔄 **Order Copying** - Detects new orders on master and copies them to all follower accounts automatically
- 📊 **Multi-Leg Support** - Copies single-leg equities/options and multi-leg spreads using Tradier indexed notation
- ✖️ **Per-Account Multipliers** - Scale order quantities per follower account (e.g., 0.5x, 1x, 2x, 5x)
- 🔧 **Modification Sync** - Detects modified master orders and syncs price/stop/duration changes to followers via PUT; quantity changes trigger cancel + replace
- ❌ **Cancellation Sync** - Detects canceled master orders and automatically syncs cancellations to all followers
- ⏱️ **Stale Order Filtering** - Skips orders older than configurable timeout (default 5 min) to prevent delayed copies
- 🕐 **Market-Aware Scheduling** - Respects NYSE market hours via exchange_calendars, sleeps during market closure
- 🛑 **Automation Killswitch** - Global on/off toggle for the copy engine with confirmation modal
- 🏷️ **Order Tags** - Follower orders are tagged with `follower-{symbol}-{master_order_id}` for lineage tracking
- 🔗 **Order Lineage** - Clickable master order IDs show follower order details (alias, order ID, status) in a modal
- 🌙 **Dark/Light Mode** - Tradier purple-themed dashboard with dark/light toggle via MantineProvider
- 📋 **Activity Logging** - All operations logged with Info/Warning/Error prefixes, Master/Follower labels, and CSV export
- 🔒 **Authentication** - Flask-Login with bcrypt password hashing and session management
- 🧪 **165+ Tests** - Comprehensive coverage across unit tests, integration scenarios, and live sandbox tests

---

## 📑 Table of Contents

- [📋 Overview](#-overview)
- [🚀 Quick Start Guide](#-quick-start-guide)
- [🏗️ Architecture](#-architecture)
- [🗄️ Database Schema](#-database-schema)
- [🔌 Tradier API Integration](#-tradier-api-integration)
- [⚡ Copy Engine](#-copy-engine)
- [🖥️ Dashboard Pages](#-dashboard-pages)
- [⚙️ Settings & Configuration](#-settings--configuration)
- [🧪 Testing](#-testing)
- [☁️ Deployment](#-deployment)
- [📡 API Routes](#-api-routes)
- [📦 Dependencies](#-dependencies)
- [📚 External Resources](#-external-resources)
- [👨‍💻 Author & Contact](#-author--contact)
- [⚠️ Disclaimer](#-disclaimer)
- [📄 License](#-license)

---

## 🚀 Quick Start Guide

Get the trade copier up and running with this streamlined setup process.

<details>
<summary><strong>📋 Prerequisites</strong></summary>

<div style="padding-left: 20px;">

- Python 3.13+
- Tradier brokerage account (sandbox VA-prefix for testing, or live)
- MongoDB Atlas account (free tier works)
- Heroku account (for cloud deployment)
- GitHub account

</div>
</details>

<details>
<summary><strong>🛠️ Installation Steps</strong></summary>

<div style="padding-left: 20px;">

### 1. Clone Repository

```bash
git clone <repository-url>
cd tradier-copy-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory (see [Environment Variables](#environment-variables-table) for full list):

```env
# MongoDB Atlas connection string
MONGO_ADDRESS=mongodb+srv://user:pass@cluster.mongodb.net/

# Flask secret key for session management
FLASK_SECRET_KEY=your-secret-key-here

# Heroku configuration
HEROKU_API_TOKEN=your-heroku-api-token
HEROKU_APP_NAME=your-heroku-app-name

# Tradier Sandbox credentials (for testing)
TRD_ACCOUNT_SIM=VA00000000
TRD_API_SIM=your-sandbox-api-key
```

### 4. Setup Tradier API

1. Create a Tradier account at https://tradier.com
2. For testing, use a sandbox account (VA-prefix account numbers)
3. Access API credentials from your Tradier dashboard:
   - Navigate to "API Access"
   - Generate an API Access Token
4. Add account credentials through the Accounts page in the dashboard

### 5. Configure MongoDB Database

1. Create MongoDB Atlas account at https://www.mongodb.com/cloud/atlas
2. Create a new cluster (free M0 tier works)
3. Create database user with read/write permissions
4. Whitelist your IP address (or 0.0.0.0/0 for all IPs)
5. Get connection string and update `MONGO_ADDRESS` in `.env`
6. The application auto-creates all required collections on first startup

</div>
</details>

<details>
<summary><strong>🚀 Run Locally</strong></summary>

<div style="padding-left: 20px;">

The application consists of two separate processes:

### Dashboard (Web UI)

```bash
python app.py
```

Access at `http://localhost:8080`

### Copy Engine (Worker Process)

```bash
python main.py
```

The copy engine runs as a separate process that continuously polls (or streams) the master account and copies orders to followers. Both processes must be running for the full system to operate.

</div>
</details>

<details>
<summary><strong>🔗 Initial Configuration</strong></summary>

<div style="padding-left: 20px;">

After deployment, complete these steps to start copying trades:

1. **Access Application**
   - Local development: `http://localhost:8080`
   - Login with default credentials (auto-created on first run)

2. **Add Trading Accounts** (Accounts Page)
   - Add your master account:
     - **Alias**: Friendly name (e.g., "Joe's Main")
     - **Account Number**: Tradier account number (VA-prefix for sandbox)
     - **API Key**: Tradier API access token
   - Toggle the master switch to designate it as the master
   - Add one or more follower accounts with their own credentials

3. **Configure Multipliers** (Settings Page)
   - Set per-follower quantity multipliers (default 1x)
   - Example: 2x multiplier copies 10-share master order as 20 shares

4. **Enable Automation** (Settings Page)
   - Toggle "Enable Automation" to activate the copy engine
   - Optionally enable streaming mode for faster detection
   - Configure poll interval and stale order timeout

5. **Monitor Operations**
   - Check **Orders** page for live order status across all accounts
   - Check **Positions** page for current holdings
   - Review **Activity** page for copy engine logs with color-coded highlighting

</div>
</details>

<details>
<summary><strong>☁️ Deploy to Heroku</strong></summary>

<div style="padding-left: 20px;">

### 1. Create Heroku App

```bash
heroku create your-app-name
```

### 2. Set Environment Variables

```bash
heroku config:set MONGO_ADDRESS="mongodb+srv://user:pass@cluster.mongodb.net/"
heroku config:set FLASK_SECRET_KEY="your-secret-key"
heroku config:set HEROKU_API_TOKEN="your-heroku-token"
heroku config:set HEROKU_APP_NAME="your-app-name"
```

### 3. Deploy

```bash
git push heroku main
```

### 4. Scale Worker Dyno

```bash
heroku ps:scale web=1 worker=1
```

The `Procfile` runs the dashboard via gunicorn (web dyno) and the copy engine via `python main.py` (worker dyno).

</div>
</details>

---

## 🏗️ Architecture

The platform follows a modular architecture with clear separation between the web dashboard, copy engine worker, API integrations, service layer, and database operations.

<details>
<summary><strong>🛠️ Technology Stack</strong></summary>

<div style="padding-left: 20px;">

| Layer | Technology |
|-------|-----------|
| **Frontend** | Dash (React-based), Dash Bootstrap Components, Dash Mantine Components |
| **Backend** | Python, Flask, Flask-Login |
| **Database** | MongoDB Atlas (pymongo with connection pooling) |
| **Broker API** | Tradier (REST API + WebSocket streaming) |
| **Authentication** | Flask-Login with bcrypt password hashing |
| **Deployment** | Heroku (gunicorn web + worker dyno) / Docker |
| **Scheduling** | exchange_calendars (NYSE market hours) |
| **Streaming** | websocket-client (Tradier account event streaming) |
| **Testing** | unittest, YAML-based scenario runner, live sandbox tests |

</div>
</details>

<details>
<summary><strong>📁 Project Structure</strong></summary>

<div style="padding-left: 20px;">

```
tradier-copy-bot/
├── 🚀 app.py                          # Dash app initialization, auth, layout, footer
├── 🔄 main.py                         # Copy engine worker loop (polling + streaming)
├── 🔗 app_callbacks.py                # All Dash callbacks (routing, auth, CRUD)
├── ⚙️ constants.py                    # Configuration, enums, default settings
├── 🛠️ helper.py                       # Utilities (market hours, hashing, formatting)
├── 📋 requirements.txt                # Python dependencies
├── 📄 Procfile                        # Heroku process definitions (web + worker)
├── 🐳 Dockerfile                      # Docker container configuration
├── 🐍 runtime.txt                     # Heroku Python runtime version
├── 🔒 .env.example                    # Environment variable template
├── 🎨 assets/                         # Static assets and styling
│   ├── css/custom.css                 # Custom CSS styling
│   ├── img/                           # Images, logos, favicon
│   └── js/custom.js                   # Custom JavaScript
├── 📱 pages/                          # Dashboard pages (UI layer)
│   ├── __init__.py                    # Page module exports
│   ├── login.py                       # 🔐 Authentication page
│   ├── accounts.py                    # 💼 Manage connected Tradier accounts
│   ├── activity.py                    # 📋 System activity logs with color coding
│   ├── orders.py                      # 📝 Live orders with cancel + lineage modal
│   ├── positions.py                   # 🗂️ Live positions with close action
│   └── settings.py                    # ⚙️ Automation, streaming, multipliers, theme
├── 🔧 services/                       # Business logic / service layer
│   ├── __init__.py                    # Service module exports
│   ├── accounts_service.py            # Account CRUD, master selection, validation
│   ├── activity_service.py            # Log retrieval and cleanup
│   ├── orders_service.py              # Live order fetching, cancellation
│   ├── positions_service.py           # Live position fetching, close position
│   └── settings_service.py            # Global settings read/write
├── 🛠️ scripts/                        # Backend modules / managers
│   ├── __init__.py                    # Script module exports
│   ├── copy_manager.py               # Core copy engine (detect, reconstruct, forward)
│   ├── stream_manager.py             # WebSocket streaming client for Tradier events
│   ├── database_manager.py           # MongoDB connection pooling, logging, cleanup
│   └── style_manager.py              # Theme colors, component factories, styling
├── 🔌 integrations/                   # External API clients
│   ├── __init__.py                    # Integration module exports
│   ├── tradier_.py                    # Tradier API (orders, positions, balances, chains, streaming)
│   ├── heroku.py                      # Heroku Platform API (dyno management)
│   ├── papertrail.py                  # Papertrail / SolarWinds log search API
│   └── upwork_.py                     # Upwork messaging API (chat history export)
├── ⏰ cron/                            # Scheduled maintenance
│   ├── __init__.py                    # Cron module exports
│   └── cron_daily.py                  # Daily cleanup (logs, history, orphans, indexes)
├── 📦 client_resources/               # Client-facing documents and resources
└── 🧪 tests/                          # Comprehensive test suite (165+ tests)
    ├── __init__.py                    # Test module initialization
    ├── run_all_tests.py               # Master test runner (unit + scenarios + live)
    ├── scenario_runner.py             # YAML-based integration scenario runner
    ├── live_test_runner.py            # Live Tradier sandbox phase-based tests
    ├── test_helper.py                 # 29 tests — flatten, format_tag, hashing, market hours
    ├── test_constants.py              # 30 tests — default settings, status classifications
    ├── test_database_manager.py       # 18 tests — serialization, log storage, cleanup
    ├── test_copy_manager.py           # 38 tests — reconstruction, copy cycle, forwarding
    ├── test_services.py               # 24 tests — settings, activity, accounts services
    ├── test_cron_daily.py             # 15 tests — log/history cleanup, orphans, indexes
    ├── test_tradier.py                # 11 tests — sandbox API connectivity
    └── scenarios/                     # 13 YAML integration scenario files
        ├── 01_single_equity_order_copied_to_one_follower.yaml
        ├── 02_multi-leg_spx_credit_spread_copied_with_multiplier.yaml
        ├── 03_duplicate_order_not_forwarded_twice.yaml
        ├── 04_stale_order_not_forwarded.yaml
        ├── 05_automation_disabled_prevents_copy.yaml
        ├── 06_canceled_master_order_cancels_follower_order.yaml
        ├── 07_order_forwarded_to_3_followers_with_different_mult.yaml
        ├── 08_no_master_account_returns_failure.yaml
        ├── 09_limit_order_preserves_price_in_reconstruction.yaml
        ├── 10_expired_and_rejected_orders_not_copied.yaml
        ├── 11_master_modifies_limit_price.yaml
        ├── 12_master_modifies_quantity_cancel_replace.yaml
        └── 13_master_modifies_duration.yaml
```

</div>
</details>

<details>
<summary><strong>📊 Core Files Reference</strong></summary>

<div style="padding-left: 20px;">

| File | Purpose | Key Functions |
|------|---------|--------------|
| `app.py` | Dash application entry point | `create_dash_app()`, `setup_authentication()`, `initialize_database()`, `serve_layout()`, `create_navbar()`, `create_footer()` |
| `main.py` | Copy engine worker loop | `main()` — polls/streams master account, runs copy cycles, manages streaming |
| `app_callbacks.py` | All Dash callbacks | Page routing, login/logout, account CRUD, settings updates, order cancel, position close, color mode toggle |
| `constants.py` | Global configuration | Environment detection, database collections, timezone, auth config, navbar pages, order/side classifications, default settings |
| `helper.py` | Utility functions | `get_current_username()`, `flatten()`, `format_tag()`, `hide_text()`, `hash_password()`, `verify_password()`, `is_market_open()` |
| `scripts/copy_manager.py` | Core copy logic | `run_copy_cycle()`, `get_new_master_orders()`, `reconstruct_single_order()`, `reconstruct_multileg_order()`, `forward_order_to_follower()`, `check_master_cancellations()`, `check_master_modifications()` |
| `scripts/stream_manager.py` | WebSocket streaming | `TradierStreamManager` — background thread, auto-reconnect, exponential backoff |
| `scripts/database_manager.py` | MongoDB operations | `connect_mongo()`, `serialize_for_mongo()`, `print_store()`, `store_log_db()`, `cleanup_old_data()` |
| `scripts/style_manager.py` | UI theming | Tradier purple palette, dark/light mode colors, Mantine component style generators |
| `integrations/tradier_.py` | Tradier API client | `get_auth_trd()`, `get_orders_trd()`, `post_orders_trd()`, `modify_orders_trd()`, `delete_orders_trd()`, `create_streaming_session()` |
| `integrations/heroku.py` | Heroku Platform API | `get_dynos()`, `start()`, `stop()`, `restart()` |
| `cron/cron_daily.py` | Daily maintenance | Log cleanup (16h), history cleanup (90d), orphan removal, index verification, health check |

</div>
</details>

<details>
<summary><strong>🔧 Service Layer</strong></summary>

<div style="padding-left: 20px;">

The service layer (`services/`) abstracts database and API calls from the UI layer, providing clean interfaces for each domain:

**Accounts Service** (`accounts_service.py`):
| Function | Description |
|----------|-------------|
| `do_get_accounts()` | Get all accounts sorted master-first |
| `do_post_account(alias, account_number, api_key)` | Add account with validation (duplicate check + API credential verification via user profile) |
| `do_delete_account(account_number)` | Remove account and associated trades/history |
| `do_set_master(account_number)` | Designate master (unsets previous master, only one allowed) |

**Settings Service** (`settings_service.py`):
| Function | Description |
|----------|-------------|
| `do_get_settings()` | Get global settings merged with defaults |
| `do_put_setting(key, value)` | Update a single global setting |
| `do_get_global_settings()` | Get raw global settings document |
| `do_put_global_setting(key, value)` | Update a global setting field |

**Orders Service** (`orders_service.py`):
| Function | Description |
|----------|-------------|
| `do_get_orders()` | Get live orders from Tradier API for all accounts (returns list of (account, orders) tuples) |
| `do_delete_order(account_number, order_id)` | Cancel an order via Tradier API |

**Positions Service** (`positions_service.py`):
| Function | Description |
|----------|-------------|
| `do_get_positions()` | Get live positions from Tradier API for all accounts (returns list of (account, positions) tuples) |
| `do_close_position(account_number, symbol, quantity, side)` | Close a position by placing a market order with the inverse side |

**Activity Service** (`activity_service.py`):
| Function | Description |
|----------|-------------|
| `do_get_logs()` | Get activity logs for the master user, sorted newest-first, capped at 200 entries |
| `do_delete_log(index)` | Delete a single log entry by index |
| `do_clear_logs()` | Clear all log entries for the master user |

</div>
</details>

<details>
<summary><strong>🔗 Dash Callbacks System</strong></summary>

<div style="padding-left: 20px;">

All Dash callbacks are registered in `app_callbacks.py` via `register_app_callbacks(app)`. The callback system handles:

**Page Routing:**
- URL pathname → page content mapping
- Active link tracking for navbar highlighting
- Authentication check (redirects to login if not authenticated)

**Login / Logout:**
- Login: validates credentials (plain or bcrypt hashed), creates Flask-Login session
- Logout: destroys session, redirects to `/login`

**Account Management:**
- Add account: validates alias/number/key, calls `do_post_account()`
- Delete account: confirms via modal, calls `do_delete_account()`
- Set master: toggle switch, calls `do_set_master()` (only one master at a time)

**Order Actions:**
- Cancel order: confirms via modal, calls `do_delete_order()`
- Deferred data loading: skeleton-first pattern for Orders and Positions pages

**Position Actions:**
- Close position: confirms via modal, auto-detects inverse side, calls `do_close_position()`

**Settings Updates:**
- Each setting change calls `do_put_setting(key, value)` and logs via `print_store()`
- Automation toggle requires confirmation modal
- Color mode toggle updates MantineProvider `forceColorScheme`

**Pattern-Matching Callbacks:**
The app uses Dash `ALL` and `MATCH` pattern-matching for dynamic component IDs:
- `{"type_": "links", "_id": ALL}` — navbar active link tracking
- `{"type_": "pages", "_id": ALL}` — navbar page visibility

</div>
</details>

<details>
<summary><strong>🎨 UI Theming & Style Manager</strong></summary>

<div style="padding-left: 20px;">

The `scripts/style_manager.py` module provides centralized UI styling with Tradier purple branding.

**Brand Colors — Tradier Purple Palette:**
| Variable | Value | Usage |
|----------|-------|-------|
| `purple_hex` | `#6f42c1` | Navbar, buttons, primary accent |
| `purple_rgb` | `rgba(111, 66, 193, 1)` | Full opacity backgrounds |
| `purple_rgb8` | `rgba(111, 66, 193, 0.8)` | Hover states |
| `purple_rgb6` | `rgba(111, 66, 193, 0.6)` | Borders |
| `purple_rgb4` | `rgba(111, 66, 193, 0.4)` | Subtle highlights |
| `purple_rgb2` | `rgba(111, 66, 193, 0.2)` | Very subtle backgrounds |

**Dark Mode Palette:**
| Element | Color |
|---------|-------|
| Page background | `#2a2a2a` |
| Card background | `#1f1f1f` |
| Card border | `#333333` |
| Table container | `#1f1f1f` |
| Row even | `#252525` |
| Row odd | `#2e2e2e` |

**Light Mode Palette:**
| Element | Color |
|---------|-------|
| Page background | `#f5f5f5` |
| Card background | `#f8f9fa` |
| Card border | `#dee2e6` |
| Table container | `#ffffff` |
| Row even | `#ffffff` |
| Row odd | `#f8f9fa` |

**Mantine Theme Configuration:**
```python
mantine_theme = {
    "primaryColor": "grape",
    "colors": {
        "grape": [
            "#f3e8ff", "#e4ccff", "#c99aff", "#ae66ff",
            "#9b3dff", "#8b2cf7", "#7c1eed", "#6f42c1",
            "#5a32a3", "#4a2886",
        ],
    },
}
```

**Style Generator Functions:**
| Function | Returns |
|----------|---------|
| `get_theme_colors(color_mode)` | Dict of color values for the current mode |
| `get_input_styles(color_mode)` | Mantine input component styles |
| `get_switch_styles(color_mode)` | Mantine switch component styles |
| `get_segmented_control_styles(color_mode)` | Mantine segmented control styles |
| `get_horizontal_gradient(color_mode)` | CSS gradient string for footer |

</div>
</details>

<details>
<summary><strong>🦶 Footer Component</strong></summary>

<div style="padding-left: 20px;">

The dashboard footer (`create_footer()` in `app.py`) is a 3-column layout with brand theming:

**Column 1 — About / Copyright:**
- App title: "Copy Bot"
- Description paragraph about the trade copier
- Copyright notice with current year

**Column 2 — Resources:**
- GitHub repository link
- Heroku dashboard link
- MongoDB Atlas link
- Tradier Documentation link

**Column 3 — Contact:**
- Developer name: Tyler Potts
- Title: Freelance Developer
- Email: twpotts11@gmail.com
- Upwork profile link
- LinkedIn profile link

**Disclaimer Row:**
- Centered trading risk disclaimer in italic
- Separated by a horizontal rule

All links use `DashIconify` icons (mdi:github, mdi:cloud, mdi:database, mdi:chart-line, mdi:email, mdi:briefcase, mdi:linkedin) and are styled with the `brand-link` CSS class.

</div>
</details>

<details>
<summary><strong>🔄 Copy Engine Pipeline</strong></summary>

<div style="padding-left: 20px;">

```
┌──────────────────────────────────────────────────────────────────────┐
│                        COPY ENGINE PIPELINE                          │
│                         (main.py loop)                               │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Connect to MongoDB                                               │
│     │                                                                │
│  2. Check market hours (cloud only)                                  │
│     │  └─ If closed → sleep 30s, continue                           │
│     │                                                                │
│  3. Load global settings                                             │
│     │  └─ poll_interval, stale_timeout, use_streaming, multipliers  │
│     │                                                                │
│  4. Manage streaming (start/stop TradierStreamManager)               │
│     │                                                                │
│  5. run_copy_cycle(db, recent_log_list)                              │
│     │                                                                │
│     ├─ 5a. Get master account                                        │
│     │       └─ db.accounts.find_one({is_master: true})              │
│     │                                                                │
│     ├─ 5b. Get follower accounts                                     │
│     │       └─ db.accounts.find({is_master: {$ne: true}})           │
│     │                                                                │
│     ├─ 5c. Check automation killswitch                               │
│     │       └─ If disabled → return early                           │
│     │                                                                │
│     ├─ 5d. Detect new master orders                                  │
│     │       ├─ Poll master via get_orders_trd()                     │
│     │       ├─ Filter bad statuses (expired, canceled, rejected)    │
│     │       └─ Deduplicate vs history + trades collections          │
│     │                                                                │
│     ├─ 5e. For each new order → for each follower:                   │
│     │       ├─ Calculate multiplier (settings.multipliers[acct])    │
│     │       ├─ Reconstruct order (single or multileg)               │
│     │       ├─ Check stale timeout                                  │
│     │       ├─ Check deduplication                                  │
│     │       ├─ Post to follower via post_orders_trd()               │
│     │       └─ Store in trades with master_snapshot + copied_fields │
│     │                                                                │
│     ├─ 5f. Check master cancellations                                │
│     │       └─ Cancel matching follower orders via DELETE            │
│     │                                                                │
│     ├─ 5g. Check master modifications                                │
│     │       ├─ Compare current master state vs master_snapshot      │
│     │       ├─ Modifiable fields (price, stop, duration, type) → PUT│
│     │       └─ Quantity changed → cancel + replace                  │
│     │                                                                │
│     ├─ 5h. Auto-cancel stale open orders                             │
│     │                                                                │
│     └─ 5i. Update trade statuses (move completed to history)         │
│                                                                      │
│  6. Sleep for poll_interval seconds                                  │
│     └─ (30s if streaming is active)                                 │
│                                                                      │
│  7. Repeat (stops after 50 consecutive errors)                       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

</div>
</details>

---

## 🗄️ Database Schema

The application uses MongoDB Atlas with a database named `copy-bot-system`. All collections are auto-created on first startup.

<details>
<summary><strong>📊 Collections</strong></summary>

<div style="padding-left: 20px;">

| Collection | Purpose | Key Fields |
|------------|---------|------------|
| `accounts` | Connected Tradier brokerage accounts | `account_number`, `alias`, `api_key`, `is_master` (bool) |
| `trades` | Active copied trades awaiting completion | `account_number`, `trades[]` — each with `id`, `master_id`, `status`, `symbol`, `side`, `quantity`, `copied_fields`, `master_snapshot` |
| `history` | Completed/archived trades (90-day retention) | `account_number`, `history[]` — full order objects moved from trades on completion |
| `settings` | Global configuration document | `type: "global"`, `use_automation`, `poll_interval`, `stale_timeout`, `use_streaming`, `multipliers`, `color_mode` |
| `logs` | Activity logs (16-hour retention) | `username`, `logs[]` — each with `datetime`, `log` text |
| `users` | Dashboard login credentials | `username`, `password`, `password_hash`, `admin` (bool) |

</div>
</details>

<details>
<summary><strong>🔗 Collection Relationships</strong></summary>

<div style="padding-left: 20px;">

```
accounts
  ├── account_number (unique key)
  │    ├── trades.account_number (1:1, active orders per account)
  │    └── history.account_number (1:1, completed orders per account)
  └── is_master: true (exactly one)
       └── follower trades link via master_id → master order.id

settings
  └── type: "global" (single document with all config)

logs
  └── username (keyed by user, e.g., "joe")
       └── logs[] array with datetime + log text

users
  └── username (unique, used for Flask-Login)
```

**Trade Lifecycle:**
1. Master order detected → stored in master's `history`
2. Follower order placed → stored in follower's `trades` with `master_id` link
3. Follower order completes (filled/canceled/expired) → moved from `trades` to `history`

**Snapshot Tracking (for modification sync):**
- `master_snapshot`: Master order's state at copy time (price, stop, duration, type, quantity)
- `copied_fields`: What was actually sent to the follower broker
- On each cycle, current master state is compared to `master_snapshot` to detect modifications

</div>
</details>

<details>
<summary><strong>🗃️ Database Functions</strong></summary>

<div style="padding-left: 20px;">

| Function | Module | Description |
|----------|--------|-------------|
| `connect_mongo()` | `database_manager.py` | Get database connection from global connection pool (cached, auto-reconnect) |
| `serialize_for_mongo()` | `database_manager.py` | Recursively convert Python objects (UUID, Enum, Decimal, dataclass) to MongoDB-compatible types |
| `print_store()` | `database_manager.py` | Print a message to stdout AND store it in the `logs` collection |
| `store_log_db()` | `database_manager.py` | Store a log entry in the database with timestamp |
| `cleanup_old_data()` | `database_manager.py` | Clean up logs older than 16 hours and history older than 90 days |
| `get_mongo_pool()` | `database_manager.py` | Get or create the global MongoClient with optimized pool settings (50 max, 5 min, retry) |

**Connection Pool Configuration:**
- `maxPoolSize`: 50
- `minPoolSize`: 5
- `maxIdleTimeMS`: 300,000 (5 min)
- `serverSelectionTimeoutMS`: 10,000
- `retryWrites` / `retryReads`: True

The `MongoPoolWrapper` class prevents accidental pool closure by intercepting `client.close()` calls.

</div>
</details>

---

## 🔌 Tradier API Integration

All Tradier API interactions are centralized in `integrations/tradier_.py`, providing a clean abstraction layer over the REST and WebSocket APIs.

<details>
<summary><strong>🔑 Authentication</strong></summary>

<div style="padding-left: 20px;">

The `get_auth_trd()` function provides automatic sandbox/real API detection:

| Account Prefix | Base URL | Mode |
|----------------|----------|------|
| `VA` (e.g., `VA00000000`) | `https://sandbox.tradier.com/v1` | Sandbox (SIM) |
| All others | `https://api.tradier.com/v1` | Real (REAL) |

```python
# Authentication is automatic based on account number
auth = get_auth_trd(trd_account="VA123456", trd_api="your-key")
# auth = {
#     'account': 'VA123456',
#     'base': 'https://sandbox.tradier.com/v1',   # Auto-detected sandbox
#     'headers': {'Authorization': 'Bearer your-key', 'Accept': 'application/json'}
# }
```

**Fallback Credentials:** If `trd_account` or `trd_api` are not provided, the system falls back to environment variables:
- Real: `TRD_ACCOUNT_REAL`, `TRD_API_REAL`
- Sandbox: `TRD_ACCOUNT_SIM`, `TRD_API_SIM`

</div>
</details>

<details>
<summary><strong>📡 API Functions</strong></summary>

<div style="padding-left: 20px;">

| Function | HTTP Method | Endpoint | Description |
|----------|-------------|----------|-------------|
| `get_orders_trd()` | GET | `/accounts/{id}/orders?includeTags=true` | Get all orders for an account (with tags) |
| `get_balances_trd()` | GET | `/accounts/{id}/balances` | Get account balances |
| `get_positions_trd()` | GET | `/accounts/{id}/positions` | Get account positions |
| `post_orders_trd()` | POST | `/accounts/{id}/orders` | Place order (form-encoded, supports multi-leg) |
| `modify_orders_trd()` | PUT | `/accounts/{id}/orders/{order_id}` | Modify order (price, stop, duration, type only) |
| `delete_orders_trd()` | DELETE | `/accounts/{id}/orders/{order_id}` | Cancel an order |
| `validate_account_trd()` | GET | `/user/profile` | Validate account credentials via user profile |
| `get_expirations_trd()` | GET | `/markets/options/expirations?symbol={sym}` | Get option expiration dates for a symbol |
| `get_chain_trd()` | GET | `/markets/options/chains?symbol={sym}&expiration={exp}` | Get full option chain at specific expiration |
| `create_streaming_session()` | POST | `/accounts/events/session` | Create WebSocket streaming session |
| `get_streaming_url()` | — | — | Returns `wss://ws.tradier.com/v1/accounts/events` |

**Important:** Orders are posted as **form-encoded data** (NOT JSON) per Tradier API requirements. Multi-leg orders use indexed notation:
```
option_symbol[0]=SPY261218C00590000
side[0]=buy_to_open
quantity[0]=5
option_symbol[1]=SPY261218C00600000
side[1]=sell_to_open
quantity[1]=5
```

</div>
</details>

<details>
<summary><strong>📡 WebSocket Streaming</strong></summary>

<div style="padding-left: 20px;">

The `TradierStreamManager` class in `scripts/stream_manager.py` provides real-time account event streaming:

**Architecture:**
- Runs in a background daemon thread
- Auto-reconnects with exponential backoff (1s → 2s → 4s → ... → 60s max)
- Filters heartbeat messages, invokes callback for order events
- Uses `websocket-client` library

**Connection Flow:**
1. Create streaming session via `create_streaming_session()` → returns `sessionid`
2. Connect to WebSocket at `wss://ws.tradier.com/v1/accounts/events`
3. Send subscription payload: `{"sessionid": "...", "account": ["VA123456"]}`
4. Receive events: order creates, fills, modifications, cancellations

**Streaming vs Polling:**
| Feature | Polling | Streaming |
|---------|---------|-----------|
| Detection Speed | 2s intervals | Near-instant |
| API Calls | High (every 2s) | Low (WebSocket) |
| Reliability | Very reliable | Requires reconnect logic |
| Fallback Poll | 2s | 30s (as backup) |

When streaming is enabled, the poll interval automatically increases to 30 seconds as a fallback mechanism.

</div>
</details>

---

## ⚡ Copy Engine

The copy engine is the core of the system — it runs as a separate worker process (`main.py`) and orchestrates all trade copying, modification syncing, and cancellation syncing.

<details>
<summary><strong>🔄 How It Works</strong></summary>

<div style="padding-left: 20px;">

The copy engine operates in a continuous loop with the following steps per cycle:

1. **Connect to MongoDB** — Uses global connection pool for efficiency
2. **Check market hours** — On cloud, sleeps 30s if NYSE is closed (skipped locally for testing)
3. **Load global settings** — Reads `use_automation`, `poll_interval`, `stale_timeout`, `use_streaming`, `multipliers`
4. **Manage streaming** — Starts/stops WebSocket streaming based on settings toggle
5. **Check automation killswitch** — If `use_automation` is False, skip all copying
6. **Detect new master orders** — Poll master account, filter bad statuses, deduplicate against history + trades
7. **Reconstruct and forward** — For each new order, for each follower: apply multiplier, reconstruct order data, check stale timeout, check dedup, post to follower
8. **Check cancellations** — Detect canceled master orders, cancel matching follower orders
9. **Check modifications** — Compare master state vs snapshot, sync via PUT or cancel+replace
10. **Auto-cancel stale orders** — Cancel any open orders older than stale timeout
11. **Update trade statuses** — Poll order statuses, move completed trades to history
12. **Sleep** — Wait `poll_interval` seconds (2s default, 30s if streaming)
13. **Repeat** — Stops after 50 consecutive errors (`MAX_ERRORS`)

</div>
</details>

<details>
<summary><strong>🏗️ Order Reconstruction</strong></summary>

<div style="padding-left: 20px;">

The copy engine reconstructs orders from the master's order data into the format required by the Tradier API:

**Single-Leg Orders** (`reconstruct_single_order`):
```python
{
    "class": "equity" | "option",
    "symbol": "AAPL",
    "duration": "day",
    "side": "buy",
    "quantity": "10",           # master_qty * multiplier, floor, min 1
    "type": "market" | "limit" | "stop" | "stop_limit",
    "price": 150.00,            # included for limit orders
    "stop": 148.00,             # included for stop orders
    "option_symbol": "...",     # included for option orders
    "tag": "follower-AAPL-12345"
}
```

**Multi-Leg Orders** (`reconstruct_multileg_order`):
```python
{
    "class": "multileg",
    "symbol": "SPY",
    "type": "market",
    "duration": "day",
    "tag": "follower-SPY-12345",
    "option_symbol[0]": "SPY261218C00590000",
    "side[0]": "buy_to_open",
    "quantity[0]": "5",         # per-leg qty * multiplier
    "option_symbol[1]": "SPY261218C00600000",
    "side[1]": "sell_to_open",
    "quantity[1]": "5",
}
```

**Quantity Scaling:**
- `follower_qty = max(1, floor(master_qty * multiplier))`
- Minimum quantity is always 1 (prevents 0-quantity orders)
- Each multi-leg leg is scaled independently

</div>
</details>

<details>
<summary><strong>🔧 Modification Sync</strong></summary>

<div style="padding-left: 20px;">

The modification sync system (`check_master_modifications`) detects when a master order's fields change after copying and syncs those changes to follower orders.

**Drift Detection:**
When an order is first copied, the system stores:
- `master_snapshot`: The master order's state at copy time
- `copied_fields`: What was actually sent to the follower

On each cycle, the current master order state is compared to `master_snapshot`. Any differences trigger sync.

**Modifiable Fields (via PUT):**
| Field | Description |
|-------|-------------|
| `price` | Limit price |
| `stop` | Stop price |
| `duration` | Order duration (day, gtc, pre, post) |
| `type` | Order type (market, limit, stop, stop_limit) |

These fields can be modified in-place via `modify_orders_trd()` (PUT request).

**Quantity Changes (via Cancel + Replace):**
The Tradier API does not allow quantity modification via PUT. When a quantity change is detected:
1. Cancel the existing follower order via DELETE
2. Reconstruct a new order from the current master state (with multiplier)
3. Post the new order to the follower via POST
4. Remove old trade record, store new one with fresh snapshots

**Fallback Logic:**
If a PUT modification fails (returns "Error"), the system automatically falls back to the cancel + replace path.

</div>
</details>

<details>
<summary><strong>❌ Cancellation Sync</strong></summary>

<div style="padding-left: 20px;">

The cancellation sync system (`check_master_cancellations`) ensures that when a master order is canceled, all corresponding follower orders are also canceled.

**How it works:**
1. Fetch all current master orders via `get_orders_trd()`
2. Identify orders with `status == "canceled"`
3. For each follower, check `trades` collection for entries with matching `master_id`
4. If the follower's trade is still in an open status, cancel it via `delete_orders_trd()`
5. Log the cancellation: `"Info: Follower '{alias}': canceling order {child_id} (master {master_id} was canceled)"`

**Open Statuses Checked:**
`open`, `partially_filled`, `pending`, `OPN`, `FPR`, `ACK`, `DON`

</div>
</details>

<details>
<summary><strong>⏱️ Stale Order Filtering</strong></summary>

<div style="padding-left: 20px;">

Stale order filtering prevents the copy engine from copying old orders that may have been placed before the engine started or during a period of downtime.

**How it works:**
1. For each new order, parse the `create_date` field
2. Calculate `minutes_since = (now - create_date) / 60`
3. If `minutes_since > stale_timeout` (default 5 minutes), skip the order
4. Log: `"Warning: Follower '{alias}': skipping order {order_id}, {minutes_since:.1f} min old > {stale_timeout} min timeout"`

**Additionally**, the `check_stale_orders()` function runs on each cycle to cancel any open orders across ALL accounts (master + followers) that exceed the stale timeout.

The stale timeout is configurable via the Settings page (default: 5 minutes).

</div>
</details>

<details>
<summary><strong>🏷️ Order Tags</strong></summary>

<div style="padding-left: 20px;">

Every copied order is tagged for lineage tracking using Tradier's order tagging system:

**Tag Format:**
```
follower-{symbol}-{master_order_id}
```

**Examples:**
- `follower-AAPL-12345`
- `follower-SPY-67890`

Tags are sanitized via `format_tag()` which replaces non-alphanumeric characters with dashes and truncates to 255 characters (Tradier's limit).

Tags are included when fetching orders (`?includeTags=true`) and displayed in the Orders page for reference.

</div>
</details>

---

## 🖥️ Dashboard Pages

The web dashboard is built with Dash (React-based) and provides a responsive, Tradier purple-themed interface with dark/light mode support. The navbar shows 5 pages plus a logout button.

<details>
<summary><strong>🔐 Login Page</strong></summary>

<div style="padding-left: 20px;">

**Route:** `/login`

The authentication gateway with a centered login card styled in Tradier purple branding.

**Layout:**
```
+------------------------------------------------------------------+
|                         🔐 Login                                 |
|           (gradient background, vertically centered)             |
|                                                                  |
|                    +------------------------+                    |
|                    |      Copy Bot          |                    |
|                    |  Tradier Trade Copier  |                    |
|                    |                        |                    |
|                    |  👤 Username [_______] |                    |
|                    |  🔒 Password [_______] |                    |
|                    |                        |                    |
|                    |  [🔓 Sign In         ] |                    |
|                    |  (alert area)          |                    |
|                    +------------------------+                    |
|                                                                  |
+------------------------------------------------------------------+
```

**Features:**
- Centered card with rounded corners and shadow
- Purple-branded title and sign-in button
- Username text input with account icon
- Password input with lock icon (masked)
- Alert container for login error messages
- Gradient background adapts to dark/light mode
- Flask-Login session management with bcrypt password hashing

**Authentication Systems:**
| System | Description |
|--------|-------------|
| `flask-login` | Default — Flask session-based auth with login page |
| `dash-auth` | Alternative — HTTP Basic Auth with Dash middleware |

</div>
</details>

<details>
<summary><strong>💼 Accounts Page</strong></summary>

<div style="padding-left: 20px;">

**Route:** `/accounts` (homepage)

Manages connected Tradier brokerage accounts. Users can view all linked accounts, designate a master account, add new accounts via API key, and remove accounts with confirmation.

**Layout:**
```
+------------------------------------------------------------------+
|                        💼 Accounts                               |
|------------------------------------------------------------------|
|  [Connected Accounts Card]                                       |
|  +--------------------------------------------------------------+|
|  | Alias | Account # | API Key (masked) | Master ◉ | Delete 🗑 ||
|  |-------|-----------|------------------|----------|------------||
|  | Joe   | VA231...  | 9i7X***          |  [on]    |   [x]     ||
|  | Fllwr | VA442...  | kR4z***          |  [off]   |   [x]     ||
|  +--------------------------------------------------------------+|
|                                                                  |
|  [Add Account Card]                                              |
|  +--------------------------------------------------------------+|
|  | Alias [________]  Account # [________]  API Key [________]   ||
|  |                                      [➕ Add Account]        ||
|  +--------------------------------------------------------------+|
|                                                                  |
|  (Delete Account Confirmation Modal)                             |
+------------------------------------------------------------------+
```

**Table Columns:**
| Column | Description |
|--------|-------------|
| Alias | Friendly display name for the account |
| Account # | Tradier account number (e.g., VA231...) |
| API Key | Masked with asterisks for security (`hide_text()`) |
| Master | Toggle switch (grape-colored, only one active at a time) |
| Delete | Delete button with confirmation modal |

**Features:**
- API credentials are validated via `validate_account_trd()` before adding
- Account number ownership is verified against the Tradier user profile
- Master toggle uses Mantine Switch with grape color
- Duplicate account numbers are rejected
- Master account is always sorted first

</div>
</details>

<details>
<summary><strong>📋 Activity Page</strong></summary>

<div style="padding-left: 20px;">

**Route:** `/activity`

Displays system activity logs with color-coded keyword highlighting. Logs are fetched from the database and rendered in a scrollable table.

**Layout:**
```
+------------------------------------------------------------------+
|                       📋 Activity                                |
|------------------------------------------------------------------|
|  [Activity Log Card]                                             |
|  +--------------------------------------------------------------+|
|  |                              [🗑️ Clear All Logs]             ||
|  | Datetime          | Log Message (color-coded)        | Del   ||
|  |-------------------|----------------------------------|-------||
|  | 2026-03-20 09:01  | Order FILLED for AAPL (green)    | [x]   ||
|  | 2026-03-20 09:00  | Starting copy engine (cyan)      | [x]   ||
|  | 2026-03-20 08:59  | ERROR connecting (red)            | [x]   ||
|  +--------------------------------------------------------------+|
|  |  Scrollable up to 200 rows, max-height 600px                 ||
|  +--------------------------------------------------------------+|
|                                                                  |
|  (Clear All Confirmation Modal)                                  |
+------------------------------------------------------------------+
```

**Keyword Color Coding:**
| Color | Keywords |
|-------|----------|
| 🟢 Green | `true`, `success`, `filled`, `buy`, `buy_to_open`, `buy_to_close`, `long`, `active`, `connected`, `started`, `enabled`, `stored`, `completed` |
| 🔴 Red | `false`, `error`, `fail`, `rejected`, `sell`, `sell_to_open`, `sell_to_close`, `sell_short`, `short`, `stopped`, `disabled`, `exit`, `cancel`, `canceled`, `expired` |
| 🟠 Orange | `warning`, `warn`, `timeout`, `retry`, `slow`, `pending`, `stale`, `skipping` |
| 🔵 Cyan | `info`, `status`, `check`, `update`, `refresh`, `fetch`, `copying`, `starting`, `cleaning` |

**Special Labels:**
- `Master` — highlighted distinctly
- `Follower` — highlighted distinctly

**Features:**
- Per-row delete buttons for individual log removal
- Clear all logs with modal confirmation dialog
- Scrollable table capped at 200 most recent entries
- 16-hour automatic retention (older logs purged by daily cron)
- CSV export capability

</div>
</details>

<details>
<summary><strong>📝 Orders Page</strong></summary>

<div style="padding-left: 20px;">

**Route:** `/orders`

Displays live orders from the Tradier API across all connected accounts. Uses a skeleton-first loading pattern for instant page render before API calls complete.

**Layout:**
```
+------------------------------------------------------------------+
|                         📝 Orders                                |
|------------------------------------------------------------------|
|  [Account 1: Joe's Account (VA231...) ⭐ Master]                |
|  +--------------------------------------------------------------+|
|  | Symbol | Class  | Side | Qty | Status  | Type | Price | ... ||
|  |--------|--------|------|-----|---------|------|-------|-----||
|  | AAPL   | equity | buy  | 10  | filled  | mkt  |       | ...||
|  | SPY    | option | 2leg | 5   | pending | lmt  | 3.50  | ...||
|  |        |        |      |     |         |      |  [Cancel]   ||
|  +--------------------------------------------------------------+|
|                                                                  |
|  [Account 2: Follower Account (VA442...)]                        |
|  +--------------------------------------------------------------+|
|  | Symbol | Class  | Side | Qty | Status  | Type | Price | ... ||
|  +--------------------------------------------------------------+|
|                                                                  |
|  (Cancel Order Confirmation Modal)                               |
+------------------------------------------------------------------+
```

**Table Columns:**
| Column | Description |
|--------|-------------|
| Account | Account alias and number for the order |
| Symbol | Underlying symbol (e.g., AAPL, SPY) |
| Class | Order class: `equity`, `option`, or `multileg` |
| Side | Order side: `buy`, `sell`, `buy_to_open`, `sell_to_close`, etc. |
| Qty | Number of shares/contracts |
| Status | Color-coded badge (green=filled, blue=open, red=rejected, gray=expired) |
| Type | Order type: `market`, `limit`, `stop`, `stop_limit` |
| Price | Limit price (if applicable) |
| Cancel | Cancel button for orders in open statuses |

**Features:**
- Skeleton loading for instant page render before API calls complete
- Account column on each row identifying which account the order belongs to
- Timestamps converted to US/Eastern timezone for display
- Export CSV button to download the full orders table
- Per-account sections with master badge (⭐) indicator
- Color-coded status badges (green/blue/red/gray)
- Cancel button only shown for open orders
- Cancel with modal confirmation dialog
- Supports equity, option, and multi-leg orders
- Clickable master order IDs show follower order details in modal

</div>
</details>

<details>
<summary><strong>🗂️ Positions Page</strong></summary>

<div style="padding-left: 20px;">

**Route:** `/positions`

Displays live positions from the Tradier API across all connected accounts. Uses the same skeleton-first loading pattern as the Orders page.

**Layout:**
```
+------------------------------------------------------------------+
|                       🗂️ Positions                               |
|------------------------------------------------------------------|
|  [Account 1: Joe's Account (VA231...) ⭐ Master]                |
|  +--------------------------------------------------------------+|
|  | Symbol    | Qty  | Cost Basis | Date       | Action          ||
|  |-----------|------|------------|------------|-----------------|  |
|  | AAPL      | 100  | $15,230.00 | 2026-03-01 |                ||
|  | SPY261218 | -5   | $3,400.00  | 2026-03-10 |                ||
|  +--------------------------------------------------------------+|
|                                                                  |
|  [Account 2: Follower Account (VA442...)]                        |
|  +--------------------------------------------------------------+|
|  | Symbol | Qty | Cost Basis | Date                              ||
|  +--------------------------------------------------------------+|
|                                                                  |
+------------------------------------------------------------------+
```

**Table Columns:**
| Column | Description |
|--------|-------------|
| Symbol | Position symbol (equity ticker or option symbol) |
| Qty | Position quantity (negative = short) |
| Cost Basis | Total cost basis for the position |
| Date | Date the position was acquired |

**Features:**
- Read-only view (Close button has been removed)
- Skeleton loading for instant page render before API calls complete
- Per-account sections with master badge (⭐) indicator
- Supports equity and option position symbols

</div>
</details>

<details>
<summary><strong>⚙️ Settings Page</strong></summary>

<div style="padding-left: 20px;">

**Route:** `/settings`

Provides controls for the copy engine, per-account trade multipliers, and display preferences. All changes are persisted immediately.

**Layout:**
```
+------------------------------------------------------------------+
|                        ⚙️ Settings                               |
|------------------------------------------------------------------|
|  [Copy Engine Control Card]                                      |
|  +--------------------------------------------------------------+|
|  | 🤖 Enable Automation          [on/off]  (master killswitch) ||
|  | 📡 Use Streaming              [on/off]  (WebSocket mode)    ||
|  | Poll Interval (sec)           [___2__]  (hidden if streaming)||
|  | Stale Timeout (min)           [___5__]                       ||
|  +--------------------------------------------------------------+|
|                                                                  |
|  [Per-Account Multipliers Card]                                  |
|  +--------------------------------------------------------------+|
|  | Follower 1 (VA442...)           [__1.00__]                    ||
|  | Sue's Account (VA553...)       [__0.50__]                    ||
|  +--------------------------------------------------------------+|
|                                                                  |
|  [Display Card]                                                  |
|  +--------------------------------------------------------------+|
|  | Color Mode    [🌙 Dark | ☀️ Light]                          ||
|  +--------------------------------------------------------------+|
|                                                                  |
|  (Automation Confirmation Modal)                                 |
+------------------------------------------------------------------+
```

**Copy Engine Controls:**
| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| Enable Automation | Toggle (on/off) | Off | Master killswitch for the copy engine — requires confirmation modal |
| Use Streaming | Toggle (on/off) | Off | Switch between WebSocket streaming and polling modes |
| Poll Interval | Number input (sec) | 2 | Seconds between poll cycles (hidden when streaming is on) |
| Stale Timeout | Number input (min) | 5 | Maximum age for orders to be eligible for copying |

**Per-Account Multipliers:**
- Displays one number input per follower account
- Range: 0 to 100 (step 0.01)
- Default: 1.0x (exact copy)
- Example: Master places 10 shares, follower with 2x multiplier receives 20 shares

**Display:**
- Color Mode segmented control: Dark / Light
- Affects all pages, navbar, and footer via MantineProvider `forceColorScheme`

</div>
</details>

---

## ⚙️ Settings & Configuration

<details>
<summary><strong>📊 Global Settings</strong></summary>

<div style="padding-left: 20px;">

All settings are stored in the `settings` MongoDB collection as a single document with `type: "global"`. They are merged with defaults from `get_default_settings()` at runtime.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `use_automation` | bool | `False` | Master killswitch — if False, copy engine skips all copying |
| `poll_interval` | int | `2` | Seconds between copy engine poll cycles |
| `stale_timeout` | int | `5` | Minutes before an order is considered stale and skipped |
| `use_streaming` | bool | `False` | Enable WebSocket streaming (faster detection, lower API usage) |
| `color_mode` | str | `"Dark"` | Dashboard color mode ("Dark" or "Light") |
| `multipliers` | dict | `{}` | Per-account quantity multipliers keyed by account number |

</div>
</details>

<details>
<summary><strong>✖️ Multipliers</strong></summary>

<div style="padding-left: 20px;">

Multipliers allow each follower account to receive scaled quantities:

```python
multipliers = {
    "VA442...": 2.0,    # Follower 1 gets 2x master quantity
    "VA553...": 0.5,    # Sue gets 0.5x master quantity (rounded down, min 1)
    "VA664...": 1.0,    # Tom gets exact master quantity
}
```

**Scaling Formula:**
```
follower_qty = max(1, floor(master_qty * multiplier))
```

**Multi-Leg Scaling:**
Each leg of a multi-leg order is scaled independently using the same formula.

**Edge Cases:**
- If no multiplier is set for an account, defaults to `1.0`
- Minimum quantity is always `1` (prevents 0-quantity orders)
- `floor()` is used for rounding (conservative approach)

</div>
</details>

<details>
<summary><strong>🕐 Market Hours</strong></summary>

<div style="padding-left: 20px;">

The system uses `exchange_calendars` (XNYS calendar) for precise NYSE market schedule awareness:

**Configuration:**
```python
market_str = "US/Eastern"
market_timezone = pytz.timezone("US/Eastern")
_nyse_calendar = xcals.get_calendar("XNYS")
```

**Behavior:**
| Environment | Market Closed | Market Open |
|-------------|---------------|-------------|
| Cloud (`is_cloud`) | Sleeps 30s, skips copy cycle | Runs normally |
| Local (`is_local`) | Runs normally (for testing) | Runs normally |

The `is_market_open()` function handles timezone conversion (aware → UTC → naive) for compatibility with exchange_calendars' `is_open_on_minute()` method.

**Holidays and Early Closes:**
The XNYS calendar automatically handles NYSE holidays, half-days, and extended hours.

</div>
</details>

<details>
<summary><strong>📊 Order Status Classifications</strong></summary>

<div style="padding-left: 20px;">

The system classifies order statuses for filtering and decision-making:

| Classification | Statuses | Used For |
|----------------|----------|----------|
| **Bad Statuses** | `expired`, `canceled`, `rejected`, `error`, `EXP`, `CAN`, `REJ` | Filtered out when detecting new master orders |
| **Open Statuses** | `open`, `partially_filled`, `pending`, `OPN`, `FPR`, `ACK`, `DON` | Determines if a follower order can be canceled/modified |
| **Closed Statuses** | `filled`, `expired`, `canceled`, `rejected`, `error`, `FLL`, `FLP`, `OUT`, `EXP`, `CAN`, `REJ` | Triggers move from trades → history |
| **Filled Statuses** | `filled`, `Filled`, `FLL` | Identifies completed fills |
| **Good Statuses** | `open`, `partially_filled`, `pending`, `filled` + abbreviations | Combined open + filled statuses |

**Trading Side Classifications:**

| Classification | Sides |
|----------------|-------|
| **Long Sides** | `buy`, `buy_to_open`, `sell_to_close`, `debit` (+ case variants) |
| **Short Sides** | `sell`, `sell_short`, `buy_to_cover`, `sell_to_open`, `buy_to_close`, `credit` (+ case variants) |

The `inverse_side_dict` maps each side to its opposite for close-position logic:

| Side | Inverse |
|------|---------|
| `buy` | `sell` |
| `sell` | `buy` |
| `sell_short` | `buy_to_cover` |
| `buy_to_cover` | `sell_short` |
| `buy_to_open` | `sell_to_close` |
| `sell_to_close` | `buy_to_open` |
| `sell_to_open` | `buy_to_close` |
| `buy_to_close` | `sell_to_open` |
| `debit` | `credit` |
| `credit` | `debit` |

</div>
</details>

<details>
<summary><strong>🚨 Error Handling & Recovery</strong></summary>

<div style="padding-left: 20px;">

The system implements multiple layers of error handling and recovery:

**Copy Engine Error Management:**
| Feature | Behavior |
|---------|----------|
| Consecutive error tracking | `error_count` increments on each exception, resets to 0 on success |
| Max error shutdown | After 50 consecutive errors (`MAX_ERRORS`), the engine stops gracefully |
| Log deduplication | `recent_log_list` prevents the same message from being logged repeatedly within a minute |
| Log reset | `recent_log_list` clears every minute (when the minute value changes) |

**API Error Handling:**
| Scenario | Response |
|----------|----------|
| HTTP 200/201 | Parse JSON response normally |
| Non-200 status on GET | Log error, return empty list/dict |
| Non-200 status on POST | Log error with response detail (first 300 chars), return `"Error"` |
| Non-200 status on PUT (modify) | Log error, fall back to cancel + replace flow |
| Non-200 status on DELETE | Log error, return raw response content |

**Database Connection Recovery:**
- `connect_mongo()` uses try/except with automatic pool reset on failure
- If the cached connection fails, the global `_mongo_connection_pool` and `_mongo_database_cache` are cleared
- A fresh connection is established on the next call
- `MongoPoolWrapper` prevents accidental pool closure by intercepting `client.close()` calls

**Streaming Reconnection:**
- `TradierStreamManager` implements exponential backoff: 1s → 2s → 4s → 8s → ... → 60s (max)
- Backoff resets to 1s on successful connection
- Runs in a daemon thread (auto-terminates when main process exits)
- Heartbeat messages are filtered (not treated as errors)

**Graceful Degradation:**
| Failure | Degraded Behavior |
|---------|-------------------|
| No master account | Log message, return False (no crash) |
| No follower accounts | Log message, return True (nothing to copy) |
| Automation disabled | Log message, return True (skip silently) |
| Stale order | Log warning, skip order (don't crash) |
| Duplicate order | Log info, skip order (don't crash) |
| Forward order fails | Log error, continue to next follower |
| Modify fails | Fall back to cancel + replace |
| Stream disconnects | Auto-reconnect with backoff |

</div>
</details>

<details>
<summary><strong>📋 Logging Architecture</strong></summary>

<div style="padding-left: 20px;">

The system uses a dual-output logging pattern: every important event is printed to stdout AND stored in the MongoDB `logs` collection.

**Log Entry Format:**
```python
{
    "datetime": "2026-03-20 09:01:23",  # US/Eastern timezone
    "log": "Info: Follower 'Follower 1': order placed — id=67890, status=pending, master_order=12345"
}
```

**Log Prefixes:**
| Prefix | Color (Activity Page) | Usage |
|--------|----------------------|-------|
| `Info:` | Cyan | Normal operations: order placed, trade stored, cycle status |
| `Warning:` | Orange | Non-critical issues: stale order skipped, timeout |
| `Error:` | Red | Failures: order failed, API error, connection error |

**Log Labels:**
| Label | Usage |
|-------|-------|
| `Master:` | Events on the master account (new order detected) |
| `Follower '{alias}':` | Events on a follower account (order placed, canceled, modified) |

**Example Log Messages:**
```
Info: Master: new order detected — BUY 10 AAPL (market), id=12345, copying to 2 follower(s)
Info: Follower 'Follower 1': order placed — id=67890, status=pending, master_order=12345
Info: Follower 'Follower 1': trade stored for master order 12345
Warning: Follower 'Follower 2': skipping order 12345, 7.3 min old > 5 min timeout
Error: Follower 'Follower 1': order failed for master order 12345, result=Error
Info: Follower 'Follower 1': canceling order 67890 (master 12345 was canceled)
Info: Follower 'Follower 1': modifying order 67890 (master 12345 changed ['price'])
Info: Follower 'Follower 1': cancel+replace order 67890 (master 12345 quantity changed)
```

**Retention:**
- Logs: 16-hour retention (cleaned by `cleanup_old_data()` and `cron_daily.py`)
- History: 90-day retention
- Activity page shows most recent 200 entries

**Important:** Activity logs are the only historical record of settings changes. Every settings callback logs the change via `print_store()` for debugging and audit purposes.

</div>
</details>

---

## 🧪 Testing

The project has a comprehensive test suite with 165+ tests across three layers: unit tests, integration scenarios, and live sandbox tests.

<details>
<summary><strong>🚀 Running Tests</strong></summary>

<div style="padding-left: 20px;">

```bash
# Run unit tests + integration scenarios (safe, no API calls)
python -m tests.run_all_tests

# Also run live Tradier sandbox tests (requires sandbox credentials)
python -m tests.run_all_tests --live

# Run live tests only with specific phases
python -m tests.live_test_runner --phase 0      # Prerequisites only
python -m tests.live_test_runner --phase 1-3    # Phase range
python -m tests.live_test_runner --required     # Phases 0-4
python -m tests.live_test_runner --cleanup      # Cancel leftover test orders
```

</div>
</details>

<details>
<summary><strong>🧩 Unit Tests — 165 tests</strong></summary>

<div style="padding-left: 20px;">

| Module | Tests | Coverage |
|--------|-------|----------|
| `test_helper.py` | 29 | `flatten()`, `format_tag()`, `hide_text()`, `hash_password()`, `verify_password()`, `is_market_open()`, `get_current_username()` |
| `test_constants.py` | 30 | Default settings, status classifications (bad, open, closed, filled, good), side classifications (long, short, inverse), navbar config, environment detection |
| `test_database_manager.py` | 18 | `serialize_for_mongo()` (UUID, Enum, Decimal, nested objects), `store_log_db()`, `print_store()`, `cleanup_old_data()`, connection pool behavior |
| `test_copy_manager.py` | 38 | `reconstruct_single_order()`, `reconstruct_multileg_order()`, `run_copy_cycle()`, `forward_order_to_follower()`, `check_master_cancellations()`, `check_master_modifications()`, `check_stale_orders()`, dedup logic, multiplier scaling |
| `test_services.py` | 24 | `do_get_settings()`, `do_put_setting()`, `do_get_accounts()`, `do_post_account()`, `do_delete_account()`, `do_set_master()`, `do_get_orders()`, `do_get_positions()`, `do_get_logs()` |
| `test_cron_daily.py` | 15 | Log cleanup (16h retention), history cleanup (90d retention), orphan removal (accounts/history/logs), index verification, health check |

**Total: 154 unit tests + 11 sandbox API tests = 165 tests**

</div>
</details>

<details>
<summary><strong>📋 Integration Scenarios — 13 scenarios</strong></summary>

<div style="padding-left: 20px;">

YAML-based integration scenarios that test the copy engine logic without making real API calls. Located in `tests/scenarios/`.

| # | Scenario | Validates |
|---|----------|-----------|
| 01 | Single equity order copy | Basic detection → reconstruction → forwarding to one follower |
| 02 | Multi-leg SPX credit spread with multiplier | Indexed notation, 3x scaling, multi-leg reconstruction |
| 03 | Duplicate order not forwarded twice | History deduplication prevents double-copy |
| 04 | Stale order not forwarded | Timeout filtering (order older than stale_timeout) |
| 05 | Automation disabled prevents copy | Killswitch prevents all copies when `use_automation=False` |
| 06 | Canceled master order cancels follower | Master cancel → follower cancel via DELETE |
| 07 | Order forwarded to 3 followers with different multipliers | 1x, 2x, 5x per-account scaling |
| 08 | No master account returns failure | Graceful failure when no master is configured |
| 09 | Limit order preserves price in reconstruction | Price field included in single-leg reconstruction |
| 10 | Expired and rejected orders not copied | Bad status filtering (expired, rejected) |
| 11 | Master modifies limit price | PUT modify syncs price change to follower |
| 12 | Master modifies quantity (cancel+replace) | Quantity change triggers cancel + replace flow |
| 13 | Master modifies duration | PUT modify syncs duration change to follower |

</div>
</details>

<details>
<summary><strong>🌐 Live Sandbox Tests — 5 phases, 39 assertions</strong></summary>

<div style="padding-left: 20px;">

Phase-based tests against the real Tradier sandbox API (`VA` prefix accounts). Tests the actual order lifecycle end-to-end through the copy engine.

| Phase | Name | What It Tests | Cost |
|-------|------|--------------|------|
| 0 | **Prerequisites** | API connectivity, account access, master/follower loaded from MongoDB | $0 |
| 1 | **Read-Only API** | `get_orders_trd()`, `get_positions_trd()`, `get_balances_trd()` return valid data structures | $0 |
| 2 | **Order Placement + Copy** | Multi-symbol equities (AAPL, MSFT, NVDA), SPY options (7+ DTE), SPY/QQQ 0 DTE options, 2-leg spreads, 4-leg iron condor → copy engine forwards to follower | ~$0 |
| 3 | **Order Modification** | Modify master limit price/duration, run `run_copy_cycle()`, verify follower orders synced via `check_master_modifications()` | ~$0 |
| 4 | **Order Cancellation** | Cancel master orders, run `run_copy_cycle()`, verify follower orders canceled via `check_master_cancellations()` | ~$0 |

**Key Details:**
- All phases run through `run_copy_cycle()` (the actual copy engine), respecting the automation toggle
- Accounts are loaded from MongoDB to stay aligned with the dashboard
- Use `--force-automation` to temporarily enable automation for test runs
- Cleanup phase cancels any leftover test orders tagged with `live-test` prefix
- All tests use sandbox accounts — no real money at risk

</div>
</details>

<details>
<summary><strong>📊 Test Summary</strong></summary>

<div style="padding-left: 20px;">

| Layer | Count | Requires API | Description |
|-------|-------|-------------|-------------|
| Unit Tests | 154 | No | Pure logic tests with mocked dependencies |
| Sandbox API Tests | 11 | Yes (sandbox) | Tradier sandbox connectivity and data validation |
| Integration Scenarios | 13 | No | YAML-driven end-to-end copy engine scenarios |
| Live Sandbox Tests | 39 assertions | Yes (sandbox) | Full order lifecycle through real copy engine |
| **Total** | **217+ tests** | — | — |

</div>
</details>

---

## ☁️ Deployment

<details>
<summary><strong>🚀 Heroku Setup</strong></summary>

<div style="padding-left: 20px;">

The application is designed for Heroku deployment with two process types:

**Procfile:**
```
web: gunicorn app:server --bind 0.0.0.0:$PORT --workers 2 --timeout 120
worker: python main.py
```

| Process | Dyno Type | Purpose |
|---------|-----------|---------|
| `web` | Web dyno | Serves the Dash dashboard via gunicorn |
| `worker` | Worker dyno | Runs the copy engine loop (`main.py`) |

**Both dynos must be running** for the full system to operate. The web dyno serves the dashboard; the worker dyno runs the copy engine.

**Recommended Dyno Configuration:**
```bash
heroku ps:scale web=1 worker=1
```

**Heroku Platform API Integration:**
The `integrations/heroku.py` module provides dyno management functions:
| Function | Description |
|----------|-------------|
| `get_dynos()` | List all running dynos |
| `start()` | Start a detached worker dyno |
| `stop()` | Stop a running dyno |
| `restart()` | Restart a dyno |

</div>
</details>

<details>
<summary><strong>🐳 Docker</strong></summary>

<div style="padding-left: 20px;">

**Dockerfile:**
```dockerfile
FROM python:3.12.7-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["gunicorn", "app:server", "--bind", "0.0.0.0:8080"]
```

**Build and Run:**
```bash
# Build
docker build -t tradier-copy-bot .

# Run dashboard
docker run -p 8080:8080 --env-file .env tradier-copy-bot

# Run copy engine (separate container)
docker run --env-file .env tradier-copy-bot python main.py
```

**Note:** The Docker image runs the dashboard by default. To run the copy engine, override the CMD as shown above.

</div>
</details>

<details>
<summary><strong>🔐 Environment Variables</strong></summary>

<div style="padding-left: 20px;">

<a id="environment-variables-table"></a>

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGO_ADDRESS` | Yes | MongoDB Atlas connection string |
| `FLASK_SECRET_KEY` | Yes | Flask session secret key (auto-generated locally if missing) |
| `HEROKU_API_TOKEN` | No | Heroku Platform API token (for dyno management) |
| `HEROKU_APP_NAME` | No | Heroku app name (for dyno management) |
| `TRD_ACCOUNT_SIM` | No | Tradier sandbox account number (fallback for testing) |
| `TRD_API_SIM` | No | Tradier sandbox API key (fallback for testing) |
| `TRD_ACCOUNT_REAL` | No | Tradier real account number (fallback) |
| `TRD_API_REAL` | No | Tradier real API key (fallback) |
| `PT_API_TOKEN` | No | Papertrail / SolarWinds Observability token |
| `UPWORK_API` | No | Upwork API key |
| `UPWORK_SECRET` | No | Upwork API secret |
| `UPWORK_CALLBACK` | No | Upwork OAuth callback URL |
| `UPWORK_ACCESS_TOKEN` | No | Upwork OAuth access token |
| `UPWORK_REFRESH_TOKEN` | No | Upwork OAuth refresh token |

**Notes:**
- `FLASK_SECRET_KEY` is auto-generated and saved to `.env` on first local run if not present
- Tradier credentials are primarily managed through the Accounts page (stored in MongoDB), not environment variables
- Environment variable fallbacks (`TRD_ACCOUNT_SIM`, etc.) are used when no account/API key is passed to API functions

</div>
</details>

<details>
<summary><strong>⏰ Scheduled Maintenance (Cron)</strong></summary>

<div style="padding-left: 20px;">

The `cron/cron_daily.py` module runs once daily (recommended: 05:00 UTC / 1:00 AM ET via Heroku Scheduler):

| Task | Description |
|------|-------------|
| Clean old logs | Remove log entries older than 16 hours |
| Clean old history | Remove trade history older than 90 days |
| Clean orphaned trades | Remove trades for accounts that no longer exist |
| Clean orphaned history | Remove history for accounts that no longer exist |
| Clean orphaned logs | Remove logs for users that no longer exist |
| Verify indexes | Ensure required database indexes exist |
| Health check | Export collection counts as backup/verification |
| Restart dynos | Restart Heroku dynos (cloud only) |

**Usage:**
```bash
python -m cron.cron_daily
```

**Heroku Scheduler:**
```
Daily at 05:00 UTC: python -m cron.cron_daily
```

</div>
</details>

---

## 📡 API Routes

<details>
<summary><strong>🌐 Health & Dashboard Endpoints</strong></summary>

<div style="padding-left: 20px;">

The application is served via Dash (Flask under the hood) and does not expose a standalone REST API. All data flows through Dash callbacks.

**Dashboard Routes:**

| Route | Page | Authentication |
|-------|------|---------------|
| `/login` | Login page | Public |
| `/` or `/accounts` | Accounts management | Required |
| `/activity` | Activity logs | Required |
| `/orders` | Live orders | Required |
| `/positions` | Live positions | Required |
| `/settings` | System settings | Required |

**Internal Dash Callbacks:**
All CRUD operations (add/delete account, update settings, cancel order, close position) are handled via Dash callbacks in `app_callbacks.py`, not via REST endpoints.

**Request Flow:**
```
Browser → Dash Frontend (React) → Dash Callback → Service Layer → Tradier API / MongoDB
                                                                          ↓
Browser ← Dash Frontend (React) ← Callback Return ← Service Response ←──┘
```

</div>
</details>

---

## 📦 Dependencies

<details>
<summary><strong>📋 Python Packages</strong></summary>

<div style="padding-left: 20px;">

All dependencies are specified in `requirements.txt`:

**Authentication & Security:**
| Package | Version | Purpose |
|---------|---------|---------|
| `bcrypt` | Latest | Password hashing (bcrypt algorithm with salt) |
| `dash-auth` | >= 2.0.0 | HTTP Basic Auth middleware for Dash |

**Web Framework & Server:**
| Package | Version | Purpose |
|---------|---------|---------|
| `dash` | >= 2.16.0, < 3.0.0 | Main web framework (React-based, Plotly ecosystem) |
| `dash_bootstrap_components` | >= 1.5.0, < 2.0.0 | Bootstrap-styled Dash components (cards, modals, navbars) |
| `dash_iconify` | Latest | Icon library for Dash (mdi icons) |
| `dash_mantine_components` | >= 0.12.0, < 1.0.0 | Mantine-styled Dash components (switches, badges, segmented controls) |
| `flask` | >= 3.0.0, < 4.0.0 | WSGI web framework (Dash backend) |
| `flask_login` | Latest | User session management |
| `gunicorn` | Latest | Production WSGI server for Heroku deployment |

**Database:**
| Package | Version | Purpose |
|---------|---------|---------|
| `pymongo` | >= 4.3 | MongoDB Python driver with connection pooling |

**Data Processing & Analysis:**
| Package | Version | Purpose |
|---------|---------|---------|
| `exchange_calendars` | >= 4.0.0 | NYSE market schedule (holidays, hours, early closes) |
| `pytz` | Latest | Timezone handling (US/Eastern, UTC) |

**API & HTTP:**
| Package | Version | Purpose |
|---------|---------|---------|
| `python-dotenv` | Latest | Load environment variables from `.env` file |
| `requests` | Latest | HTTP client for Tradier REST API |

**Streaming:**
| Package | Version | Purpose |
|---------|---------|---------|
| `websocket-client` | >= 1.6.0 | WebSocket client for Tradier account event streaming |

**Testing:**
| Package | Version | Purpose |
|---------|---------|---------|
| `PyYAML` | >= 6.0 | YAML parsing for integration scenario files |

</div>
</details>

---

## 📚 External Resources

<details>
<summary><strong>📖 Documentation Links</strong></summary>

<div style="padding-left: 20px;">

**Tradier:**
- [Tradier API Documentation](https://documentation.tradier.com) — Full REST API reference
- [Tradier Streaming API](https://documentation.tradier.com/brokerage-api/streaming/get-streaming-events) — WebSocket account event streaming
- [Tradier Order Placement](https://documentation.tradier.com/brokerage-api/trading/place-equity-order) — Order format and parameters
- [Tradier Multi-Leg Orders](https://documentation.tradier.com/brokerage-api/trading/place-multileg-order) — Indexed notation for spreads
- [Tradier Sandbox](https://documentation.tradier.com/brokerage-api/overview/endpoints) — Sandbox vs production endpoints

**Dash / Plotly:**
- [Dash Documentation](https://dash.plotly.com/) — Dash web framework
- [Dash Bootstrap Components](https://dash-bootstrap-components.opensource.faculty.ai/) — Bootstrap-styled Dash components
- [Dash Mantine Components](https://www.dash-mantine-components.com/) — Mantine-styled Dash components

**MongoDB:**
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) — Cloud database platform
- [PyMongo Documentation](https://pymongo.readthedocs.io/) — Python MongoDB driver
- [MongoDB Connection Pooling](https://pymongo.readthedocs.io/en/stable/api/pymongo/mongo_client.html) — Pool configuration

**Heroku:**
- [Heroku Dev Center](https://devcenter.heroku.com/) — Deployment documentation
- [Heroku Procfile](https://devcenter.heroku.com/articles/procfile) — Process type definitions
- [Heroku Scheduler](https://devcenter.heroku.com/articles/scheduler) — Scheduled job add-on
- [Heroku Platform API](https://devcenter.heroku.com/articles/platform-api-reference) — Dyno management

**Other:**
- [exchange_calendars](https://github.com/gerrymanoim/exchange_calendars) — NYSE market schedule library
- [websocket-client](https://websocket-client.readthedocs.io/) — Python WebSocket client library
- [Flask-Login](https://flask-login.readthedocs.io/) — User session management
- [bcrypt](https://pypi.org/project/bcrypt/) — Password hashing library

</div>
</details>

---

## 👨‍💻 Author & Contact

**Tyler Potts** - *Lead Developer & Trading Automation Consultant*

- 📧 **Email**: [twpotts11@gmail.com](mailto:twpotts11@gmail.com)
- 💼 **Upwork**: [Professional Profile](https://www.upwork.com/freelancers/robotraderguy)
- 🔗 **LinkedIn**: [Tyler Potts](https://www.linkedin.com/in/tyler-potts-022b6573/)

---

## ⚠️ Disclaimer

Trading involves substantial risk and is not suitable for all investors. Past performance does not guarantee future results. The use of this software is at your own risk. This tool copies trades automatically — any errors, delays, or failures in the copy process may result in financial loss. Always monitor your accounts and consult with a qualified financial advisor before making investment decisions. The developer assumes no liability for any trading losses incurred through the use of this software.

---

## 📄 License

This project is proprietary software. All rights reserved. Unauthorized distribution or modification is prohibited.

---

<div align="center">

**Built with ❤️ for algorithmic traders**

</div>
