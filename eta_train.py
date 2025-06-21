# eta_train.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
import pandas as pd
from main import DeliveryLog, Base, DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def fetch_delivery_logs():
    async with SessionLocal() as session:
        result = await session.execute(select(DeliveryLog))
        logs = result.scalars().all()
        data = [
            {
                "pickup_location": log.pickup_location,
                "destination_location": log.destination_location,
                "num_stops": len(log.stops),
                "distance_km": log.distance_km,
                "duration_min": log.duration_min,
                "actual_eta_min": log.actual_eta_min,
                "weather": log.weather,
                "time_of_day": log.time_of_day,
                "traffic_level": log.traffic_level,
            }
            for log in logs
        ]
        return pd.DataFrame(data)

if __name__ == "__main__":
   df = asyncio.run(fetch_delivery_logs())
print(f"✅ Loaded rows: {len(df)}")  # Shows how many rows you got
df.to_csv("delivery_data.csv", index=False)

