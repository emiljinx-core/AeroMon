import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import {
  Search,
  MapPin,
  Navigation,
  Wind,
  Bike,
  Footprints,
  Clock,
  TrendingDown,
  Leaf,
  ChevronRight,
  LocateFixed,
  ArrowRight,
  Sparkles,
  Route
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Autocomplete } from "@/components/ui/autocomplete";
import heroImage from "@assets/generated_images/abstract_city_airflow_visualization.png";

import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

interface RouteData {
  id: number;
  name: string;
  aqiScore: number;
  aqiLevel: string;
  distance: string;
  distanceKm: number; // Store raw distance in km for time calculation
  duration: string;
  mode: string;
  description: string;
  savings: string;
  coordinates?: [number, number][];
}

const ROUTE_COLORS = ["#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

const startIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const endIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

function MapController({ routes, recommendedId }: { routes: RouteData[]; recommendedId: string | null }) {
  const map = useMap();
  if (routes.length > 0 && recommendedId) {
    const recommended = routes.find(r => r.name.includes(recommendedId) || r.name === `Route ${recommendedId}`);
    if (recommended && recommended.coordinates && recommended.coordinates.length > 0) {
      const bounds = L.latLngBounds(recommended.coordinates);
      map.fitBounds(bounds, { padding: [50, 50] });
    } else if (routes[0] && routes[0].coordinates && routes[0].coordinates.length > 0) {
      // Fallback to first route if recommended not found
      const bounds = L.latLngBounds(routes[0].coordinates);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }
  return null;
}

// Helper function to get AQI level and description from value
const getAQILevel = (value: number | null) => {
  if (value === null) return { level: "Unknown", description: "Air quality data unavailable" };
  if (value <= 50) return { level: "Good", description: "Air quality is satisfactory" };
  if (value <= 100) return { level: "Moderate", description: "Air quality is acceptable" };
  return { level: "Poor", description: "Air quality may be unhealthy" };
};

function AQIIndicator({ value, size = "lg" }: { value: number; size?: "sm" | "lg" }) {
  const getColor = (val: number) => {
    if (val <= 50) return { 
      bg: "bg-aqi-good", 
      text: "text-gradient-good", 
      ring: "ring-emerald-400/30",
      pulse: "bg-emerald-400/20"
    };
    if (val <= 100) return { 
      bg: "bg-aqi-moderate", 
      text: "text-gradient-moderate", 
      ring: "ring-amber-400/30",
      pulse: "bg-amber-400/20"
    };
    return { 
      bg: "bg-aqi-poor", 
      text: "text-gradient-poor", 
      ring: "ring-red-400/30",
      pulse: "bg-red-400/20"
    };
  };

  const colors = getColor(value);
  const sizeClasses = size === "lg" ? "w-24 h-24 text-3xl" : "w-12 h-12 text-lg";

  return (
    <div className={`relative ${sizeClasses} rounded-full ${colors.bg} flex items-center justify-center ring-2 ${colors.ring}`}>
      <span className={`font-display font-bold ${colors.text}`}>{value}</span>
      {size === "lg" && (
        <div className={`absolute inset-0 rounded-full animate-pulse-ring ${colors.pulse}`} />
      )}
    </div>
  );
}

function RouteCard({ route, index }: { route: RouteData; index: number }) {
  const getAQIStyles = (level: string) => {
    switch (level) {
      case "good":
        return { badge: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300", border: "border-emerald-200 dark:border-emerald-800/50" };
      case "moderate":
        return { badge: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300", border: "border-amber-200 dark:border-amber-800/50" };
      default:
        return { badge: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300", border: "border-red-200 dark:border-red-800/50" };
    }
  };

  const styles = getAQIStyles(route.aqiLevel);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.4 }}
    >
      <Card
        className={`p-4 cursor-pointer transition-all duration-300 hover:shadow-lg hover:-translate-y-1 border ${styles.border} bg-card/80 backdrop-blur-sm`}
        data-testid={`route-card-${route.id}`}
      >
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0">
            <AQIIndicator value={route.aqiScore} size="sm" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-display font-semibold text-foreground">{route.name}</h3>
              {route.aqiLevel === "good" && (
                <Badge className={`${styles.badge} text-xs font-medium`}>
                  <Leaf className="w-3 h-3 mr-1" />
                  Recommended
                </Badge>
              )}
            </div>

            <p className="text-sm text-muted-foreground mb-2">{route.description}</p>

            <div className="flex items-center gap-4 text-sm">
              <span className="flex items-center gap-1 text-muted-foreground">
                {route.mode === "walk" ? <Footprints className="w-4 h-4" /> : <Bike className="w-4 h-4" />}
                {route.distance}
              </span>
              <span className="flex items-center gap-1 text-muted-foreground">
                <Clock className="w-4 h-4" />
                {route.duration}
              </span>
              {route.savings !== "Standard route" && (
                <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                  <TrendingDown className="w-4 h-4" />
                  {route.savings}
                </span>
              )}
            </div>
          </div>

          <Button variant="ghost" size="icon" className="flex-shrink-0" data-testid={`select-route-${route.id}`}>
            <ChevronRight className="w-5 h-5" />
          </Button>
        </div>
      </Card>
    </motion.div>
  );
}

function MapVisualization({ routes, recommendedId, origin, destination }: {
  routes: RouteData[];
  recommendedId: string | null;
  origin: string;
  destination: string;
}) {
  const defaultCenter: [number, number] = [40.7128, -74.0060];

  return (
    <div className="relative w-full h-full map-gradient rounded-2xl overflow-hidden">
      <MapContainer
        center={defaultCenter}
        zoom={13}
        className="h-full w-full"
        zoomControl={true}
        style={{ borderRadius: "1rem" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {routes.length > 0 && recommendedId && <MapController routes={routes} recommendedId={recommendedId} />}
        {routes.map((route, index) => {
          if (!route.coordinates || route.coordinates.length === 0) return null;
          const isRecommended = route.name.includes(recommendedId || "");
          return (
            <Polyline
              key={route.id}
              positions={route.coordinates}
              color={ROUTE_COLORS[index % ROUTE_COLORS.length]}
              weight={isRecommended ? 6 : 3}
              opacity={isRecommended ? 1 : 0.5}
            />
          );
        })}
        {routes.length > 0 && routes[0].coordinates && routes[0].coordinates.length > 0 && (
          <>
            <Marker position={routes[0].coordinates[0]} icon={startIcon}>
              <Popup>Start: {origin || "Origin"}</Popup>
            </Marker>
            <Marker position={routes[0].coordinates[routes[0].coordinates.length - 1]} icon={endIcon}>
              <Popup>Destination: {destination || "Destination"}</Popup>
            </Marker>
          </>
        )}
      </MapContainer>

      {routes.length > 0 && (
        <motion.div
          className="absolute bottom-4 left-4 glass rounded-xl p-3 shadow-lg z-[1000]"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-gradient-to-r from-emerald-500 to-green-500" />
              <span className="text-xs font-medium">Clean Route</span>
            </div>
            {routes.length > 1 && (
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-gradient-to-r from-amber-400 to-orange-400" />
                <span className="text-xs font-medium">Alternative</span>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}

// Helper function to calculate travel time based on mode and distance
const calculateTravelTime = (distanceKm: number, mode: "walk" | "bike"): string => {
  if (distanceKm <= 0) return "Calculating...";
  const speedKmh = mode === "walk" ? 5 : 15; // 5 km/h for walking, 15 km/h for cycling
  const timeHours = distanceKm / speedKmh;
  const timeMinutes = Math.round(timeHours * 60);
  return `${timeMinutes} min`;
};

export default function Home() {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [routes, setRoutes] = useState<RouteData[]>([]);
  const [showRoutes, setShowRoutes] = useState(false);
  const [loading, setLoading] = useState(false);
  const [locating, setLocating] = useState(false);
  const [recommendedRouteId, setRecommendedRouteId] = useState<string | null>(null);
  const [currentAQI, setCurrentAQI] = useState<number | null>(45); // Default to 45, null means not loaded
  const [aqiLoading, setAqiLoading] = useState(false);
  const [aqiError, setAqiError] = useState(false);
  const [travelMode, setTravelMode] = useState<"walk" | "bike">("bike"); // Default to bike
  const { toast } = useToast();

  const handleFindRoutes = async () => {
    if (!origin || !destination) {
      toast({
        title: "Error",
        description: "Please enter both starting point and destination",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    console.log(`Fetching routes from ${origin} to ${destination}`);
    try {
      const res = await apiRequest("POST", "/get-routes", {
        start: origin,
        destination: destination,
      });
      const data = await res.json();
      console.log("API Data:", data);

      // Store recommended route ID
      setRecommendedRouteId(data.recommended_route_id || null);

      const transformedRoutes = data.routes.map((route: any, index: number) => {
        let level = "poor";
        if (route.average_aqi <= 50) level = "good";
        else if (route.average_aqi <= 100) level = "moderate";

        // Calculate savings relative to the worst route in the set (or just a baseline)
        const maxAqi = Math.max(...data.routes.map((r: any) => r.average_aqi));
        const savings = maxAqi > 0
          ? `${Math.round(((maxAqi - route.average_aqi) / maxAqi) * 100)}% cleaner air`
          : "Standard route";

        // Calculate approximate distance from coordinates
        const calculateDistance = (coords: [number, number][]) => {
          if (coords.length < 2) return 0;
          let total = 0;
          for (let i = 1; i < coords.length; i++) {
            const [lat1, lon1] = coords[i - 1];
            const [lat2, lon2] = coords[i];
            const R = 6371; // Earth's radius in km
            const dLat = (lat2 - lat1) * Math.PI / 180;
            const dLon = (lon2 - lon1) * Math.PI / 180;
            const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
            total += R * c;
          }
          return total;
        };

        const distanceKm = calculateDistance(route.coordinates || []);

        return {
          id: index + 1,
          name: `Route ${route.route_id}`,
          aqiScore: Math.round(route.average_aqi),
          aqiLevel: level,
          distance: distanceKm > 0 ? `${distanceKm.toFixed(1)} km` : "Calculating...",
          distanceKm: distanceKm, // Store raw distance for time calculation
          duration: calculateTravelTime(distanceKm, travelMode), // Calculate based on current mode
          mode: travelMode, // Use current travel mode
          description: index === 0 ? "Recommended Route" : "Alternative Route",
          savings: index === 0 ? "Recommended" : savings,
          coordinates: route.coordinates || [],
        };
      });

      setRoutes(transformedRoutes);
      setShowRoutes(true);
    } catch (error) {
      console.error("Route fetch error:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to fetch routes. Check console.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  // Update route durations when travel mode changes
  useEffect(() => {
    setRoutes(prevRoutes => {
      if (prevRoutes.length === 0) return prevRoutes;
      return prevRoutes.map(route => ({
        ...route,
        duration: calculateTravelTime(route.distanceKm, travelMode),
        mode: travelMode,
      }));
    });
  }, [travelMode]);

  const handleMyLocation = () => {
    if (!navigator.geolocation) {
      toast({
        title: "Error",
        description: "Geolocation is not supported by your browser",
        variant: "destructive",
      });
      return;
    }

    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const { latitude, longitude } = position.coords;
          console.log(`Got location: ${latitude}, ${longitude}`);

          // Existing functionality: Fetch address and set origin
          const res = await apiRequest("POST", "/reverse-geocode", {
            lat: latitude,
            lon: longitude,
          });

          if (!res.ok) {
            throw new Error("Failed to get address");
          }

          const data = await res.json();
          if (data.address) {
            setOrigin(data.address);
            toast({
              title: "Location Found",
              description: `Set starting point to: ${data.address}`,
            });
          }

          // New functionality: Fetch AQI for current location
          setAqiLoading(true);
          setAqiError(false);
          try {
            const aqiRes = await apiRequest("POST", "/get-aqi", {
              lat: latitude,
              lon: longitude,
            });

            if (!aqiRes.ok) {
              throw new Error("Failed to fetch AQI");
            }

            const aqiData = await aqiRes.json();
            if (aqiData.aqi !== undefined) {
              setCurrentAQI(Math.round(aqiData.aqi));
              setAqiError(false);
            } else {
              throw new Error("Invalid AQI response");
            }
          } catch (aqiError) {
            console.error("AQI fetch error:", aqiError);
            setAqiError(true);
            setCurrentAQI(null);
          } finally {
            setAqiLoading(false);
          }
        } catch (error) {
          console.error("Reverse geocode error:", error);
          toast({
            title: "Error",
            description: "Failed to get your address. Please try again.",
            variant: "destructive",
          });
        } finally {
          setLocating(false);
        }
      },
      (error) => {
        console.error("Geolocation error:", error);
        setLocating(false);

        let errorMessage = "Could not retrieve your location.";
        if (error.code === 1) errorMessage = "Location permission denied. Please enable it in your browser settings.";
        else if (error.code === 2) errorMessage = "Location unavailable. Ensure your GPS is on or try a different network.";
        else if (error.code === 3) errorMessage = "Location request timed out.";

        toast({
          title: "Location Error",
          description: errorMessage,
          variant: "destructive",
        });
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  return (
    <div className="min-h-screen bg-gradient-fresh">
      <header className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-md">
                <Wind className="w-5 h-5 text-white" />
              </div>
              <span className="font-display font-bold text-xl tracking-tight">Aeromon</span>
            </div>

            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-2 text-sm">
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300">
                  <Sparkles className="w-4 h-4" />
                  <span className="font-medium">
                    AQI: {
                      aqiLoading ? "Loading..." : 
                      aqiError ? "AQI unavailable" : 
                      currentAQI !== null ? currentAQI : "..."
                    }
                  </span>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                data-testid="button-locate"
                onClick={handleMyLocation}
                disabled={locating}
              >
                {locating ? <span className="animate-spin text-xs">⏳</span> : <LocateFixed className="w-4 h-4" />}
                <span className="hidden sm:inline">{locating ? "Locating..." : "My Location"}</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="pt-16">
        <section className="relative overflow-hidden">
          <div
            className="absolute inset-0 opacity-30"
            style={{
              backgroundImage: `url(${heroImage})`,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
            }}
          />
          <div className="absolute inset-0 bg-gradient-to-b from-background/60 via-background/80 to-background" />

          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="text-center mb-8"
            >
              <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-4">
                Breathe easier on
                <span className="text-gradient-good"> every journey</span>
              </h1>
              <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto">
                Smart navigation that prioritizes your health. Find routes with the cleanest air in real-time.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="max-w-2xl mx-auto"
            >
              <Card className="p-4 sm:p-6 shadow-xl border-0 bg-card/90 backdrop-blur-md">
                <div className="space-y-4">
                  <div className="relative">
                    <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-emerald-500 z-10" />
                    <Autocomplete
                      value={origin}
                      onChange={setOrigin}
                      placeholder="Starting point"
                      className="pl-11 h-12 text-base"
                    />
                  </div>

                  <div className="relative">
                    <Navigation className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-red-500 z-10" />
                    <Autocomplete
                      value={destination}
                      onChange={setDestination}
                      placeholder="Where to?"
                      className="pl-11 h-12 text-base"
                    />
                  </div>

                  <div className="flex gap-3">
                    <Button
                      className="flex-1 h-12 text-base font-semibold gap-2 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-500/25"
                      data-testid="button-find-routes"
                      onClick={handleFindRoutes}
                      disabled={loading}
                    >
                      {loading ? (
                        <span className="animate-spin mr-2">⏳</span>
                      ) : (
                        <Route className="w-5 h-5" />
                      )}
                      {loading ? "Finding Routes..." : "Find Clean Routes"}
                    </Button>
                  </div>

                  <div className="flex items-center justify-center gap-6 pt-2">
                    <button 
                      onClick={() => setTravelMode("walk")}
                      className={`flex items-center gap-2 text-sm transition-colors ${
                        travelMode === "walk" 
                          ? "text-primary font-medium" 
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                      data-testid="button-mode-walk"
                    >
                      <Footprints className="w-4 h-4" />
                      Walk
                    </button>
                    <button 
                      onClick={() => setTravelMode("bike")}
                      className={`flex items-center gap-2 text-sm transition-colors ${
                        travelMode === "bike" 
                          ? "text-primary font-medium" 
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                      data-testid="button-mode-bike"
                    >
                      <Bike className="w-4 h-4" />
                      Bike
                    </button>
                  </div>
                </div>
              </Card>
            </motion.div>
          </div>
        </section>

        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid lg:grid-cols-5 gap-6">
            <div className="lg:col-span-3 h-[400px] lg:h-[500px]">
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5 }}
                className="h-full"
              >
                <Card className="h-full p-0 overflow-hidden border-0 shadow-xl">
                  <MapVisualization
                    routes={routes}
                    recommendedId={recommendedRouteId}
                    origin={origin}
                    destination={destination}
                  />
                </Card>
              </motion.div>
            </div>

            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-xl font-semibold">Recommended Routes</h2>
                <Badge variant="secondary" className="font-medium">
                  2 options
                </Badge>
              </div>

              <AnimatePresence>
                {showRoutes && (
                  <div className="space-y-3">
                    {routes.map((route, index) => (
                      <RouteCard key={route.id} route={route} index={index} />
                    ))}
                  </div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </section>

        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <Card className="p-6 sm:p-8 bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-950/30 dark:to-teal-950/30 border-emerald-200/50 dark:border-emerald-800/30">
              <div className="flex flex-col sm:flex-row items-center gap-6">
                <div className="flex-shrink-0">
                  {currentAQI !== null && !aqiError ? (
                    <AQIIndicator value={currentAQI} size="lg" />
                  ) : aqiLoading ? (
                    <div className="w-24 h-24 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                      <span className="text-lg text-muted-foreground">...</span>
                    </div>
                  ) : (
                    <div className="w-24 h-24 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                      <span className="text-sm text-muted-foreground text-center px-2">N/A</span>
                    </div>
                  )}
                </div>
                <div className="text-center sm:text-left">
                  <h3 className="font-display text-2xl font-bold mb-1">
                    Current Air Quality: {
                      currentAQI !== null && !aqiError ? (
                        <span className="text-gradient-good">{getAQILevel(currentAQI).level}</span>
                      ) : aqiLoading ? (
                        <span className="text-muted-foreground">Loading...</span>
                      ) : (
                        <span className="text-muted-foreground">Unavailable</span>
                      )
                    }
                  </h3>
                  <p className="text-muted-foreground mb-3">
                    {currentAQI !== null && !aqiError ? getAQILevel(currentAQI).description : aqiLoading ? "Fetching air quality data..." : "Air quality data is currently unavailable"}
                  </p>
                  <div className="flex flex-wrap gap-2 justify-center sm:justify-start">
                    <Badge variant="secondary" className="gap-1">
                      <Wind className="w-3 h-3" />
                      PM2.5: 12 µg/m³
                    </Badge>
                    <Badge variant="secondary" className="gap-1">
                      <Leaf className="w-3 h-3" />
                      O₃: 28 ppb
                    </Badge>
                  </div>
                </div>
                <div className="sm:ml-auto">
                  <Button variant="outline" className="gap-2" data-testid="button-view-details">
                    View Details
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </Card>
          </motion.div>
        </section>

        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 pb-20">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-10"
          >
            <h2 className="font-display text-3xl font-bold mb-3">How it works</h2>
            <p className="text-muted-foreground">Three simple steps to healthier journeys</p>
          </motion.div>

          <div className="grid sm:grid-cols-3 gap-6">
            {[
              { icon: MapPin, title: "Set Your Route", description: "Enter your starting point and destination" },
              { icon: Wind, title: "Analyze Air Quality", description: "We check real-time AQI data across all paths" },
              { icon: Leaf, title: "Breathe Easy", description: "Follow the route with the cleanest air" },
            ].map((step, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card className="p-6 text-center h-full hover:shadow-lg transition-shadow" data-testid={`step-card-${index + 1}`}>
                  <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-emerald-100 to-teal-100 dark:from-emerald-900/30 dark:to-teal-900/30 flex items-center justify-center">
                    <step.icon className="w-7 h-7 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <h3 className="font-display font-semibold text-lg mb-2">{step.title}</h3>
                  <p className="text-sm text-muted-foreground">{step.description}</p>
                </Card>
              </motion.div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-border/50 bg-card/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
                <Wind className="w-4 h-4 text-white" />
              </div>
              <span className="font-display font-semibold">Aeromon</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Navigate smarter. Breathe better.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
