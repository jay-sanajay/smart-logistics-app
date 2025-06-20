import { API_BASE, MAPBOX_TOKEN } from "./constants";
import { resolveCoords } from "./geocoding";
import { toPng } from "html-to-image";
import L from "leaflet";

const haversineDistance = (coord1, coord2) => {
  const toRad = (deg) => deg * Math.PI / 180;
  const [lng1, lat1] = coord1;
  const [lng2, lat2] = coord2;

  const R = 6371;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lng2 - lng1);

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
};

export const getRoute = async ({
  pickup,
  destination,
  stops,
  token,
  setRouteInfo,
  mapRef,
  routeLayerRef,
  markerRefs,
  setLastRoute,
}) => {
  try {
    const allAddresses = [pickup, ...stops.filter((s) => s.trim()), destination];

    const res = await fetch(`${API_BASE}/optimize`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ addresses: allAddresses.map((address) => ({ address })) }),
    });

    let optimizedOrder = allAddresses;
    let liveTraffic = null;
    let eta = null;

    if (res.ok) {
      const data = await res.json();
      optimizedOrder = data.optimized_order;
      liveTraffic = data.live_traffic || null;
      eta = data.eta || null;
    } else if (res.status === 401) {
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

    const stopsWithDistance = stopCoords.map((s) => ({
      ...s,
      distance: haversineDistance(pickupCoords, s.coords),
    }));
    const sortedStops = stopsWithDistance.sort((a, b) => a.distance - b.distance);
    const nearestStopObj = sortedStops[0];
    const secondNearestStopObj = sortedStops[1] || null;

    if (routeLayerRef.current) mapRef.current.removeLayer(routeLayerRef.current);
    markerRefs.current.forEach((m) => mapRef.current.removeLayer(m));
    markerRefs.current = [];

    for (let i = 0; i < coordsList.length; i++) {
      const [lng, lat] = coordsList[i];
      const label = i === 0 ? "Pickup" : i === coordsList.length - 1 ? "Destination" : `Stop ${i}`;
      const marker = L.marker([lat, lng]).addTo(mapRef.current).bindPopup(label).openPopup();
      markerRefs.current.push(marker);
    }

    if (nearestStopObj) {
      const [lng, lat] = nearestStopObj.coords;
      const marker = L.marker([lat, lng], {
        icon: L.icon({
          iconUrl: "https://maps.google.com/mapfiles/ms/icons/red-dot.png",
          iconSize: [32, 32],
          iconAnchor: [16, 32],
        }),
      }).addTo(mapRef.current).bindPopup(`Nearest Stop: ${nearestStopObj.stop}`).openPopup();
      markerRefs.current.push(marker);
    }

    const directions = await fetch(
      `https://api.mapbox.com/directions/v5/mapbox/driving/${coordsList.map((c) => c.join(",")).join(";")}?geometries=geojson&access_token=${MAPBOX_TOKEN}`
    );
    const directionsData = await directions.json();
    const route = directionsData.routes?.[0];
    if (!route) throw new Error("No route found.");

    setLastRoute(route);

    const routeLine = L.geoJSON(route.geometry, { style: { color: "#10b981", weight: 4 } }).addTo(mapRef.current);
    routeLayerRef.current = routeLine;
    mapRef.current.fitBounds(routeLine.getBounds(), { padding: [50, 50] });

    let infoHTML = `
      <strong>Distance:</strong> ${(route.distance / 1000).toFixed(2)} km<br/>
      <strong>Duration (Live Traffic ETA):</strong> ${(route.duration / 60).toFixed(2)} minutes<br/>
    `;

    const etaDate = new Date(Date.now() + route.duration * 1000);
    infoHTML += `<strong>Expected Arrival Time:</strong> ${etaDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}<br/>`;

    if (eta) {
      const etaMinutes = typeof eta === "number" ? (eta / 60).toFixed(2) : eta;
      infoHTML += `<strong>Estimated Time of Arrival (ETA):</strong> ${etaMinutes} minutes<br/>`;
    }

    if (liveTraffic) {
      infoHTML += `<strong>Live Traffic:</strong> ${liveTraffic}<br/>`;
    }

    infoHTML += `<strong>${pickup} ➡ Nearest Stop:</strong> ${nearestStopObj.stop}<br/>`;

    if (secondNearestStopObj) {
      infoHTML += `<strong>${pickup} ➡ Second Nearest Stop:</strong> ${secondNearestStopObj.stop}<br/>`;
    }

    let routeList = [pickup, nearestStopObj.stop];
    if (secondNearestStopObj) routeList.push(secondNearestStopObj.stop);
    const extraStops = stopCoords.map(s => s.stop).filter(s => s !== nearestStopObj.stop && s !== secondNearestStopObj?.stop);
    routeList.push(...extraStops);
    routeList.push(destination);

    infoHTML += `<strong>Route:</strong> ${routeList.join(" ➡ ")}<br/>`;

    setRouteInfo(infoHTML);
  } catch (err) {
    alert(err.message);
    console.error("Route error:", err);
  }
};

export const saveAndEmailRoute = async ({ lastRoute, pickup, stops, destination, token }) => {
  try {
    if (!lastRoute) {
      alert("No route to save. Please generate a route first.");
      return;
    }

    const email = prompt("Enter recipient email:");
    if (!email) return alert("Email address is required!");

    const mapElement = document.getElementById("map");
    const mapImageBase64 = await toPng(mapElement);
    const addresses = [pickup, ...stops.filter((s) => s.trim()), destination];
    const routePath = addresses.filter(Boolean);
    const distanceKm = (lastRoute.distance / 1000).toFixed(2);
    const durationMin = (lastRoute.duration / 60).toFixed(2);

    const response = await fetch(`${API_BASE}/save_route_with_map`, {
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
        recipient_email: email,
        map_image_base64: mapImageBase64,
      }),
    });

    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Failed to save route.");

    const routeId = result.id;

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
    if (!emailRes.ok) {
      console.error("❌ Email error:", emailResult);
      alert("Email error:\n" + (emailResult.detail || JSON.stringify(emailResult, null, 2)));
    } else {
      alert("📧 Route PDF emailed successfully!");
    }
  } catch (err) {
    alert("Error: " + (err.message || err));
  }
};
