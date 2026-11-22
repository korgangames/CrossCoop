"""
Hub Client for SplitScreen.Me / Nucleus Co-op API and database caching.
"""

import os
import json
import urllib.request
import zipfile
import io
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
PACKAGE_CACHE_DIR = CACHE_DIR / "packages"
DATABASE_PATH = Path(__file__).resolve().parent.parent.parent / "nucleus_supported_games.json"

class HubClient:
    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        PACKAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.games = {}
        self.load_database()

    def load_database(self):
        if DATABASE_PATH.exists():
            with open(DATABASE_PATH, "r", encoding="utf-8") as f:
                self.games = json.load(f)
        return self.games

    def search(self, query: str = "", genre: str = "All", min_players: int = 0):
        results = []
        q = query.lower().strip()
        for hid, h in self.games.items():
            gname = h.get("gameName", "")
            title = h.get("title", "")
            
            # Query match
            if q and (q not in gname.lower() and q not in title.lower()):
                continue

            # Genre match
            if genre != "All":
                genres = h.get("genres", [])
                if not any(genre.lower() == g.lower() for g in genres):
                    continue

            # Min players
            max_players = h.get("maxPlayers", 2)
            if isinstance(max_players, int) and max_players < min_players:
                continue

            results.append((hid, h))

        # Sort by downloadCount descending by default
        results.sort(key=lambda x: x[1].get("downloadCount", 0), reverse=True)
        return results

    def get_all_genres(self):
        genres = set()
        for h in self.games.values():
            for g in h.get("genres", []):
                genres.add(g)
        return sorted(list(genres))

    def fetch_handler_package(self, package_id: str, progress_callback=None) -> bytes:
        """Fetch package zip from CDN with local disk caching."""
        cached_file = PACKAGE_CACHE_DIR / f"{package_id}.zip"
        if cached_file.exists():
            return cached_file.read_bytes()

        url = f"https://hub.splitscreen.me/cdn/storage/packages/{package_id}/original/{package_id}.zip"
        req = urllib.request.Request(url, headers={"User-Agent": "CrossCoop/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()

        cached_file.write_bytes(data)
        return data

    def extract_handler_js(self, package_id: str) -> str:
        """Extract handler.js content from package."""
        pkg_bytes = self.fetch_handler_package(package_id)
        with zipfile.ZipFile(io.BytesIO(pkg_bytes)) as zf:
            for name in zf.namelist():
                if name.endswith("handler.js"):
                    return zf.read(name).decode("utf-8", errors="ignore")
        return ""
