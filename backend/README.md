# Aeromon Backend

Flask backend API for the Aeromon air quality route finder application.

## Features

- **Geocoding**: Converts location strings to coordinates using Nominatim (free)
- **Route Finding**: Fetches multiple walking routes using OSRM routing API (free)
- **Air Quality**: Retrieves real-time AQI data using OpenWeather Air Pollution API
- **Route Analysis**: Samples 8-12 points along each route and calculates average AQI
- **Smart Recommendations**: Identifies the cleanest route (lowest average AQI)

## Prerequisites

- Python 3.8 or higher
- OpenWeather API key (free tier available at https://openweathermap.org/api)

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the `backend` directory:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenWeather API key:

```
OPENWEATHER_API_KEY=your_actual_api_key_here
```

**Getting an OpenWeather API Key:**
1. Go to https://openweathermap.org/api
2. Sign up for a free account
3. Navigate to API keys section
4. Copy your API key and paste it in the `.env` file

### 3. Run the Server

#### Option A: Using the run script (recommended)

```bash
python run.py
```

This script automatically loads environment variables from `.env` file.

#### Option B: Direct Python Execution

```bash
python app.py
```

#### Option B: Using Flask CLI

```bash
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```

#### Option C: Using Python Module

```bash
python -m flask run
```

The server will start on `http://localhost:5000` by default.

### 4. Test the API

You can test the health endpoint:

```bash
curl http://localhost:5000/health
```

Or test the main route endpoint:

```bash
curl -X POST http://localhost:5000/get-routes \
  -H "Content-Type: application/json" \
  -d '{"start": "Times Square, New York", "destination": "Central Park, New York"}'
```

## API Endpoints

### POST /get-routes

Fetches multiple walking routes between two locations and calculates average AQI for each.

**Request:**
```json
{
  "start": "Times Square, New York",
  "destination": "Central Park, New York"
}
```

**Response:**
```json
{
  "routes": [
    {
      "route_id": "A",
      "average_aqi": 45.5,
      "coordinates": [[40.7580, -73.9855], [40.7585, -73.9850], ...]
    },
    {
      "route_id": "B",
      "average_aqi": 52.3,
      "coordinates": [[40.7580, -73.9855], [40.7590, -73.9845], ...]
    }
  ],
  "recommended_route_id": "A"
}
```

### GET /health

Health check endpoint to verify the server is running and API key is configured.

**Response:**
```json
{
  "status": "healthy",
  "api_key_configured": true
}
```

## Configuration

### Environment Variables

- `OPENWEATHER_API_KEY` (required): Your OpenWeather API key for air quality data
- `PORT` (optional): Port to run the server on (default: 5000)
- `FLASK_ENV` (optional): Set to `development` for debug mode

### CORS Configuration

The backend is configured to accept requests from any origin. For production, you may want to restrict this to your frontend domain:

```python
CORS(app, origins=["http://localhost:5173"])  # Example for Vite dev server
```

## How It Works

1. **Geocoding**: The start and destination strings are converted to coordinates using Nominatim (OpenStreetMap's geocoding service).

2. **Route Finding**: Multiple walking routes are fetched using OSRM (Open Source Routing Machine), a free routing service.

3. **Coordinate Sampling**: Each route is sampled at 8-12 evenly spaced points to get representative air quality measurements.

4. **AQI Fetching**: For each sampled point, the OpenWeather Air Pollution API is called to get real-time AQI data.

5. **Average Calculation**: The average AQI is calculated for each route.

6. **Recommendation**: The route with the lowest average AQI is marked as recommended.

## Error Handling

The API includes error handling for:
- Invalid or missing location strings
- Geocoding failures
- Routing failures
- API key issues
- Network timeouts

All errors are returned with appropriate HTTP status codes and error messages.

## Rate Limiting

The code includes small delays (0.1 seconds) between AQI API calls to respect rate limits. For production use with high traffic, consider:
- Implementing caching
- Using a queue system
- Requesting higher rate limits from OpenWeather

## Troubleshooting

### "OPENWEATHER_API_KEY not set" warning

Make sure you've created a `.env` file with your API key. The server will still run but won't be able to fetch AQI data.

### "Location not found" errors

- Try more specific location strings (include city, state/country)
- Check spelling
- Use addresses or well-known landmarks

### Routing failures

- OSRM may have rate limits or temporary outages
- Very long routes (>100km) may fail
- Some remote locations may not have routing data

### CORS errors in frontend

Make sure the Flask server is running and accessible. Check the CORS configuration if you're running on a different port.

## License

This project is part of the Aeromon application.
