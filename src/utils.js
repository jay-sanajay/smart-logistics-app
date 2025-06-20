export const haversineDistance = (coord1, coord2) => {
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

export const fetchSuggestions = async (query, setter, apiKey) => {
  if (!query.trim()) return setter([]);
  try {
    const res = await fetch(
      `https://api.opencagedata.com/geocode/v1/json?q=${encodeURIComponent(query)}&key=${apiKey}&limit=5`
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

export const resolveCoords = async (addr, apiKey) => {
  if (!addr) return null;
  try {
    const res = await fetch(
      `https://api.opencagedata.com/geocode/v1/json?q=${encodeURIComponent(addr)}&key=${apiKey}&limit=1`
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
