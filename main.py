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
from dotenv import load_dotenv
from difflib import SequenceMatcher
from dotenv import load_dotenv
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
print("📧 SMTP_HOST:", os.getenv("SMTP_HOST"))
print("📧 SMTP_PORT:", os.getenv("SMTP_PORT"))
print("📧 SMTP_USERNAME:", os.getenv("SMTP_USERNAME"))
print("📧 SMTP_PASSWORD:", os.getenv("SMTP_PASSWORD"))


# --- Load environment variables ---
load_dotenv()
OPENCAGE_TOKEN = os.getenv("OPENCAGE_API_KEY", "your_opencage_key")
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "your_mapbox_token")
SECRET_KEY = os.getenv("SECRET_KEY", "secret123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
print("SMTP_HOST:", os.getenv("SMTP_HOST"))
print("SMTP_USERNAME:", os.getenv("SMTP_USERNAME"))
# --- App init ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class RouteHistory(Base):
    __tablename__ = "route_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)  # ✅ Add this line
    distance_km = Column(Float)
    duration_min = Column(Float)
    route = Column(String)

class RouteCreate(BaseModel):
    name: str  # ✅ MUST include this!
    distance_km: float
    duration_min: float
    route: list[str]

# --- Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    full_name: Optional[str] = None

class UserInDB(User):
    hashed_password: str

class UserCreate(BaseModel):
    username: str
    full_name: Optional[str] = None
    password: str

class Location(BaseModel):
    address: str

class RouteRequest(BaseModel):
    addresses: List[Location]

class RouteSaveRequest(BaseModel):
    name: str
    distance_km: float
    duration_min: float
    route: List[str]


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
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token_data = TokenData(username=username)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await get_user(token_data.username, db)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# --- Auth Routes ---
@app.post("/signup")
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_user = await get_user(user.username, db)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = pwd_context.hash(user.password)
    new_user = UserModel(username=user.username, full_name=user.full_name, hashed_password=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"message": "User created"}

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=User)
async def read_users_me(current_user: UserModel = Depends(get_current_user)):
    return {"username": current_user.username, "full_name": current_user.full_name}

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

class EmailRequest(BaseModel):
    route_id: int
    recipient_email: str

from reportlab.pdfgen import canvas
import tempfile, uuid

def generate_pdf(route):
    pdf_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.pdf")
    c = canvas.Canvas(pdf_path)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 800, "Route Report")
    c.setFont("Helvetica", 12)
    c.drawString(100, 770, f"Route ID: {route.id}")
    c.drawString(100, 750, f"Path: {route.route}")
    c.drawString(100, 730, f"Distance: {route.distance_km} km")
    c.drawString(100, 710, f"Duration: {route.duration_min} mins")
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
        result = await db.execute(select(RouteHistory).where(
            RouteHistory.id == data.route_id,
            RouteHistory.user_id == current_user.id
        ))
        route = result.scalar_one_or_none()

        if not route:
            raise HTTPException(status_code=404, detail="Route not found")

        # ✅ Generate PDF with ReportLab
        pdf_path = generate_pdf(route)

        # 📧 Send email
        await send_email_with_attachment(
            to_email=data.recipient_email,
            subject="Shared Route PDF",
            body=f"Hi, please find attached the route report from user {current_user.username}.",
            file_path=pdf_path
        )

        return {"message": f"PDF sent to {data.recipient_email}"}
    except Exception:
        print("❌ Email sending error:")
        print(traceback.format_exc())
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

