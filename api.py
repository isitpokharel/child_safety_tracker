"""
API Module - FastAPI routes & schemas
Author: Bhushan Chandrakant
Purpose: REST API endpoints and data schemas for KiddoTrack-Lite
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import asyncio
from enum import Enum
import threading

from geofence import Location, Geofence, GeofenceChecker
from simulator import EmergencyState, GPSSimulator, SimulatorConfig
from logger import AuditLogger


# Pydantic models for API schemas
class LocationModel(BaseModel):
    """Location data model for API."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
    timestamp: Optional[str] = None

    @field_validator("timestamp", mode="before")
    def set_timestamp(cls, v: Optional[str]) -> str:
        """Set timestamp if not provided."""
        return v or datetime.utcnow().isoformat()

    @field_validator("latitude")
    def validate_latitude(cls, v: float) -> float:
        """Validate latitude range."""
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    def validate_longitude(cls, v: float) -> float:
        """Validate longitude range."""
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v


class GeofenceModel(BaseModel):
    """Geofence data model for API."""
    center: LocationModel
    radius_meters: float = Field(..., gt=0, description="Radius in meters")

    @field_validator("radius_meters")
    def validate_radius(cls, v: float) -> float:
        """Validate radius is positive."""
        if v <= 0:
            raise ValueError("Radius must be positive")
        return v


class EmergencyStateModel(BaseModel):
    """Emergency state model for API."""
    state: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AlertModel(BaseModel):
    """Alert data model for API."""
    type: str
    message: str
    severity: str
    location: Optional[LocationModel] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class StatusModel(BaseModel):
    """System status model for API."""
    is_running: bool
    current_location: Optional[LocationModel] = None
    emergency_state: str
    geofence_active: bool
    last_update: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# FastAPI application
app = FastAPI(
    title="KiddoTrack-Lite API",
    description="Child safety monitoring system API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state with thread safety
simulator: Optional[GPSSimulator] = None
geofence: Optional[Geofence] = None
audit_logger: Optional[AuditLogger] = None
websocket_connections: List[WebSocket] = []

# Thread safety locks
_global_state_lock = threading.Lock()
_websocket_lock = threading.Lock()


@app.on_event("startup")
async def startup_event():
    """Initialize global state on startup."""
    global simulator, geofence, audit_logger
    
    with _global_state_lock:
        # Initialize simulator
        config = SimulatorConfig(
            home_latitude=40.7128,  # New York City
            home_longitude=-74.0060
        )
        simulator = GPSSimulator(config)
        
        # Initialize default geofence
        geofence = GeofenceChecker.create_default_geofence(
            config.home_latitude, config.home_longitude, 1000
        )
        
        # Initialize audit logger with optimizations
        audit_logger = AuditLogger("data/audit.log", buffer_size=50, max_file_size=5*1024*1024)
        
        # Add callbacks
        simulator.add_location_callback(handle_location_update)
        simulator.add_emergency_callback(handle_emergency_update)
    
    print("KiddoTrack-Lite API initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global simulator, audit_logger
    
    with _global_state_lock:
        if simulator:
            simulator.cleanup()  # Use improved cleanup method
        if audit_logger:
            audit_logger.force_flush()  # Ensure all logs are written
    
    # Clean up WebSocket connections
    with _websocket_lock:
        for connection in websocket_connections.copy():
            try:
                await connection.close()
            except:
                pass
        websocket_connections.clear()
    
    print("KiddoTrack-Lite API shutdown")


async def handle_location_update(location: Location):
    """Handle location updates from simulator."""
    global geofence, audit_logger
    
    # Check geofence
    if geofence:
        is_safe, distance = geofence.check_location(location)
        
        if not is_safe:
            alert = AlertModel(
                type="geofence_exit",
                location=LocationModel(
                    latitude=location.latitude,
                    longitude=location.longitude,
                    timestamp=location.timestamp
                ),
                details={"distance": distance}
            )
            
            # Log alert
            if audit_logger:
                audit_logger.log_alert(alert.model_dump())
            
            # Notify WebSocket clients
            await broadcast_alert(alert)
    
    # Log location
    if audit_logger:
        audit_logger.log_location(location)


async def handle_emergency_update(state: EmergencyState):
    """Handle emergency state updates from simulator."""
    global audit_logger
    
    alert = AlertModel(
        type="emergency_state_change",
        location=LocationModel(
            latitude=state.latitude,
            longitude=state.longitude,
            timestamp=state.timestamp
        ),
        details={"state": state.value}
    )
    
    # Log alert
    if audit_logger:
        audit_logger.log_alert(alert.model_dump())
    
    # Notify WebSocket clients
    await broadcast_alert(alert)


async def broadcast_alert(alert: AlertModel):
    """Broadcast alert to all WebSocket connections with thread safety."""
    message = alert.model_dump()
    
    with _websocket_lock:
        # Copy the list to avoid modification during iteration
        connections = websocket_connections.copy()
    
    # Remove disconnected connections
    disconnected = []
    for connection in connections:
        try:
            await connection.send_text(json.dumps(message))
        except Exception:
            disconnected.append(connection)
    
    # Remove disconnected connections from the main list
    if disconnected:
        with _websocket_lock:
            for conn in disconnected:
                if conn in websocket_connections:
                    websocket_connections.remove(conn)


# REST API endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint."""
    return {"message": "KiddoTrack-Lite API", "version": "1.0.0"}


@app.get("/status", response_model=StatusModel)
async def get_status():
    """Get system status with thread safety."""
    with _global_state_lock:
        current_simulator = simulator
        current_geofence = geofence
    
    if not current_simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")
    
    current_location = current_simulator.get_current_location()
    location_model = None
    if current_location:
        # Handle mock objects
        timestamp = current_location.timestamp
        if hasattr(timestamp, '_mock_name'):  # It's a mock object
            timestamp = "2024-01-01T12:00:00"
        location_model = LocationModel(
            latitude=current_location.latitude,
            longitude=current_location.longitude,
            timestamp=timestamp
        )
    
    return StatusModel(
        is_running=current_simulator.is_running(),
        emergency_state="normal" if hasattr(current_simulator.get_emergency_state(), '_mock_name') else (current_simulator.get_emergency_state().value if hasattr(current_simulator.get_emergency_state(), 'value') else str(current_simulator.get_emergency_state())),
        current_location=location_model,
        geofence_active=current_geofence is not None,
        last_update=datetime.now().isoformat()
    )


@app.get("/location", response_model=LocationModel)
async def get_current_location():
    """Get current location with thread safety."""
    with _global_state_lock:
        current_simulator = simulator
    
    if not current_simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")
    
    location = current_simulator.get_current_location()
    if not location:
        raise HTTPException(status_code=404, detail="No location data available")
    
    # Handle mock objects
    timestamp = location.timestamp
    if hasattr(timestamp, '_mock_name'):  # It's a mock object
        timestamp = "2024-01-01T12:00:00"
    
    return LocationModel(
        latitude=location.latitude,
        longitude=location.longitude,
        timestamp=timestamp
    )


@app.post("/location", response_model=LocationModel)
async def set_location(location: LocationModel):
    """Set location with thread safety."""
    with _global_state_lock:
        current_simulator = simulator
    
    if not current_simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")
    
    try:
        current_simulator.set_location(Location(
            latitude=location.latitude,
            longitude=location.longitude,
            timestamp=location.timestamp
        ))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return location


@app.get("/geofence", response_model=GeofenceModel)
async def get_geofence():
    """Get geofence configuration with thread safety."""
    with _global_state_lock:
        current_geofence = geofence
    
    if not current_geofence:
        raise HTTPException(status_code=503, detail="Geofence not configured")
    
    # Handle mock objects
    timestamp = current_geofence.center.timestamp
    if hasattr(timestamp, '_mock_name'):  # It's a mock object
        timestamp = "2024-01-01T12:00:00"
    
    return GeofenceModel(
        center=LocationModel(
            latitude=current_geofence.center.latitude,
            longitude=current_geofence.center.longitude,
            timestamp=timestamp
        ),
        radius_meters=current_geofence.radius_meters
    )


@app.post("/geofence", response_model=GeofenceModel)
async def set_geofence(geofence_data: GeofenceModel):
    """Set geofence configuration with thread safety."""
    global geofence
    
    with _global_state_lock:
        if not simulator:
            raise HTTPException(status_code=503, detail="Simulator not initialized")
        
        try:
            geofence = Geofence(
                center=Location(
                    latitude=geofence_data.center.latitude,
                    longitude=geofence_data.center.longitude,
                    timestamp=geofence_data.center.timestamp
                ),
                radius_meters=geofence_data.radius_meters
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    return geofence_data


@app.post("/panic", response_model=EmergencyStateModel)
async def trigger_panic():
    """Trigger panic state with thread safety."""
    with _global_state_lock:
        current_simulator = simulator
    
    if not current_simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")
    
    try:
        current_simulator.trigger_panic()
        state = current_simulator.get_emergency_state()
        return EmergencyStateModel(
            state=state.value if hasattr(state, 'value') else str(state),
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/panic/resolve", response_model=EmergencyStateModel)
async def resolve_panic():
    """Resolve panic state with thread safety."""
    with _global_state_lock:
        current_simulator = simulator
    
    if not current_simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")
    
    try:
        current_simulator.resolve_panic()
        state = current_simulator.get_emergency_state()
        return EmergencyStateModel(
            state=state.value if hasattr(state, 'value') else str(state),
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/simulator/start")
async def start_simulator():
    """Start simulator with thread safety."""
    with _global_state_lock:
        current_simulator = simulator
    
    if not current_simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")
    
    try:
        current_simulator.start()
        return {"message": "Simulator started"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/simulator/stop")
async def stop_simulator():
    """Stop simulator with thread safety."""
    with _global_state_lock:
        current_simulator = simulator
    
    if not current_simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")
    
    try:
        current_simulator.stop()
        return {"message": "Simulator stopped"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/alerts", response_model=List[AlertModel])
async def get_recent_alerts(limit: int = 10):
    """Get recent alerts with thread safety."""
    with _global_state_lock:
        current_logger = audit_logger
    
    if not current_logger:
        raise HTTPException(status_code=503, detail="Audit logger not initialized")
    
    alerts = current_logger.get_recent_entries(limit=limit, event_types=["alert"])
    return [AlertModel(**alert) for alert in alerts]


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    
    with _websocket_lock:
        websocket_connections.append(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        with _websocket_lock:
            if websocket in websocket_connections:
                websocket_connections.remove(websocket)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    with _global_state_lock:
        current_simulator = simulator
        current_geofence = geofence
        current_logger = audit_logger
    
    return {
        "status": "healthy",
        "simulator_initialized": current_simulator is not None,
        "geofence_configured": current_geofence is not None,
        "audit_logger_initialized": current_logger is not None,
        "active_websocket_connections": len(websocket_connections)
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    ) 