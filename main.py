from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import connect_db, close_db, get_settings
from routers.auth import router as auth_router
from routers.profiles import router as profiles_router
from routers.exam_sessions import router as sessions_router
from routers.admin import router as admin_router
from routers.vouchers_certs import vouchers_router, certs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="Nemo Online Exam API",
    description="Python + MongoDB backend for Nemo Online Exam platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
settings = get_settings()
origins = [o.strip() for o in settings.allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(sessions_router)
app.include_router(admin_router)
app.include_router(vouchers_router)
app.include_router(certs_router)


@app.get("/")
async def root():
    return {"status": "ok", "service": "Nemo Online Exam API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
