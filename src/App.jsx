import { useState, useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { MAPBOX_TOKEN, OPENCAGE_API_KEY, API_BASE } from "./constants";
import { fetchSuggestions, resolveCoords } from "./geocoding";
import { login, signup, logout } from "./auth";
import { getRoute, saveAndEmailRoute } from "./routeUtils.jsx";
import mapImage from './map.jpg';
import AdminDashboard from "./AdminDashboard";
import { predictETA } from "./predictEta";
import ChatBotAssistant from "./ChatBotAssistant";


function App() {
  const [userRole, setUserRole] = useState("");
  const [adminConfirmed, setAdminConfirmed] = useState(false);
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
  const [signupRole, setSignupRole] = useState("customer");
  const mapRef = useRef(null);
  const routeLayerRef = useRef(null);
  const markerRefs = useRef([]);
  const [predictedEta, setPredictedEta] = useState(null);

  useEffect(() => {
  if (!token) return;

  const mapContainer = document.getElementById("map");
  if (!mapContainer || mapRef.current) return;

  if (mapContainer._leaflet_id) {
    mapContainer._leaflet_id = null;
  }

  const map = L.map(mapContainer).setView([19.076, 72.8777], 8);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  mapRef.current = map;

  return () => {
    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
    }
  };
}, [token]);




const handleLogin = async () => {
  const result = await login(username, password);
  if (result.token) {
    setToken(result.token);
    setUserRole(result.role); // ✅ set the role from decoded token
    localStorage.setItem("token", result.token);

    if (result.role === "admin") {
      const isAdmin = window.confirm("Are you an Admin?");
      setAdminConfirmed(isAdmin);
    }
  }
};


const handleSignup = async () => {
  const result = await signup(username, password, signupRole); // include role
  if (result.token) {
    setToken(result.token);
    localStorage.setItem("token", result.token);
    // `useEffect` will fetch role
  }
};

// Stops Logic
const addStop = () => {
  setStops((prev) => [...prev, ""]);
  setStopSuggestions((prev) => [...prev, []]);
};

const updateStop = (index, value) => {
  const updatedStops = [...stops];
  updatedStops[index] = value;
  setStops(updatedStops);

  fetchSuggestions(value, (suggestions) => {
    const updatedSuggestions = [...stopSuggestions];
    updatedSuggestions[index] = suggestions;
    setStopSuggestions(updatedSuggestions);
  });
};

const removeStop = (index) => {
  setStops((prev) => prev.filter((_, i) => i !== index));
  setStopSuggestions((prev) => prev.filter((_, i) => i !== index));
};
return (
  <>
    <div className="header">Smart Logistics Route Optimizer</div>
    <ChatBotAssistant />

    {token && userRole === "admin" && adminConfirmed ? (
      <AdminDashboard token={token} />
    ) : (
      <div className="outer-container">
        <div className="card">
          <div className="login-wrapper">
            <div className="login-left">
              {!token ? (
                <img src={mapImage} alt="Map" className="login-image" />
              ) : (
                <div id="map" className="leaflet-map" />
              )}
            </div>

            <div className="login-right">
              {!token ? (
                <div className="login-form">
                  <h2>Login or Sign Up</h2>
                  <input
                    placeholder="Username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                  <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />

                  <button onClick={handleLogin}>Log In</button>

                  <select
                    className="styled-select"
                    value={signupRole}
                    onChange={(e) => setSignupRole(e.target.value)}
                  >
                    <option value="customer">Customer</option>
                    <option value="driver">Driver</option>
                    <option value="admin">Admin</option>
                  </select>

                  <button onClick={handleSignup}>Sign Up</button>
                </div>
              ) : (
                <div className="login-form">
                  {/* Pickup */}
                  <div className="form-group">
                    <label>Pickup</label>
                    <input
                      value={pickup}
                      onChange={(e) => {
                        setPickup(e.target.value);
                        fetchSuggestions(e.target.value, setPickupSuggestions);
                      }}
                    />
                    <ul className="suggestions">
                      {pickupSuggestions.map((item, i) => (
                        <li
                          key={i}
                          onClick={() => {
                            setPickup(item.place_name || item);
                            setPickupSuggestions([]);
                          }}
                        >
                          {item.place_name || item}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Stops */}
                  {stops.map((stop, index) => (
                    <div key={index} className="form-group">
                      <label>🛑 Stop {index + 1}</label>
                      <input
                        value={stop}
                        onChange={(e) => updateStop(index, e.target.value)}
                        placeholder="e.g., Nashik"
                      />
                      <button onClick={() => removeStop(index)}>Remove Stop</button>
                      <ul className="suggestions">
                        {(stopSuggestions[index] || []).map((item, i) => (
                          <li
                            key={i}
                            onClick={() => {
                              const newStops = [...stops];
                              newStops[index] = item.place_name || item;
                              setStops(newStops);

                              const newSuggestions = [...stopSuggestions];
                              newSuggestions[index] = [];
                              setStopSuggestions(newSuggestions);
                            }}
                          >
                            {item.place_name || item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                  <button onClick={addStop}>Add Stop</button>

                  {/* Destination */}
                  <div className="form-group">
                    <label>Destination</label>
                    <input
                      value={destination}
                      onChange={(e) => {
                        setDestination(e.target.value);
                        fetchSuggestions(e.target.value, setDestinationSuggestions);
                      }}
                    />
                    <ul className="suggestions">
                      {destinationSuggestions.map((item, i) => (
                        <li
                          key={i}
                          onClick={() => {
                            setDestination(item.place_name || item);
                            setDestinationSuggestions([]);
                          }}
                        >
                          {item.place_name || item}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Route Actions */}
                  <button
                    onClick={async () => {
                      await getRoute({
                        pickup,
                        destination,
                        stops,
                        token,
                        setRouteInfo,
                        mapRef,
                        routeLayerRef,
                        markerRefs,
                        setLastRoute,
                      });

                      if (lastRoute) {
                        const eta = await predictETA({
                          distance_km: lastRoute.distance / 1000,
                          num_stops: stops.length,
                          weather: "Clear",
                          time_of_day: "Afternoon",
                          traffic_level: "Moderate",
                        });
                        setPredictedEta(eta);
                      }
                    }}
                    className="route-btn"
                  >
                    Optimize Route
                  </button>

                  <button onClick={() => logout(setToken)} className="route-btn">
                    Log Out
                  </button>

                  <button
                    onClick={() =>
                      saveAndEmailRoute({
                        lastRoute,
                        pickup,
                        stops,
                        destination,
                        token,
                      })
                    }
                    className="route-btn"
                  >
                    Save & Email PDF
                  </button>
{routeInfo && (
  <div
    className="route-info"
    dangerouslySetInnerHTML={{ __html: routeInfo }}
  />
)}

{routeInfo && (
  <div
    id="route-summary"
    style={{
      position: "absolute",
      top: "-9999px",
      left: "-9999px",
      zIndex: -1,
    }}
    dangerouslySetInnerHTML={{ __html: routeInfo }}
  />
)}










                  {/* Predicted ETA */}
                  {predictedEta && (
                    <div className="route-info">
                      <h4>🧠 ML Predicted ETA:</h4>
                      <p><strong>{(predictedEta / 60).toFixed(2)} minutes</strong></p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    )}
  </>
);



}

export default App;
