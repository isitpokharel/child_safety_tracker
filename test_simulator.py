"""
Unit Tests for Simulator Module
Author: Isit Pokharel
Purpose: State-transition testing for GPS simulator and emergency states
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
from simulator import (
    EmergencyState, SimulatorConfig, GPSSimulator, 
    LocationGenerator, create_default_simulator, create_custom_simulator
)
from geofence import Location


class TestEmergencyState:
    """Test cases for EmergencyState enum."""
    
    def test_emergency_state_values(self):
        """Test emergency state enum values."""
        assert EmergencyState.NORMAL.value == "normal"
        assert EmergencyState.PANIC.value == "panic"
        assert EmergencyState.RESOLVED.value == "resolved"
    
    def test_emergency_state_creation(self):
        """Test creating emergency states from values."""
        assert EmergencyState("normal") == EmergencyState.NORMAL
        assert EmergencyState("panic") == EmergencyState.PANIC
        assert EmergencyState("resolved") == EmergencyState.RESOLVED
    
    def test_emergency_state_invalid_value(self):
        """Test creating emergency state with invalid value."""
        with pytest.raises(ValueError):
            EmergencyState("invalid")


class TestSimulatorConfig:
    """Test cases for SimulatorConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = SimulatorConfig()
        
        assert config.home_lat == 40.7128  # NYC
        assert config.home_lon == -74.0060
        assert config.update_frequency == 1.0
        assert config.max_wander_distance == 2000.0
        assert config.panic_probability == 0.01
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = SimulatorConfig(
            home_lat=51.5074,  # London
            home_lon=-0.1278,
            update_frequency=2.0,
            max_wander_distance=1000.0,
            panic_probability=0.05
        )
        
        assert config.home_lat == 51.5074
        assert config.home_lon == -0.1278
        assert config.update_frequency == 2.0
        assert config.max_wander_distance == 1000.0
        assert config.panic_probability == 0.05


class TestGPSSimulator:
    """Test cases for GPSSimulator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = SimulatorConfig()
        self.simulator = GPSSimulator(self.config)
    
    def test_initialization(self):
        """Test simulator initialization."""
        assert self.simulator.config == self.config
        assert self.simulator.emergency_state == EmergencyState.NORMAL
        assert not self.simulator._running
        assert self.simulator._thread is None
        assert len(self.simulator._location_callbacks) == 0
        assert len(self.simulator._emergency_callbacks) == 0
        
        # Check initial location
        initial_location = self.simulator.current_location
        assert initial_location.latitude == self.config.home_lat
        assert initial_location.longitude == self.config.home_lon
    
    def test_add_location_callback(self):
        """Test adding location callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        
        self.simulator.add_location_callback(callback1)
        self.simulator.add_location_callback(callback2)
        
        assert len(self.simulator._location_callbacks) == 2
        assert callback1 in self.simulator._location_callbacks
        assert callback2 in self.simulator._location_callbacks
    
    def test_add_emergency_callback(self):
        """Test adding emergency callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        
        self.simulator.add_emergency_callback(callback1)
        self.simulator.add_emergency_callback(callback2)
        
        assert len(self.simulator._emergency_callbacks) == 2
        assert callback1 in self.simulator._emergency_callbacks
        assert callback2 in self.simulator._emergency_callbacks
    
    def test_generate_random_offset(self):
        """Test random offset generation."""
        lat_offset, lon_offset = self.simulator._generate_random_offset()
        
        # Check that offsets are within expected range
        max_degree_offset = self.config.max_wander_distance / 111000
        
        assert abs(lat_offset) <= max_degree_offset
        assert abs(lon_offset) <= max_degree_offset
    
    def test_update_location(self):
        """Test location update functionality."""
        original_location = self.simulator.current_location
        
        self.simulator._update_location()
        
        new_location = self.simulator.current_location
        
        # Location should have changed
        assert new_location != original_location
        
        # Should still be within valid GPS bounds
        assert -90 <= new_location.latitude <= 90
        assert -180 <= new_location.longitude <= 180
        
        # Should have timestamp
        assert new_location.timestamp is not None
    
    def test_trigger_panic_normal_to_panic(self):
        """Test state transition: NORMAL -> PANIC."""
        assert self.simulator.emergency_state == EmergencyState.NORMAL
        
        self.simulator.trigger_panic()
        
        assert self.simulator.emergency_state == EmergencyState.PANIC
    
    def test_trigger_panic_already_panic(self):
        """Test trigger panic when already in panic state."""
        self.simulator.emergency_state = EmergencyState.PANIC
        
        self.simulator.trigger_panic()
        
        # Should remain in panic state
        assert self.simulator.emergency_state == EmergencyState.PANIC
    
    def test_resolve_panic_panic_to_resolved(self):
        """Test state transition: PANIC -> RESOLVED."""
        self.simulator.emergency_state = EmergencyState.PANIC
        
        self.simulator.resolve_panic()
        
        assert self.simulator.emergency_state == EmergencyState.RESOLVED
    
    def test_resolve_panic_not_in_panic(self):
        """Test resolve panic when not in panic state."""
        self.simulator.emergency_state = EmergencyState.NORMAL
        
        self.simulator.resolve_panic()
        
        # Should remain in normal state
        assert self.simulator.emergency_state == EmergencyState.NORMAL
    
    def test_reset_to_normal_resolved_to_normal(self):
        """Test state transition: RESOLVED -> NORMAL."""
        self.simulator.emergency_state = EmergencyState.RESOLVED
        
        self.simulator._reset_to_normal()
        
        assert self.simulator.emergency_state == EmergencyState.NORMAL
    
    def test_state_transition_sequence(self):
        """Test complete state transition sequence."""
        # Start in normal state
        assert self.simulator.emergency_state == EmergencyState.NORMAL
        
        # Trigger panic
        self.simulator.trigger_panic()
        assert self.simulator.emergency_state == EmergencyState.PANIC
        
        # Resolve panic
        self.simulator.resolve_panic()
        assert self.simulator.emergency_state == EmergencyState.RESOLVED
        
        # Reset to normal
        self.simulator._reset_to_normal()
        assert self.simulator.emergency_state == EmergencyState.NORMAL
    
    def test_get_current_location(self):
        """Test getting current location."""
        location = self.simulator.get_current_location()
        
        assert isinstance(location, Location)
        assert location.latitude == self.config.home_lat
        assert location.longitude == self.config.home_lon
    
    def test_get_emergency_state(self):
        """Test getting emergency state."""
        state = self.simulator.get_emergency_state()
        assert state == EmergencyState.NORMAL
        
        self.simulator.emergency_state = EmergencyState.PANIC
        state = self.simulator.get_emergency_state()
        assert state == EmergencyState.PANIC
    
    def test_set_location(self):
        """Test manually setting location."""
        new_lat = 51.5074
        new_lon = -0.1278
        
        self.simulator.set_location(new_lat, new_lon)
        
        location = self.simulator.get_current_location()
        assert location.latitude == new_lat
        assert location.longitude == new_lon
        assert location.timestamp is not None
    
    def test_start_simulator(self):
        """Test starting the simulator."""
        assert not self.simulator._running
        
        self.simulator.start()
        
        assert self.simulator._running
        assert self.simulator._thread is not None
        assert self.simulator._thread.is_alive()
        
        # Clean up
        self.simulator.stop()
    
    def test_stop_simulator(self):
        """Test stopping the simulator."""
        self.simulator.start()
        assert self.simulator._running
        
        self.simulator.stop()
        
        assert not self.simulator._running
    
    def test_start_already_running(self):
        """Test starting simulator that's already running."""
        self.simulator.start()
        assert self.simulator._running
        
        # Try to start again
        self.simulator.start()
        
        # Should still be running
        assert self.simulator._running
        
        # Clean up
        self.simulator.stop()
    
    def test_simulation_loop_location_updates(self):
        """Test that simulation loop updates location."""
        location_callback = Mock()
        self.simulator.add_location_callback(location_callback)
        
        self.simulator.start()
        time.sleep(0.1)  # Let it run briefly
        
        # Should have called the callback
        assert location_callback.called
        
        self.simulator.stop()
    
    def test_simulation_loop_panic_check(self):
        """Test panic probability check in simulation loop."""
        # Set high panic probability for testing
        self.simulator.config.panic_probability = 1.0
        
        emergency_callback = Mock()
        self.simulator.add_emergency_callback(emergency_callback)
        
        self.simulator.start()
        time.sleep(0.1)  # Let it run briefly
        
        # Should have triggered panic
        assert self.simulator.emergency_state == EmergencyState.PANIC
        assert emergency_callback.called
        
        self.simulator.stop()
    
    def test_callback_error_handling(self):
        """Test that callback errors don't crash the simulator."""
        def failing_callback(location):
            raise Exception("Callback error")
        
        self.simulator.add_location_callback(failing_callback)
        
        # Should not raise exception
        self.simulator._notify_location_callbacks(self.simulator.current_location)
    
    def test_boundary_coordinate_handling(self):
        """Test handling of boundary coordinates."""
        # Test near boundary values
        self.simulator.set_location(89.9, 179.9)
        location = self.simulator.get_current_location()
        assert location.latitude == 89.9
        assert location.longitude == 179.9
        
        # Test that updates don't exceed boundaries
        self.simulator._update_location()
        location = self.simulator.get_current_location()
        assert -90 <= location.latitude <= 90
        assert -180 <= location.longitude <= 180


class TestLocationGenerator:
    """Test cases for LocationGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = SimulatorConfig()
        self.generator = LocationGenerator(self.config)
    
    def test_initialization(self):
        """Test location generator initialization."""
        assert self.generator.config == self.config
        assert isinstance(self.generator.simulator, GPSSimulator)
    
    def test_generate_locations(self):
        """Test location generation."""
        locations = []
        
        # Start generator
        self.generator.simulator.start()
        
        # Collect a few locations
        for i, location in enumerate(self.generator.generate_locations()):
            if i >= 3:  # Get 3 locations
                break
            locations.append(location)
        
        # Should have generated locations
        assert len(locations) == 3
        
        for location in locations:
            assert isinstance(location, Location)
            assert -90 <= location.latitude <= 90
            assert -180 <= location.longitude <= 180
        
        # Clean up
        self.generator.simulator.stop()
    
    def test_get_simulator(self):
        """Test getting simulator instance."""
        simulator = self.generator.get_simulator()
        assert isinstance(simulator, GPSSimulator)
        assert simulator == self.generator.simulator


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    def test_create_default_simulator(self):
        """Test creating default simulator."""
        simulator = create_default_simulator()
        
        assert isinstance(simulator, GPSSimulator)
        assert simulator.config.home_lat == 40.7128  # NYC
        assert simulator.config.home_lon == -74.0060
        assert simulator.config.max_wander_distance == 2000.0
    
    def test_create_custom_simulator(self):
        """Test creating custom simulator."""
        simulator = create_custom_simulator(
            home_lat=51.5074,  # London
            home_lon=-0.1278,
            max_distance=1000.0
        )
        
        assert isinstance(simulator, GPSSimulator)
        assert simulator.config.home_lat == 51.5074
        assert simulator.config.home_lon == -0.1278
        assert simulator.config.max_wander_distance == 1000.0


class TestStateTransitionScenarios:
    """Test complex state transition scenarios."""
    
    def test_rapid_panic_trigger_resolve(self):
        """Test rapid panic trigger and resolve."""
        config = SimulatorConfig()
        simulator = GPSSimulator(config)
        
        # Track state changes
        state_changes = []
        def state_callback(state):
            state_changes.append(state)
        
        simulator.add_emergency_callback(state_callback)
        
        # Rapid state changes
        simulator.trigger_panic()
        simulator.resolve_panic()
        simulator.trigger_panic()
        simulator.resolve_panic()
        
        # Should have recorded state changes
        assert len(state_changes) >= 4
        assert EmergencyState.PANIC in state_changes
        assert EmergencyState.RESOLVED in state_changes
    
    def test_concurrent_location_updates(self):
        """Test concurrent location updates."""
        config = SimulatorConfig()
        simulator = GPSSimulator(config)
        
        # Track location updates
        location_updates = []
        def location_callback(location):
            location_updates.append(location)
        
        simulator.add_location_callback(location_callback)
        
        # Start simulator
        simulator.start()
        time.sleep(0.1)  # Let it run briefly
        
        # Should have generated location updates
        assert len(location_updates) > 0
        
        # All locations should be valid
        for location in location_updates:
            assert isinstance(location, Location)
            assert -90 <= location.latitude <= 90
            assert -180 <= location.longitude <= 180
        
        simulator.stop()
    
    def test_simulator_lifecycle(self):
        """Test complete simulator lifecycle."""
        config = SimulatorConfig()
        simulator = GPSSimulator(config)
        
        # Initial state
        assert not simulator._running
        assert simulator.emergency_state == EmergencyState.NORMAL
        
        # Start
        simulator.start()
        assert simulator._running
        assert simulator._thread.is_alive()
        
        # Trigger panic
        simulator.trigger_panic()
        assert simulator.emergency_state == EmergencyState.PANIC
        
        # Resolve panic
        simulator.resolve_panic()
        assert simulator.emergency_state == EmergencyState.RESOLVED
        
        # Stop
        simulator.stop()
        assert not simulator._running


class TestErrorConditions:
    """Test error conditions and edge cases."""
    
    def test_invalid_config_values(self):
        """Test simulator with invalid config values."""
        config = SimulatorConfig()
        config.max_wander_distance = -1000  # Invalid negative value
        
        simulator = GPSSimulator(config)
        
        # Should handle gracefully
        simulator._update_location()
        location = simulator.get_current_location()
        assert -90 <= location.latitude <= 90
        assert -180 <= location.longitude <= 180
    
    def test_zero_update_frequency(self):
        """Test simulator with zero update frequency."""
        config = SimulatorConfig()
        config.update_frequency = 0.0
        
        simulator = GPSSimulator(config)
        
        # Should handle gracefully
        simulator.start()
        time.sleep(0.1)
        simulator.stop()
    
    def test_very_high_panic_probability(self):
        """Test simulator with very high panic probability."""
        config = SimulatorConfig()
        config.panic_probability = 1.0  # 100% chance
        
        simulator = GPSSimulator(config)
        
        # Should trigger panic immediately
        simulator._check_panic_trigger()
        assert simulator.emergency_state == EmergencyState.PANIC


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 