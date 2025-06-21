// predictEta.js
import { API_BASE } from "./constants";

export const predictETA = async ({ distance_km, num_stops, weather, time_of_day, traffic_level }) => {
  const res = await fetch(`${API_BASE}/predict_eta`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ distance_km, num_stops, weather, time_of_day, traffic_level }),
  });
  if (!res.ok) throw new Error("ETA prediction failed");
  const data = await res.json();
  return data.eta_min;
};
