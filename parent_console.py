#!/usr/bin/env python3
"""
Parent Console - Rich terminal UI for monitoring
Author: Pooja Poudel
Purpose: Parent monitoring interface with ASCII map and alerts
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.align import Align
from rich import box

from geofence import Location, Geofence, GeofenceChecker, check_location_safety
from simulator import EmergencyState
from config import get_config, get_ui_config


class ParentConsole:
    """Rich terminal-based parent monitoring console with optimizations."""
    
    def __init__(self, api_url: Optional[str] = None):
        """
        Initialize the parent console.
        
        Args:
            api_url: URL of the KiddoTrack-Lite API (uses config default if None)
        """
        self.config = get_config()
        self.ui_config = get_ui_config()
        self.api_url = api_url or self.config.get_api_url()
        
        self.console = Console()
        self.client = httpx.AsyncClient(timeout=self.config.api.request_timeout)
        
        # State variables
        self.current_location: Optional[Location] = None
        self.geofence: Optional[Geofence] = None
        self.emergency_state = EmergencyState.NORMAL
        self.recent_alerts = []
        self.is_running = False
        self.last_update_time = datetime.now()
        
    async def start(self):
        """Start the parent console."""
        self.is_running = True
        
        # Clear screen and show welcome
        self.console.clear()
        self._show_welcome()
        
        # Start the monitoring loop
        try:
            refresh_rate = self.ui_config.update_frequency
            with Live(self._create_layout(), refresh_per_second=refresh_rate, screen=True) as live:
                while self.is_running:
                    await self._update_data()
                    live.update(self._create_layout())
                    await asyncio.sleep(1.0 / refresh_rate)
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Shutting down parent console...[/yellow]")
        finally:
            await self.client.aclose()
    
    def _show_welcome(self):
        """Display welcome message."""
        welcome_panel = Panel.fit(
            "[bold blue]KiddoTrack-Lite[/bold blue]\n"
            "[italic]Parent Monitoring Console[/italic]\n\n"
            "Press Ctrl+C to exit",
            border_style="blue"
        )
        self.console.print(welcome_panel)
    
    async def _update_data(self):
        """Update data from the API with improved error handling."""
        try:
            # Update status and location
            await self._update_status()
            
            # Update alerts
            await self._update_alerts()
            
            self.last_update_time = datetime.now()
            
        except httpx.TimeoutException:
            self.console.print("[red]API request timeout[/red]")
        except httpx.ConnectError:
            self.console.print("[red]Cannot connect to API[/red]")
        except Exception as e:
            self.console.print(f"[red]Error updating data: {e}[/red]")
    
    async def _update_status(self):
        """Update status data from API."""
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
    
    async def _update_alerts(self):
        """Update alerts from API."""
        response = await self.client.get(f"{self.api_url}/alerts?limit={self.ui_config.max_recent_alerts}")
        if response.status_code == 200:
            self.recent_alerts = response.json()
    
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
            Layout(name="map", ratio=2),
            Layout(name="status", ratio=1)
        )
        
        layout["right"].split_column(
            Layout(name="alerts", ratio=1),
            Layout(name="controls", ratio=1)
        )
        
        # Populate sections
        layout["header"].update(self._create_header())
        layout["map"].update(self._create_map())
        layout["status"].update(self._create_status())
        layout["alerts"].update(self._create_alerts())
        layout["controls"].update(self._create_controls())
        layout["footer"].update(self._create_footer())
        
        return layout
    
    def _create_header(self) -> Panel:
        """Create the header panel."""
        title = Text("KiddoTrack-Lite Parent Console", style="bold blue")
        subtitle = Text("Real-time Child Safety Monitoring", style="italic")
        
        # Emergency indicator
        if self.emergency_state == EmergencyState.PANIC:
            emergency_text = Text("!!! EMERGENCY - PANIC TRIGGERED !!!", style="bold red on white")
        elif self.emergency_state == EmergencyState.RESOLVED:
            emergency_text = Text("Emergency Resolved", style="bold green")
        else:
            emergency_text = Text("All Systems Normal", style="bold green")
        
        content = Align.center(
            title + "\n" + subtitle + "\n" + emergency_text
        )
        
        return Panel(content, border_style="blue", box=box.DOUBLE)
    
    def _create_map(self) -> Panel:
        """Create the ASCII map panel with optimized rendering."""
        if not self.current_location:
            return Panel("No location data available", title="Location Map")
        
        map_size = self.ui_config.map_size
        map_chars = [[" " for _ in range(map_size)] for _ in range(map_size)]
        
        # Place home/geofence center
        if self.geofence:
            center_x = map_size // 2
            center_y = map_size // 2
            map_chars[center_y][center_x] = "H"
            
            # Draw geofence boundary (optimized calculation)
            radius_pixels = min(self.ui_config.geofence_display_radius, 
                              int(self.geofence.radius_meters / 250))  # Rough scale
            
            self._draw_geofence_boundary(map_chars, center_x, center_y, radius_pixels, map_size)
        
        # Place child location
        if self.current_location and self.geofence:
            child_x, child_y = self._calculate_child_position(map_size)
            
            # Check if child is in safe zone
            is_safe, distance = check_location_safety(self.current_location, self.geofence)
            child_icon = "C" if is_safe else "!"
            
            # Ensure within bounds and place icon
            if 0 <= child_x < map_size and 0 <= child_y < map_size:
                map_chars[child_y][child_x] = child_icon
        
        # Convert to string more efficiently
        map_str = "\n".join("".join(row) for row in map_chars)
        
        # Add legend
        legend = "\n\nLegend: H Home | C Child (Safe) | ! Child (Alert) | . Geofence"
        
        return Panel(map_str + legend, title="Location Map", border_style="green")
    
    def _draw_geofence_boundary(self, map_chars: list, center_x: int, center_y: int, 
                               radius_pixels: int, map_size: int):
        """Draw geofence boundary on the map efficiently."""
        for y in range(map_size):
            for x in range(map_size):
                distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                if abs(distance - radius_pixels) < 1:
                    map_chars[y][x] = "."
    
    def _calculate_child_position(self, map_size: int) -> tuple[int, int]:
        """Calculate child position on the map using configuration scale factor."""
        center_x = map_size // 2
        center_y = map_size // 2
        
        # Calculate relative position using config scale factor
        lat_diff = self.current_location.latitude - self.geofence.center.latitude
        lon_diff = self.current_location.longitude - self.geofence.center.longitude
        
        # Convert to map coordinates using config scale factor
        child_x = center_x + int(lon_diff * self.ui_config.map_scale_factor)
        child_y = center_y - int(lat_diff * self.ui_config.map_scale_factor)
        
        # Ensure within bounds
        child_x = max(0, min(map_size - 1, child_x))
        child_y = max(0, min(map_size - 1, child_y))
        
        return child_x, child_y
    
    def _create_status(self) -> Panel:
        """Create the status panel."""
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Property", style="bold")
        table.add_column("Value")
        
        if self.current_location:
            table.add_row("Location", f"{self.current_location.latitude:.4f}, {self.current_location.longitude:.4f}")
            table.add_row("Last Update", self.current_location.timestamp or "Unknown")
            
            if self.geofence:
                is_safe, distance = check_location_safety(self.current_location, self.geofence)
                status_icon = "[SAFE]" if is_safe else "[ALERT]"
                status_text = "Safe" if is_safe else f"Outside ({distance:.0f}m)"
                table.add_row("Status", f"{status_icon} {status_text}")
        else:
            table.add_row("Location", "No data")
            table.add_row("Status", "Unknown")
        
        table.add_row("Emergency", self.emergency_state.value.upper())
        
        if self.geofence:
            table.add_row("Geofence", f"{self.geofence.radius_meters}m radius")
        else:
            table.add_row("Geofence", "Not configured")
        
        return Panel(table, title="Status", border_style="cyan")
    
    def _create_alerts(self) -> Panel:
        """Create the alerts panel."""
        if not self.recent_alerts:
            return Panel("No recent alerts", title="Recent Alerts")
        
        table = Table(show_header=True, box=box.SIMPLE)
        table.add_column("Time", style="dim")
        table.add_column("Type", style="bold")
        table.add_column("Message")
        
        for alert in self.recent_alerts[-5:]:  # Show last 5 alerts
            timestamp = alert.get("timestamp", "")
            if timestamp:
                # Format timestamp
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = timestamp[:8]
            else:
                time_str = "Unknown"
            
            alert_type = alert.get("type", "unknown")
            message = alert.get("message", "")
            
            # Color code by severity
            severity = alert.get("severity", "medium")
            if severity == "critical":
                style = "bold red"
            elif severity == "high":
                style = "bold yellow"
            else:
                style = "white"
            
            table.add_row(time_str, alert_type, message, style=style)
        
        return Panel(table, title="Recent Alerts", border_style="yellow")
    
    def _create_controls(self) -> Panel:
        """Create the controls panel."""
        controls_text = Text()
        controls_text.append("Controls:\n\n", style="bold")
        controls_text.append("• Ctrl+C: Exit\n", style="white")
        controls_text.append("• API: ", style="white")
        controls_text.append(f"{self.api_url}\n", style="blue")
        controls_text.append("• Status: ", style="white")
        
        if self.is_running:
            controls_text.append("Running", style="green")
        else:
            controls_text.append("Stopped", style="red")
        
        return Panel(controls_text, title="Controls", border_style="magenta")
    
    def _create_footer(self) -> Panel:
        """Create the footer panel."""
        footer_text = Text()
        footer_text.append("KiddoTrack-Lite v1.0 | ", style="dim")
        footer_text.append("CISC 593 - Software Verification & Validation | ", style="dim")
        footer_text.append("Team: Vivek, Isit, Bhushan, Pooja", style="dim")
        
        return Panel(Align.center(footer_text), border_style="blue")


async def main():
    """Main entry point."""
    console = ParentConsole()
    await console.start()


if __name__ == "__main__":
    asyncio.run(main()) 