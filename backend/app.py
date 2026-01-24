"""
Flask backend for Aeromon - Air Quality Route Finder

This backend provides an API endpoint to find walking routes between two locations
and calculate average air quality index (AQI) for each route.
"""

import os
import math
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from typing import List, Tuple, Dict, Any
from collections import Counter
import time

app = Flask(__name__)
CORS(
    app,
    supports_credentials=True,
    resources={
        r"/*": {
            "origins": [
                "https://aero-mon-9uux.vercel.app"
            ]
        }
    },
)
# Configuration
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org/route/v1"
OPENWEATHER_AIR_POLLUTION_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

# Get API key from environment variable
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
if not OPENWEATHER_API_KEY:
    print("Warning: OPENWEATHER_API_KEY not set. Air quality data will not be available.")


def geocode_location(location: str) -> Tuple[float, float]:
    """
    Convert a location string to coordinates using Nominatim geocoding API.
    
    Args:
        location: Location string (e.g., "New York, NY")
        
    Returns:
        Tuple of (latitude, longitude)
        
    Raises:
        ValueError: If location cannot be geocoded
    """
    params = {
        "q": location,
        "format": "json",
        "limit": 1
    }
    
    headers = {
        "User-Agent": "Aeromon/1.0"  # Required by Nominatim
    }
    
    try:
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            raise ValueError(f"Location '{location}' not found")
        
        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        return lat, lon
        
    except requests.RequestException as e:
        raise ValueError(f"Geocoding failed for '{location}': {str(e)}")


def reverse_geocode(lat: float, lon: float) -> str:
    """
    Convert coordinates to an address using Nominatim reverse geocoding API.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        Formatted address string
        
    Raises:
        ValueError: If reverse geocoding fails
    """
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 18,
        "addressdetails": 1
    }
    
    headers = {
        "User-Agent": "Aeromon/1.0"
    }
    
    try:
        response = requests.get("https://nominatim.openstreetmap.org/reverse", params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            raise ValueError("Location not found")
            
        # Try to construct a readable address
        address = data.get("address", {})
        
        # Prioritize specific fields for a concise address
        road = address.get("road", "")
        house_number = address.get("house_number", "")
        suburb = address.get("suburb", "")
        city = address.get("city") or address.get("town") or address.get("village", "")
        state = address.get("state", "")
        country = address.get("country", "")
        
        parts = []
        if road:
            parts.append(f"{house_number} {road}".strip())
        if suburb:
            parts.append(suburb)
        if city:
            parts.append(city)
        if state:
            parts.append(state)
        
        return ", ".join(filter(None, parts)) or data.get("display_name", "")
        
    except requests.RequestException as e:
        raise ValueError(f"Reverse geocoding failed: {str(e)}")


def get_walking_routes(start_lat: float, start_lon: float, 
                      dest_lat: float, dest_lon: float, 
                      num_routes: int = 3) -> List[List[Tuple[float, float]]]:
    """
    Fetch multiple walking routes between two points using OSRM routing API.
    
    Args:
        start_lat: Starting latitude
        start_lon: Starting longitude
        dest_lat: Destination latitude
        dest_lon: Destination longitude
        num_routes: Number of alternative routes to fetch
        
    Returns:
        List of routes, where each route is a list of (lat, lon) coordinates
    """
    # OSRM uses lon,lat format (not lat,lon)
    coordinates = f"{start_lon},{start_lat};{dest_lon},{dest_lat}"
    
    params = {
        "overview": "full",
        "geometries": "geojson",
        "alternatives": num_routes - 1,  # alternatives + 1 main route = num_routes total
        "steps": "false"
    }
    
    try:
        response = requests.get(
            f"{OSRM_URL}/walking/{coordinates}",
            params=params,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != "Ok":
            raise ValueError(f"Routing failed: {data.get('message', 'Unknown error')}")
        
        routes = []
        for route in data.get("routes", []):
            # Extract coordinates from GeoJSON geometry
            geometry = route.get("geometry", {})
            coordinates_list = geometry.get("coordinates", [])
            
            # Convert from [lon, lat] to (lat, lon) tuples
            route_coords = [(coord[1], coord[0]) for coord in coordinates_list]
            routes.append(route_coords)
        
        if not routes:
            raise ValueError("No routes found")
        
        # Always return exactly 2 routes
        if len(routes) > 2:
            # Keep only first 2 routes
            routes = routes[:2]
        elif len(routes) == 1:
            # Duplicate the single route
            routes.append(routes[0])
        
        return routes
        
    except requests.RequestException as e:
        raise ValueError(f"Routing failed: {str(e)}")


def sample_coordinates_along_route(route: List[Tuple[float, float]], 
                                   num_samples: int = 10) -> List[Tuple[float, float]]:
    """
    Sample evenly spaced coordinates along a route.
    
    Args:
        route: List of (lat, lon) coordinates representing the route
        num_samples: Number of points to sample (8-12 recommended)
        
    Returns:
        List of sampled (lat, lon) coordinates
    """
    if len(route) <= num_samples:
        return route
    
    # Calculate total distance along route
    total_distance = 0
    segment_distances = []
    
    for i in range(len(route) - 1):
        lat1, lon1 = route[i]
        lat2, lon2 = route[i + 1]
        
        # Haversine distance calculation
        R = 6371000  # Earth radius in meters
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        
        total_distance += distance
        segment_distances.append(distance)
    
    # Sample points at evenly spaced intervals
    sample_interval = total_distance / (num_samples - 1)
    sampled_points = [route[0]]  # Always include start point
    
    current_distance = 0
    route_index = 0
    segment_accumulated = 0
    
    for i in range(1, num_samples - 1):
        target_distance = i * sample_interval
        
        # Find the segment containing this distance
        while route_index < len(segment_distances) and segment_accumulated + segment_distances[route_index] < target_distance:
            segment_accumulated += segment_distances[route_index]
            route_index += 1
        
        if route_index >= len(route) - 1:
            break
        
        # Interpolate within the current segment
        segment_progress = (target_distance - segment_accumulated) / segment_distances[route_index]
        lat1, lon1 = route[route_index]
        lat2, lon2 = route[route_index + 1]
        
        sampled_lat = lat1 + (lat2 - lat1) * segment_progress
        sampled_lon = lon1 + (lon2 - lon1) * segment_progress
        sampled_points.append((sampled_lat, sampled_lon))
    
    sampled_points.append(route[-1])  # Always include end point
    return sampled_points


def get_aqi_for_coordinate(lat: float, lon: float) -> float:
    """
    Fetch Air Quality Index (AQI) for a coordinate using OpenWeather Air Pollution API.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        AQI value (0-500 scale, US EPA standard)
        
    Raises:
        ValueError: If API key is missing or request fails
    """
    if not OPENWEATHER_API_KEY:
        raise ValueError("OPENWEATHER_API_KEY not configured")
    
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY
    }
    
    try:
        response = requests.get(OPENWEATHER_AIR_POLLUTION_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # OpenWeather returns AQI in the 'list' array
        if "list" in data and len(data["list"]) > 0:
            air_data = data["list"][0]
            components = air_data.get("components", {})
            
            # Calculate US AQI from PM2.5 (primary pollutant for health)
            # OpenWeather provides PM2.5 in µg/m³
            pm25 = components.get("pm2_5", 0)
            
            if pm25 > 0:
                # Convert PM2.5 to US AQI using EPA formula
                # Breakpoints: 0-12 (0-50), 12.1-35.4 (51-100), 35.5-55.4 (101-150),
                # 55.5-150.4 (151-200), 150.5-250.4 (201-300), 250.5+ (301-500)
                if pm25 <= 12:
                    aqi = (50 / 12) * pm25
                elif pm25 <= 35.4:
                    aqi = ((100 - 51) / (35.4 - 12.1)) * (pm25 - 12.1) + 51
                elif pm25 <= 55.4:
                    aqi = ((150 - 101) / (55.4 - 35.5)) * (pm25 - 35.5) + 101
                elif pm25 <= 150.4:
                    aqi = ((200 - 151) / (150.4 - 55.5)) * (pm25 - 55.5) + 151
                elif pm25 <= 250.4:
                    aqi = ((300 - 201) / (250.4 - 150.5)) * (pm25 - 150.5) + 201
                else:
                    aqi = ((500 - 301) / (500 - 250.5)) * (pm25 - 250.5) + 301
                
                return min(500, max(0, aqi))  # Clamp to 0-500 range
            
            # Fallback: Use OpenWeather's CAQI scale (1-5) and convert
            # This is less accurate but works if PM2.5 is not available
            aqi_caqi = air_data.get("main", {}).get("aqi", 3)
            # Map CAQI 1-5 to approximate US AQI midpoints
            aqi_scale = {1: 25, 2: 75, 3: 125, 4: 175, 5: 300}
            return aqi_scale.get(aqi_caqi, 100)
        
        raise ValueError("No AQI data in response")
        
    except requests.RequestException as e:
        raise ValueError(f"Failed to fetch AQI: {str(e)}")


def calculate_route_aqi(route_coordinates: List[Tuple[float, float]]) -> Tuple[float, List[float]]:
    """
    Calculate average AQI for a route by sampling points and fetching AQI data.
    
    Args:
        route_coordinates: List of (lat, lon) coordinates along the route
        
    Returns:
        Tuple of (average_aqi, aqi_values_list) where:
        - average_aqi: Average AQI value for the route
        - aqi_values_list: List of AQI samples collected for that route
    """
    # Sample 8-12 points along the route
    num_samples = min(12, max(8, len(route_coordinates) // 10))
    sampled_points = sample_coordinates_along_route(route_coordinates, num_samples)
    
    aqi_values = []
    
    for lat, lon in sampled_points:
        try:
            # Add small delay to respect API rate limits
            time.sleep(0.1)
            aqi = get_aqi_for_coordinate(lat, lon)
            aqi_values.append(aqi)
        except ValueError as e:
            # If AQI fetch fails for a point, skip it
            print(f"Warning: {e}")
            continue
    
    if not aqi_values:
        # If no AQI data available, return default moderate value with empty list
        return (100.0, [100.0])
    
    average_aqi = sum(aqi_values) / len(aqi_values)
    return (average_aqi, aqi_values)


@app.route("/get-routes", methods=["POST"])
def get_routes():
    """
    Main API endpoint to get routes with air quality data.
    
    Request JSON:
        {
            "start": "string location",
            "destination": "string location"
        }
    
    Response JSON:
        {
            "routes": [
                {
                    "route_id": "A",
                    "final_aqi": number,
                    "coordinates": [[lat, lon], [lat, lon], ...]
                },
                {
                    "route_id": "B",
                    "final_aqi": number,
                    "coordinates": [[lat, lon], [lat, lon], ...]
                }
            ],
            "recommended_route_id": "A"
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        start = data.get("start")
        destination = data.get("destination")
        
        if not start or not destination:
            return jsonify({"error": "Both 'start' and 'destination' are required"}), 400
        
        # Step 1: Geocode start and destination
        print(f"Geocoding start: {start}")
        start_lat, start_lon = geocode_location(start)
        print(f"Start coordinates: ({start_lat}, {start_lon})")
        
        print(f"Geocoding destination: {destination}")
        dest_lat, dest_lon = geocode_location(destination)
        print(f"Destination coordinates: ({dest_lat}, {dest_lon})")
        
        # Step 2: Fetch multiple walking routes
        print("Fetching routes...")
        routes = get_walking_routes(start_lat, start_lon, dest_lat, dest_lon, num_routes=3)
        print(f"Found {len(routes)} routes")
        
        # Step 3: Calculate AQI for each route
        route_aqi_data = []
        for i, route_coords in enumerate(routes):
            route_id = chr(65 + i)  # A, B, etc.
            print(f"Calculating AQI for Route {route_id}...")
            
            try:
                average_aqi, aqi_values_list = calculate_route_aqi(route_coords)
                print(f"Route {route_id} average AQI: {average_aqi:.2f}, samples: {len(aqi_values_list)}")
            except Exception as e:
                print(f"Error calculating AQI for Route {route_id}: {e}")
                # Use default moderate AQI if calculation fails
                average_aqi = 100.0
                aqi_values_list = [100.0]
            
            route_aqi_data.append({
                "route_id": route_id,
                "average_aqi": average_aqi,
                "aqi_values_list": aqi_values_list,
                "coordinates": [[lat, lon] for lat, lon in route_coords]
            })
        
        # Step 4: Apply penalty-based comparison using non-common AQI values
        if len(route_aqi_data) >= 2:
            route_a = route_aqi_data[0]
            route_b = route_aqi_data[1]
            
            # Identify which route is non-recommended (higher average AQI)
            if route_a["average_aqi"] > route_b["average_aqi"]:
                non_recommended_route = route_a
                recommended_route = route_b
                non_recommended_id = "A"
            else:
                non_recommended_route = route_b
                recommended_route = route_a
                non_recommended_id = "B"
            
            # Find common and non-common AQI values
            # Round to nearest integer for comparison (to handle floating point precision)
            aqi_list_a = [round(aqi) for aqi in route_a["aqi_values_list"]]
            aqi_list_b = [round(aqi) for aqi in route_b["aqi_values_list"]]
            
            # Find common values (values that appear in both routes)
            # For each value, count occurrences in both lists and match them
            counter_a = Counter(aqi_list_a)
            counter_b = Counter(aqi_list_b)
            
            common_values = []
            non_common_a = []
            non_common_b = []
            
            # Process all unique values from both routes
            all_values = set(aqi_list_a + aqi_list_b)
            for val in all_values:
                count_a = counter_a.get(val, 0)
                count_b = counter_b.get(val, 0)
                common_count = min(count_a, count_b)
                
                # Add common values
                common_values.extend([val] * common_count)
                
                # Add non-common values (remaining after matching)
                non_common_a.extend([val] * (count_a - common_count))
                non_common_b.extend([val] * (count_b - common_count))
            
            # If no non-common values, use all values
            if not non_common_a:
                non_common_a = aqi_list_a
            if not non_common_b:
                non_common_b = aqi_list_b
            
            # Get peak of non-recommended route's non-common values
            peak_non_recommended = max(non_common_a) if non_recommended_route == route_a else max(non_common_b)
            
            # Get least of recommended route's non-common values
            least_recommended = min(non_common_b) if non_recommended_route == route_a else min(non_common_a)
            
            # Apply penalty only if non-recommended route's peak > recommended route's least
            penalty = 0
            if peak_non_recommended > least_recommended:
                # Apply penalty to non-recommended route based on its peak
                if 100 <= peak_non_recommended < 150:
                    penalty = 15
                elif 150 <= peak_non_recommended < 200:
                    penalty = 20
                elif 200 <= peak_non_recommended < 250:
                    penalty = 25
                elif peak_non_recommended >= 250:
                    penalty = 30
            
            # Calculate final AQI (penalty only applied to non-recommended route)
            if non_recommended_route == route_a:
                final_aqi_a = route_a["average_aqi"] + penalty
                final_aqi_b = route_b["average_aqi"]
            else:
                final_aqi_a = route_a["average_aqi"]
                final_aqi_b = route_b["average_aqi"] + penalty
            
            route_a["final_aqi"] = final_aqi_a
            route_b["final_aqi"] = final_aqi_b
            
            print(f"Common AQI values: {common_values}")
            print(f"Route A non-common: {non_common_a}, Route B non-common: {non_common_b}")
            print(f"Non-recommended route ({non_recommended_id}): peak={peak_non_recommended:.2f}, least_recommended={least_recommended:.2f}")
            print(f"Route A: avg={route_a['average_aqi']:.2f}, penalty={penalty if non_recommended_route == route_a else 0}, final={final_aqi_a:.2f}")
            print(f"Route B: avg={route_b['average_aqi']:.2f}, penalty={penalty if non_recommended_route == route_b else 0}, final={final_aqi_b:.2f}")
        else:
            # Fallback if we don't have 2 routes
            for route in route_aqi_data:
                route["final_aqi"] = route["average_aqi"]
        
        # Step 5: Build response with final_aqi
        route_data = []
        for route in route_aqi_data:
            route_data.append({
                "route_id": route["route_id"],
                "final_aqi": round(route["final_aqi"], 2),
                "coordinates": route["coordinates"]
            })
        
        # Step 6: Determine recommended route (lowest final_aqi)
        if route_data:
            recommended_route = min(route_data, key=lambda r: r["final_aqi"])
            recommended_route_id = recommended_route["route_id"]
        else:
            recommended_route_id = "A"
        
        return jsonify({
            "routes": route_data,
            "recommended_route_id": recommended_route_id
        })
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route("/reverse-geocode", methods=["POST"])
def reverse_geocode_endpoint():
    """
    Endpoint to convert coordinates to address.
    
    Request JSON:
        {
            "lat": number,
            "lon": number
        }
        
    Response JSON:
        {
            "address": "string address"
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        lat = data.get("lat")
        lon = data.get("lon")
        
        if lat is None or lon is None:
            return jsonify({"error": "Latitude and longitude required"}), 400
            
        address = reverse_geocode(float(lat), float(lon))
        return jsonify({"address": address})
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Reverse geocode error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/get-aqi", methods=["POST"])
def get_aqi_endpoint():
    """
    Endpoint to fetch AQI for a coordinate.
    
    Request JSON:
        {
            "lat": number,
            "lon": number
        }
        
    Response JSON:
        {
            "aqi": number (0-500)
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        lat = data.get("lat")
        lon = data.get("lon")
        
        if lat is None or lon is None:
            return jsonify({"error": "Latitude and longitude required"}), 400
            
        aqi = get_aqi_for_coordinate(float(lat), float(lon))
        return jsonify({"aqi": round(aqi, 2)})
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Get AQI error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "api_key_configured": bool(OPENWEATHER_API_KEY)})


# Optional: serve frontend static files (for Docker / single-server deploy)
FRONTEND_DIST = os.getenv("FRONTEND_DIST")
if FRONTEND_DIST and os.path.isdir(FRONTEND_DIST):
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        if path:
            full = os.path.join(FRONTEND_DIST, path)
            if os.path.isfile(full):
                return send_from_directory(FRONTEND_DIST, path)
        return send_from_directory(FRONTEND_DIST, "index.html")


if __name__ == "__main__":
    # Run the Flask app
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    
    print(f"Starting Aeromon backend on port {port}")
    print(f"OpenWeather API Key configured: {bool(OPENWEATHER_API_KEY)}")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
