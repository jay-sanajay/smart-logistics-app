import L from "leaflet";
import "leaflet/dist/leaflet.css";

export const initializeMap = (containerId = "map") => {
  const existingMap = L.DomUtil.get(containerId);
  if (existingMap && existingMap._leaflet_id !== undefined) {
    existingMap._leaflet_id = null;
  }

  const map = L.map(containerId).setView([19.076, 72.8777], 8);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  return map;
};
