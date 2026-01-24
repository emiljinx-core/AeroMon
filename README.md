# AeroMon 🌍💨

**Find the cleanest route, not just the fastest.**

AeroMon is an air quality-aware route finder that helps you choose the path with the lowest pollution exposure between two locations. By analyzing real-time air quality data across multiple route options, AeroMon recommends the healthiest path for your journey.

---

## ✨ Features

- 🛣️ **Clean Route Recommendations** — Compare alternative routes and get the lowest-AQI option
- 📊 **Route AQI Scoring** — Samples air quality at multiple points along each route with penalties for pollution spikes
- 🗺️ **Interactive Map UI** — Visualize routes with start/end markers and route overlays using Leaflet
- 📍 **My Location Support** — Quick origin setup with device GPS and reverse geocoding
- 🤖 **AI-Powered Explanations** — Gemini generates human-friendly explanations for route choices and air quality guidance

---

## 🚀 Demo

🔗 **Live Demo:** [https://your-aeromon-app.vercel.app](https://aero-mon-9uux.vercel.app)



## 🏗️ Architecture

```
┌─────────────────┐
│  React Frontend │ (Vercel)
│   (Vite + TS)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Flask Backend  │ (Python API)
└────────┬────────┘
         │
    ┌────┴────────────────┐
    │                     │
    ▼                     ▼
┌─────────┐         ┌──────────────┐
│ OSRM +  │         │ OpenWeather  │
│Nominatim│         │  Air Quality │
└─────────┘         └──────────────┘
                          │
                          ▼
                    ┌──────────┐
                    │  Gemini  │
                    │   API    │
                    └──────────┘
```

---

## 🛠️ Tech Stack

### Frontend
- React 18 + TypeScript
- Vite 7
- Tailwind CSS
- Leaflet / React-Leaflet
- Vercel (Deployment)

### Backend
- Flask + Flask-CORS
- OpenWeather Air Pollution API
- Nominatim (OpenStreetMap) for geocoding
- OSRM for route generation
- Google Gemini API for explanations

---

## 📋 Prerequisites

- **Node.js 18+** (required for Vite 7)
- **Python 3.8+**
- API Keys:
  - [OpenWeather API Key](https://openweathermap.org/api) (required)
  - [Google Gemini API Key](https://ai.google.dev/) (optional, for AI explanations)

---

## 🔧 Local Setup

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/emiljinx-core/AeroMon.git
cd AeroMon
```

### 2️⃣ Backend Setup

```bash
cd AeroMon/backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in `AeroMon/backend`:

```env
OPENWEATHER_API_KEY=your_openweather_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
PORT=5000
FLASK_ENV=development
```

Run the backend:

```bash
python run.py
```

Backend runs at `http://localhost:5000`

### 3️⃣ Frontend Setup

```bash
cd AeroMon/frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend runs at `http://localhost:5173`

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/get-routes` | Get route alternatives with AQI scores |
| `POST` | `/get-aqi` | Get AQI for specific coordinates |
| `POST` | `/reverse-geocode` | Convert coordinates to address |
| `POST` | `/get-route-explanation` | AI explanation for route recommendation |
| `POST` | `/get-current-aqi-details` | AI explanation of current AQI + health advice |
| `GET` | `/health` | Server health check |

### Example Request

```bash
curl -X POST http://localhost:5000/get-routes \
  -H "Content-Type: application/json" \
  -d '{
    "start": "India Gate, New Delhi",
    "destination": "Connaught Place, New Delhi"
  }'
```

---

## 🚢 Deployment

### Frontend (Vercel)

The frontend is deployed on Vercel. To deploy your own instance:

1. Push your code to GitHub
2. Import the project in [Vercel](https://vercel.com)
3. Set the root directory to `AeroMon/frontend`
4. Vercel will auto-detect Vite settings
5. Add environment variable if needed:
   ```
   VITE_API_BASE=https://your-backend-url.com
   ```
6. Deploy!

Alternatively, use the Vercel CLI:

```bash
cd AeroMon/frontend
npm run build
vercel --prod
```

### Backend (Your Choice)

Deploy the Flask backend to services like:
- Railway
- Render
- AWS EC2
- Google Cloud Run
- Heroku

**Important:** Update CORS settings in `AeroMon/backend/app.py` to include your deployed frontend domain.

---

## 📁 Project Structure

```
AeroMon/
├── README.md
└── AeroMon/
    ├── backend/
    │   ├── app.py              # Main Flask application
    │   ├── run.py              # Server entry point
    │   ├── requirements.txt    # Python dependencies
    │   └── README.md
    └── frontend/
        ├── src/
        │   ├── components/     # React components
        │   ├── App.tsx         # Main app component
        │   └── ...
        ├── package.json
        ├── vite.config.ts      # Vite configuration
        └── ...
```

---

## 🌟 How It Works

1. **Geocoding** — Converts start and destination addresses to coordinates using Nominatim
2. **Route Generation** — OSRM generates multiple alternative routes
3. **Air Quality Sampling** — Samples 8-12 points along each route
4. **AQI Fetching** — Retrieves real-time air quality data from OpenWeather API
5. **Route Scoring** — Calculates overall exposure score with penalties for pollution spikes
6. **AI Explanation** — Gemini generates user-friendly explanations (optional)

---

## 🔮 Future Enhancements

- 🧭 Turn-by-turn navigation with live rerouting
- 🚨 Real-time AQI hotspot alerts with safer detours
- 👥 Personalized sensitivity profiles (asthma, children, elderly)
- ⚡ Caching and performance improvements
- 📱 Mobile app (React Native)

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [OpenStreetMap](https://www.openstreetmap.org/) / [Nominatim](https://nominatim.org/) for geocoding
- [OSRM](http://project-osrm.org/) for routing
- [OpenWeather](https://openweathermap.org/) for air quality data
- [Google Gemini](https://ai.google.dev/) for AI-powered explanations
- [Leaflet](https://leafletjs.com/) for interactive maps

---

## 📧 Contact

Your Name - Emil Jinu - emil.jinx@gmail.com

Project Link: [https://github.com/emiljinx-core/AeroMon](https://github.com/emiljinx-core/AeroMon)

---

<p align="center">Made with ❤️ for cleaner commutes</p>
