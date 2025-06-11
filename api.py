"""
API Module - FastAPI routes & schemas
Author: Bhushan Chandrakant
Purpose: REST API endpoints and data schemas for KiddoTrack-Lite
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
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
    timestamp: Optional[str] = Field(None, description="ISO timestamp")

    @validator('latitude')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v

    @validator('longitude')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v


class GeofenceModel(BaseModel):
    """Geofence data model for API."""
    center: LocationModel
    radius_meters: float = Field(..., gt=0, description="Radius in meters")

    @validator('radius_meters')
    def validate_radius(cls, v):
        if v <= 0:
            raise ValueError('Radius must be positive')
        return v


class EmergencyStateModel(BaseModel):
    """Emergency state model for API."""
    state: str = Field(..., description="Emergency state")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class AlertModel(BaseModel):
    """Alert data model for API."""
    type: str = Field(..., description="Alert type (geofence_exit, panic, etc.)")
    message: str = Field(..., description="Alert message")
    location: Optional[LocationModel] = Field(None, description="Location when alert occurred")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    severity: str = Field(default="medium", description="Alert severity")


class StatusModel(BaseModel):
    """System status model for API."""
    is_running: bool
    current_location: Optional[LocationModel]
    emergency_state: str
    geofence_active: bool
    last_update: str


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
        config = SimulatorConfig()
        simulator = GPSSimulator(config)
        
        # Initialize default geofence
        geofence = GeofenceChecker.create_default_geofence(
            config.home_lat, config.home_lon, 1000
        )
        
        # Initialize audit logger with optimizations
        audit_logger = AuditLogger("data/audit_log.jsonl", buffer_size=50, max_file_size=5*1024*1024)
        
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
        is_safe, distance = check_location_safety(location, geofence)
        
        if not is_safe:
            alert = AlertModel(
                type="geofence_exit",
                message=f"Child has left safe zone! Distance: {distance:.1f}m",
                location=LocationModel(
                    latitude=location.latitude,
                    longitude=location.longitude,
                    timestamp=location.timestamp
                ),
                severity="high"
            )
            
            # Log alert
            if audit_logger:
                audit_logger.log_alert(alert.dict())
            
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
        message=f"Emergency state changed to: {state.value}",
        severity="critical" if state == EmergencyState.PANIC else "medium"
    )
    
    # Log alert
    if audit_logger:
        audit_logger.log_alert(alert.dict())
    
    # Notify WebSocket clients
    await broadcast_alert(alert)


async def broadcast_alert(alert: AlertModel):
    """Broadcast alert to all WebSocket connections with thread safety."""
    message = alert.dict()
    
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
    
    return StatusModel(
        is_running=current_simulator._running,
        current_location=LocationModel(
            latitude=current_location.latitude,
            longitude=current_location.longitude,
            timestamp=current_location.timestamp
        ) if current_location else None,
        emergency_state=current_simulator.get_emergency_state().value,
        geofence_active=current_geofence is not None,
        last_update=datetime.now().isoformat()
    )


@app.get("/location", response_model=LocationModel)
async def get_current_location():
    """Get current child location."""
    global simulator
    
    if not simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")
    
    location = simulator.get_current_location()
    return LocationModel(
        latitude=location.latitude,
        longitude=location.longitude,
        timestamp=location.timestamp
    )


@app.post("/location", response_model=LocationModel)
async def set_location(location: LocationModel):
    """Manually set child location."""
    global simulator, audit_logger
    
    if not simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")
    
    # Set location in simulator
    simulator.set_location(location.latitude, location.longitude)
    
    # Log manual location set
    if audit_logger:
        audit_logger.log_location(Location(
            latitude=location.latitude,
            longitude=location.longitude,
            timestamp=location.timestamp or datetime.now().isoformat()
        ))
    
    return location


@app.get("/geofence", response_model=GeofenceModel)
async def get_geofence():
    """Get current geofence configuration."""
    global geofence
    
    if not geofence:
        raise HTTPException(status_code=404, detail="No geofence configured")
    
    return GeofenceModel(
        center=LocationModel(
            latitude=geofence.center.latitude,
            longitude=geofence.center.longitude
        ),
        radius_meters=geofence.radius_meters
    )


@app.post("/geofence", response_model=GeofenceModel)
async def set_geofence(geofence_data: GeofenceModel):
    """Set the geofence."""
    try:
        global geofence
        if not geofence:
            raise HTTPException(status_code=503, detail="Geofence not initialized")
        
        geofence = Geofence(
            center=Location(
                latitude=geofence_data.center.latitude,
                longitude=geofence_data.center.longitude
            ),
            radius_meters=geofence_data.radius_meters
        )
        
        if audit_logger:
            audit_logger.log_geofence_update(geofence_data.dict())
        
        return geofence_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting geofence: {str(e)}")


@app.post("/panic", response_model=EmergencyStateModel)
async def trigger_panic():
    """Manually trigger panic state."""
    global simulator, audit_logger
    
    if not simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")
    
    simulator.trigger_panic()
    state = simulator.get_emergency_state()
    
    # Log panic trigger
    if audit_logger:
        audit_logger.log_panic_trigger()
    
    return EmergencyStateModel(state=state.value)


@app.post("/panic/resolve", response_model=EmergencyStateModel)
async def resolve_panic():
    """Resolve panic state."""
    global simulator, audit_logger
    
    if not simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")
    
    simulator.resolve_panic()
    state = simulator.get_emergency_state()
    
    # Log panic resolution
    if audit_logger:
        audit_logger.log_panic_resolution()
    
    return EmergencyStateModel(state=state.value)


@app.post("/simulator/start")
async def start_simulator():
    """Start the GPS simulator with thread safety."""
    with _global_state_lock:
        current_simulator = simulator
    
    if not current_simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")
    
    current_simulator.start()
    return {"message": "Simulator started"}


@app.post("/simulator/stop")
async def stop_simulator():
    """Stop the GPS simulator with thread safety."""
    with _global_state_lock:
        current_simulator = simulator
    
    if not current_simulator:
        raise HTTPException(status_code=503, detail="Simulator not initialized")
    
    current_simulator.stop()
    return {"message": "Simulator stopped"}


@app.get("/alerts", response_model=List[AlertModel])
async def get_recent_alerts(limit: int = 10):
    """Get recent alerts."""
    try:
        if not audit_logger:
            raise HTTPException(status_code=503, detail="Logger not initialized")
        
        alerts = audit_logger.get_recent_alerts(limit)
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {str(e)}")


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    try:
        await websocket.accept()
        
        # Add to connections list with thread safety
        with _websocket_lock:
            websocket_connections.append(websocket)
        
        try:
            while True:
                # Keep connection alive and handle client messages
                data = await websocket.receive_text()
                # Echo back for now
                await websocket.send_text(f"Message received: {data}")
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            # Remove from connections list with thread safety
            with _websocket_lock:
                if websocket in websocket_connections:
                    websocket_connections.remove(websocket)
    except Exception as e:
        print(f"Error setting up WebSocket: {e}")
        with _websocket_lock:
            if websocket in websocket_connections:
                websocket_connections.remove(websocket)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    global simulator, geofence, audit_logger
    
    return {
        "status": "healthy",
        "simulator_initialized": simulator is not None,
        "geofence_configured": geofence is not None,
        "audit_logger_initialized": audit_logger is not None,
        "active_websocket_connections": len(websocket_connections)
    }


# Import helper function
from geofence import check_location_safety 