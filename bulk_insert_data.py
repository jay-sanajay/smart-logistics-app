# bulk_insert_data.py
import random
from faker import Faker
import psycopg2
import json

fake = Faker()

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="logisticsdb",
    user="postgres",
    password="jay@123",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

weather_options = ['Clear', 'Rainy', 'Cloudy', 'Foggy']
time_of_day_options = ['Morning', 'Afternoon', 'Evening', 'Night']
traffic_levels = ['Light', 'Moderate', 'Heavy']

def generate_record():
    pickup = fake.city()
    destination = fake.city()
    stops = [fake.city() for _ in range(random.randint(0, 3))]
    distance = round(random.uniform(10, 500), 2)
    duration = round(distance * random.uniform(1.0, 1.5), 2)
    eta = round(duration * random.uniform(0.9, 1.1), 2)
    weather = random.choice(weather_options)
    time_of_day = random.choice(time_of_day_options)
    traffic = random.choice(traffic_levels)
    return (pickup, destination, stops, distance, duration, eta, weather, time_of_day, traffic)

# Generate and insert 10,000 records
for _ in range(10000):
    record = generate_record()
    cur.execute("""
        INSERT INTO delivery_logs (
            pickup_location, destination_location, stops,
            distance_km, duration_min, actual_eta_min,
            weather, time_of_day, traffic_level
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, record)

conn.commit()
cur.close()
conn.close()

print("✅ Inserted 10,000 fake delivery logs into the database.")
