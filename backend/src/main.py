from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.src.config import settings
from backend.src.database import get_db_connection
from backend.src.routes import stations, consumption, sessions, losses
from backend.src.services.data_processor import process_csv_data

app = FastAPI(
    title="Charging Station Loss Analysis API",
    description="API for analyzing energy losses in EV charging stations",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stations.router)
app.include_router(consumption.router)
app.include_router(sessions.router)
app.include_router(losses.router)

@app.on_event("startup")
async def startup_event():
    """Check database connection on startup"""
    print("🚀 Starting Charging Station Loss Analysis API...")
    try:
        connection = get_db_connection()
        connection.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

@app.get("/")
async def root():
    """API root endpoint with available endpoints"""
    return {
        "message": "Charging Station Loss Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "stations": "/api/stations",
            "consumption": "/api/consumption",
            "sessions": "/api/sessions",
            "losses": "/api/losses",
            "process_data": "/api/process-data",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        connection = get_db_connection()
        connection.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

@app.post("/api/process-data")
async def process_data():
    """Process CSV files and insert data into database"""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        consumption_count, session_count = process_csv_data(cursor, connection)

        return {
            "success": True,
            "message": "Data processed successfully",
            "consumption_records": consumption_count,
            "session_records": session_count
        }

    except FileNotFoundError as e:
        return {
            "success": False,
            "error": f"CSV file not found: {str(e)}"
        }
    except Exception as e:
        connection.rollback()
        print(f"Error processing data: {e}")
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )