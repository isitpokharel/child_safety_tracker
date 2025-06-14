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
from datetime import datetime
from typing import Optional
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
        self.client = httpx.AsyncClient()
        
        # Initialize GPS simulator
        config = SimulatorConfig()
        self.simulator = GPSSimulator(config)
        
        # State tracking
        self.is_running = False
        self.current_location: Optional[Location] = None
        self.geofence: Optional[Geofence] = None
        self.emergency_state = EmergencyState.NORMAL
        self.last_alert_time = 0
        
        # Add callbacks
        self.simulator.add_location_callback(self._on_location_update)
        self.simulator.add_emergency_callback(self._on_emergency_update)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
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
                    
        except Exception as e:
            self.console.print(f"[red]Error updating data: {e}[/red]")
    
    async def _update_geofence(self):
        """Update geofence data from API."""
        try:
            response = await self.client.get(f"{self.api_url}/geofence")
            if response.status_code == 200:
                geofence_data = response.json()
                center_data = geofence_data["center"]
                
                self.geofence = Geofence(
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
        if self.geofence:
            is_safe, distance = check_location_safety(location, self.geofence)
            
            if not is_safe:
                # Prevent spam - only alert every 30 seconds
                current_time = time.time()
                if current_time - self.last_alert_time > 30:
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
            emergency_text = Text("!!! EMERGENCY - PANIC ACTIVE !!!", style="bold red on white")
        elif self.emergency_state == EmergencyState.RESOLVED:
            emergency_text = Text("Emergency Resolved", style="bold green")
        else:
            emergency_text = Text("Normal Operation", style="bold green")
        
        content = Align.center(
            title + "\n" + subtitle + "\n" + emergency_text
        )
        
        return Panel(content, border_style="green", box=box.DOUBLE)
    
    def _create_location(self) -> Panel:
        """Create the location panel."""
        if not self.current_location:
            return Panel("No location data available", title="Current Location")
        
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Property", style="bold")
        table.add_column("Value")
        
        table.add_row("Latitude", f"{self.current_location.latitude:.6f}")
        table.add_row("Longitude", f"{self.current_location.longitude:.6f}")
        table.add_row("Timestamp", self.current_location.timestamp or "Unknown")
        
        # Add geofence status
        if self.geofence:
            is_safe, distance = check_location_safety(self.current_location, self.geofence)
            status_icon = "[SAFE]" if is_safe else "[ALERT]"
            status_text = "Safe" if is_safe else f"Outside ({distance:.0f}m)"
            table.add_row("Geofence", f"{status_icon} {status_text}")
        else:
            table.add_row("Geofence", "Not configured")
        
        return Panel(table, title="Current Location", border_style="cyan")
    
    def _create_status(self) -> Panel:
        """Create the status panel."""
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Property", style="bold")
        table.add_column("Value")
        
        # GPS Status
        gps_status = "[ACTIVE]" if self.simulator._running else "[INACTIVE]"
        table.add_row("GPS Status", gps_status)
        
        # Emergency State
        emergency_icon = {
            EmergencyState.NORMAL: "[NORMAL]",
            EmergencyState.PANIC: "[PANIC]",
            EmergencyState.RESOLVED: "[RESOLVED]"
        }.get(self.emergency_state, "[UNKNOWN]")
        
        table.add_row("Emergency", f"{emergency_icon} {self.emergency_state.value.upper()}")
        
        # Connection Status
        connection_status = "[CONNECTED]" if self.is_running else "[DISCONNECTED]"
        table.add_row("API Connection", connection_status)
        
        # Update Frequency
        table.add_row("Update Rate", f"{self.simulator.config.update_frequency} Hz")
        
        return Panel(table, title="Device Status", border_style="yellow")
    
    def _create_controls(self) -> Panel:
        """Create the controls panel."""
        controls_text = Text()
        controls_text.append("Controls:\n\n", style="bold")
        controls_text.append("• Ctrl+C: Exit\n", style="white")
        controls_text.append("• p: Trigger Panic\n", style="red")
        controls_text.append("• r: Resolve Panic\n", style="green")
        controls_text.append("• API: ", style="white")
        controls_text.append(f"{self.api_url}\n", style="blue")
        
        # Add current state info
        controls_text.append("\nCurrent State:\n", style="bold")
        controls_text.append(f"• GPS: {'Running' if self.simulator._running else 'Stopped'}\n", 
                           style="green" if self.simulator._running else "red")
        controls_text.append(f"• Emergency: {self.emergency_state.value}\n", 
                           style="red" if self.emergency_state == EmergencyState.PANIC else "green")
        
        return Panel(controls_text, title="Controls", border_style="magenta")
    
    def _create_info(self) -> Panel:
        """Create the info panel."""
        info_text = Text()
        info_text.append("Device Info:\n\n", style="bold")
        info_text.append("• Type: Child Simulator\n", style="white")
        info_text.append("• Version: 1.0.0\n", style="white")
        info_text.append("• Mode: GPS Tracking\n", style="white")
        info_text.append("• Emergency: Enabled\n", style="white")
        
        # Add geofence info
        if self.geofence:
            info_text.append(f"• Safe Zone: {self.geofence.radius_meters}m\n", style="white")
        else:
            info_text.append("• Safe Zone: Not set\n", style="dim")
        
        info_text.append("\nFeatures:\n", style="bold")
        info_text.append("• Real-time GPS\n", style="white")
        info_text.append("• Panic Button\n", style="white")
        info_text.append("• Geofence Alerts\n", style="white")
        info_text.append("• Emergency Mode\n", style="white")
        
        return Panel(info_text, title="Device Info", border_style="blue")
    
    def _create_footer(self) -> Panel:
        """Create the footer panel."""
        footer_text = Text()
        footer_text.append("KiddoTrack-Lite Child Simulator v1.0 | ", style="dim")
        footer_text.append("CISC 593 - Software Verification & Validation | ", style="dim")
        footer_text.append("Team: Vivek, Isit, Bhushan, Pooja", style="dim")
        
        return Panel(Align.center(footer_text), border_style="green")


async def main():
    """Main entry point."""
    simulator = ChildSimulator()
    await simulator.start()


if __name__ == "__main__":
    # Import helper function
    from geofence import check_location_safety
    
    asyncio.run(main()) 