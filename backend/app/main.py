import json
import sqlite3
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import router as api_v1_router
from app.api.v1.telegram import router as telegram_router
from app.api.v1.textbee import router as textbee_router
from app.core.config import settings
from app.core.ws import manager
from app.services.triage import DB_PATH, get_all_clusters

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend service for Krisis AI Damage Mapper",
    version="1.0.0"
)


@app.on_event("startup")
def startup_db_migration():
    """Ensure database schema has all required columns on startup."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("ALTER TABLE reports ADD COLUMN phash TEXT;")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
        finally:
            conn.close()
    except Exception as e:
        print(f"[Startup] Database migration warning: {e}")


# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 endpoints
app.include_router(api_v1_router, prefix=settings.API_V1_STR)
app.include_router(telegram_router, prefix=f"{settings.API_V1_STR}/telegram", tags=["Telegram"])
app.include_router(textbee_router, prefix=f"{settings.API_V1_STR}/textbee", tags=["Textbee"])


@app.websocket("/ws/incidents")
async def websocket_incidents_endpoint(websocket: WebSocket):
    """Real-time WebSocket endpoint for incident cluster updates."""
    await manager.connect(websocket)
    try:
        # Send initial snapshot of all clusters to newly connected client
        initial_clusters = get_all_clusters()
        await manager.send_json(websocket, {
            "type": "INITIAL_STATE",
            "incidents": initial_clusters
        })
        while True:
            # Keep connection alive and accept ping/pong or client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "krisis-backend"}
