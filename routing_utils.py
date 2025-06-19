import openrouteservice
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
ORS_API_KEY = os.getenv("ORS_API_KEY")

# Initialize ORS client
client = openrouteservice.Client(key=ORS_API_KEY)

def geocode_address(address):
    """Convert address to [lon, lat] using ORS Pelias search."""
    geocode = client.pelias_search(text=address)
    if geocode and geocode['features']:
        coords = geocode['features'][0]['geometry']['coordinates']  # [lon, lat]
        return coords
    else:
        raise ValueError(f"Could not geocode address: {address}")

def get_optimized_route(addresses):
    """Return the optimized address order using ORS Optimization API."""
    if len(addresses) < 2:
        raise ValueError("At least two addresses are required.")

    # Geocode all addresses
    coords = [geocode_address(addr) for addr in addresses]

    # ORS expects 'jobs' to be stops (excluding the first which is the vehicle start/end)
    jobs = [{"id": i+1, "location": loc} for i, loc in enumerate(coords[1:])]

    vehicle = {
        "id": 1,
        "start": coords[0],
        "end": coords[-1] if len(coords) > 2 else coords[1]
    }

    # Request optimized route
    optimized = client.optimization(jobs=jobs, vehicles=[vehicle])

    # Extract step IDs from optimization result
    steps = optimized["routes"][0]["steps"]
    ordered_indices = [0] + [step["job"] for step in steps if step["type"] == "job"]

    # Convert job IDs back to index in original address list
    optimized_order = [addresses[0]] + [addresses[job_id] for job_id in ordered_indices[1:]]

    return optimized_order
