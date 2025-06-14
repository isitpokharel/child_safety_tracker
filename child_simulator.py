#!/usr/bin/env python3
"""
Child Simulator - GPS generator & panic flag
Author: Isit Pokharel
Purpose: Simulated child device that emits location data and handles emergency states
"""

import asyncio
import json
import time
import random
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.align import Align
from rich import box

from simulator import GPSSimulator, SimulatorConfig, EmergencyState
from geofence import Location, Geofence, GeofenceChecker


def check_location_safety(location: Location, geofence: Geofence) -> Tuple[bool, float]:
    """
    Check if a location is within the geofence.
    
    Args:
        location: Current location to check
        geofence: Geofence to check against
        
    Returns:
        Tuple of (is_safe, distance_meters)
    """
    return geofence.check_location(location)


class ChildSimulator:
    """Child device simulator with location tracking and panic functionality."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Initialize the child simulator.
        
        Args:
            api_url: URL of the KiddoTrack-Lite API
        """
        self.api_url = api_url
        self.console = Console()
        self.client = httpx.AsyncClient(timeout=5.0)
        
        # Initialize GPS simulator
        config = SimulatorConfig(
            home_latitude=40.7128,  # New York City
            home_longitude=-74.0060,
            update_frequency=1.0,
            max_wander_distance=100.0,
            panic_probability=0.01
        )
        self.simulator = GPSSimulator(config)
        
        # State tracking
        self.is_running = False
        self.current_location: Optional[Location] = None
        self.current_geofence: Optional[Geofence] = None
        self.emergency_state = EmergencyState.NORMAL
        self.last_alert_time: float = 0  # Unix timestamp for compatibility
        self.last_update_time: Optional[datetime] = None
        self.alert_cooldown_seconds = 30
        
        # Add callbacks
        self.simulator.add_location_callback(self._on_location_update)
        self.simulator.add_emergency_callback(self._on_emergency_update)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    @property
    def geofence(self) -> Optional[Geofence]:
        """Get current geofence (for backward compatibility)."""
        return self.current_geofence
    
    @geofence.setter  
    def geofence(self, value: Optional[Geofence]) -> None:
        """Set current geofence (for backward compatibility)."""
        self.current_geofence = value
    
    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        self.console.print(f"\n[yellow]Received signal {signum}, shutting down...[/yellow]")
        self.is_running = False
    
    async def start(self):
        """Start the child simulator."""
        self.is_running = True
        
        # Clear screen and show welcome
        self.console.clear()
        self.console.print(Panel.fit(
            "[bold green]KiddoTrack-Lite[/bold green]\n"
            "[italic]Child Device Simulator[/italic]\n\n"
            "Press Ctrl+C to exit\n"
            "Press 'p' to trigger panic\n"
            "Press 'r' to resolve panic",
            border_style="green"
        ))
        
        # Start GPS simulator
        self.simulator.start()
        
        # Start the monitoring loop
        try:
            with Live(self._create_layout(), refresh_per_second=1, screen=True) as live:
                while self.is_running:
                    await self._update_data()
                    live.update(self._create_layout())
                    await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Shutting down child simulator...[/yellow]")
        finally:
            self.simulator.stop()
            await self.client.aclose()
    
    async def _update_data(self):
        """Update data from the API."""
        try:
            # Get current status
            response = await self.client.get(f"{self.api_url}/status")
            if response.status_code == 200:
                status_data = response.json()
                
                # Update location
                if status_data.get("current_location"):
                    loc_data = status_data["current_location"]
                    self.current_location = Location(
                        latitude=loc_data["latitude"],
                        longitude=loc_data["longitude"],
                        timestamp=loc_data.get("timestamp")
                    )
                
                # Update emergency state
                self.emergency_state = EmergencyState(status_data.get("emergency_state", "normal"))
                
                # Update geofence status
                if status_data.get("geofence_active"):
                    await self._update_geofence()
                
                self.last_update_time = datetime.now()
                    
        except Exception as e:
            self.console.print(f"[red]Error updating data: {e}[/red]")
    
    async def _update_geofence(self):
        """Update geofence data from API."""
        try:
            response = await self.client.get(f"{self.api_url}/geofence")
            if response.status_code == 200:
                geofence_data = response.json()
                center_data = geofence_data["center"]
                
                self.current_geofence = Geofence(
                    center=Location(
                        latitude=center_data["latitude"],
                        longitude=center_data["longitude"]
                    ),
                    radius_meters=geofence_data["radius_meters"]
                )
        except Exception:
            # Geofence might not be configured yet
            pass
    
    def _on_location_update(self, location: Location):
        """Handle location updates from simulator."""
        self.current_location = location
        
        # Check geofence if available
        if self.current_geofence:
            is_safe, distance = check_location_safety(location, self.current_geofence)
            
            if not is_safe:
                # Prevent spam - only alert every 30 seconds
                current_time = time.time()
                if current_time - self.last_alert_time > self.alert_cooldown_seconds:
                    self.console.print(f"[yellow]WARNING: Left safe zone! Distance: {distance:.1f}m[/yellow]")
                    self.last_alert_time = current_time
    
    def _on_emergency_update(self, state: EmergencyState):
        """Handle emergency state updates from simulator."""
        self.emergency_state = state
        
        if state == EmergencyState.PANIC:
            self.console.print("[bold red]!!! PANIC TRIGGERED !!![/bold red]")
        elif state == EmergencyState.RESOLVED:
            self.console.print("[bold green]Panic resolved[/bold green]")
        elif state == EmergencyState.NORMAL:
            self.console.print("[green]Back to normal state[/green]")
    
    async def trigger_panic(self):
        """Manually trigger panic state."""
        try:
            response = await self.client.post(f"{self.api_url}/panic")
            if response.status_code == 200:
                self.console.print("[bold red]Manual panic triggered![/bold red]")
            else:
                self.console.print(f"[red]Failed to trigger panic: {response.status_code}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error triggering panic: {e}[/red]")
    
    async def resolve_panic(self):
        """Manually resolve panic state."""
        try:
            response = await self.client.post(f"{self.api_url}/panic/resolve")
            if response.status_code == 200:
                self.console.print("[bold green]Manual panic resolution![/bold green]")
            else:
                self.console.print(f"[red]Failed to resolve panic: {response.status_code}[/red]")
        except Exception as e:
            self.console.print(f"[red]Error resolving panic: {e}[/red]")
    
    def _create_layout(self) -> Layout:
        """Create the main layout."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        
        layout["left"].split_column(
            Layout(name="location", ratio=1),
            Layout(name="status", ratio=1)
        )
        
        layout["right"].split_column(
            Layout(name="controls", ratio=1),
            Layout(name="info", ratio=1)
        )
        
        # Populate sections
        layout["header"].update(self._create_header())
        layout["location"].update(self._create_location())
        layout["status"].update(self._create_status())
        layout["controls"].update(self._create_controls())
        layout["info"].update(self._create_info())
        layout["footer"].update(self._create_footer())
        
        return layout
    
    def _create_header(self) -> Panel:
        """Create the header panel."""
        title = Text("KiddoTrack-Lite Child Simulator", style="bold green")
        subtitle = Text("GPS Location & Emergency Monitoring", style="italic")
        
        # Emergency indicator
        if self.emergency_state == EmergencyState.PANIC:
            status = Text("EMERGENCY - PANIC TRIGGERED", style="bold red")
        elif self.emergency_state == EmergencyState.RESOLVED:
            status = Text("Emergency Resolved", style="bold yellow")
        else:
            status = Text("Normal Operation", style="bold green")
        
        content = Align.center(
            Text.assemble(
                title, "\n", subtitle, "\n", status
            )
        )
        
        return Panel(
            content,
            border_style="green",
            box=box.ROUNDED
        )
    
    def _create_location(self) -> Panel:
        """Create the location panel."""
        if not self.current_location:
            content = Text("No location data available", style="yellow")
        else:
            table = Table.grid(padding=1)
            table.add_row("Latitude:", f"{self.current_location.latitude:.6f}")
            table.add_row("Longitude:", f"{self.current_location.longitude:.6f}")
            table.add_row("Last Update:", self.current_location.timestamp)
            
            if self.current_geofence:
                is_safe, distance = check_location_safety(self.current_location, self.current_geofence)
                status = "Safe" if is_safe else f"Unsafe ({distance:.1f}m from safe zone)"
                table.add_row("Geofence Status:", status)
            
            content = table
        
        return Panel(
            content,
            title="Location Data",
            border_style="blue",
            box=box.ROUNDED
        )
    
    def _create_status(self) -> Panel:
        """Create the status panel."""
        table = Table.grid(padding=1)
        table.add_row("Device Status:", self.emergency_state.value.title())
        table.add_row("Simulator:", "Running" if self.simulator.is_running else "Stopped")
        table.add_row("Last Update:", self.last_update_time.strftime("%H:%M:%S") if self.last_update_time else "Never")
        
        return Panel(
            table,
            title="Device Status",
            border_style="blue",
            box=box.ROUNDED
        )
    
    def _create_controls(self) -> Panel:
        """Create the controls panel."""
        table = Table.grid(padding=1)
        table.add_row("[bold]Controls:[/bold]")
        table.add_row("p - Trigger Panic")
        table.add_row("r - Resolve Panic")
        table.add_row("Ctrl+C - Exit")
        
        return Panel(
            table,
            title="Controls",
            border_style="blue",
            box=box.ROUNDED
        )
    
    def _create_info(self) -> Panel:
        """Create the info panel."""
        table = Table.grid(padding=1)
        table.add_row("[bold]Device Info:[/bold]")
        table.add_row("API URL:", self.api_url)
        
        if self.current_geofence:
            table.add_row("Geofence:", f"Active ({self.current_geofence.radius_meters:.0f}m radius)")
        else:
            table.add_row("Geofence:", "Not set")
        
        return Panel(
            table,
            title="Device Info",
            border_style="blue",
            box=box.ROUNDED
        )
    
    def _create_footer(self) -> Panel:
        """Create the footer panel."""
        content = Text.assemble(
            "KiddoTrack-Lite ",
            Text("v1.0.0", style="dim"),
            " | ",
            Text("Child Simulator", style="italic")
        )
        
        return Panel(
            Align.center(content),
            border_style="green",
            box=box.ROUNDED
        )


async def main():
    """Main entry point."""
    simulator = ChildSimulator()
    await simulator.start()


if __name__ == "__main__":
    asyncio.run(main()) 