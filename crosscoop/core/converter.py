"""
Two-way conversion engine between Nucleus Co-op and PartyDeck.
Includes lenient parser for unconfirmed, unofficial, and community-scripted handlers.
"""

import re
import json
import zipfile
import io
from pathlib import Path

def parse_lenient_handler(content: str, filename: str = "", meta: dict = None) -> dict:
    """
    Lenient parser for unofficial, unconfirmed, or non-standard handlers
    (forum posts, community scripts, Discord shares).
    """
    meta = meta or {}

    def get_str(patterns, default=""):
        if isinstance(patterns, str):
            patterns = [patterns]
        for pat in patterns:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if val:
                    return val
        return default

    def get_int(patterns, default=None):
        if isinstance(patterns, str):
            patterns = [patterns]
        for pat in patterns:
            m = re.search(pat, content, re.IGNORECASE)
            if m:
                try:
                    return int(m.group(1).strip())
                except ValueError:
                    continue
        return default

    # 1. Game Name
    game_name = get_str([
        r'Game\.GameName\s*=\s*[\"\']([^\"\']+)[\"\']',
        r'Game\.Name\s*=\s*[\"\']([^\"\']+)[\"\']',
        r'//\s*(?:Game|Title|Handler(?:\s+for)?)\s*:\s*([^\r\n]+)',
        r'/\*\s*(?:Game|Title|Handler(?:\s+for)?)\s*:\s*([^\r\n*]+)'
    ])
    if not game_name:
        game_name = meta.get("gameName", meta.get("title", ""))
    if not game_name and filename:
        stem = Path(filename).stem
        # Clean up stem: e.g. "Borderlands3_unofficial_v1" -> "Borderlands 3 Unofficial V1"
        game_name = re.sub(r'[_.-]+', ' ', stem).title()
    if not game_name:
        game_name = "Custom Game"

    clean_name = re.sub(r'[\/:*?"<>|]', '', game_name).strip()

    # 2. Executable name
    exec_name = get_str([
        r'Game\.ExecutableName\s*=\s*[\"\']([^\"\']+)[\"\']',
        r'Game\.ExecutableToLaunch\s*=\s*[\"\']([^\"\']+)[\"\']',
        r'Game\.LauncherExe\s*=\s*[\"\']([^\"\']+)[\"\']',
        r'Game\.Binary\s*=\s*[\"\']([^\"\']+)[\"\']',
        r'ExecutableContext\s*=\s*[\"\']([^\"\']+)[\"\']',
        r'(?:var|let|const)\s+(?:exe|executable|binary)\s*=\s*[\"\']([^\"\']+)[\"\']',
        r'[\"\']([a-zA-Z0-9_\-\.]+\.(?:exe|bin|x86_64))[\"\']'
    ])
    if not exec_name:
        exec_name = re.sub(r'[^a-zA-Z0-9]', '', clean_name) + ".exe"

    # 3. Steam AppID
    steam_id = get_int([
        r'Game\.SteamID\s*=\s*[\"\']?(\d+)[\"\']?',
        r'Game\.AppId\s*=\s*[\"\']?(\d+)[\"\']?',
        r'steam_appid\s*[:=]\s*[\"\']?(\d+)[\"\']?',
        r'store\.steampowered\.com/app/(\d+)',
        r'AppID\s*[:=]\s*[\"\']?(\d+)[\"\']?'
    ])
    if steam_id is None and meta.get("steamAppId"):
        try:
            steam_id = int(meta["steamAppId"])
        except ValueError:
            pass

    # 4. Startup Arguments
    args = get_str([
        r'Game\.StartArguments\s*=\s*[\"\']([^\"\']*)[\"\']',
        r'Game\.CommandLine\s*=\s*[\"\']([^\"\']*)[\"\']',
        r'(?:var|let|const)\s+(?:args|cmd|arguments)\s*=\s*[\"\']([^\"\']*)[\"\']'
    ])

    # 5. Pause timing
    pause = get_int([
        r'Game\.PauseBetweenStarts\s*=\s*(\d+)',
        r'Game\.HandlerInterval\s*=\s*(\d+)'
    ], default=5)

    # 6. Goldberg / LAN Emulation
    use_goldberg = bool(
        re.search(r'Game\.UseGoldberg\s*=\s*true', content, re.IGNORECASE) or
        re.search(r'Game\.NeedsSteamEmulation\s*=\s*true', content, re.IGNORECASE) or
        "goldberg" in content.lower() or
        "steam_api" in content.lower() or
        "smartsteamemu" in content.lower()
    )

    # 7. Author
    author = get_str([
        r'Hub\.Maintainer\.Name\s*=\s*[\"\']([^\"\']+)[\"\']',
        r'//\s*Author\s*:\s*([^\r\n]+)',
        r'/\*\s*Author\s*:\s*([^\r\n*]+)'
    ])
    if not author:
        author = meta.get("ownerName", "Unofficial Community Author")

    detected = []
    if steam_id:
        detected.append(f"Steam AppID: {steam_id}")
    if use_goldberg:
        detected.append("Goldberg LAN Emulation")
    if args:
        detected.append(f"Launch Args: {args}")
    if re.search(r'ProtoInput', content, re.IGNORECASE):
        detected.append("ProtoInput Hooking")
    if re.search(r'SymlinkGame\s*=\s*true', content, re.IGNORECASE):
        detected.append("Symlink Sandboxing")

    info = f"Imported via CrossCoop Unofficial Handler Bridge (Author: {author})."
    if detected:
        info += f"\nDetected features: {', '.join(detected)}."
    if meta.get("description"):
        info += f"\n\nNotes: {meta.get('description')[:300]}"

    return {
        "name": clean_name,
        "author": f"CrossCoop ({author})",
        "version": "1.0-custom",
        "info": info,
        "spec_ver": 3,
        "path_gameroot": "",
        "runtime": "umu",
        "exec": exec_name,
        "args": args,
        "env": "",
        "sdl2_override": "No",
        "pause_between_starts": float(pause) if pause is not None else 5.0,
        "use_mangohud": False,
        "use_goldberg": use_goldberg,
        "ps_xinput": True,
        "steam_appid": steam_id,
        "game_null_paths": [],
        "overrides": {},
        "_detected_features": detected,
        "_is_unofficial": True
    }


def parse_nucleus_js(content: str, meta: dict = None) -> dict:
    """Wrapper for backward compatibility, leveraging the lenient parser."""
    return parse_lenient_handler(content, meta=meta)


def import_handler_file(file_path: str) -> dict:
    """
    Imports a local file (.js, .zip, .nc, .json, .txt) and extracts
    the handler specification, raw code, and detected features.
    Handles unconfirmed community packages and loose downloads.
    """
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = p.suffix.lower()

    if ext in [".zip", ".nc", ".pd2"]:
        # Inspect archive
        with zipfile.ZipFile(p, "r") as zf:
            names = zf.namelist()
            
            # Check for steam_appid.txt
            found_steam_id = None
            for n in names:
                if n.endswith("steam_appid.txt"):
                    try:
                        raw_id = zf.read(n).decode("utf-8").strip()
                        if raw_id.isdigit():
                            found_steam_id = int(raw_id)
                    except Exception:
                        pass

            # Check for JSON handler
            json_file = next((n for n in names if n.endswith("handler.json") or n.endswith(".json")), None)
            if json_file and ext == ".pd2":
                raw_json = zf.read(json_file).decode("utf-8", errors="ignore")
                pd_data = json.loads(raw_json)
                if found_steam_id and not pd_data.get("steam_appid"):
                    pd_data["steam_appid"] = found_steam_id
                return {
                    "partydeck_data": pd_data,
                    "raw_code": raw_json,
                    "game_name": pd_data.get("name", p.stem),
                    "detected_features": ["PartyDeck Archive (.pd2)"],
                    "source_path": str(p),
                    "source_type": "archive_json"
                }

            # Check for JS handler
            js_file = next((n for n in names if n.endswith("handler.js") or n.endswith(".js")), None)
            if js_file:
                raw_js = zf.read(js_file).decode("utf-8", errors="ignore")
                pd_data = parse_lenient_handler(raw_js, filename=p.name)
                if found_steam_id and not pd_data.get("steam_appid"):
                    pd_data["steam_appid"] = found_steam_id
                    pd_data["_detected_features"].append(f"Steam AppID: {found_steam_id} (from steam_appid.txt)")

                # Check if archive has goldberg files
                has_goldberg_files = any("goldberg" in n.lower() or "steam_api" in n.lower() for n in names)
                if has_goldberg_files and not pd_data.get("use_goldberg"):
                    pd_data["use_goldberg"] = True
                    pd_data["_detected_features"].append("Goldberg LAN Emulation (bundled in archive)")

                return {
                    "partydeck_data": pd_data,
                    "raw_code": raw_js,
                    "game_name": pd_data.get("name", p.stem),
                    "detected_features": pd_data.get("_detected_features", []),
                    "source_path": str(p),
                    "source_type": "archive_js"
                }

            raise ValueError("No valid handler.js or handler.json found inside archive.")

    elif ext == ".json":
        raw_json = p.read_text(encoding="utf-8", errors="ignore")
        pd_data = json.loads(raw_json)
        return {
            "partydeck_data": pd_data,
            "raw_code": raw_json,
            "game_name": pd_data.get("name", p.stem),
            "detected_features": ["PartyDeck JSON Handler"],
            "source_path": str(p),
            "source_type": "json"
        }

    else:
        # Loose .js or .txt file
        raw_code = p.read_text(encoding="utf-8", errors="ignore")
        pd_data = parse_lenient_handler(raw_code, filename=p.name)
        return {
            "partydeck_data": pd_data,
            "raw_code": raw_code,
            "game_name": pd_data.get("name", p.stem),
            "detected_features": pd_data.get("_detected_features", []),
            "source_path": str(p),
            "source_type": "js"
        }


def partydeck_to_nucleus_js(pd_data: dict) -> str:
    """Generate Nucleus Co-op handler.js from PartyDeck handler data."""
    name = pd_data.get("name", "Unknown Game")
    exec_name = pd_data.get("exec", "Game.exe")
    steam_id = str(pd_data.get("steam_appid") or "")
    args = pd_data.get("args", "")
    use_goldberg = "true" if pd_data.get("use_goldberg") else "false"
    pause = int(pd_data.get("pause_between_starts") or 5)
    guid = re.sub(r'[^a-zA-Z0-9]', '', name) or "CustomGame"

    return f"""// =============================================================================
// Generated by CrossCoop Universal Bridge (PartyDeck -> Nucleus Co-op)
// Game: {name}
// =============================================================================

Game.GameName = "{name}";
Game.HandlerInterval = 100;
Game.SymlinkGame = true;
Game.SymlinkExe = false;
Game.SupportsKeyboard = true;
Game.ExecutableName = "{exec_name}";
Game.SteamID = "{steam_id}";
Game.GUID = "{guid}";
Game.MaxPlayers = 4;
Game.MaxPlayersOneMonitor = 4;
Game.BinariesFolder = "";
Game.WorkingFolder = "";
Game.StartArguments = "{args}";
Game.UseGoldberg = {use_goldberg};
Game.NeedsSteamEmulation = {use_goldberg};
Game.SupportsPositioning = true;
Game.PauseBetweenStarts = {pause};

// Input hooks
Game.Hook.ForceFocus = true;
Game.Hook.ForceFocusWindowName = "";
Game.Hook.DInputEnabled = false;
Game.Hook.DInputForceDisable = true;
Game.Hook.XInputEnabled = true;
Game.Hook.XInputReroute = false;
Game.Hook.CustomDllEnabled = false;

Game.Play = function() {{
    if (Game.UseGoldberg) {{
        Context.CopyScriptFolder();
    }}
}};
"""

def export_partydeck_package(pd_data: dict, out_zip_path: str, extra_files: list = None):
    """Save PartyDeck handler as a .pd2 package (zip)."""
    with zipfile.ZipFile(out_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        json_bytes = json.dumps(pd_data, indent=2).encode("utf-8")
        zf.writestr("handler.json", json_bytes)
        if extra_files:
            for filepath, arcname in extra_files:
                if Path(filepath).exists():
                    zf.write(filepath, arcname)

def export_nucleus_package(js_content: str, out_zip_path: str, extra_files: list = None):
    """Save Nucleus handler as a .zip / .nc package."""
    with zipfile.ZipFile(out_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("handler.js", js_content.encode("utf-8"))
        if extra_files:
            for filepath, arcname in extra_files:
                if Path(filepath).exists():
                    zf.write(filepath, arcname)
