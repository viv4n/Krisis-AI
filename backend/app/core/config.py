from pydantic import BaseModel


class Settings(BaseModel):
    PROJECT_NAME: str = "Krisis AI - Damage Mapper"
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "*"]
    
    # Thresholds
    SPATIAL_CLUSTER_RADIUS_METERS: float = 50.0
    VISUAL_CONFIDENCE_THRESHOLD: float = 0.50
    DEEPFAKE_THRESHOLD: float = 0.85
    ROUTE_PROXIMITY_THRESHOLD_METERS: float = 75.0


settings = Settings()
