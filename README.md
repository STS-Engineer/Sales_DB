# Monday.com → PostgreSQL Sync

A FastAPI webhook service that automatically syncs data from Monday.com boards to a PostgreSQL database in real-time.

## What It Does

This application listens for webhook events from Monday.com and automatically inserts or updates records in PostgreSQL whenever items on your board change. It acts as a real-time data bridge between Monday.com and your database.

### Workflow

1. **Event Trigger**: Someone modifies a column in a Monday.com board
2. **Webhook Fired**: Monday.com sends an HTTP POST to your webhook endpoint
3. **Verification**: The webhook signature is validated (if configured)
4. **Data Fetch**: The app queries Monday.com GraphQL API to get the complete item data
5. **Column Mapping**: Monday.com column IDs are mapped to PostgreSQL column names
6. **Database Insert**: The row is inserted into the `monday_logger` table in PostgreSQL

## Architecture

### Core Components

**`main.py`** - FastAPI application entry point
- Initializes the FastAPI app with title and version
- Registers the webhooks router
- Provides `/health` endpoint for monitoring

**`settings.py`** - Configuration management
- Loads environment variables from `.env` file
- Defines required settings: API token, board ID, database URL
- Handles trigger column configuration (which columns trigger syncs)
- Defaults to monitoring the "Statut" column (`color_mksysrr6`)

**`app/routers/webhooks.py`** - Webhook handler
- Receives POST requests from Monday.com at `/webhooks/monday`
- Validates webhook signature for security
- Filters events by board ID and column ID
- Orchestrates the data sync process
- Returns appropriate status responses

**`app/services/monday.py`** - Monday.com API client
- `MondayClient`: Async GraphQL client for Monday.com API
- `ITEM_QUERY`: GraphQL query to fetch complete item details
- `verify_signature_or_skip()`: Validates webhook authenticity using HMAC-SHA256

**`app/services/ingest.py`** - Data transformation & database operations
- `build_row()`: Converts Monday.com item data to database row format
- `insert_row()`: Inserts data into PostgreSQL with parameterized queries
- Maps 50+ Monday.com columns to database columns

**`app/config/columns.py`** - Column mapping configuration
- Maps Monday.com column IDs to PostgreSQL column names
- Supports all Monday.com column types: status, relations, lookups, files, dates, numbers, etc.
- Example: `"color_mkvx38z5": "priority"` (Monday status column → priority column)

**`app/db.py`** - Database connection
- Creates SQLAlchemy engine for PostgreSQL
- Manages connection pooling with health checks

## How It Works

### Data Flow Example

**Monday.com Board** (Sales board, ID: 9550168457)
```
Item: "Enterprise Client A"
├── Name: "Enterprise Client A"
├── Status (color_mksysrr6): "In Progress"
├── Priority (color_mkvx38z5): "High"
├── Customer (board_relation_mksp63gj): "Acme Corp"
└── Estimated Price (numeric_mkszczs): "50000"
```

**Event Triggered** → Webhook POST to `/webhooks/monday`

**Data Extracted & Mapped**
```python
{
  "name": "Enterprise Client A",
  "statut": "In Progress",
  "priority": "High",
  "customer": "Acme Corp",
  "estimated_price": "50000"
}
```

**Inserted to PostgreSQL**
```sql
INSERT INTO public.monday_logger 
  (name, statut, priority, customer, estimated_price)
VALUES 
  ('Enterprise Client A', 'In Progress', 'High', 'Acme Corp', '50000')
```

## Configuration

### Environment Variables (.env)

```env
# Monday.com API token (generate from Monday.com dashboard)
MONDAY_API_TOKEN=eyJhbGciOiJIUzI1NiJ9...

# Webhook signing secret (optional, for validation)
MONDAY_SIGNING_SECRET=your_secret_here

# Monday.com board ID to monitor
BOARD_ID=9550168457

# PostgreSQL connection string
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/Sales

# Comma-separated column IDs that trigger syncs (optional)
# Defaults to "color_mksysrr6" (Status column) if not set
TRIGGER_COLUMN_IDS=color_mksysrr6,color_mkvx38z5
```

### Column Mapping

The `COLUMN_MAP` in `columns.py` defines 50+ mappings. Examples:

| Monday.com Column ID | Type | PostgreSQL Column |
|---|---|---|
| `name` | Text | `name` |
| `color_mkvx38z5` | Status | `priority` |
| `board_relation_mksp63gj` | Board Relation | `customer` |
| `multiple_person_mkszszx` | Multiple People | `sales_contact` |
| `numeric_mkszczs` | Number | `estimated_price` |
| `date_mksy346v` | Date | `status_end_date_planned` |
| `file_mksz8e3v` | File | `costing_files` |

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Create `.env` file with your credentials (see Configuration section)

### 3. Set Up Database
Ensure PostgreSQL has a table to receive data:
```sql
CREATE TABLE public.monday_logger (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255),
  statut VARCHAR(100),
  priority VARCHAR(100),
  customer VARCHAR(255),
  estimated_price NUMERIC,
  -- ... add other columns as needed
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. Run the Application
```bash
uvicorn main:app --reload
```

Server runs at: `http://localhost:8000`

## API Endpoints

### GET `/health`
Health check endpoint
```bash
curl http://localhost:8000/health
# Response: {"status": "ok"}
```

### POST `/webhooks/monday`
Webhook receiver for Monday.com events
- Requires webhook configured in Monday.com board settings
- Validates signature if `MONDAY_SIGNING_SECRET` is set
- Returns: `{"ok": true, "inserted": true, "item_id": "12345"}`

### GET `/docs`
Interactive Swagger UI documentation
```
http://localhost:8000/docs
```

## Deployment

### Using ngrok (Local Testing)
```bash
ngrok http 8000
# Use the generated URL in Monday.com webhook settings
# Example: https://abc123.ngrok.io/webhooks/monday
```

### Production Deployment
- Deploy to cloud service (AWS, Heroku, DigitalOcean, etc.)
- Update webhook URL in Monday.com to your production domain
- Use environment variables for sensitive credentials
- Enable `MONDAY_SIGNING_SECRET` for webhook validation

## Security Considerations

1. **API Token**: Never commit `.env` to git; regenerate tokens after exposure
2. **Database Credentials**: Store in environment variables, not code
3. **Webhook Validation**: Use `MONDAY_SIGNING_SECRET` to verify requests come from Monday.com
4. **SQL Injection Prevention**: Uses parameterized queries with SQLAlchemy
5. **HTTPS**: Use HTTPS in production (required by Monday.com)

## Monitoring & Debugging

### Check Logs
```bash
# Watch real-time logs
tail -f app.log
```

### Test Webhook Locally
```bash
curl -X POST http://localhost:8000/webhooks/monday \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "boardId": 9550168457,
      "itemId": 12345,
      "columnId": "color_mksysrr6"
    }
  }'
```

### Verify Database Insert
```sql
SELECT * FROM public.monday_logger ORDER BY created_at DESC LIMIT 1;
```

## Troubleshooting

**"ModuleNotFoundError: No module named 'app'"**
- Ensure you're running from project root, not app folder
- Run: `uvicorn main:app --reload`

**"Invalid signature" errors**
- Verify `MONDAY_SIGNING_SECRET` matches Monday.com webhook secret
- Or set to empty to skip validation (development only)

**Database connection refused**
- Check PostgreSQL is running
- Verify `DATABASE_URL` credentials and host
- Test: `psql postgresql://user:pass@host:5432/dbname`

**No data appearing in database**
- Verify webhook is configured in Monday.com board
- Check `BOARD_ID` matches your board
- Ensure modified column is in `TRIGGER_COLUMN_IDS`
- Check PostgreSQL table structure matches mapped columns

## Requirements

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic-settings==2.1.0
pydantic==2.5.0
psycopg[binary]==3.1.13
sqlalchemy==2.0.23
python-dotenv==1.0.0
httpx==0.25.2
```

## Author Notes

This sync service automatically captures changes from Monday.com without manual data entry, enabling real-time reporting and analytics from your board data in PostgreSQL.
