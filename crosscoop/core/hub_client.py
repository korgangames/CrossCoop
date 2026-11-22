"""
Hub Client for SplitScreen.Me / Nucleus Co-op API, live sync, and database caching.
"""

import os
import json
import asyncio
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
            try:
                with open(DATABASE_PATH, "r", encoding="utf-8") as f:
                    self.games = json.load(f)
            except Exception as e:
                print(f"Error loading database: {e}")
        return self.games

    def save_database(self):
        try:
            with open(DATABASE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.games, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving database: {e}")

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

    def fetch_handler_package(self, package_id: str) -> bytes:
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

    def sync_from_live_hub(self, progress_callback=None) -> tuple[int, int]:
        """
        Polls live SplitScreen.Me Hub to discover brand new games or handler updates.
        Returns (new_count, updated_count).
        """
        if progress_callback:
            progress_callback("Connecting to live SplitScreen.Me Hub...")

        fetched_handlers = {}
        
        # 1. Try DDP WebSocket first for complete database fetch
        try:
            import websockets
            async def ddp_fetch():
                uri = "wss://hub.splitscreen.me/websocket"
                res = {}
                for sort_order in ["down", "up"]:
                    async with websockets.connect(uri) as ws:
                        await ws.recv() # server_id
                        await ws.send(json.dumps({"msg": "connect", "version": "1", "support": ["1"]}))
                        await ws.recv() # connected
                        await ws.send(json.dumps({
                            "msg": "sub",
                            "id": f"sub-{sort_order}",
                            "name": "handlers",
                            "params": ["", "alphabetical", sort_order, 600, [], ""]
                        }))
                        while True:
                            try:
                                raw = await asyncio.wait_for(ws.recv(), timeout=4.0)
                                d = json.loads(raw)
                                if d.get("msg") == "added" and d.get("collection") == "Handlers":
                                    res[d.get("id")] = d.get("fields", {})
                                elif d.get("msg") == "ready":
                                    break
                            except asyncio.TimeoutError:
                                break
                return res

            fetched_handlers = asyncio.run(ddp_fetch())
        except Exception as e:
            print(f"DDP sync fallback: {e}")

        # 2. Fallback to REST API if DDP returned empty
        if not fetched_handlers:
            try:
                if progress_callback:
                    progress_callback("Fetching via REST API...")
                req = urllib.request.Request("https://hub.splitscreen.me/api/v1/allhandlers", headers={"User-Agent": "CrossCoop/1.0"})
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for h in data.get("Handlers", []):
                        hid = h.get("_id")
                        if hid:
                            fetched_handlers[hid] = h
            except Exception as e:
                print(f"REST sync error: {e}")

        if not fetched_handlers:
            return 0, 0

        # Merge updates
        new_count = 0
        updated_count = 0

        for hid, h in fetched_handlers.items():
            if hid not in self.games:
                self.games[hid] = h
                new_count += 1
            else:
                # Check if currentPackage or version changed
                old = self.games[hid]
                if old.get("currentPackage") != h.get("currentPackage") or old.get("currentVersion") != h.get("currentVersion"):
                    self.games[hid] = h
                    updated_count += 1

        if new_count > 0 or updated_count > 0:
            self.save_database()

        return new_count, updated_count
