"""
Simulator Module - GPS generator & panic flag
Author: Isit Pokharel
Purpose: Simulated GPS feed and emergency state management
"""

import time
import random
import math
import threading
from typing import Generator, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from geofence import Location


class EmergencyState(Enum):
    """Enumeration of emergency states."""
    NORMAL = "normal"
    PANIC = "panic"
    RESOLVED = "resolved"


@dataclass
class SimulatorConfig:
    """Configuration for the GPS simulator."""
    home_lat: float = 40.7128  # Default: New York City
    home_lon: float = -74.0060
    update_frequency: float = 1.0  # Hz
    max_wander_distance: float = 2000.0  # meters
    panic_probability: float = 0.01  # 1% chance per update


class GPSSimulator:
    """Simulates GPS location data with configurable behavior."""
    
    def __init__(self, config: SimulatorConfig):
        """
        Initialize the GPS simulator.
        
        Args:
            config: Simulator configuration
        """
        self.config = config
        self.current_location = Location(config.home_lat, config.home_lon)
        self.emergency_state = EmergencyState.NORMAL
        self._running = False
        self._thread = None
        self._location_callbacks = []
        self._emergency_callbacks = []
        self._callback_lock = threading.Lock()
        
    def add_location_callback(self, callback: Callable[[Location], None]):
        """Add a callback to be called when location updates."""
        with self._callback_lock:
            self._location_callbacks.append(callback)
    
    def add_emergency_callback(self, callback: Callable[[EmergencyState], None]):
        """Add a callback to be called when emergency state changes."""
        with self._callback_lock:
            self._emergency_callbacks.append(callback)
    
    def _notify_location_callbacks(self, location: Location):
        """Notify all location callbacks."""
        with self._callback_lock:
            callbacks = self._location_callbacks.copy()
        
        for callback in callbacks:
            try:
                callback(location)
            except Exception as e:
                print(f"Error in location callback: {e}")
    
    def _notify_emergency_callbacks(self, state: EmergencyState):
        """Notify all emergency callbacks."""
        with self._callback_lock:
            callbacks = self._emergency_callbacks.copy()
        
        for callback in callbacks:
            try:
                callback(state)
            except Exception as e:
                print(f"Error in emergency callback: {e}")
    
    def _generate_random_offset(self) -> tuple[float, float]:
        """Generate random lat/lon offset within max_wander_distance."""
        # Convert max distance to approximate lat/lon offset
        # Rough approximation: 1 degree ≈ 111km
        max_degree_offset = self.config.max_wander_distance / 111000
        
        # Generate random angle and distance
        angle = random.uniform(0, 2 * 3.14159)
        distance_ratio = random.uniform(0, 1)
        
        # Convert to lat/lon offsets
        lat_offset = distance_ratio * max_degree_offset * math.cos(angle)
        lon_offset = distance_ratio * max_degree_offset * math.sin(angle)
        
        return lat_offset, lon_offset
    
    def _update_location(self):
        """Update the current location with some random movement."""
        lat_offset, lon_offset = self._generate_random_offset()
        
        new_lat = self.current_location.latitude + lat_offset
        new_lon = self.current_location.longitude + lon_offset
        
        # Ensure we stay within valid GPS bounds
        new_lat = max(-90, min(90, new_lat))
        new_lon = max(-180, min(180, new_lon))
        
        self.current_location = Location(
            latitude=new_lat,
            longitude=new_lon,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )
    
    def _check_panic_trigger(self):
        """Check if panic should be triggered based on probability."""
        if random.random() < self.config.panic_probability:
            self.trigger_panic()
    
    def _simulation_loop(self):
        """Main simulation loop."""
        while self._running:
            try:
                self._update_location()
                self._notify_location_callbacks(self.current_location)
                self._check_panic_trigger()
                time.sleep(1.0 / self.config.update_frequency)
            except Exception as e:
                print(f"Error in simulation loop: {e}")
                time.sleep(1.0 / self.config.update_frequency)
    
    def start(self):
        """Start the GPS simulation."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self._thread.start()
        print("GPS Simulator started")
    
    def stop(self):
        """Stop the GPS simulation."""
        if not self._running:
            return
            
        self._running = False
        if self._thread:
            try:
                self._thread.join(timeout=2.0)  # Increased timeout for cleanup
                if self._thread.is_alive():
                    print("Warning: Simulation thread did not stop gracefully")
            except Exception as e:
                print(f"Error stopping simulation thread: {e}")
        
        # Clear callbacks
        with self._callback_lock:
            self._location_callbacks.clear()
            self._emergency_callbacks.clear()
        
        print("GPS Simulator stopped")
    
    def cleanup(self):
        """Clean up resources and ensure proper shutdown."""
        self.stop()
        # Additional cleanup if needed
        self._thread = None
        self.current_location = None
        self.emergency_state = EmergencyState.NORMAL
    
    def trigger_panic(self):
        """Manually trigger panic state."""
        if self.emergency_state == EmergencyState.NORMAL:
            self.emergency_state = EmergencyState.PANIC
            self._notify_emergency_callbacks(self.emergency_state)
            print("🚨 PANIC TRIGGERED! 🚨")
    
    def resolve_panic(self):
        """Resolve panic state."""
        if self.emergency_state == EmergencyState.PANIC:
            self.emergency_state = EmergencyState.RESOLVED
            self._notify_emergency_callbacks(self.emergency_state)
            print("✅ Panic resolved")
            # Reset to normal after a short delay
            threading.Timer(2.0, self._reset_to_normal).start()
    
    def _reset_to_normal(self):
        """Reset emergency state to normal."""
        self.emergency_state = EmergencyState.NORMAL
        self._notify_emergency_callbacks(self.emergency_state)
        print("🔄 Back to normal state")
    
    def get_current_location(self) -> Location:
        """Get the current simulated location."""
        return self.current_location
    
    def get_emergency_state(self) -> EmergencyState:
        """Get the current emergency state."""
        return self.emergency_state
    
    def set_location(self, lat: float, lon: float):
        """Manually set the current location."""
        self.current_location = Location(
            latitude=lat,
            longitude=lon,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        self._notify_location_callbacks(self.current_location)


class LocationGenerator:
    """Generator for location data streams."""
    
    def __init__(self, config: SimulatorConfig):
        """
        Initialize the location generator.
        
        Args:
            config: Simulator configuration
        """
        self.config = config
        self.simulator = GPSSimulator(config)
    
    def generate_locations(self) -> Generator[Location, None, None]:
        """
        Generate location data at specified frequency.
        
        Yields:
            Location objects with current GPS data
        """
        self.simulator.start()
        
        try:
            while True:
                location = self.simulator.get_current_location()
                yield location
                time.sleep(1.0 / self.config.update_frequency)
        finally:
            self.simulator.stop()
    
    def get_simulator(self) -> GPSSimulator:
        """Get the underlying simulator instance."""
        return self.simulator


# Convenience functions
def create_default_simulator() -> GPSSimulator:
    """Create a default GPS simulator with NYC coordinates."""
    config = SimulatorConfig()
    return GPSSimulator(config)


def create_custom_simulator(home_lat: float, home_lon: float, 
                          max_distance: float = 2000.0) -> GPSSimulator:
    """Create a custom GPS simulator with specified parameters."""
    config = SimulatorConfig(
        home_lat=home_lat,
        home_lon=home_lon,
        max_wander_distance=max_distance
    )
    return GPSSimulator(config) 