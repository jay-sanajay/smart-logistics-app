document.getElementById("optimizeBtn").addEventListener("click", async () => {
  const pickup = document.getElementById("pickup").value.trim();
  const destination = document.getElementById("destination").value.trim();
  const resultDiv = document.getElementById("result") || document.getElementById("routeInfo");
  resultDiv.innerHTML = "";

  if (!pickup || !destination) {
    resultDiv.innerHTML = `<div class="error"><strong>Error:</strong> Please enter both pickup and destination addresses.</div>`;
    return;
  }

  // 🔁 Replace this with your actual Mapbox token
  const MAPBOX_TOKEN = "pk.eyJ1IjoiamF5MTIzNzgiLCJhIjoiY21jMDlkNzdmMXR2NDJrcHFtbGkwajZnOCJ9.bX0QUyTDfoclbqwfX82oww";

  try {
    // Step 1: Geocode pickup and destination
    const geocode = async (address) => {
      const response = await fetch(`https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(address)}.json?access_token=${MAPBOX_TOKEN}`);
      const data = await response.json();
      if (!data.features || data.features.length === 0) {
        throw new Error(`Could not geocode address: "${address}"`);
      }
      return {
        name: address,
        coords: data.features[0].center // [lon, lat]
      };
    };

    const [pickupData, destData] = await Promise.all([
      geocode(pickup),
      geocode(destination)
    ]);

    // Step 2: Build coordinates for optimization API
    const coordinates = [pickupData.coords, destData.coords];
    const coordString = coordinates.map(coord => coord.join(",")).join(";");

    const optimizationUrl = `https://api.mapbox.com/optimized-trips/v1/mapbox/driving/${coordString}?access_token=${MAPBOX_TOKEN}&roundtrip=false&source=first&destination=last&geometries=geojson`;

    const routeResponse = await fetch(optimizationUrl);
    const routeData = await routeResponse.json();

    if (!routeData.trips || routeData.trips.length === 0) {
      throw new Error("Mapbox Optimization API did not return a valid route.");
    }

    const trip = routeData.trips[0];
    const waypoints = routeData.waypoints;

    // Step 3: Sort waypoints and display results
    const sortedWaypoints = waypoints
      .sort((a, b) => a.waypoint_index - b.waypoint_index)
      .map(wp => wp.name || `${wp.location[1].toFixed(5)}, ${wp.location[0].toFixed(5)}`);

    resultDiv.innerHTML = `
      <h3 class="success">Optimized Route:</h3>
      <ol>${sortedWaypoints.map(p => `<li>${p}</li>`).join("")}</ol>
      <p><strong>Distance:</strong> ${(trip.distance / 1000).toFixed(2)} km<br>
         <strong>Duration:</strong> ${(trip.duration / 60).toFixed(2)} min</p>
    `;

    // Optional: Update map with route (let me know if you want this next)
  } catch (err) {
    console.error("Route Optimization Error:", err);
    resultDiv.innerHTML = `<div class="error"><strong>Error:</strong> ${err.message}</div>`;
  }
});
