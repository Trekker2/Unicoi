# Tradier Copy Bot

A trade copier that monitors a master Tradier brokerage account and automatically replicates orders to follower accounts. Includes a Dash web dashboard for managing accounts, viewing positions/orders, and configuring settings.

## ✨ Features

- **Order Copying** - Detects new orders on the master account and copies them to all follower accounts
- **Polling + Streaming** - 2-second polling by default, with optional WebSocket streaming for instant detection
- **Multi-Leg Support** - Copies single-leg equities/options and multi-leg spreads (indexed notation)
- **Per-Account Multipliers** - Scale order quantities per follower account (e.g., 2x, 3x)
- **Cancellation Sync** - Detects canceled master orders and syncs cancellations to followers
- **Stale Order Filtering** - Skips orders older than configurable timeout (default 5 min)
- **Market-Aware Scheduling** - Respects NYSE market hours, sleeps during closure
- **Automation Killswitch** - Global on/off toggle for the copy engine
- **Modification Sync** - Detects modified master orders and syncs price/stop/duration changes to followers
- **Dark/Light Mode** - Tradier purple-themed dashboard with dark/light toggle
- **Activity Logging** - All copy engine operations logged with Info/Warning/Error prefixes, Master/Follower labels, and CSV export
- **Order Lineage** - Clickable master order IDs show follower order details (alias, order ID, status) in a modal; rejected orders display explanation

## 🏗️ Architecture

```
app.py              → Dash app initialization, auth, layout
main.py             → Copy engine worker loop (polling + streaming)
constants.py        → Configuration, enums, default settings
helper.py           → Utilities (market hours, hashing, formatting)
app_callbacks.py    → All Dash callbacks (routing, auth, CRUD actions)

pages/              → Dashboard pages
  accounts.py       → Manage connected Tradier accounts
  activity.py       → System activity logs
  orders.py         → Live orders with clickable master IDs → follower detail modal
  positions.py      → Live positions across all accounts
  settings.py       → Automation, streaming, multipliers, color mode
  login.py          → Authentication page

services/           → Service layer (business logic)
  accounts_service  → Account CRUD, master selection, validation
  activity_service  → Log retrieval and cleanup
  orders_service    → Live order fetching, cancellation
  positions_service → Live position fetching, close position
  settings_service  → Global settings read/write

scripts/            → Backend modules
  copy_manager.py   → Core copy engine (detect, reconstruct, forward orders)
  stream_manager.py → WebSocket streaming client for Tradier events
  database_manager  → MongoDB connection pooling, logging, cleanup
  style_manager.py  → Theme colors, component factories, styling

integrations/       → External API clients
  tradier_.py       → Tradier API (orders, positions, balances, option chains, streaming)
  heroku.py         → Heroku platform API (dyno management)
  papertrail.py     → Papertrail / SolarWinds log search API
  upwork_.py        → Upwork messaging API (chat history export)

cron/               → Scheduled maintenance
  cron_daily.py     → Daily cleanup (logs, history, orphans, indexes, health check)
```

## 🛠️ Tech Stack

| Layer       | Technology                                  |
|-------------|---------------------------------------------|
| Frontend    | Dash, Dash Bootstrap, Dash Mantine          |
| Backend     | Flask, Flask-Login                          |
| Database    | MongoDB Atlas (pymongo)                     |
| Broker API  | Tradier (REST + WebSocket streaming)        |
| Auth        | Flask-Login with bcrypt password hashing    |
| Deployment  | Heroku (gunicorn) / Docker                  |
| Scheduling  | exchange_calendars (NYSE market hours)      |

## 🗄️ Database Collections

| Collection  | Purpose                                      |
|-------------|----------------------------------------------|
| `accounts`  | Tradier accounts with `is_master` flag       |
| `trades`    | Active copied trades with `master_id` link   |
| `history`   | Completed/archived trades (90-day retention) |
| `settings`  | Global config (automation, multipliers, etc) |
| `logs`      | Activity logs (16-hour retention)            |
| `users`     | Dashboard login credentials                  |

## 🚀 Setup

### 1. Environment Variables

Copy `.env.example` to `.env` and fill in:

```
MONGO_ADDRESS=mongodb+srv://user:pass@cluster.mongodb.net/
FLASK_SECRET_KEY=your-secret-key
HEROKU_API_TOKEN=your-heroku-token
HEROKU_APP_NAME=your-app-name
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Locally

**Dashboard:**
```bash
python app.py
```
Opens at `http://localhost:8080`

**Copy Engine (separate process):**
```bash
python main.py
```

### 4. Deploy to Heroku

**Live deployment**: [unicoi-4c207001df14.herokuapp.com](https://unicoi-4c207001df14.herokuapp.com/)

**GitHub**: [github.com/Trekker2/Unicoi](https://github.com/Trekker2/Unicoi)

```bash
git push heroku main
```

The `Procfile` runs the dashboard via gunicorn. The copy engine (`main.py`) runs as a separate worker process.

## ⚡ How It Works

1. **Master account** is designated via the Accounts page
2. **Follower accounts** are added with their Tradier API credentials
3. **Copy engine** (`main.py`) polls the master account every 2 seconds (or streams via WebSocket)
4. **New orders** detected on master are reconstructed and forwarded to each follower
5. **Quantities** are scaled by per-account multipliers (default 1x)
6. **Modifications** (price, stop, duration) on master are detected and synced to followers via PUT; quantity changes trigger cancel + replace
7. **Cancellations** on master are automatically synced to followers
8. **Stale orders** (older than timeout) are skipped to prevent delayed copies
9. **All operations** are logged with `Info:`/`Warning:`/`Error:` prefixes, `Master:`/`Follower '{alias}':` labels, and viewable on the Activity page with color-coded highlighting and CSV export

## 🧪 Tests

240+ tests across 3 layers (unit, integration scenarios, live):

```bash
python -m tests.run_all_tests          # Unit tests + integration scenarios (default)
python -m tests.run_all_tests --live   # Also runs live Tradier sandbox tests
```

### Unit Tests — 165 tests

| Module               | Tests | Coverage                                                        |
|----------------------|-------|-----------------------------------------------------------------|
| test_helper          | 29    | flatten, format_tag, hide_text, hashing, market hours           |
| test_constants       | 30    | Default settings, status/side classifications, config           |
| test_database_manager| 18    | Serialization, log storage, cleanup                             |
| test_copy_manager    | 38    | Reconstruction, copy cycle, forwarding, cancel sync, mod sync   |
| test_services        | 24    | Settings, activity, accounts, orders, positions services        |
| test_cron_daily      | 15    | Log/history cleanup, orphan removal, indexes, health check      |

### Sandbox API Tests — 11 tests

| Module        | Tests | Coverage                                                    |
|---------------|-------|-------------------------------------------------------------|
| test_tradier  | 11    | Sandbox connectivity (auth, orders, balances, positions, streaming) |

### Integration Scenarios — 13 scenarios

| Scenario                                    | Validates                                    |
|---------------------------------------------|----------------------------------------------|
| Single equity order copy                    | Basic detection → reconstruction → forwarding|
| Multi-leg credit spread with multiplier     | Indexed notation, 3x scaling                 |
| Duplicate order prevention                  | History deduplication                        |
| Stale order rejection                       | Timeout filtering                            |
| Automation disabled                         | Killswitch prevents all copies               |
| Cancellation sync                           | Master cancel → follower cancel              |
| Multiple followers, different multipliers   | 1x, 2x, 5x per-account scaling              |
| No master account                           | Graceful failure                             |
| Limit order price preservation              | Price field included in reconstruction       |
| Bad status filtering                        | Expired/rejected orders skipped              |
| Master modifies limit price                 | PUT modify syncs price to follower           |
| Master modifies quantity                    | Cancel + replace (PUT can't change qty)      |
| Master modifies duration                    | PUT modify syncs duration to follower        |

### Live Integration Tests — 5 phases, 39 assertions (sandbox, `--live` flag)

All phases run through `run_copy_cycle` (the actual copy engine), respecting the automation toggle. Accounts are loaded from MongoDB to stay aligned with the dashboard. Use `--force-automation` to temporarily enable automation for test runs.

| Phase | What it tests | Cost |
|-------|--------------|------|
| 0 | Prerequisites — API connectivity, account access | $0 |
| 1 | Read-Only API — orders, positions, balances valid | $0 |
| 2 | Order Placement + Copy — multi-symbol equities (AAPL, MSFT, NVDA), SPY/QQQ options (7+ DTE and 0 DTE), 2-leg spreads, 4-leg iron condor → copy engine forwards to follower | ~$0 |
| 3 | Order Modification — modify master limit price/duration, copy engine syncs to follower | ~$0 |
| 4 | Order Cancellation — cancel master, copy engine syncs cancellation to follower | ~$0 |
