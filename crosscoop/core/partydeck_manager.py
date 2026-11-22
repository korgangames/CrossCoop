"""
PartyDeck local installation and handler manager.
"""

import os
import json
import shutil
import subprocess
from pathlib import Path

DEFAULT_PARTYDECK_DIR = Path.home() / ".local" / "share" / "partydeck"
DEFAULT_HANDLERS_DIR = DEFAULT_PARTYDECK_DIR / "handlers"
WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent

class PartyDeckManager:
    def __init__(self, handlers_dir=None):
        self.handlers_dir = Path(handlers_dir) if handlers_dir else DEFAULT_HANDLERS_DIR
        self.handlers_dir.mkdir(parents=True, exist_ok=True)

    def get_installed_handlers(self):
        """Scan and return all installed PartyDeck handlers."""
        handlers = []
        if not self.handlers_dir.exists():
            return handlers

        for item in sorted(self.handlers_dir.iterdir()):
            if item.is_dir():
                json_path = item / "handler.json"
                if json_path.exists():
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            handlers.append({
                                "folder_name": item.name,
                                "path": str(item),
                                "json_path": str(json_path),
                                "data": data
                            })
                    except Exception as e:
                        print(f"Error reading {json_path}: {e}")
        return handlers

    def is_installed(self, game_name: str) -> bool:
        """Check if a game by name is installed in PartyDeck."""
        clean = game_name.strip().lower()
        for h in self.get_installed_handlers():
            h_name = h["data"].get("name", h["folder_name"]).strip().lower()
            if h_name == clean or h["folder_name"].lower() == clean:
                return True
        return False

    def save_handler(self, folder_name: str, handler_data: dict) -> Path:
        """Save/install a handler to PartyDeck."""
        clean_folder = "".join(c for c in folder_name if c.isalnum() or c in " ._-").strip()
        target_dir = self.handlers_dir / clean_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        json_file = target_dir / "handler.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(handler_data, f, indent=2)
        return json_file

    def delete_handler(self, folder_name: str) -> bool:
        """Delete an installed handler."""
        target_dir = self.handlers_dir / folder_name
        if target_dir.exists() and target_dir.is_dir():
            shutil.rmtree(target_dir)
            return True
        return False

    @property
    def profiles_dir(self) -> Path:
        return DEFAULT_PARTYDECK_DIR / "profiles"

    def get_profiles(self) -> list[str]:
        """Return list of persistent profile names (excluding .guests)."""
        if not self.profiles_dir.exists():
            return []
        profiles = []
        for item in self.profiles_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                profiles.append(item.name)
        return sorted(profiles)

    def create_profile(self, name: str) -> Path:
        """Create a persistent PartyDeck profile matching its exact directory structure."""
        clean_name = "".join(c for c in name if c.isalnum() or c in " _-").strip()
        if not clean_name:
            clean_name = "Player"

        prof_dir = self.profiles_dir / clean_name
        steam_settings = prof_dir / "steam" / "settings"

        # Windata folders
        for sub in ["AppData/Local/Temp", "AppData/LocalLow", "AppData/Roaming", "Documents", "Saved Games", "Desktop"]:
            (prof_dir / "windata" / sub).mkdir(parents=True, exist_ok=True)

        # Linux home folders (for native games like Terraria)
        (prof_dir / "home" / ".local" / "share").mkdir(parents=True, exist_ok=True)
        (prof_dir / "home" / ".config").mkdir(parents=True, exist_ok=True)
        steam_settings.mkdir(parents=True, exist_ok=True)

        # Goldberg/Steam config
        ini_file = steam_settings / "configs.user.ini"
        if not ini_file.exists():
            ini_file.write_text(f"[user::general]\naccount_name={clean_name}\n", encoding="utf-8")

        return prof_dir

    def ensure_default_profiles(self, count: int = 4) -> list[str]:
        """Ensure standard persistent profiles (Player1, Player2, etc.) exist."""
        existing = self.get_profiles()
        if not existing:
            for i in range(1, count + 1):
                self.create_profile(f"Player{i}")
        return self.get_profiles()

    def find_partydeck_executable(self) -> str:
        """Look for partydeck executable in PATH or workspace."""
        # 1. Check workspace
        local_appimage = WORKSPACE_DIR / "partydeck.AppImage"
        if local_appimage.exists() and os.access(local_appimage, os.X_OK):
            return str(local_appimage)

        # 2. Check which partydeck
        path_which = shutil.which("partydeck")
        if path_which:
            return path_which

        return ""

    def launch_partydeck(self):
        """Launch PartyDeck in background."""
        exe = self.find_partydeck_executable()
        if exe:
            subprocess.Popen([exe], start_new_session=True)
            return True, exe
        return False, "PartyDeck executable not found. Make sure partydeck.AppImage is in the workspace or installed in PATH."
