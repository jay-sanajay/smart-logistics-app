from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import os, requests, traceback
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import Column, Integer, String, Float, ForeignKey, desc
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from difflib import SequenceMatcher
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
from fastapi import FastAPI
import traceback
from sqlalchemy import Column, Integer, Float, String, Text, ForeignKey, select, desc

load_dotenv()

from email.message import EmailMessage
import aiosmtplib

async def send_email_with_attachment(to_email: str, subject: str, body: str, file_path: str):
    try:
        message = EmailMessage()
        message["From"] = os.getenv("SMTP_USERNAME")
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        with open(file_path, "rb") as f:
            file_data = f.read()
            message.add_attachment(
                file_data,
                maintype="application",
                subtype="pdf",
                filename=os.path.basename(file_path)
            )

        print("📨 Sending email...")
        await aiosmtplib.send(
            message,
            hostname=os.getenv("SMTP_HOST"),
            port=int(os.getenv("SMTP_PORT")),
            start_tls=True,
            username=os.getenv("SMTP_USERNAME"),
            password=os.getenv("SMTP_PASSWORD"),
        )
        print("✅ Email sent")
    except Exception as e:
        print("❌ Failed to send email:", str(e))
        raise

# --- Load environment variables ---
OPENCAGE_TOKEN = os.getenv("OPENCAGE_API_KEY", "your_opencage_key")
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "your_mapbox_token")
SECRET_KEY = os.getenv("SECRET_KEY", "secret123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

# --- App init ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from chat_gemini import router as chat_router
app.include_router(chat_router)

# --- Auth setup ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- DB setup ---
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with async_session() as session:
        yield session

# --- Models ---
class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="customer")

class RouteHistory(Base):
    __tablename__ = "route_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    distance_km = Column(Float)
    duration_min = Column(Float)
    route = Column(String)
    map_image_base64 = Column(Text)
    summary_image_base64 = Column(Text, nullable=True)


class RouteCreate(BaseModel):
    name: str
    distance_km: float
    duration_min: float
    route: list[str]

# --- Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class User(BaseModel):
    username: str
    full_name: Optional[str] = None

class UserInDB(User):
    hashed_password: str

class UserCreate(BaseModel):
    username: str
    full_name: Optional[str] = None
    password: str
    role: str = "customer"

class Location(BaseModel):
    address: str

class RouteRequest(BaseModel):
    addresses: List[Location]

class RouteSaveRequest(BaseModel):
    name: str
    distance_km: float
    duration_min: float
    route: List[str]

class RouteEmailRequest(BaseModel):
    name: str
    distance_km: float
    duration_min: float
    route: list[str]
    recipient_email: str
    map_image_base64: str
    summary_image_base64: str 

from sqlalchemy import Column, Integer, Float, String, Text, TIMESTAMP, ARRAY
from datetime import datetime

class DeliveryLog(Base):
    __tablename__ = "delivery_logs"

    id = Column(Integer, primary_key=True, index=True)
    pickup_location = Column(Text)
    destination_location = Column(Text)
    stops = Column(ARRAY(Text))
    distance_km = Column(Float)
    duration_min = Column(Float)
    actual_eta_min = Column(Float)
    weather = Column(Text)
    time_of_day = Column(String)
    traffic_level = Column(String)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
from sqlalchemy.orm import Session
from datetime import datetime

def log_delivery(
    db: Session,
    pickup_location: str,
    destination_location: str,
    stops: list,
    distance_km: float,
    duration_min: float,
    actual_eta_min: float,
    weather: str = "clear",
    time_of_day: str = "day",
    traffic_level: str = "moderate"
):
    delivery = DeliveryLog(
        pickup_location=pickup_location,
        destination_location=destination_location,
        stops=stops,
        distance_km=distance_km,
        duration_min=duration_min,
        actual_eta_min=actual_eta_min,
        weather=weather,
        time_of_day=time_of_day,
        traffic_level=traffic_level,
        created_at=datetime.utcnow()
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    return delivery
import joblib
from pydantic import BaseModel

# Load trained model
MODEL_PATH = "eta_model.pkl"
model = joblib.load(MODEL_PATH)

# Define input schema
class ETAPredictRequest(BaseModel):
    distance_km: float
    num_stops: int
    weather: str
    time_of_day: str
    traffic_level: str

@app.post("/predict_eta")
async def predict_eta(data: ETAPredictRequest):
    try:
        # Match features as used during training
        df = {
            "distance_km": [data.distance_km],
            "num_stops": [data.num_stops],
            "weather": [data.weather],
            "time_of_day": [data.time_of_day],
            "traffic_level": [data.traffic_level]
        }

        import pandas as pd
        input_df = pd.DataFrame(df)
        prediction = model.predict(input_df)[0]
        return {"predicted_eta_min": round(prediction, 2)}
    except Exception as e:
        return {"error": str(e)}


# --- Auth Logic ---
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

async def get_user(username: str, db: AsyncSession):
    result = await db.execute(select(UserModel).where(UserModel.username == username))
    return result.scalar_one_or_none()

async def authenticate_user(db: AsyncSession, username: str, password: str):
    user = await get_user(username, db)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if username is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await get_user(token_data.username, db)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# --- Role-Based Access Control ---
async def get_current_user_role(required_roles: list[str]):
    async def role_checker(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            role = payload.get("role")
            if username is None or role is None:
                raise HTTPException(status_code=403, detail="Invalid token or role")
            if role not in required_roles:
                raise HTTPException(status_code=403, detail="Access denied for this role")
        except JWTError:
            raise HTTPException(status_code=403, detail="Could not validate token")

        user = await get_user(username, db)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    return role_checker


# --- Auth Routes ---
# --- Auth Routes ---
@app.post("/signup", response_model=Token)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_user = await get_user(user.username, db)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = pwd_context.hash(user.password)
    new_user = UserModel(
        username=user.username,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=user.role
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    access_token = create_access_token(
        data={"sub": new_user.username, "role": new_user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=User)
async def read_users_me(current_user: UserModel = Depends(get_current_user)):
    return {"username": current_user.username, "full_name": current_user.full_name}

# --- Role-based Access Dependency ---
def get_current_user_role(roles: List[str]):
    async def _get_user(user: UserModel = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Access denied")
        return user
    return _get_user

# Example Usage:
# @app.get("/admin-only")
# async def admin_dashboard(user: UserModel = Depends(get_current_user_role(["admin"]))):
#     return {"msg": "Welcome admin"}

# --- Add 'role' to TokenData if needed in future ---
class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


@app.post("/save_route")
async def save_route(data: RouteSaveRequest, current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        print("➡️ Route save data received:", data)
        route_str = " ➡️ ".join(data.route)
        print("✅ Final route string:", route_str)
        route_entry = RouteHistory(
            user_id=current_user.id,
            name=data.name, 
            distance_km=data.distance_km,
            duration_min=data.duration_min,
            route=route_str
        )
        db.add(route_entry)
        await db.commit()
        await db.refresh(route_entry)
        return {"status": "Route saved successfully", "id": route_entry.id}
    except Exception:
        print("❌ Failed to save route:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal Server Error: Could not save route")
    
@app.get("/admin/drivers", dependencies=[Depends(get_current_user_role(["admin"]))])
async def get_all_driver_routes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserModel.id, UserModel.username)
        .where(UserModel.role == "driver")
    )
    drivers = result.fetchall()

    history = []
    for driver_id, driver_name in drivers:
        res = await db.execute(
            select(RouteHistory).where(RouteHistory.user_id == driver_id)
        )
        routes = res.scalars().all()
        for r in routes:
            history.append({
                "route_id": r.id,
                "driver_id": driver_id,
                "driver_name": driver_name,
                "path": r.route.split(" ➡️ ") if r.route else [],
                "distance_km": r.distance_km,
                "duration_min": r.duration_min,
            })
    return history


class EmailRequest(BaseModel):
    route_id: int
    recipient_email: str

from reportlab.pdfgen import canvas
import tempfile, uuid

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def generate_pdf(route, summary_image_base64=None):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import ImageReader
    from io import BytesIO
    from PIL import Image
    import base64
    import traceback

    pdf_path = "route_summary.pdf"
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    y = height - 50

    # --- Header ---
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "📍 Route Report")
    y -= 30

    # --- Route Info ---
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"🆔 Route ID: {route.id}")
    y -= 20
    c.drawString(50, y, f"📝 Name: {route.name}")
    y -= 20
    c.drawString(50, y, f"📏 Distance: {route.distance_km:.2f} km")
    y -= 20
    c.drawString(50, y, f"⏱️ Duration: {route.duration_min:.2f} minutes")
    y -= 30

    # --- Route Path ---
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y, "🛣️ Route Path:")
    y -= 20
    c.setFont("Helvetica", 12)
    stops = route.route.split("➡")

    for i, stop in enumerate(stops):
        c.drawString(70, y, f"- Stop {i + 1}: {stop.strip()}")
        y -= 20
        if y < 100:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 12)

    # --- Map Image ---
    if route.map_image_base64:
        try:
            c.showPage()
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(width / 2, height - 40, "🗺 Optimized Route Map")

            header, base64_img = route.map_image_base64.split(",", 1)
            img_data = base64.b64decode(base64_img)
            img_stream = BytesIO(img_data)
            pil_image = Image.open(img_stream)

            # ✅ Fix transparency
            if pil_image.mode in ("RGBA", "P"):
                pil_image = pil_image.convert("RGBA")
                white_bg = Image.new("RGBA", pil_image.size, (255, 255, 255, 255))
                pil_image = Image.alpha_composite(white_bg, pil_image)
                pil_image = pil_image.convert("RGB")

            pil_image.thumbnail((500, 350), Image.LANCZOS)
            img_buf = BytesIO()
            pil_image.save(img_buf, format="JPEG", quality=95)
            img_buf.seek(0)

            img_reader = ImageReader(img_buf)
            img_w, img_h = pil_image.size
            img_x = (width - img_w) // 2
            img_y = (height - img_h) // 2
            c.drawImage(img_reader, img_x, img_y, width=img_w, height=img_h)

            print("✅ Map image embedded")
        except Exception as e:
            traceback.print_exc()
            print("❌ Map image error:", e)

    # --- Summary Screenshot ---
    if summary_image_base64:
        try:
            c.showPage()
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(width / 2, height - 40, "🧾 Summary Report")

            header, base64_summary = summary_image_base64.split(",", 1)
            summary_img_data = base64.b64decode(base64_summary)
            summary_stream = BytesIO(summary_img_data)
            summary_pil = Image.open(summary_stream)

            # ✅ Handle transparency
            if summary_pil.mode in ("RGBA", "P"):
                summary_pil = summary_pil.convert("RGBA")
                white_bg = Image.new("RGBA", summary_pil.size, (255, 255, 255, 255))
                summary_pil = Image.alpha_composite(white_bg, summary_pil)
                summary_pil = summary_pil.convert("RGB")

            summary_pil.thumbnail((700, 600), Image.LANCZOS)  
            summary_buf = BytesIO()
            summary_pil.save(summary_buf, format="JPEG", quality=95)
            summary_buf.seek(0)

            summary_reader = ImageReader(summary_buf)
            img_w, img_h = summary_pil.size
            img_x = (width - img_w) // 2
            img_y = (height - img_h) // 2
            c.drawImage(summary_reader, img_x, img_y, width=img_w, height=img_h)

            print("✅ Summary image embedded")
        except Exception as e:
            traceback.print_exc()
            print("❌ Summary image error:", e)

    # --- Footer ---
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, 30, f"Generated • {__import__('datetime').datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
    c.save()
    return pdf_path








@app.post("/email_route/")
async def email_route_pdf(
    data: EmailRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Fetch route
        result = await db.execute(
            select(RouteHistory).where(
                RouteHistory.id == data.route_id,
                RouteHistory.user_id == current_user.id
            )
        )
        route = result.scalar_one_or_none()
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")

        # ✅ Generate PDF with map + summary
        pdf_path = generate_pdf(route, summary_image_base64=route.summary_image_base64)

        # Prepare Email
        msg = EmailMessage()
        msg["Subject"] = "📍 Smart Logistics Route"
        msg["From"] = os.getenv("SMTP_USERNAME")
        msg["To"] = data.recipient_email
        msg.set_content(f"Hi, please find attached the optimized route for '{route.name}'.")

        with open(pdf_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="pdf",
                filename="route_report.pdf"
            )

        # Send Email
        await aiosmtplib.send(
            msg,
            hostname=os.getenv("SMTP_HOST"),
            port=int(os.getenv("SMTP_PORT")),
            start_tls=True,
            username=os.getenv("SMTP_USERNAME"),
            password=os.getenv("SMTP_PASSWORD")
        )

        return {"message": f"PDF sent to {data.recipient_email}"}
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to send email")




# --- Suggest Locations ---
@app.get("/suggest")
async def suggest_locations(query: str):
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    try:
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json?access_token={MAPBOX_TOKEN}&autocomplete=true&limit=5&country=in"
        res = requests.get(url).json()
        return {"suggestions": [f["place_name"] for f in res.get("features", [])]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Suggest failed: {str(e)}")

# --- Route History ---
@app.get("/history")
async def get_route_history(current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RouteHistory)
        .where(RouteHistory.user_id == current_user.id)
        .order_by(desc(RouteHistory.id))
    )
    routes = result.scalars().all()
    return [
        {
            "id": r.id,
            "distance_km": r.distance_km,
            "duration_min": r.duration_min,
            "route": r.route,
        }
        for r in routes
    ]

# --- New Endpoint: OpenCage Geocoding ---
@app.get("/geocode")
async def geocode(address: str = Query(..., min_length=3), current_user: UserModel = Depends(get_current_user)):
    try:
        url = f"https://api.opencagedata.com/geocode/v1/json?q={address}&key={OPENCAGE_TOKEN}&limit=1"
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        if data["results"]:
            location = data["results"][0]["geometry"]
            return {"lat": location["lat"], "lng": location["lng"]}
        else:
            raise HTTPException(status_code=404, detail="Location not found")
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Geocoding service unavailable: {str(e)}")

# --- New Endpoint: Mapbox Traffic-aware Routing ---
@app.get("/api/traffic-route")
async def traffic_route(source: str = Query(...), destination: str = Query(...)):
    try:
        coords = f"{source};{destination}"
        url = (
            f"https://api.mapbox.com/directions/v5/mapbox/driving-traffic/"
            f"{coords}?access_token={MAPBOX_TOKEN}&overview=full&geometries=geojson"
        )
        res = requests.get(url)
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching route: {str(e)}")
    
from email.message import EmailMessage
from email.utils import make_msgid

from fastapi import Depends
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from io import BytesIO
from email.message import EmailMessage
from PIL import Image
import base64, os
import aiosmtplib
from fastapi import HTTPException
from fastapi import status

@app.post("/save_route_with_map")
async def save_route_with_map(
    data: RouteEmailRequest,
    db: AsyncSession = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    try:
        route_str = "➡".join(data.route)
        route_entry = RouteHistory(
            user_id=user.id,
            name=data.name,
            distance_km=data.distance_km,
            duration_min=data.duration_min,
            route=route_str,
            map_image_base64=data.map_image_base64,
            summary_image_base64=data.summary_image_base64 
        )
        db.add(route_entry)
        await db.commit()
        await db.refresh(route_entry)
        return {"id": route_entry.id}

    except Exception as e:
        import traceback
        print("❌ Save route error:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to save route: {str(e)}")



        # Step 2: Generate PDF
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        width, height = letter

        # === HEADER BOX ===
        c.setStrokeColorRGB(0.3, 0.3, 0.3)
        c.setFillColorRGB(0.93, 0.93, 0.93)
        c.rect(40, height - 100, width - 80, 50, fill=1)

        c.setFont("Helvetica-Bold", 18)
        c.setFillColorRGB(0.1, 0.1, 0.1)
        c.drawString(50, height - 80, "📍 Route Report")

        # === Route Info ===
        c.setFont("Helvetica", 12)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(50, height - 130, f"🆔 Route ID: {route_entry.id}")
        c.drawString(50, height - 150, f"📦 Name: {data.name}")
        c.drawString(50, height - 170, f"📏 Distance: {data.distance_km:.2f} km")
        c.drawString(50, height - 190, f"⏱ Duration: {data.duration_min:.2f} minutes")

        # === Route Path ===
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, height - 220, "🗺 Route Path:")
        c.setFont("Helvetica", 11)
        y = height - 240
        for i, point in enumerate(data.route, 1):
            c.drawString(60, y, f"➡ Stop {i}: {point}")
            y -= 18

        # === Footer ===
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawCentredString(width / 2, 20, f"Generated by Smart Logistics • {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # === Map Page ===
        c.showPage()
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, height - 40, "🗺 Optimized Route Map")

        try:
            header, base64_img = data.map_image_base64.split(",", 1)
            img_data = base64.b64decode(base64_img)
            img_stream = BytesIO(img_data)
            pil_image = Image.open(img_stream)

            if pil_image.mode in ("RGBA", "P"):
                pil_image = pil_image.convert("RGB")

            pil_image.thumbnail((500, 350))
            img_buf = BytesIO()
            pil_image.save(img_buf, format="JPEG")
            img_buf.seek(0)

            img_reader = ImageReader(img_buf)

            # Centered image
            img_x = (width - pil_image.width) // 2
            img_y = (height - pil_image.height) // 2
            c.drawImage(img_reader, img_x, img_y, width=pil_image.width, height=pil_image.height)

            print("✅ Image embedded")

        except Exception as e:
            traceback.print_exc()
            print("❌ Image error:", e)

        c.showPage()
        c.save()
        pdf_buffer.seek(0)

        # Step 3: Email PDF
        msg = EmailMessage()
        msg["Subject"] = "📍 Smart Logistics Route"
        msg["From"] = os.getenv("SMTP_USERNAME")
        msg["To"] = data.recipient_email
        msg.set_content(f"Hi, please find the attached optimized route for '{data.name}'.")

        msg.add_attachment(
            pdf_buffer.read(),
            maintype="application",
            subtype="pdf",
            filename="route_report.pdf"
        )

        await aiosmtplib.send(
            msg,
            hostname=os.getenv("SMTP_HOST"),
            port=int(os.getenv("SMTP_PORT")),
            start_tls=True,
            username=os.getenv("SMTP_USERNAME"),
            password=os.getenv("SMTP_PASSWORD")
        )

        print("✅ Email sent")

        # ✅ Always return JSON
        return {"id": route_entry.id}

    except Exception as e:
        traceback.print_exc()
        print("❌ Error while saving/emailing route:", str(e))
        raise HTTPException(status_code=500, detail="Failed to save and email route.")

# --- OpenAPI Customization ---
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Smart Logistics API",
        version="1.0.0",
        description="Smart Logistics Route Optimizer with JWT Authentication",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", []).append({"BearerAuth": []})

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# --- Run once to create tables ---
import asyncio
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# asyncio.run(create_tables())
# --- Run once to create tables ---
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


