import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import websocket

from src.models import Destination
from src.services.location_catalog import LocationCatalogService


class NavigationService:
    """Service to handle destination lookup and navigation start requests."""

    def __init__(
        self,
        locations_file: str = "data/locations.json",
        history_file: str = "data/Navigation history/history.json",
    ):
        self.catalog = LocationCatalogService(locations_file=locations_file)
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.rosbridge_url = os.getenv("ROSBRIDGE_URL", "ws://localhost:9090").strip()
        self.navigation_topic = os.getenv("ROS_NAVIGATION_TOPIC", "/navigation_goal").strip()

    def list_locations(self):
        return self.catalog.list_locations()

    def get_categories(self):
        return ["All", *self.catalog.get_categories()]

    def search_locations(self, query: str = "", category: str = "All", limit: Optional[int] = None):
        return self.catalog.search_locations(query=query, category=category, limit=limit)

    def resolve_location(self, user_input: str) -> Optional[Destination]:
        return self.catalog.resolve_location(user_input)

    def prepare_navigation(self, user_input: str) -> Optional[dict]:
        location = self.resolve_location(user_input)
        if not location:
            return None

        # Use getattr so it doesn't crash if the attribute is missing
        matched = getattr(location, 'matched_name', None) or location.location_name

        return {
            "location_name": location.location_name,
            "category": location.category,
            "description": location.description,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "building": location.building,
            "floor": location.floor,
            "accessible": location.accessible,
            "matched_name": matched,
        }

    def get_coordinates(self, user_input: str):
        location = self.prepare_navigation(user_input)
        if not location:
            return None, None
        return location["latitude"], location["longitude"]

    def start_navigation(self, user_input: str, requested_by: str = "ui") -> Optional[dict]:
        navigation_payload = self.prepare_navigation(user_input)
        if not navigation_payload:
            return None

        dispatch_result = self._dispatch_navigation_command(navigation_payload)
        navigation_payload["dispatch"] = dispatch_result

        history = self._read_history()
        history.append(
            {
                "location": navigation_payload["location_name"],
                "matched_name": navigation_payload["matched_name"],
                "category": navigation_payload["category"],
                "date": datetime.now(timezone.utc).isoformat(),
                "requested_by": requested_by,
                "coordinates": {
                    "latitude": navigation_payload["latitude"],
                    "longitude": navigation_payload["longitude"],
                },
                "dispatch": dispatch_result,
            }
        )
        self._write_history(history)

        return navigation_payload

    def get_history(self, limit: Optional[int] = None) -> list[dict]:
        history = list(reversed(self._read_history()))
        return history[:limit] if limit else history

    def _read_history(self) -> list[dict]:
        try:
            with self.history_file.open("r", encoding="utf-8") as handle:
                try:
                    return json.load(handle)
                except json.JSONDecodeError:
                    return []
        except FileNotFoundError:
            return []

    def _write_history(self, history: list[dict]) -> None:
        with self.history_file.open("w", encoding="utf-8") as handle:
            json.dump(history, handle, indent=4, ensure_ascii=False)

    def _dispatch_navigation_command(self, navigation_payload: dict) -> dict:
        command_payload = {
            "destination": navigation_payload["location_name"],
            "matched_name": navigation_payload["matched_name"],
            "coordinates": {
                "latitude": navigation_payload["latitude"],
                "longitude": navigation_payload["longitude"],
            },
            "building": navigation_payload["building"],
            "floor": navigation_payload["floor"],
        }

        # Send the command to ROS2 via rosbridge using a WebSocket connection
        try:
            ws = websocket.create_connection(self.rosbridge_url)
            msg = {
                "op": "publish",
                "topic": self.navigation_topic,
                "type": "std_msgs/String",
                "msg": {"data": json.dumps(command_payload)}
            }
            ws.send(json.dumps(msg))
            ws.close()
            return {
                "status": "sent",
                "message": "Navigation command sent to ROS2 via rosbridge.",
                "topic": self.navigation_topic,
                "payload": command_payload,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to send navigation command: {str(e)}",
                "rosbridge_url": self.rosbridge_url,
                "topic": self.navigation_topic,
            }
