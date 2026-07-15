# Transport Service - Train Domain

A production-ready FastAPI microservice for searching trains and stations.

## Folder Structure

```text
train/
├── app/
│   ├── main.py                 # FastAPI application and middlewares
│   ├── config.py               # Configuration and constants
│   ├── routes/
│   │   ├── stations.py         # Endpoints for stations
│   │   └── trains.py           # Endpoints for trains
│   ├── services/
│   │   ├── station_service.py  # Pure Python domain logic for stations
│   │   ├── train_service.py    # Pure Python domain logic for trains
│   │   └── *.json              # Offline fallback / mock responses
│   ├── models/
│   │   ├── request_models.py   # Pydantic query models
│   │   └── response_models.py  # Pydantic output schema
│   ├── utils.py                # Generic helpers
│   └── exceptions.py           # Custom exception definitions
├── requirements.txt
├── README.md
└── .env.example
```

## Installation

1. Clone the repository and navigate to the `transport-service/train` folder.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running Locally

To start the development server, run:
```bash
uvicorn app.main:app --reload
```

The server will start at `http://127.0.0.1:8000`.

## Available Endpoints

### 1. Health Check
`GET /health`
Returns the status of the server.

### 2. Search Stations
`GET /api/v1/stations/search`
Search for a station by its name.

**Query Parameters:**
- `q` (required): The station name.

**Example:**
`/api/v1/stations/search?q=rajapalayam`

### 3. Search Trains
`GET /api/v1/trains/search`
Search for trains between two stations on a given date.

**Query Parameters:**
- `from` (required): Source station name.
- `to` (required): Destination station name.
- `date` (required): Date in `DD-MM-YYYY` format.
- `travelClass` (optional): Filter by class (e.g., `3A`).
- `sortBy` (optional): Sort by `fare`, `departure`, `arrival`, or `duration`.
- `maxFare` (optional): Maximum fare in Rs.
- `minRating` (optional): Minimum train rating (e.g., `4.0`).
- `pantry` (optional): Boolean (true/false) if a pantry is required.

**Example:**
`/api/v1/trains/search?from=Rajapalayam&to=Chennai&date=24-07-2026&travelClass=3A&sortBy=fare`

## API Documentation (Swagger)

Auto-generated production-level documentation is available natively through FastAPI.
Once the server is running, visit:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
