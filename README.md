# BreatheESG Data Ingestion Platform

A Django REST + React application for ingesting, normalising, and reviewing
corporate emissions data from SAP, utility providers, and Concur travel.

---

## Quick Start (Local)

### Prerequisites
- Python 3.11+
- Node.js 18+
- (Optional) PostgreSQL — SQLite works for local development

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment variables
cp ../.env.example .env         # Edit .env as needed

# Run migrations
python manage.py migrate

# Create a superuser (for /admin)
python manage.py createsuperuser

# Start development server
python manage.py runserver
# API available at http://localhost:8000/api/
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Set API URL (optional — defaults to /api proxy)
echo "VITE_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
# UI available at http://localhost:5173
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/ingest/sap/` | Upload SAP flat file CSV |
| `POST` | `/api/ingest/utility/` | Upload utility electricity CSV |
| `POST` | `/api/ingest/travel/` | Upload Concur travel CSV |
| `GET` | `/api/records/` | List records (filterable) |
| `PATCH` | `/api/records/{id}/approve/` | Approve a record |
| `PATCH` | `/api/records/{id}/reject/` | Reject a record with note |
| `POST` | `/api/records/bulk-approve/` | Approve multiple records |
| `GET` | `/api/dashboard/stats/` | Aggregated statistics |
| `GET` | `/api/jobs/` | List ingestion jobs |

### Example: Upload a SAP file

```bash
curl -X POST http://localhost:8000/api/ingest/sap/ \
  -F "file=@sample_data/sap_sample.csv"
```

### Example: Filter records by status

```bash
curl "http://localhost:8000/api/records/?status=SUSPICIOUS&scope=1"
```

### Example: Approve a record

```bash
curl -X PATCH http://localhost:8000/api/records/{uuid}/approve/ \
  -H "Content-Type: application/json" \
  -d '{"review_note": "Verified against purchase order PO-12345"}'
```

---

## Sample Data

Three CSV files in `sample_data/` contain 20 rows each with intentional
data quality issues:

| File | Issues |
|------|--------|
| `sap_sample.csv` | Zero quantity row, negative quantity, unknown unit (BARREL), missing value, 1 duplicate row |
| `utility_sample.csv` | 90-day billing period (suspicious), negative consumption, missing carbon intensity, end-before-start dates, 1 duplicate row |
| `travel_sample.csv` | Flight with no distance, hotel with negative nights, missing origin/destination, 1 duplicate row |

---

## Project Structure

```
breathe-esg/
├── backend/
│   ├── breathe_esg/         Django project settings & URLs
│   ├── ingestion/
│   │   ├── models.py        All data models
│   │   ├── serializers.py   DRF serializers
│   │   ├── views.py         API views
│   │   ├── admin.py         Django admin registration
│   │   ├── urls.py          URL routing
│   │   ├── parsers/
│   │   │   ├── sap.py       SAP CSV parser (Scope 1)
│   │   │   ├── utility.py   Utility CSV parser (Scope 2)
│   │   │   └── travel.py    Travel CSV parser (Scope 3)
│   │   └── migrations/
│   ├── requirements.txt
│   └── Procfile
├── frontend/
│   ├── src/
│   │   ├── api/client.js    Axios API client
│   │   ├── components/
│   │   │   ├── Sidebar.jsx
│   │   │   └── StatusBadge.jsx
│   │   └── pages/
│   │       ├── Dashboard.jsx
│   │       ├── Upload.jsx
│   │       └── Review.jsx
│   ├── index.html
│   └── vite.config.js
├── sample_data/
│   ├── sap_sample.csv
│   ├── utility_sample.csv
│   └── travel_sample.csv
├── MODEL.md       Data model documentation
├── DECISIONS.md   Architecture decisions
├── TRADEOFFS.md   What wasn't built and why
├── SOURCES.md     Real-world research references
└── render.yaml    One-click Render.com deployment
```

---

## Deployment (Render.com)

1. Push this repository to GitHub.
2. Go to [render.com](https://render.com) → New → Blueprint.
3. Connect your GitHub repo and select `render.yaml`.
4. Render will create:
   - `breathe-esg-api` — Django web service
   - `breathe-esg` — React static site
   - `breathe-esg-db` — PostgreSQL database
5. First deploy runs `migrate` automatically.
6. Create a superuser via the Render shell:
   ```bash
   python manage.py createsuperuser
   ```

---

## Key Design Decisions

See [DECISIONS.md](./DECISIONS.md) for full rationale. Summary:
- **SAP flat file** over IDoc/OData — zero client SAP configuration required
- **Utility CSV** over PDF — avoids fragile OCR, uses standard portal exports
- **Concur CSV** over API — no OAuth setup, uses standard report export

See [TRADEOFFS.md](./TRADEOFFS.md) for three features not built:
1. PDF utility bill parsing (would need OCR)
2. Real SAP OData integration (needs SAP system access)
3. Multi-user RBAC auth (deferred to keep prototype focused)

See [MODEL.md](./MODEL.md) for full data model documentation including
emission factor sources, normalisation logic, and audit trail design.
