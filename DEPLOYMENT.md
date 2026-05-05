# Deployment Guide

This guide explains how to deploy the Data Enrichment Pipeline as a REST API.

## Local Development

### Prerequisites

- Python 3.7+
- pip

### Installation

```bash
cd DataEnrich
pip install -r requirements.txt
```

### Running the API

```bash
python3 api_server.py
```

The API will be available at `http://localhost:8000`

### API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Docker Deployment

### Build Docker Image

```bash
docker build -t data-enrichment-api .
```

### Run Container

```bash
docker run -p 8000:8000 data-enrichment-api
```

### Docker Compose

```bash
docker-compose up
```

## Cloud Deployment Options

### Option 1: Vercel (Serverless)

1. Create a `vercel.json` file:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api_server.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api_server.py"
    }
  ]
}
```

2. Deploy:
```bash
vercel
```

### Option 2: Railway

1. Install Railway CLI:
```bash
npm install -g @railway/cli
```

2. Login and deploy:
```bash
railway login
railway init
railway up
```

### Option 3: Render

1. Push code to GitHub
2. Connect GitHub repository to Render
3. Select "Web Service"
4. Build command: `pip install -r requirements.txt && python api_server.py`
5. Start command: `uvicorn api_server:app --host 0.0.0.0 --port $PORT`

### Option 4: AWS EC2

1. Launch EC2 instance
2. SSH into instance
3. Install dependencies:
```bash
sudo apt update
sudo apt install python3-pip
git clone <your-repo>
cd DataEnrich
pip3 install -r requirements.txt
```

4. Run with gunicorn:
```bash
pip3 install gunicorn
gunicorn api_server:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

5. Use nginx as reverse proxy (optional)

### Option 5: Heroku

1. Create `Procfile`:
```
web: uvicorn api_server:app --host 0.0.0.0 --port $PORT
```

2. Deploy:
```bash
heroku create
git push heroku main
```

## API Endpoints

### POST /api/v1/enrich

Enrich a single user profile.

**Request:**
```json
{
  "email": "alice@example.com",
  "name": "Alice Smith"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_input": {...},
    "personal_info": {...},
    "metadata": {...}
  },
  "error": null,
  "processing_time_ms": 412.5,
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### POST /api/v1/batch-enrich

Enrich multiple user profiles.

**Request:**
```json
[
  {"email": "user1@example.com"},
  {"name": "Bob Smith", "phone": "+1-555-0100"}
]
```

**Response:**
Array of enrichment responses.

### GET /health

Check API health status.

## Environment Variables

Optional environment variables:

```bash
# API Configuration
PORT=8000
HOST=0.0.0.0

# Cache Configuration
CACHE_TTL_SECONDS=3600
ENABLE_CACHING=true
```

## Production Considerations

1. **Rate Limiting**: Add rate limiting to prevent abuse
2. **Authentication**: Add API key authentication
3. **HTTPS**: Use HTTPS in production
4. **Monitoring**: Add logging and monitoring
5. **Database**: Consider Redis for distributed caching
6. **Load Balancing**: Use multiple instances for high traffic

## Testing the API

### Using curl

```bash
# Health check
curl http://localhost:8000/health

# Enrich profile
curl -X POST http://localhost:8000/api/v1/enrich \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "name": "Alice Smith"}'
```

### Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/enrich",
    json={"email": "alice@example.com", "name": "Alice Smith"}
)
print(response.json())
```

### Using JavaScript

```javascript
fetch('http://localhost:8000/api/v1/enrich', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    email: 'alice@example.com',
    name: 'Alice Smith'
  })
})
  .then(res => res.json())
  .then(data => console.log(data));
```

## Troubleshooting

### Port already in use
```bash
# Change port
uvicorn api_server:app --port 8001
```

### Import errors
```bash
# Ensure you're in the correct directory
cd DataEnrich
pip install -r requirements.txt
```

### CORS issues
The API allows all origins by default. For production, restrict origins in the CORS middleware.
