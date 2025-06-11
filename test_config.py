"""
Unit Tests for Configuration Module
Author: KiddoTrack-Lite Team
Purpose: Configuration management and environment variable testing
"""

import pytest
import os
import tempfile
from unittest.mock import patch
from config import (
    LoggerConfig, SimulatorConfig, GeofenceConfig, APIConfig, UIConfig, SecurityConfig,
    Config, get_config, get_simulator_config, get_logger_config, get_api_config,
    get_geofence_config, get_ui_config
)


class TestLoggerConfig:
    """Test cases for LoggerConfig dataclass."""
    
    def test_default_logger_config(self):
        """Test default logger configuration values."""
        config = LoggerConfig()
        
        assert config.buffer_size == 50
        assert config.max_file_size == 5 * 1024 * 1024  # 5MB
        assert config.max_cache_size == 1000
        assert config.log_rotation_enabled is True
        assert config.log_directory == "data"
        assert config.log_filename == "audit_log.jsonl"
    
    def test_custom_logger_config(self):
        """Test custom logger configuration values."""
        config = LoggerConfig(
            buffer_size=100,
            max_file_size=10 * 1024 * 1024,
            max_cache_size=2000,
            log_rotation_enabled=False,
            log_directory="logs",
            log_filename="custom.jsonl"
        )
        
        assert config.buffer_size == 100
        assert config.max_file_size == 10 * 1024 * 1024
        assert config.max_cache_size == 2000
        assert config.log_rotation_enabled is False
        assert config.log_directory == "logs"
        assert config.log_filename == "custom.jsonl"


class TestSimulatorConfig:
    """Test cases for SimulatorConfig dataclass."""
    
    def test_default_simulator_config(self):
        """Test default simulator configuration values."""
        config = SimulatorConfig()
        
        assert config.home_lat == 40.7128  # NYC
        assert config.home_lon == -74.0060
        assert config.update_frequency == 1.0
        assert config.max_wander_distance == 2000.0
        assert config.panic_probability == 0.01
        assert config.thread_join_timeout == 2.0
    
    def test_custom_simulator_config(self):
        """Test custom simulator configuration values."""
        config = SimulatorConfig(
            home_lat=51.5074,  # London
            home_lon=-0.1278,
            update_frequency=2.0,
            max_wander_distance=1000.0,
            panic_probability=0.05,
            thread_join_timeout=5.0
        )
        
        assert config.home_lat == 51.5074
        assert config.home_lon == -0.1278
        assert config.update_frequency == 2.0
        assert config.max_wander_distance == 1000.0
        assert config.panic_probability == 0.05
        assert config.thread_join_timeout == 5.0


class TestGeofenceConfig:
    """Test cases for GeofenceConfig dataclass."""
    
    def test_default_geofence_config(self):
        """Test default geofence configuration values."""
        config = GeofenceConfig()
        
        assert config.default_radius == 1000.0
        assert config.earth_radius == 6371000
        assert config.alert_cooldown == 30.0
    
    def test_custom_geofence_config(self):
        """Test custom geofence configuration values."""
        config = GeofenceConfig(
            default_radius=500.0,
            earth_radius=6371001,  # Slightly different
            alert_cooldown=60.0
        )
        
        assert config.default_radius == 500.0
        assert config.earth_radius == 6371001
        assert config.alert_cooldown == 60.0


class TestAPIConfig:
    """Test cases for APIConfig dataclass."""
    
    def test_default_api_config(self):
        """Test default API configuration values."""
        config = APIConfig()
        
        assert config.host == "localhost"
        assert config.port == 8000
        assert config.title == "KiddoTrack-Lite API"
        assert config.description == "Child safety monitoring system API"
        assert config.version == "1.0.0"
        assert config.websocket_max_connections == 100
        assert config.request_timeout == 30.0
    
    def test_custom_api_config(self):
        """Test custom API configuration values."""
        config = APIConfig(
            host="0.0.0.0",
            port=9000,
            title="Custom API",
            description="Custom description",
            version="2.0.0",
            websocket_max_connections=200,
            request_timeout=60.0
        )
        
        assert config.host == "0.0.0.0"
        assert config.port == 9000
        assert config.title == "Custom API"
        assert config.description == "Custom description"
        assert config.version == "2.0.0"
        assert config.websocket_max_connections == 200
        assert config.request_timeout == 60.0


class TestUIConfig:
    """Test cases for UIConfig dataclass."""
    
    def test_default_ui_config(self):
        """Test default UI configuration values."""
        config = UIConfig()
        
        assert config.update_frequency == 1.0
        assert config.map_size == 20
        assert config.max_recent_alerts == 5
        assert config.map_scale_factor == 10000
        assert config.geofence_display_radius == 8
    
    def test_custom_ui_config(self):
        """Test custom UI configuration values."""
        config = UIConfig(
            update_frequency=0.5,
            map_size=30,
            max_recent_alerts=10,
            map_scale_factor=5000,
            geofence_display_radius=12
        )
        
        assert config.update_frequency == 0.5
        assert config.map_size == 30
        assert config.max_recent_alerts == 10
        assert config.map_scale_factor == 5000
        assert config.geofence_display_radius == 12


class TestSecurityConfig:
    """Test cases for SecurityConfig dataclass."""
    
    def test_default_security_config(self):
        """Test default security configuration values."""
        config = SecurityConfig()
        
        assert config.max_log_file_age_days == 30
        assert config.max_archived_logs == 10
        assert config.enable_cors is True
        assert config.cors_allow_origins == ["*"]
    
    def test_custom_security_config(self):
        """Test custom security configuration values."""
        config = SecurityConfig(
            max_log_file_age_days=60,
            max_archived_logs=20,
            enable_cors=False,
            cors_allow_origins=["https://example.com"]
        )
        
        assert config.max_log_file_age_days == 60
        assert config.max_archived_logs == 20
        assert config.enable_cors is False
        assert config.cors_allow_origins == ["https://example.com"]
    
    def test_security_config_post_init(self):
        """Test SecurityConfig post_init behavior."""
        # Default case - None should become ["*"]
        config = SecurityConfig()
        assert config.cors_allow_origins == ["*"]
        
        # Custom case - should preserve custom value
        config = SecurityConfig(cors_allow_origins=["https://example.com"])
        assert config.cors_allow_origins == ["https://example.com"]


class TestConfig:
    """Test cases for main Config class."""
    
    def test_default_config_initialization(self):
        """Test default config initialization."""
        config = Config()
        
        assert isinstance(config.logger, LoggerConfig)
        assert isinstance(config.simulator, SimulatorConfig)
        assert isinstance(config.geofence, GeofenceConfig)
        assert isinstance(config.api, APIConfig)
        assert isinstance(config.ui, UIConfig)
        assert isinstance(config.security, SecurityConfig)
    
    def test_get_log_file_path(self):
        """Test log file path generation."""
        config = Config()
        expected_path = os.path.join(config.logger.log_directory, config.logger.log_filename)
        
        assert config.get_log_file_path() == expected_path
    
    def test_get_api_url(self):
        """Test API URL generation."""
        config = Config()
        expected_url = f"http://{config.api.host}:{config.api.port}"
        
        assert config.get_api_url() == expected_url
    
    @patch.dict(os.environ, {
        'LOGGER_BUFFER_SIZE': '200',
        'LOGGER_MAX_FILE_SIZE': '20971520',  # 20MB
        'LOG_DIRECTORY': 'custom_logs',
        'HOME_LATITUDE': '51.5074',
        'HOME_LONGITUDE': '-0.1278',
        'UPDATE_FREQUENCY': '2.0',
        'MAX_WANDER_DISTANCE': '1500.0',
        'API_HOST': '0.0.0.0',
        'API_PORT': '9000',
        'DEFAULT_GEOFENCE_RADIUS': '500.0'
    })
    def test_load_from_env(self):
        """Test loading configuration from environment variables."""
        config = Config()
        
        # Logger config from env
        assert config.logger.buffer_size == 200
        assert config.logger.max_file_size == 20971520
        assert config.logger.log_directory == "custom_logs"
        
        # Simulator config from env
        assert config.simulator.home_lat == 51.5074
        assert config.simulator.home_lon == -0.1278
        assert config.simulator.update_frequency == 2.0
        assert config.simulator.max_wander_distance == 1500.0
        
        # API config from env
        assert config.api.host == "0.0.0.0"
        assert config.api.port == 9000
        
        # Geofence config from env
        assert config.geofence.default_radius == 500.0
    
    @patch.dict(os.environ, {
        'LOGGER_BUFFER_SIZE': 'invalid',
        'HOME_LATITUDE': 'not_a_number'
    })
    def test_load_from_env_invalid_values(self):
        """Test handling of invalid environment variable values."""
        # Should not raise exception, should use defaults
        config = Config()
        
        # Should use default values when env vars are invalid
        assert config.logger.buffer_size == 50  # Default
        assert config.simulator.home_lat == 40.7128  # Default
    
    @patch.dict(os.environ, {}, clear=True)
    def test_load_from_env_no_env_vars(self):
        """Test behavior when no environment variables are set."""
        config = Config()
        
        # Should use all default values
        assert config.logger.buffer_size == 50
        assert config.simulator.home_lat == 40.7128
        assert config.api.host == "localhost"


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    def test_get_config(self):
        """Test get_config function."""
        config = get_config()
        assert isinstance(config, Config)
    
    def test_get_simulator_config(self):
        """Test get_simulator_config function."""
        config = get_simulator_config()
        assert isinstance(config, SimulatorConfig)
    
    def test_get_logger_config(self):
        """Test get_logger_config function."""
        config = get_logger_config()
        assert isinstance(config, LoggerConfig)
    
    def test_get_api_config(self):
        """Test get_api_config function."""
        config = get_api_config()
        assert isinstance(config, APIConfig)
    
    def test_get_geofence_config(self):
        """Test get_geofence_config function."""
        config = get_geofence_config()
        assert isinstance(config, GeofenceConfig)
    
    def test_get_ui_config(self):
        """Test get_ui_config function."""
        config = get_ui_config()
        assert isinstance(config, UIConfig)


class TestConfigurationIntegration:
    """Integration test cases for configuration module."""
    
    def test_config_consistency(self):
        """Test that all configurations are consistent."""
        config = Config()
        
        # API URL should be consistent
        expected_url = f"http://{config.api.host}:{config.api.port}"
        assert config.get_api_url() == expected_url
        
        # Log path should be consistent
        expected_path = os.path.join(config.logger.log_directory, config.logger.log_filename)
        assert config.get_log_file_path() == expected_path
    
    def test_config_validation(self):
        """Test configuration value validation."""
        config = Config()
        
        # Positive values
        assert config.logger.buffer_size > 0
        assert config.logger.max_file_size > 0
        assert config.simulator.update_frequency > 0
        assert config.geofence.default_radius > 0
        assert config.api.port > 0
        
        # Valid ranges
        assert -90 <= config.simulator.home_lat <= 90
        assert -180 <= config.simulator.home_lon <= 180
        assert 0 <= config.simulator.panic_probability <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 