# Quick Start Guide

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Get OpenWeather API Key

1. Visit https://openweathermap.org/api
2. Sign up for a free account
3. Go to API keys section
4. Copy your API key

## 3. Create .env File

Create a file named `.env` in the `backend` directory:

```
OPENWEATHER_API_KEY=your_api_key_here
```

Replace `your_api_key_here` with your actual API key.

## 4. Run the Server

```bash
python run.py
```

The server will start on `http://localhost:5000`

## 5. Test It

Open your browser and visit:
- Health check: http://localhost:5000/health
- Or use the frontend which is already configured to connect to this backend

## Troubleshooting

- **"OPENWEATHER_API_KEY not set"**: Make sure you created the `.env` file with your API key
- **CORS errors**: The backend is configured to accept requests from any origin. Make sure the server is running.
- **Port already in use**: Change the port by setting `PORT=5001` in your `.env` file
