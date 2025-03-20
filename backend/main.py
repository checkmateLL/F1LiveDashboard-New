from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
import uvicorn

from backend.routes import router, get_data_service
from backend.data_service import F1DataService
from backend.session_id_fix import patch_data_service
from backend.error_handling import F1DashboardError

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("f1dashboard.log")
    ]
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="F1 Data API",
    description="API for accessing Formula 1 data",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handlers
@app.exception_handler(F1DashboardError)
async def handle_f1_dashboard_error(request, exc: F1DashboardError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )

@app.exception_handler(Exception)
async def handle_general_exception(request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "details": str(exc)}
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    app.state.data_service = F1DataService()
    logger.info(f"Startup: Using SQLite DB at {app.state.data_service.sqlite_path}")
    patch_data_service()
    logger.info("Startup: Data service initialized")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, "data_service"):
        app.state.data_service.close()
        logger.info("Shutdown: Data service closed.")

# Override the get_data_service dependency
def get_data_service_override():
    return app.state.data_service

# Override the get_data_service in the router
app.dependency_overrides[get_data_service] = get_data_service_override

# Include the router
app.include_router(router)

# Main entry point
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)