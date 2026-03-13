import json
from rapidfuzz import process, fuzz
from datetime import datetime

class NavigationService:
    """Service to handle navigation-related tasks, such as retrieving coordinates for a location and interfacing with ROS."""

    def __init__(self, locations_file: str = "data/locations.json", history_file: str = "data/Navigation history/history.json"):
        self.locations_file = locations_file
        self.history_file = history_file

    def get_coordinates(self, user_input: str):
        # Load locations (your existing logic)
        with open(self.locations_file, "r") as f:
            locations = json.load(f)

        # Build mapping of names + aliases to coordinates
        name_to_coords = {}
        for loc in locations:
            coords = (loc["coordinates"]["latitude"], loc["coordinates"]["longitude"])
            name_to_coords[loc["location_name"].lower()] = coords
            for alias in loc.get("aliases", []):
                name_to_coords[alias.lower()] = coords

        # Fuzzy match
        match, score, _ = process.extractOne(user_input.lower(), name_to_coords.keys(), scorer=fuzz.WRatio)
        if score < 60:
            return None, None

        lat, long = name_to_coords[match]

        # --- FIX: read history in read mode ---
        try:
            with open(self.history_file, "r") as f:
                try:
                    history = json.load(f)
                except json.JSONDecodeError:
                    history = []
        except FileNotFoundError:
            history = []

        # Append new entry
        history.append({
            "location": user_input,
            "date": datetime.utcnow().isoformat(),
            "coordinates": {"latitude": lat, "longitude": long}
        })

        # Save entire array back
        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=4)

        return name_to_coords[match]