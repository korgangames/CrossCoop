"""
Persistent Settings & Application Launcher Manager.
Allows users to connect and customize their PartyDeck and Nucleus Co-op bootables/executables.
"""

import os
import json
import shutil
import subprocess
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "crosscoop"
CONFIG_FILE = CONFIG_DIR / "config.json"
WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent

class SettingsManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.settings = self.load_settings()

    def get_default_settings(self) -> dict:
        """Auto-detect defaults from workspace or system PATH."""
        # PartyDeck
        partydeck_path = ""
        local_appimage = WORKSPACE_DIR / "partydeck.AppImage"
        if local_appimage.exists():
            partydeck_path = str(local_appimage)
        elif shutil.which("partydeck"):
            partydeck_path = shutil.which("partydeck")

        # Nucleus Co-op
        nucleus_path = ""
        local_sh = WORKSPACE_DIR / "run_nucleus.sh"
        local_exe = WORKSPACE_DIR / "nucleus_coop" / "NucleusCoop.exe"
        if local_sh.exists():
            nucleus_path = str(local_sh)
        elif local_exe.exists():
            nucleus_path = str(local_exe)

        # Wine
        wine_path = shutil.which("wine") or "/usr/bin/wine"
        wine_prefix = str(Path.home() / ".wine")

        return {
            "partydeck_path": partydeck_path,
            "nucleus_path": nucleus_path,
            "wine_path": wine_path,
            "wine_prefix": wine_prefix,
            "partydeck_handlers_dir": str(Path.home() / ".local" / "share" / "partydeck" / "handlers")
        }

    def load_settings(self) -> dict:
        defaults = self.get_default_settings()
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    defaults.update(saved)
            except Exception as e:
                print(f"Error reading config: {e}")
        return defaults

    def save_settings(self, new_settings: dict) -> bool:
        self.settings.update(new_settings)
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def launch_partydeck(self) -> tuple[bool, str]:
        """Launch configured PartyDeck executable/AppImage."""
        exe = self.settings.get("partydeck_path", "").strip()
        if not exe or not Path(exe).exists():
            return False, f"PartyDeck bootable not found at: '{exe}'. Please configure it in Settings."

        try:
            if not os.access(exe, os.X_OK):
                os.chmod(exe, 0o755)
            subprocess.Popen([exe], start_new_session=True)
            return True, f"PartyDeck launched from: {exe}"
        except Exception as e:
            return False, f"Failed to launch PartyDeck: {str(e)}"

    def launch_nucleus(self) -> tuple[bool, str]:
        """Launch configured Nucleus Co-op executable or runner script."""
        n_path = self.settings.get("nucleus_path", "").strip()
        wine_path = self.settings.get("wine_path", "/usr/bin/wine").strip()
        wine_prefix = self.settings.get("wine_prefix", "").strip()

        if not n_path or not Path(n_path).exists():
            return False, f"Nucleus Co-op bootable not found at: '{n_path}'. Please configure it in Settings."

        env = os.environ.copy()
        if wine_prefix and Path(wine_prefix).exists():
            env["WINEPREFIX"] = wine_prefix

        try:
            # If bash script (e.g. run_nucleus.sh)
            if n_path.endswith(".sh"):
                if not os.access(n_path, os.X_OK):
                    os.chmod(n_path, 0o755)
                subprocess.Popen([n_path], start_new_session=True, env=env)
                return True, f"Nucleus Co-op launcher script executed: {n_path}"

            # If Windows EXE (e.g. NucleusCoop.exe)
            if not wine_path or not Path(wine_path).exists():
                return False, f"Wine executable not found at '{wine_path}' to run NucleusCoop.exe."

            exe_dir = str(Path(n_path).parent)
            subprocess.Popen([wine_path, n_path], cwd=exe_dir, env=env, start_new_session=True)
            return True, f"Nucleus Co-op launched via Wine ({wine_path}): {n_path}"
        except Exception as e:
            return False, f"Failed to launch Nucleus Co-op: {str(e)}"
