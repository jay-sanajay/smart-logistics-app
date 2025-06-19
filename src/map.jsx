import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup } from 'react-leaflet';
import axios from 'axios';
import 'leaflet/dist/leaflet.css';

export default function RouteMap() {
  const [routeCoords, setRouteCoords] = useState([]);
  const [eta, setEta] = useState(null);
  const [distance, setDistance] = useState(null);

  const source = "73.8567,18.5204";     // Pune
  const destination = "77.142,20.139";  // Washim

  useEffect(() => {
    axios.get("http://localhost:8000/api/traffic-route", {
      params: { source, destination }
    }).then(res => {
      const route = res.data.routes?.[0];
      if (!route) {
        throw new Error("No route found");
      }

      const coords = route.geometry.coordinates.map(([lng, lat]) => [lat, lng]);

      setRouteCoords(coords);
      setEta(Math.round(route.duration / 60)); // seconds to minutes
      setDistance((route.distance / 1000).toFixed(2)); // meters to km
    }).catch(err => {
      console.error("Error fetching traffic-aware route:", err.message);
    });
  }, []);

  return (
    <div style={{ marginTop: "2rem" }}>
      <h2>🚦 Live Traffic ETA Preview (Pune ➡️ Washim)</h2>
      <MapContainer center={[19.5, 76.5]} zoom={7} style={{ height: "400px", width: "100%" }}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <Polyline positions={routeCoords} color="blue" />
        {routeCoords.length > 0 && (
          <>
            <Marker position={routeCoords[0]}>
              <Popup>Start (Pune)</Popup>
            </Marker>
            <Marker position={routeCoords[routeCoords.length - 1]}>
              <Popup>End (Washim)</Popup>
            </Marker>
          </>
        )}
      </MapContainer>
      <p><strong>Distance:</strong> {distance} km</p>
      <p><strong>ETA (with traffic):</strong> {eta} minutes</p>
    </div>
  );
}
