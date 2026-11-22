#!/usr/bin/env python3
"""
Nucleus Co-op to PartyDeck Handler Bridge
Extracts game parameters from Nucleus Co-op handlers (SplitScreen.Me Hub)
and converts them into native PartyDeck handlers (.json / .pd2).
"""

import sys
import os
import re
import json
import io
import zipfile
import urllib.request
import argparse
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
DATABASE_PATH = WORKSPACE / "nucleus_supported_games.json"
PARTYDECK_HANDLERS_DIR = Path.home() / ".local" / "share" / "partydeck" / "handlers"

def load_database():
    if not DATABASE_PATH.exists():
        print(f"Error: {DATABASE_PATH} not found. Run database sync first.")
        sys.exit(1)
    with open(DATABASE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def search_games(query, db):
    query_lower = query.lower()
    matches = []
    for hid, h in db.items():
        gname = h.get("gameName", "")
        title = h.get("title", "")
        if query_lower in gname.lower() or query_lower in title.lower():
            matches.append((hid, h))
    return matches

def fetch_nucleus_package(package_id):
    url = f"https://hub.splitscreen.me/cdn/storage/packages/{package_id}/original/{package_id}.zip"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception as e:
        print(f"Error downloading package {package_id}: {e}")
        return None

def parse_handler_js(content):
    def get_str(pattern, default=""):
        m = re.search(pattern, content)
        return m.group(1).strip() if m else default

    def get_int(pattern, default=None):
        m = re.search(pattern, content)
        if m:
            try:
                return int(m.group(1).strip())
            except ValueError:
                return default
        return default

    exec_name = get_str(r'Game\.ExecutableName\s*=\s*[\"\']([^\"\']+)[\"\']')
    steam_id = get_int(r'Game\.SteamID\s*=\s*[\"\']?(\d+)[\"\']?')
    args = get_str(r'Game\.StartArguments\s*=\s*[\"\']([^\"\']*)[\"\']')
    pause = get_int(r'Game\.PauseBetweenStarts\s*=\s*(\d+)', default=5)
    
    use_goldberg = bool(
        re.search(r'Game\.UseGoldberg\s*=\s*true', content, re.IGNORECASE) or
        re.search(r'Game\.NeedsSteamEmulation\s*=\s*true', content, re.IGNORECASE)
    )

    return {
        "exec": exec_name,
        "steam_appid": steam_id,
        "args": args,
        "use_goldberg": use_goldberg,
        "pause_between_starts": float(pause) if pause else 5.0
    }

def convert_handler(hid, hinfo, install_to_partydeck=True):
    gname = hinfo.get("gameName", "Unknown Game")
    pkg_id = hinfo.get("currentPackage")
    if not pkg_id:
        print(f"Error: No package found for '{gname}' (ID: {hid})")
        return None

    print(f"Fetching Nucleus package for '{gname}' ({pkg_id})...")
    pkg_bytes = fetch_nucleus_package(pkg_id)
    if not pkg_bytes:
        return None

    try:
        zf = zipfile.ZipFile(io.BytesIO(pkg_bytes))
    except Exception as e:
        print(f"Invalid zip archive: {e}")
        return None

    # Find handler.js
    js_filename = None
    for name in zf.namelist():
        if name.endswith("handler.js"):
            js_filename = name
            break

    if not js_filename:
        print("Could not find handler.js inside package.")
        return None

    js_content = zf.read(js_filename).decode("utf-8", errors="ignore")
    parsed = parse_handler_js(js_content)

    clean_name = re.sub(r'[\/:*?"<>|]', '', gname).strip()
    party_handler = {
        "name": clean_name,
        "author": f"Nucleus Porter ({hinfo.get('ownerName', 'Community')})",
        "version": "1.0",
        "info": f"Converted from Nucleus Co-op Handler (Hub ID: {hid}). Description: {hinfo.get('description', '')[:200]}",
        "spec_ver": 3,
        "path_gameroot": "",
        "runtime": "umu",
        "exec": parsed["exec"],
        "args": parsed["args"],
        "env": "",
        "sdl2_override": "No",
        "pause_between_starts": parsed["pause_between_starts"],
        "use_mangohud": False,
        "use_goldberg": parsed["use_goldberg"],
        "ps_xinput": True,
        "steam_appid": parsed["steam_appid"],
        "game_null_paths": [],
        "overrides": {}
    }

    # Save locally or directly to PartyDeck
    if install_to_partydeck:
        target_dir = PARTYDECK_HANDLERS_DIR / clean_name
        target_dir.mkdir(parents=True, exist_ok=True)
        json_file = target_dir / "handler.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(party_handler, f, indent=2)
        print(f"Successfully installed handler to: {json_file}")
    
    # Also save a copy in the workspace
    workspace_out = WORKSPACE / f"partydeck_handler_{clean_name}.json"
    with open(workspace_out, "w", encoding="utf-8") as f:
        json.dump(party_handler, f, indent=2)
    print(f"Local copy saved to: {workspace_out}")

    return party_handler

def main():
    parser = argparse.ArgumentParser(description="Convert Nucleus Co-op Handlers to PartyDeck on Linux")
    parser.add_argument("-s", "--search", type=str, help="Search games in Nucleus database")
    parser.add_argument("-c", "--convert", type=str, help="Convert a game by exact name or Nucleus handler ID")
    parser.add_argument("--no-install", action="store_true", help="Do not install directly to ~/.local/share/partydeck/handlers")

    args = parser.parse_args()
    db = load_database()

    if args.search:
        results = search_games(args.search, db)
        print(f"Found {len(results)} matches for '{args.search}':")
        for hid, h in results[:20]:
            print(f"  [{hid}] {h.get('gameName')} (Downloads: {h.get('downloadCount', 0):,})")
        if len(results) > 20:
            print(f"  ... and {len(results) - 20} more.")
        return

    if args.convert:
        target = args.convert.strip()
        hinfo = db.get(target)
        hid = target
        if not hinfo:
            # Search by name
            matches = search_games(target, db)
            if not matches:
                print(f"No game found matching '{target}'")
                return
            hid, hinfo = matches[0]
            print(f"Matched '{target}' to '{hinfo.get('gameName')}' (ID: {hid})")
        
        convert_handler(hid, hinfo, install_to_partydeck=not args.no_install)
        return

    parser.print_help()

if __name__ == "__main__":
    main()
