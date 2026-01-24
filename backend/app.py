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

# Get API keys from environment variables
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
if not OPENWEATHER_API_KEY:
    print("Warning: OPENWEATHER_API_KEY not set. Air quality data will not be available.")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not set. Route explanations will not be available.")


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
                    "average_aqi": number,
                    "coordinates": [[lat, lon], [lat, lon], ...]
                },
                {
                    "route_id": "B",
                    "average_aqi": number,
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
                non_common_a = aqi_list_a if aqi_list_a else [route_a["average_aqi"]]
            if not non_common_b:
                non_common_b = aqi_list_b if aqi_list_b else [route_b["average_aqi"]]
            
            # Safety check: ensure we have values to compare
            if not non_common_a or not non_common_b:
                # Fallback: use average AQI if lists are empty
                peak_non_recommended = route_a["average_aqi"] if non_recommended_route == route_a else route_b["average_aqi"]
                least_recommended = route_b["average_aqi"] if non_recommended_route == route_a else route_a["average_aqi"]
            else:
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
        
        # Step 5: Build response with final_aqi (but use average_aqi field name for frontend compatibility)
        route_data = []
        for route in route_aqi_data:
            # Ensure final_aqi is set and is a valid number
            final_aqi = route.get("final_aqi", route.get("average_aqi", 100.0))
            if not isinstance(final_aqi, (int, float)) or math.isnan(final_aqi) or math.isinf(final_aqi):
                final_aqi = route.get("average_aqi", 100.0)
            
            route_data.append({
                "route_id": route["route_id"],
                "average_aqi": round(final_aqi, 2),  # Use final_aqi value but keep field name as average_aqi
                "aqi_values_list": route.get("aqi_values_list", []),  # Include AQI values for explanation
                "coordinates": route["coordinates"]
            })
        
        # Step 6: Determine recommended route (lowest final_aqi)
        if route_data:
            recommended_route = min(route_data, key=lambda r: r["average_aqi"])
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


@app.route("/get-route-explanation", methods=["POST"])
def get_route_explanation():
    """
    Generate AI-powered explanation for a route using Gemini API.
    
    Request JSON:
        {
            "route_id": "A" or "B",
            "average_aqi": number,
            "aqi_values_list": [number, number, ...],
            "distance_km": number,
            "duration_min": number (optional),
            "is_recommended": boolean,
            "other_route_aqi": number (optional, for comparison),
            "cleanliness_percentage": number (optional, % cleaner than other route),
            "coordinates": [[lat, lon], [lat, lon], ...]
        }
    
    Response JSON:
        {
            "explanation": "string explanation"
        }
    """
    try:
        if not GEMINI_API_KEY:
            print("ERROR: GEMINI_API_KEY not configured in environment variables")
            return jsonify({"error": "GEMINI_API_KEY not configured. Please set it in your environment variables."}), 500
        
        print(f"DEBUG: Gemini API key is set (first 10 chars: {GEMINI_API_KEY[:10]}...)")
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        route_id = data.get("route_id")
        average_aqi = data.get("average_aqi")
        aqi_values_list = data.get("aqi_values_list", [])
        distance_km = data.get("distance_km", 0)
        duration_min = data.get("duration_min", 0)
        is_recommended = data.get("is_recommended", False)
        other_route_aqi = data.get("other_route_aqi")
        cleanliness_percentage = data.get("cleanliness_percentage", 0)
        coordinates = data.get("coordinates", [])
        
        # Calculate statistics
        peak_aqi = max(aqi_values_list) if aqi_values_list else average_aqi
        min_aqi = min(aqi_values_list) if aqi_values_list else average_aqi
        
        # Calculate AQI range description
        if aqi_values_list:
            sorted_aqi = sorted(aqi_values_list)
            aqi_range = f"{sorted_aqi[0]:.0f}–{sorted_aqi[-1]:.0f}"
            # Most common range (middle 50%)
            mid_start = len(sorted_aqi) // 4
            mid_end = len(sorted_aqi) - mid_start
            if mid_end > mid_start:
                common_range = f"{sorted_aqi[mid_start]:.0f}–{sorted_aqi[mid_end-1]:.0f}"
            else:
                common_range = aqi_range
        else:
            aqi_range = f"{min_aqi:.0f}–{peak_aqi:.0f}"
            common_range = aqi_range
        
        # Determine AQI level
        if average_aqi <= 50:
            aqi_level = "Good"
            aqi_description = "excellent air quality"
        elif average_aqi <= 100:
            aqi_level = "Moderate"
            aqi_description = "acceptable air quality"
        elif average_aqi <= 150:
            aqi_level = "Unhealthy for Sensitive Groups"
            aqi_description = "air quality that may affect sensitive individuals"
        elif average_aqi <= 200:
            aqi_level = "Unhealthy"
            aqi_description = "poor air quality"
        elif average_aqi <= 300:
            aqi_level = "Very Unhealthy"
            aqi_description = "very poor air quality"
        else:
            aqi_level = "Hazardous"
            aqi_description = "hazardous air quality"
        
        # Build comprehensive prompt for Gemini
        comparison_text = ""
        if other_route_aqi:
            other_route_id = "B" if route_id == "A" else "A"
            if is_recommended:
                comparison_text = f"\nComparison: Route {route_id} has an average AQI of {average_aqi:.1f}, while Route {other_route_id} has {other_route_aqi:.1f}. "
                if cleanliness_percentage > 0:
                    comparison_text += f"Route {route_id} offers approximately {cleanliness_percentage:.0f}% cleaner air compared to Route {other_route_id}. "
            else:
                comparison_text = f"\nComparison: Route {other_route_id} (the recommended route) has better air quality with an average AQI of {other_route_aqi:.1f}, compared to Route {route_id}'s {average_aqi:.1f}. "
        
        duration_text = ""
        if duration_min > 0:
            hours = duration_min // 60
            minutes = duration_min % 60
            if hours > 0:
                duration_text = f"{hours} hour{'s' if hours > 1 else ''} and {minutes} minute{'s' if minutes != 1 else ''}"
            else:
                duration_text = f"{minutes} minute{'s' if minutes != 1 else ''}"
        
        prompt = f"""You are an air quality route analysis assistant. Provide a comprehensive, structured explanation about Route {route_id}.

Route Information:
- Route ID: {route_id}
- Distance: {distance_km:.1f} km
- Travel Time: {duration_text if duration_text else 'Not specified'}
- Average AQI: {average_aqi:.1f} ({aqi_level})
- Peak AQI: {peak_aqi:.1f}
- Minimum AQI: {min_aqi:.1f}
- AQI Range: {aqi_range}
- Most Common AQI Range: {common_range}
- Recommended: {"Yes" if is_recommended else "No"}{comparison_text}

Provide a detailed explanation covering ALL of the following points in a natural, flowing narrative:

1. **Why this route is {'recommended' if is_recommended else 'an alternative option'}**
   - Explain the recommendation status clearly
   - If recommended, explain why it's better (e.g., "Route {route_id} is recommended because it has lower air pollution exposure compared to Route {'B' if route_id == 'A' else 'A'}.")
   - If alternative, explain its position relative to the recommended route

2. **Air quality levels along the route**
   - Describe the AQI range (e.g., "Along Route {route_id}, AQI values mostly range between {common_range}, indicating {aqi_description.lower()}.")
   - Mention the peak and minimum values
   - Explain what these levels mean in practical terms

3. **Health exposure comparison**
   - Compare exposure risk if comparison data is available
   - Explain the health implications (e.g., "The alternative route passes through areas with higher peak AQI, increasing pollution exposure.")
   - Discuss who might be most affected

4. **Travel distance and time context**
   - Mention the distance ({distance_km:.1f} km) and time ({duration_text if duration_text else 'travel time'})
   - Explain how this relates to the recommendation (e.g., "Both routes take approximately {distance_km:.1f} km and {duration_text if duration_text else 'similar time'}, so air quality becomes the deciding factor.")

5. **Cleanliness percentage**
   - If available, mention the percentage difference (e.g., "Route {route_id} offers approximately {cleanliness_percentage:.0f}% cleaner air compared to the alternative route.")
   - Put this in context of what it means for the traveler

6. **Practical suggestion**
   - Provide actionable advice (e.g., "If you are sensitive to pollution or traveling with children, Route {route_id if is_recommended else 'the recommended route'} is safer.")
   - Consider different traveler profiles (sensitive individuals, children, elderly, etc.)

7. **Friendly closing line**
   - End with an encouraging, positive statement (e.g., "Choosing Route {route_id if is_recommended else 'the recommended route'} ensures a healthier and more comfortable journey.")

Write in a friendly, conversational tone. Make it informative but easy to understand. Structure it as 2-3 well-organized paragraphs that flow naturally. Be specific about AQI values and their health implications."""

        # Call Gemini API
        # Try gemini-1.5-pro first, fallback to gemini-pro
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        try:
            print(f"DEBUG: Calling Gemini API with model gemini-1.5-pro")
            print(f"DEBUG: Prompt length: {len(prompt)} characters")
            response = requests.post(gemini_url, json=payload, timeout=30)
            print(f"DEBUG: Gemini API response status: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            print(f"DEBUG: Gemini API response keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
            
            # Extract the generated text
            if "candidates" in result and len(result["candidates"]) > 0:
                if "content" in result["candidates"][0] and "parts" in result["candidates"][0]["content"]:
                    explanation = result["candidates"][0]["content"]["parts"][0]["text"]
                    print(f"DEBUG: Successfully extracted explanation (length: {len(explanation)} chars)")
                else:
                    print(f"ERROR: Unexpected Gemini response structure: {result}")
                    raise ValueError("Unexpected response structure")
            else:
                print(f"ERROR: Gemini API returned no candidates: {result}")
                raise ValueError("No candidates in response")
                
        except requests.RequestException as e:
            # Try fallback model
            print(f"Gemini 1.5-pro error: {e}, trying gemini-pro...")
            try:
                gemini_url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
                response = requests.post(gemini_url_fallback, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                
                if "candidates" in result and len(result["candidates"]) > 0:
                    explanation = result["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    raise ValueError("No candidates in fallback response")
            except Exception as e2:
                print(f"Gemini API fallback also failed: {e2}")
                raise e
        
        return jsonify({"explanation": explanation})
        
    except requests.RequestException as e:
        print(f"Gemini API request error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"Gemini API error details: {error_detail}")
            except:
                print(f"Gemini API error response: {e.response.text}")
        # Fallback explanation with more detail
        route_id = data.get("route_id", "Unknown")
        average_aqi = data.get("average_aqi", 100)
        is_recommended = data.get("is_recommended", False)
        peak_aqi = max(data.get("aqi_values_list", [average_aqi])) if data.get("aqi_values_list") else average_aqi
        min_aqi = min(data.get("aqi_values_list", [average_aqi])) if data.get("aqi_values_list") else average_aqi
        distance_km = data.get("distance_km", 0)
        
        # Build a comprehensive fallback explanation
        explanation_parts = []
        
        # 1. Why recommended
        if is_recommended:
            other_route_id = "B" if route_id == "A" else "A"
            explanation_parts.append(f"Route {route_id} is recommended because it has lower air pollution exposure compared to Route {other_route_id}.")
        else:
            other_route_id = "B" if route_id == "A" else "A"
            explanation_parts.append(f"Route {route_id} is an alternative option, while Route {other_route_id} is the recommended route with better air quality.")
        
        # 2. Air quality levels
        explanation_parts.append(f"Along Route {route_id}, AQI values range between {min_aqi:.0f}–{peak_aqi:.0f}, indicating {aqi_description.lower()}.")
        
        # 3. Health exposure (if comparison data available)
        other_route_aqi = data.get("other_route_aqi")
        if other_route_aqi:
            if peak_aqi > other_route_aqi:
                explanation_parts.append(f"Route {route_id} passes through areas with higher peak AQI ({peak_aqi:.0f}), increasing pollution exposure compared to the alternative route.")
        
        # 4. Distance and time
        duration_min = data.get("duration_min", 0)
        if duration_min > 0:
            hours = duration_min // 60
            minutes = duration_min % 60
            time_text = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            explanation_parts.append(f"Both routes take approximately {distance_km:.1f} km and {time_text}, so air quality becomes the deciding factor.")
        else:
            explanation_parts.append(f"This route covers {distance_km:.1f} km.")
        
        # 5. Cleanliness percentage
        cleanliness_percentage = data.get("cleanliness_percentage", 0)
        if cleanliness_percentage > 0 and is_recommended:
            other_route_id = "B" if route_id == "A" else "A"
            explanation_parts.append(f"Route {route_id} offers approximately {cleanliness_percentage:.0f}% cleaner air compared to Route {other_route_id}.")
        
        # 6. Practical suggestion
        if is_recommended:
            explanation_parts.append(f"If you are sensitive to pollution or traveling with children, Route {route_id} is safer.")
        else:
            other_route_id = "B" if route_id == "A" else "A"
            explanation_parts.append(f"If you are sensitive to pollution or traveling with children, Route {other_route_id} (the recommended route) is safer.")
        
        # 7. Friendly closing
        if is_recommended:
            explanation_parts.append(f"Choosing Route {route_id} ensures a healthier and more comfortable journey.")
        else:
            other_route_id = "B" if route_id == "A" else "A"
            explanation_parts.append(f"Consider choosing Route {other_route_id} for a healthier and more comfortable journey.")
        
        explanation = " ".join(explanation_parts)
        return jsonify({"explanation": explanation})
    except Exception as e:
        print(f"Error generating explanation: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        # Provide a more detailed fallback explanation
        route_id = data.get("route_id", "Unknown")
        average_aqi = data.get("average_aqi", 100)
        is_recommended = data.get("is_recommended", False)
        peak_aqi = max(data.get("aqi_values_list", [average_aqi])) if data.get("aqi_values_list") else average_aqi
        min_aqi = min(data.get("aqi_values_list", [average_aqi])) if data.get("aqi_values_list") else average_aqi
        distance_km = data.get("distance_km", 0)
        other_route_aqi = data.get("other_route_aqi")
        cleanliness_percentage = data.get("cleanliness_percentage", 0)
        
        # Build a basic explanation manually
        explanation_parts = []
        
        if is_recommended:
            explanation_parts.append(f"Route {route_id} is recommended because it has lower air pollution exposure.")
        else:
            explanation_parts.append(f"Route {route_id} is an alternative option.")
        
        explanation_parts.append(f"Along Route {route_id}, AQI values range between {min_aqi:.0f}–{peak_aqi:.0f}, indicating {aqi_description.lower()}.")
        
        if other_route_aqi:
            other_route_id = "B" if route_id == "A" else "A"
            if cleanliness_percentage > 0:
                explanation_parts.append(f"Route {route_id} offers approximately {cleanliness_percentage:.0f}% cleaner air compared to Route {other_route_id}.")
        
        explanation_parts.append(f"This route covers {distance_km:.1f} km.")
        
        if is_recommended:
            explanation_parts.append("If you are sensitive to pollution or traveling with children, Route {route_id} is safer.")
            explanation_parts.append(f"Choosing Route {route_id} ensures a healthier and more comfortable journey.")
        
        explanation = " ".join(explanation_parts)
        return jsonify({"explanation": explanation})


@app.route("/get-current-aqi-details", methods=["POST"])
def get_current_aqi_details():
    """
    Generate AI-powered explanation for current air quality using Gemini API.
    
    Request JSON:
        {
            "aqi": number,
            "pm25": number (optional, in µg/m³),
            "o3": number (optional, in ppb),
            "has_routes": boolean (optional, whether user has routes)
        }
    
    Response JSON:
        {
            "explanation": "string explanation"
        }
    """
    try:
        if not GEMINI_API_KEY:
            print("ERROR: GEMINI_API_KEY not configured")
            return jsonify({"error": "GEMINI_API_KEY not configured"}), 500
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        aqi = data.get("aqi")
        pm25 = data.get("pm25", 12)  # Default values if not provided
        o3 = data.get("o3", 28)
        has_routes = data.get("has_routes", False)
        
        if aqi is None:
            return jsonify({"error": "AQI value required"}), 400
        
        # Determine AQI level
        if aqi <= 50:
            aqi_level = "Good"
        elif aqi <= 100:
            aqi_level = "Satisfactory"
        elif aqi <= 200:
            aqi_level = "Moderate"
        elif aqi <= 300:
            aqi_level = "Poor"
        elif aqi <= 400:
            aqi_level = "Very Poor"
        else:
            aqi_level = "Hazardous"
        
        # Build comprehensive prompt for Gemini
        prompt = f"""You are an air quality health advisor. Provide a detailed, structured explanation about the current air quality.

Current Air Quality Information:
- AQI: {aqi:.1f} ({aqi_level})
- PM2.5: {pm25} µg/m³
- Ozone (O₃): {o3} ppb
- User has route options: {"Yes" if has_routes else "No"}

Provide a comprehensive explanation covering ALL of the following sections in a natural, flowing narrative:

1. **Health Interpretation**
   - Explain what the current AQI level means for health
   - Example format: "Air quality is currently in the {aqi_level} range (AQI {aqi:.0f}). [Explain health implications]."

2. **Pollutant Breakdown Explanation**
   - Explain PM2.5 levels: "PM2.5 levels at {pm25} µg/m³ indicate fine particulate matter concentration, which affects lung health."
   - Explain Ozone levels: "Ozone (O₃) at {o3} ppb is [within/above/below] [range description]."

3. **Short-term Advice**
   - Provide actionable advice for sensitive individuals
   - Example: "Sensitive individuals should limit outdoor exertion."
   - Example: "Wearing a mask can reduce inhalation of particulates."

4. **Trend-based Reasoning**
   - Provide generic reasoning about what might contribute to current levels
   - Example: "Nearby traffic congestion contributes to higher PM2.5 concentration."
   - Keep it generic - no extra API needed

5. **Travel Recommendation Context** (only if has_routes is True)
   - Connect to route selection: "For your planned journey, selecting the recommended route reduces exposure to these pollutants."

6. **Friendly Closing**
   - End with an encouraging statement: "Stay safe and enjoy cleaner travel with AeroMon."

Write in a friendly, conversational tone. Structure it as clear paragraphs. Be specific about the AQI and pollutant values. Make it informative but easy to understand."""

        # Call Gemini API
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        try:
            print(f"DEBUG: Calling Gemini API for current AQI details")
            response = requests.post(gemini_url, json=payload, timeout=30)
            print(f"DEBUG: Gemini API response status: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            
            if "candidates" in result and len(result["candidates"]) > 0:
                if "content" in result["candidates"][0] and "parts" in result["candidates"][0]["content"]:
                    explanation = result["candidates"][0]["content"]["parts"][0]["text"]
                    print(f"DEBUG: Successfully extracted explanation")
                else:
                    raise ValueError("Unexpected response structure")
            else:
                raise ValueError("No candidates in response")
                
        except requests.RequestException as e:
            print(f"Gemini API error: {e}")
            # Fallback explanation
            explanation = f"""**Health Interpretation**

Air quality is currently in the {aqi_level} range (AQI {aqi:.0f}). {"Prolonged outdoor exposure may cause breathing discomfort." if aqi > 100 else "Air quality is generally safe for most people."}

**Pollutant Breakdown Explanation**

PM2.5 levels at {pm25} µg/m³ indicate fine particulate matter concentration, which affects lung health. Ozone (O₃) at {o3} ppb is within moderate range.

**Short-term Advice**

{"Sensitive individuals should limit outdoor exertion." if aqi > 100 else "Most people can continue normal outdoor activities."} Wearing a mask can reduce inhalation of particulates.

**Trend-based Reasoning**

Nearby traffic congestion and industrial activities contribute to higher PM2.5 concentration in urban areas.

{"**Travel Recommendation Context**\n\nFor your planned journey, selecting the recommended route reduces exposure to these pollutants.\n\n" if has_routes else ""}**Friendly Closing**

Stay safe and enjoy cleaner travel with AeroMon."""
        
        return jsonify({"explanation": explanation})
        
    except Exception as e:
        print(f"Error generating AQI details: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to generate explanation: {str(e)}"}), 500


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
