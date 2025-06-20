import { OPENCAGE_API_KEY } from "./constants";

export const fetchSuggestions = async (query, setter) => {
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

export const resolveCoords = async (addr) => {
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
