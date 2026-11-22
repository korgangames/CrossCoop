"""
PartyDeck Community Handlers Browser & Repository Client.
Fetches verified and community-submitted PartyDeck handlers from GitHub and community sources.
"""

import json
import urllib.request
import re
from pathlib import Path

# Built-in verified PartyDeck community handlers database
VERIFIED_PARTYDECK_HANDLERS = [
    {
        "name": "Dark Souls III (Seamless Co-op)",
        "author": "DaughterOfMars",
        "category": "Action RPG",
        "max_players": 4,
        "exec": "DarkSoulsIII.exe",
        "steam_appid": 374320,
        "runtime": "umu",
        "use_goldberg": True,
        "args": "-windowed",
        "env": "WINEDLLOVERRIDES=\"dxgi=n,b\"",
        "source": "https://github.com/partydeck/partydeck/issues/241",
        "description": "Seamless Co-op mod handler for legit Steam copy (DRM untouched). Enables smooth 4-player co-op without invasion interruptions."
    },
    {
        "name": "Call of Duty Alt Launcher (WaW, BO1, BO2, MW3)",
        "author": "framilano",
        "category": "First-Person Shooter",
        "max_players": 4,
        "exec": "CoD_Alt_Launcher.exe",
        "steam_appid": 10090,
        "runtime": "umu",
        "use_goldberg": True,
        "args": "",
        "env": "",
        "source": "https://github.com/partydeck/partydeck/issues/190",
        "description": "Multi-game handler for World at War, Black Ops 1, Black Ops 2, and Modern Warfare 3. Supports offline split-screen bots and zombies."
    },
    {
        "name": "System Shock 2 (25th Anniversary Remaster)",
        "author": "framilano",
        "category": "Sci-Fi / Immersive Sim",
        "max_players": 4,
        "exec": "Shock2.exe",
        "steam_appid": 238210,
        "runtime": "umu",
        "use_goldberg": True,
        "args": "-windowed",
        "env": "",
        "source": "https://github.com/partydeck/partydeck/issues/229",
        "description": "System Shock 2 25th Anniversary Remaster split-screen co-op handler. Fully isolates controllers and player saves."
    },
    {
        "name": "shadPS4 (Bloodborne testing)",
        "author": "framilano",
        "category": "Emulator / Action",
        "max_players": 2,
        "exec": "shadPS4.exe",
        "steam_appid": None,
        "runtime": "native",
        "use_goldberg": False,
        "args": "",
        "env": "",
        "source": "https://github.com/partydeck/partydeck/issues/219",
        "description": "Specialized emulator launcher mapping dual PS4/PS5 gamepads to separate shadPS4 windows."
    },
    {
        "name": "Left 4 Dead 2",
        "author": "Community Verified",
        "category": "Co-Op Zombie Shooter",
        "max_players": 4,
        "exec": "left4dead2.exe",
        "steam_appid": 550,
        "runtime": "umu",
        "use_goldberg": True,
        "args": "-windowed -noborder -novid",
        "env": "",
        "source": "PartyDeck Verified",
        "description": "Standard 4-player split-screen campaign and versus mode with separate Steam IDs via Goldberg."
    },
    {
        "name": "Risk of Rain 2",
        "author": "Community Verified",
        "category": "Roguelike Action",
        "max_players": 4,
        "exec": "Risk of Rain 2.exe",
        "steam_appid": 632360,
        "runtime": "umu",
        "use_goldberg": True,
        "args": "",
        "env": "",
        "source": "PartyDeck Verified",
        "description": "Full local 4-player co-op with isolated profiles and Goldberg LAN emulation."
    },
    {
        "name": "Borderlands 2",
        "author": "Community Verified",
        "category": "Looter Shooter",
        "max_players": 4,
        "exec": "Borderlands2.exe",
        "steam_appid": 49520,
        "runtime": "umu",
        "use_goldberg": True,
        "args": "-windowed -noborder",
        "env": "",
        "source": "PartyDeck Verified",
        "description": "4-player Pandora vault hunting on a single PC or Steam Deck dock."
    },
    {
        "name": "Don't Starve Together",
        "author": "Community Verified",
        "category": "Survival",
        "max_players": 4,
        "exec": "dontstarve_steam.exe",
        "steam_appid": 322330,
        "runtime": "umu",
        "use_goldberg": True,
        "args": "",
        "env": "",
        "source": "PartyDeck Verified",
        "description": "Local survival world with separate client accounts and split-screen composition."
    },
    {
        "name": "Wreckfest",
        "author": "Community Verified",
        "category": "Racing / Destruction",
        "max_players": 4,
        "exec": "Wreckfest_x64.exe",
        "steam_appid": 228380,
        "runtime": "umu",
        "use_goldberg": True,
        "args": "-windowed -noborder",
        "env": "",
        "source": "PartyDeck Verified",
        "description": "Demolition derby split-screen action for 2 to 4 controllers."
    },
    {
        "name": "Deep Rock Galactic",
        "author": "Community Verified",
        "category": "Co-Op Mining Shooter",
        "max_players": 4,
        "exec": "FSD.exe",
        "steam_appid": 548430,
        "runtime": "umu",
        "use_goldberg": True,
        "args": "-windowed",
        "env": "",
        "source": "PartyDeck Verified",
        "description": "4-player dwarf squad mining expeditions with isolated saves and Goldberg networking."
    }
]

class PartyDeckCommunityClient:
    def __init__(self):
        self.handlers = list(VERIFIED_PARTYDECK_HANDLERS)

    def fetch_live_issues(self):
        """Fetch latest handler release issues from GitHub API."""
        url = "https://api.github.com/repos/partydeck/partydeck/issues?state=all&per_page=100"
        req = urllib.request.Request(url, headers={"User-Agent": "CrossCoop/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                issues = json.loads(resp.read().decode("utf-8"))
            
            for iss in issues:
                title = iss.get("title", "")
                labels = [l.get("name", "").lower() for l in iss.get("labels", [])]
                if "handler" in labels or "handler release" in title.lower() or "[handler]" in title.lower():
                    # Parse game title
                    clean_title = re.sub(r'\[Handler Release\]|\[Game issue\]|\[Handler Request\]', '', title, flags=re.IGNORECASE).strip()
                    # Check if already present
                    if not any(h["name"].lower() == clean_title.lower() for h in self.handlers):
                        self.handlers.append({
                            "name": clean_title,
                            "author": iss.get("user", {}).get("login", "Community"),
                            "category": "Community Submissions",
                            "max_players": 4,
                            "exec": "Game.exe",
                            "steam_appid": None,
                            "runtime": "umu",
                            "use_goldberg": True,
                            "args": "-windowed",
                            "env": "",
                            "source": iss.get("html_url"),
                            "description": iss.get("body", "")[:350]
                        })
        except Exception as e:
            print(f"Error fetching live issues: {e}")
        return self.handlers

    def search(self, query: str = "", category: str = "All"):
        q = query.lower().strip()
        results = []
        for h in self.handlers:
            if q and (q not in h["name"].lower() and q not in h.get("description", "").lower()):
                continue
            if category != "All" and h.get("category") != category:
                continue
            results.append(h)
        return results

    def get_categories(self):
        cats = set(h.get("category", "General") for h in self.handlers)
        return sorted(list(cats))
