"""
Configuration Module - Centralized configuration constants
Author: KiddoTrack-Lite Team
Purpose: Centralized configuration management for all components
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class LoggerConfig:
    """Configuration for the audit logger."""
    buffer_size: int = 50
    max_file_size: int = 5 * 1024 * 1024  # 5MB
    max_cache_size: int = 1000
    log_rotation_enabled: bool = True
    log_directory: str = "data"
    log_filename: str = "audit_log.jsonl"


@dataclass
class SimulatorConfig:
    """Configuration for the GPS simulator."""
    home_lat: float = 40.7128  # Default: New York City
    home_lon: float = -74.0060
    update_frequency: float = 1.0  # Hz
    max_wander_distance: float = 2000.0  # meters
    panic_probability: float = 0.01  # 1% chance per update
    thread_join_timeout: float = 2.0  # seconds


@dataclass
class GeofenceConfig:
    """Configuration for geofencing."""
    default_radius: float = 1000.0  # meters
    earth_radius: float = 6371000  # meters
    alert_cooldown: float = 30.0  # seconds between alerts


@dataclass
class APIConfig:
    """Configuration for the API server."""
    host: str = "localhost"
    port: int = 8000
    title: str = "KiddoTrack-Lite API"
    description: str = "Child safety monitoring system API"
    version: str = "1.0.0"
    websocket_max_connections: int = 100
    request_timeout: float = 30.0  # seconds


@dataclass
class UIConfig:
    """Configuration for the user interface."""
    update_frequency: float = 1.0  # Hz
    map_size: int = 20
    max_recent_alerts: int = 5
    map_scale_factor: int = 10000  # For coordinate conversion
    geofence_display_radius: int = 8  # pixels


@dataclass
class SecurityConfig:
    """Configuration for security settings."""
    max_log_file_age_days: int = 30
    max_archived_logs: int = 10
    enable_cors: bool = True
    cors_allow_origins: list = None
    
    def __post_init__(self):
        if self.cors_allow_origins is None:
            self.cors_allow_origins = ["*"]


class Config:
    """Main configuration class that aggregates all config sections."""
    
    def __init__(self):
        self.logger = LoggerConfig()
        self.simulator = SimulatorConfig()
        self.geofence = GeofenceConfig()
        self.api = APIConfig()
        self.ui = UIConfig()
        self.security = SecurityConfig()
        
        # Load from environment variables if available
        self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Logger config
        try:
            if os.getenv("LOGGER_BUFFER_SIZE"):
                self.logger.buffer_size = int(os.getenv("LOGGER_BUFFER_SIZE"))
        except (ValueError, TypeError):
            pass  # Use default value
            
        try:
            if os.getenv("LOGGER_MAX_FILE_SIZE"):
                self.logger.max_file_size = int(os.getenv("LOGGER_MAX_FILE_SIZE"))
        except (ValueError, TypeError):
            pass
            
        if os.getenv("LOG_DIRECTORY"):
            self.logger.log_directory = os.getenv("LOG_DIRECTORY")
        
        # Simulator config
        try:
            if os.getenv("HOME_LATITUDE"):
                self.simulator.home_lat = float(os.getenv("HOME_LATITUDE"))
        except (ValueError, TypeError):
            pass
            
        try:
            if os.getenv("HOME_LONGITUDE"):
                self.simulator.home_lon = float(os.getenv("HOME_LONGITUDE"))
        except (ValueError, TypeError):
            pass
            
        try:
            if os.getenv("UPDATE_FREQUENCY"):
                self.simulator.update_frequency = float(os.getenv("UPDATE_FREQUENCY"))
        except (ValueError, TypeError):
            pass
            
        try:
            if os.getenv("MAX_WANDER_DISTANCE"):
                self.simulator.max_wander_distance = float(os.getenv("MAX_WANDER_DISTANCE"))
        except (ValueError, TypeError):
            pass
        
        # API config
        if os.getenv("API_HOST"):
            self.api.host = os.getenv("API_HOST")
            
        try:
            if os.getenv("API_PORT"):
                self.api.port = int(os.getenv("API_PORT"))
        except (ValueError, TypeError):
            pass
        
        # Geofence config
        try:
            if os.getenv("DEFAULT_GEOFENCE_RADIUS"):
                self.geofence.default_radius = float(os.getenv("DEFAULT_GEOFENCE_RADIUS"))
        except (ValueError, TypeError):
            pass
    
    def get_log_file_path(self) -> str:
        """Get the full path to the log file."""
        return os.path.join(self.logger.log_directory, self.logger.log_filename)
    
    def get_api_url(self) -> str:
        """Get the full API URL."""
        return f"http://{self.api.host}:{self.api.port}"


# Global configuration instance
config = Config()


# Convenience functions for backwards compatibility
def get_config() -> Config:
    """Get the global configuration instance."""
    return config


def get_simulator_config() -> SimulatorConfig:
    """Get simulator configuration."""
    return config.simulator


def get_logger_config() -> LoggerConfig:
    """Get logger configuration."""
    return config.logger


def get_api_config() -> APIConfig:
    """Get API configuration."""
    return config.api


def get_geofence_config() -> GeofenceConfig:
    """Get geofence configuration."""
    return config.geofence


def get_ui_config() -> UIConfig:
    """Get UI configuration."""
    return config.ui 