document.getElementById("optimizeBtn")?.addEventListener("click", optimizeRoute);

async function optimizeRoute() {
  const pickup = document.getElementById('pickup').value.trim();
  const destination = document.getElementById('destination').value.trim();
  const output = document.getElementById('output') || document.getElementById('routeInfo');
  output.innerHTML = ""; // Clear previous output

  if (!pickup || !destination) {
    output.innerHTML = "<b>Please enter both pickup and destination addresses.</b>";
    return;
  }

  try {
    const MAPBOX_TOKEN = 'pk.eyJ1IjoiamF5MTIzNzgiLCJhIjoiY21jMDlkNzdmMXR2NDJrcHFtbGkwajZnOCJ9.bX0QUyTDfoclbqwfX82oww'; // 🔁 Replace with your actual token

    if (MAPBOX_TOKEN === 'pk.eyJ1IjoiamF5MTIzNzgiLCJhIjoiY21jMDlkNzdmMXR2NDJrcHFtbGkwajZnOCJ9.bX0QUyTDfoclbqwfX82oww') {
      output.innerHTML = "<b>Error:</b> Please replace 'YOUR_MAPBOX_ACCESS_TOKEN' with a valid Mapbox token.";
      return;
    }

    // Step 1: Geocode both addresses
    const geocode = async (place) => {
      const res = await fetch(`https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(place)}.json?access_token=${MAPBOX_TOKEN}`);
      const data = await res.json();

      if (!data.features || data.features.length === 0) {
        throw new Error(`Geocoding failed for address: ${place}`);
      }

      return {
        name: data.features[0].place_name,
        coords: data.features[0].center // [lon, lat]
      };
    };

    const [pickupData, destData] = await Promise.all([geocode(pickup), geocode(destination)]);
    const coordinates = [pickupData.coords, destData.coords];

    // Step 2: Build Optimization API URL
    const coordString = coordinates.map(c => c.join(',')).join(';');
    const url = `https://api.mapbox.com/optimized-trips/v1/mapbox/driving/${coordString}?roundtrip=false&source=first&destination=last&access_token=${MAPBOX_TOKEN}`;

    const response = await fetch(url);
    const data = await response.json();

    if (!data.trips || data.trips.length === 0) {
      throw new Error("Mapbox did not return a valid optimized trip.");
    }

    // Step 3: Show Optimized Route Order
    const waypoints = data.waypoints;
    const ordered = waypoints
      .sort((a, b) => a.waypoint_index - b.waypoint_index)
      .map(wp => wp.name || `${wp.location[1].toFixed(5)}, ${wp.location[0].toFixed(5)}`);

    output.innerHTML = `
      <h3>Optimized Route:</h3>
      <ol>${ordered.map(addr => `<li>${addr}</li>`).join('')}</ol>
      <p><strong>Distance:</strong> ${(data.trips[0].distance / 1000).toFixed(2)} km<br>
         <strong>Duration:</strong> ${(data.trips[0].duration / 60).toFixed(2)} min</p>
    `;

    // Optional: Update input boxes with new order
    document.getElementById('pickup').value = ordered[0];
    document.getElementById('destination').value = ordered[ordered.length - 1];

  } catch (err) {
    console.error(err);
    output.innerHTML = `<b>Error:</b> ${err.message}`;
  }
}
