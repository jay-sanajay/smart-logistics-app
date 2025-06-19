import { useState, useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./style.css";
import RouteMap from "./map";
const API_BASE = "http://localhost:8000";
const MAPBOX_TOKEN = "pk.eyJ1IjoiamF5MTIzNzgiLCJhIjoiY21jMDlkNzdmMXR2NDJrcHFtbGkwajZnOCJ9.bX0QUyTDfoclbqwfX82oww";
const OPENCAGE_API_KEY = "ba85308afc004f2e88d1e8be53c94a2f";

function App() {
  const [pickup, setPickup] = useState("");
  const [destination, setDestination] = useState("");
  const [stops, setStops] = useState([""]);
  const [pickupSuggestions, setPickupSuggestions] = useState([]);
  const [destinationSuggestions, setDestinationSuggestions] = useState([]);
  const [stopSuggestions, setStopSuggestions] = useState([[]]);
  const [routeInfo, setRouteInfo] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [lastRoute, setLastRoute] = useState(null);

  const mapRef = useRef(null);
  const routeLayerRef = useRef(null);
  const markerRefs = useRef([]);

  const haversineDistance = (coord1, coord2) => {
    const toRad = (deg) => deg * Math.PI / 180;
    const [lng1, lat1] = coord1;
    const [lng2, lat2] = coord2;

    const R = 6371; // Earth radius in km
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lng2 - lng1);

    const a = Math.sin(dLat / 2) ** 2 +
              Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
              Math.sin(dLon / 2) ** 2;

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  };

  const fetchSuggestions = async (query, setter) => {
    if (!query.trim()) return setter([]);
    try {
      const res = await fetch(
        `https://api.opencagedata.com/geocode/v1/json?q=${encodeURIComponent(query)}&key=${OPENCAGE_API_KEY}&limit=5`
      );
      const data = await res.json();
      const features = data.results.map((item) => ({
        place_name: item.formatted,
        geometry: item.geometry,
      }));
      setter(features);
    } catch (err) {
      console.error("Suggestion fetch error:", err);
      setter([]);
    }
  };

  useEffect(() => {
    if (!token || mapRef.current || !document.getElementById("map")) return;
    const container = L.DomUtil.get("map");
    if (container) container._leaflet_id = null;
    const map = L.map("map").setView([19.076, 72.8777], 8);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);
    mapRef.current = map;
  }, [token]);

  const resolveCoords = async (addr) => {
    if (!addr) return null;
    try {
      const res = await fetch(
        `https://api.opencagedata.com/geocode/v1/json?q=${encodeURIComponent(addr)}&key=${OPENCAGE_API_KEY}&limit=1`
      );
      const data = await res.json();
      if (!data.results?.length) return null;
      const { lat, lng } = data.results[0].geometry;
      return [lng, lat];
    } catch (err) {
      console.error("Geocode error:", err);
      return null;
    }
  };

  const getRoute = async () => {
    if (!pickup || !destination) {
      alert("Please enter both pickup and destination.");
      return;
    }

    try {
      const allAddresses = [pickup, ...stops.filter(s => s.trim()), destination];

      const res = await fetch(`${API_BASE}/optimize`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ addresses: allAddresses.map(address => ({ address })) }),
      });

      let optimizedOrder = allAddresses;
      let liveTraffic = null;
      let eta = null;
       // add a useState for lastRoute

      if (res.ok) {
        const data = await res.json();
        optimizedOrder = data.optimized_order;
        liveTraffic = data.live_traffic || null; // Live traffic info from backend
        eta = data.eta || null;                   // ETA info from backend
      } else if (res.status === 401) {
        logout();
        throw new Error("Session expired. Please log in again.");
      }

      const coordsList = [];
      const stopCoords = [];
      let pickupCoords = null;
      let destinationCoords = null;

      for (const addr of optimizedOrder) {
        const point = await resolveCoords(addr);
        if (!point) throw new Error(`Could not resolve: ${addr}`);
        coordsList.push(point);

        if (addr === pickup) pickupCoords = point;
        else if (addr === destination) destinationCoords = point;
        else stopCoords.push({ stop: addr, coords: point });
      }

      if (!pickupCoords) throw new Error("Pickup coordinates not found.");
      if (stopCoords.length === 0) throw new Error("No valid stops found.");

      // 🧠 Find Nearest and 2nd Nearest Stops
      const stopsWithDistance = stopCoords.map((stopObj) => ({
        ...stopObj,
        distance: haversineDistance(pickupCoords, stopObj.coords),
      }));

      const sortedStops = stopsWithDistance.sort((a, b) => a.distance - b.distance);
      const nearestStopObj = sortedStops[0];
      const secondNearestStopObj = sortedStops[1] || null;

      // Clear previous markers & layers
      if (routeLayerRef.current) mapRef.current.removeLayer(routeLayerRef.current);
      markerRefs.current.forEach(marker => mapRef.current.removeLayer(marker));
      markerRefs.current = [];

      // Add Markers
      for (let i = 0; i < coordsList.length; i++) {
        const [lng, lat] = coordsList[i];
        const label = i === 0 ? "Pickup" : i === coordsList.length - 1 ? "Destination" : `Stop ${i}`;
        const marker = L.marker([lat, lng]).addTo(mapRef.current).bindPopup(label).openPopup();
        markerRefs.current.push(marker);
      }

      // Add Marker for Nearest Stop
      if (nearestStopObj) {
        const [lng, lat] = nearestStopObj.coords;
        const marker = L.marker([lat, lng], {
          icon: L.icon({
            iconUrl: "https://maps.google.com/mapfiles/ms/icons/red-dot.png",
            iconSize: [32, 32],
            iconAnchor: [16, 32],
          })
        }).addTo(mapRef.current).bindPopup(`Nearest Stop: ${nearestStopObj.stop}`).openPopup();
        markerRefs.current.push(marker);
      }

      // 📦 Request directions
      const directions = await fetch(
        `https://api.mapbox.com/directions/v5/mapbox/driving/${coordsList.map(c => c.join(",")).join(";")}?geometries=geojson&access_token=${MAPBOX_TOKEN}`
      );
      const directionsData = await directions.json();
      const route = directionsData.routes?.[0];
      if (!route) throw new Error("No route found.");
      setLastRoute(route);
      const routeLine = L.geoJSON(route.geometry, { style: { color: "#10b981", weight: 4 } }).addTo(mapRef.current);
      routeLayerRef.current = routeLine;
      mapRef.current.fitBounds(routeLine.getBounds(), { padding: [50, 50] });

      // Display Route Info with live traffic and ETA
     let infoHTML = `
  <strong>Distance:</strong> ${(route.distance / 1000).toFixed(2)} km<br/>
  <strong>Duration (Live Traffic ETA):</strong> ${(route.duration / 60).toFixed(2)} minutes<br/>
`;
      const etaDate = new Date(Date.now() + route.duration * 1000);
infoHTML += `<strong>Expected Arrival Time:</strong> ${etaDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}<br/>`;


      // Add ETA from backend if available
      if (eta) {
        const etaMinutes = typeof eta === "number" ? (eta / 60).toFixed(2) : eta;
        infoHTML += `<strong>Estimated Time of Arrival (ETA):</strong> ${etaMinutes} minutes<br/>`;
      }

      // Add live traffic info if available
      if (liveTraffic) {
        infoHTML += `<strong>Live Traffic:</strong> ${liveTraffic}<br/>`;
      }

      infoHTML += `
        <strong>${pickup} ➡️ Nearest Stop:</strong> ${nearestStopObj.stop}<br/>
      `;

      if (secondNearestStopObj) {
        infoHTML += `<strong>${pickup} ➡️ Second Nearest Stop:</strong> ${secondNearestStopObj.stop}<br/>`;
      }

      let routeList = [pickup, nearestStopObj.stop];
      if (secondNearestStopObj) {
        routeList.push(secondNearestStopObj.stop);
      }
      const extraStops = stopCoords
        .map(s => s.stop)
        .filter(s => s !== nearestStopObj.stop && s !== secondNearestStopObj?.stop);
      routeList.push(...extraStops);
      routeList.push(destination);

      infoHTML += `<strong>Route:</strong> ${routeList.join(" ➡️ ")}<br/>`;

      setRouteInfo(infoHTML);

    } catch (err) {
      console.error("Route error:", err);
      alert(err.message);
    }
  };
 const saveAndEmailRoute = async () => {
  try {
    if (!lastRoute) {
      alert("No route to save. Please generate a route first.");
      return;
    }

    const addresses = [pickup, ...stops.filter(s => s.trim()), destination];
    const routePath = addresses.filter(Boolean);
    if (!routePath.length) throw new Error("No route to save.");

    // ✅ Use lastRoute instead of undefined 'route'
    const distanceKm = (lastRoute.distance / 1000).toFixed(2);
    const durationMin = (lastRoute.duration / 60).toFixed(2);

    const response = await fetch(`${API_BASE}/save_route`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        name: "My Route",
        distance_km: parseFloat(distanceKm),
        duration_min: parseFloat(durationMin),
        route: routePath,
      }),
    });

    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Failed to save route.");

    const routeId = result.id;

    // 🔐 Ask user for email before sending
    const email = prompt("Enter recipient email:");
    if (!email) return alert("Email address is required!");

    const emailRes = await fetch(`${API_BASE}/email_route/`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        route_id: routeId,
        recipient_email: email,
      }),
    });

    const emailResult = await emailRes.json();
    if (!emailRes.ok) throw new Error(emailResult.detail || "Failed to send email");

    alert("📧 Route PDF emailed successfully!");
  } catch (err) {
    alert("Error: " + err.message);
  }
};



  const addStop = () => {
    setStops([...stops, ""]);
    setStopSuggestions([...stopSuggestions, []]);
  };

  const updateStop = (index, value) => {
    const newStops = [...stops];
    newStops[index] = value;
    setStops(newStops);

    fetchSuggestions(value, (suggestions) => {
      const newSuggestions = [...stopSuggestions];
      newSuggestions[index] = suggestions;
      setStopSuggestions(newSuggestions);
    });
  };

  const removeStop = (index) => {
    const newStops = stops.filter((_, i) => i !== index);
    const newSuggestions = stopSuggestions.filter((_, i) => i !== index);
    setStops(newStops);
    setStopSuggestions(newSuggestions);
  };

  const logout = () => {
    setToken("");
    localStorage.removeItem("token");
  };

  const login = async () => {
    try {
      const res = await fetch(`${API_BASE}/token`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username, password }),
      });
      if (!res.ok) throw new Error("Login failed");
      const data = await res.json();
      setToken(data.access_token);
      localStorage.setItem("token", data.access_token);
    } catch (err) {
      alert(err.message);
    }
  };

  const signup = async () => {
    try {
      const res = await fetch(`${API_BASE}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) throw new Error("Signup failed");
      alert("Signup successful! Please login.");
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <>
      <div className="header">Smart Logistics Route Optimizer</div>
      <div className="outer-container">
        <div className="card">
          {!token ? (
            <>
              <div className="form-group">
                <label>👤 Username</label>
                <input value={username} onChange={(e) => setUsername(e.target.value)} />
              </div>
              <div className="form-group">
                <label>🔑 Password</label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
              </div>
              <button onClick={login} className="route-btn">🔐 Login</button>
              <button onClick={signup} className="route-btn">📝 Sign Up</button>
               <div id="map" className="map-box"></div>

            {routeInfo && <div className="route-info" dangerouslySetInnerHTML={{ __html: routeInfo }} />}
            </>
          ) : (
            <>
              <div className="form-group">
                <label>🚩 Pickup</label>
                <input
                  value={pickup}
                  onChange={(e) => {
                    setPickup(e.target.value);
                    fetchSuggestions(e.target.value, setPickupSuggestions);
                  }}
                />
                <ul className="suggestions">
                  {pickupSuggestions.map((item, i) => (
                    <li key={i} onClick={() => {
                      setPickup(item.place_name);
                      setPickupSuggestions([]);
                    }}>{item.place_name}</li>
                  ))}
                </ul>
              </div>

              {stops.map((stop, index) => (
                <div key={index} className="form-group">
                  <label>🛑 Stop {index + 1}</label>
                  <input
                    value={stop}
                    onChange={(e) => updateStop(index, e.target.value)}
                    placeholder="e.g., Nashik"
                  />
                  <button onClick={() => removeStop(index)}>❌</button>
                  <ul className="suggestions">
                    {(stopSuggestions[index] || []).map((item, i) => (
                      <li
                        key={i}
                        onClick={() => {
                          const newStops = [...stops];
                          newStops[index] = item.place_name;
                          setStops(newStops);
                          const newSuggestions = [...stopSuggestions];
                          newSuggestions[index] = [];
                          setStopSuggestions(newSuggestions);
                        }}
                      >
                        {item.place_name}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              <button onClick={addStop}>➕ Add Stop</button>

              <div className="form-group">
                <label>🏁 Destination</label>
                <input
                  value={destination}
                  onChange={(e) => {
                    setDestination(e.target.value);
                    fetchSuggestions(e.target.value, setDestinationSuggestions);
                  }}
                />
                <ul className="suggestions">
                  {destinationSuggestions.map((item, i) => (
                    <li key={i} onClick={() => {
                      setDestination(item.place_name);
                      setDestinationSuggestions([]);
                    }}>{item.place_name}</li>
                  ))}
                </ul>
              </div>

              <button onClick={getRoute} className="route-btn">🚀 Optimize Route</button>
              <button onClick={logout} className="route-btn">🔓 Log Out</button>
              <button onClick={saveAndEmailRoute} className="route-btn">📩 Save & Email PDF</button>

              <div id="map" className="map-box"></div>
              {routeInfo && <div className="route-info" dangerouslySetInnerHTML={{ __html: routeInfo }} />}
            </>
          )}
        </div>
      </div>
    </>
  );
}

export default App; 