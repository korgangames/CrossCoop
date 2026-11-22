"""
Two-way conversion engine between Nucleus Co-op and PartyDeck.
Includes intelligent environment-aware translation:
- Detects whether games are installed as Linux-native or Windows (Wine/Proton).
- Maps native executables (.bin.x86_64, .x86_64, native scripts) automatically.
- Precision Steam LAN emulation detection (avoids unwanted Goldberg injection).
- Clamps Windows focus-wait pauses (40s -> 3s) to prevent Gamescope timeouts.
- Injects necessary windowed arguments (-windowed) for Gamescope tiling.
- Auto-configures PartyDeck's Proton environment to avoid background download freezes.
"""

import re
import json
import zipfile
import io
import os
from pathlib import Path

# Curated catalog of games with native Linux builds on Steam
NATIVE_LINUX_GAMES_CATALOG = {
    "105600": {
        "name": "Terraria",
        "linux_exec": "Terraria.bin.x86_64",
        "alt_execs": ["Terraria", "Terraria.bin.x86"],
        "default_args": "-windowed",
        "goldberg": False,
        "runtime": "native"
    },
    "550": {
        "name": "Left 4 Dead 2",
        "linux_exec": "hl2_linux",
        "alt_execs": ["left4dead2.sh"],
        "default_args": "-game left4dead2 -windowed -noborder",
        "goldberg": False,
        "runtime": "native"
    },
    "620": {
        "name": "Portal 2",
        "linux_exec": "hl2_linux",
        "alt_execs": ["portal2.sh"],
        "default_args": "-game portal2 -windowed",
        "goldberg": False,
        "runtime": "native"
    },
    "892970": {
        "name": "Valheim",
        "linux_exec": "valheim.x86_64",
        "alt_execs": ["valheim.bin.x86_64"],
        "default_args": "-windowed",
        "goldberg": False,
        "runtime": "native"
    },
    "413150": {
        "name": "Stardew Valley",
        "linux_exec": "StardewValley.bin.x86_64",
        "alt_execs": ["Stardew Valley.bin.x86_64", "StardewValley"],
        "default_args": "",
        "goldberg": False,
        "runtime": "native"
    },
    "49520": {
        "name": "Borderlands 2",
        "linux_exec": "Borderlands2",
        "alt_execs": ["Borderlands2.bin.x86_64"],
        "default_args": "-windowed -noborder",
        "goldberg": False,
        "runtime": "native"
    },
    "322330": {
        "name": "Don't Starve Together",
        "linux_exec": "dontstarve_steam",
        "alt_execs": ["dontstarve_steam_x64"],
        "default_args": "",
        "goldberg": False,
        "runtime": "native"
    },
    "218620": {
        "name": "PAYDAY 2",
        "linux_exec": "payday2_release",
        "alt_execs": ["PAYDAY2_linux"],
        "default_args": "",
        "goldberg": False,
        "runtime": "native"
    },
    "239140": {
        "name": "Dying Light",
        "linux_exec": "DyingLightGame",
        "alt_execs": ["DyingLight"],
        "default_args": "-windowed",
        "goldberg": False,
        "runtime": "native"
    }
}


def find_steam_common_dirs() -> list[Path]:
    """Find all local Steam steamapps/common directories across mounts."""
    dirs = []
    home = Path.home()
    standard_paths = [
        home / ".steam" / "steam" / "steamapps" / "common",
        home / ".local" / "share" / "Steam" / "steamapps" / "common",
        home / ".var" / "app" / "com.valvesoftware.Steam" / ".steam" / "steam" / "steamapps" / "common"
    ]
    for p in standard_paths:
        if p.exists() and p.is_dir() and p not in dirs:
            dirs.append(p)

    vdf_path = home / ".steam" / "steam" / "steamapps" / "libraryfolders.vdf"
    if not vdf_path.exists():
        vdf_path = home / ".local" / "share" / "Steam" / "steamapps" / "libraryfolders.vdf"

    if vdf_path.exists():
        try:
            content = vdf_path.read_text(encoding="utf-8", errors="ignore")
            paths = re.findall(r'"path"\s+"([^"]+)"', content)
            for path_str in paths:
                common = Path(path_str) / "steamapps" / "common"
                if common.exists() and common not in dirs:
                    dirs.append(common)
        except Exception:
            pass
    return dirs


def detect_game_installation(game_name: str, steam_id: int = None) -> tuple[Path | None, str | None, str]:
    """
    Scans local Steam directories for game files.
    Returns (game_dir_path, executable_name, runtime) where runtime is 'native' or 'umu'.
    """
    common_dirs = find_steam_common_dirs()
    clean_target = re.sub(r'[^a-zA-Z0-9]', '', game_name).lower()

    # 1. Search for directory
    found_dir = None
    for cdir in common_dirs:
        if not cdir.exists():
            continue
        for child in cdir.iterdir():
            if child.is_dir():
                clean_child = re.sub(r'[^a-zA-Z0-9]', '', child.name).lower()
                if clean_target == clean_child or clean_target in clean_child or clean_child in clean_target:
                    found_dir = child
                    break
        if found_dir:
            break

    # If directory found, scan files for native Linux binaries
    if found_dir and found_dir.is_dir():
        all_files = [f for f in found_dir.iterdir() if f.is_file()]

        # Look for explicit native binary candidates
        native_candidates = [
            f.name for f in all_files
            if (f.name.endswith('.bin.x86_64') or f.name.endswith('.x86_64') or
                f.name.endswith('.bin.x86') or f.name in ['hl2_linux', 'runner', 'Terraria'])
            and os.access(f, os.X_OK)
        ]

        if native_candidates:
            # Sort preferred (prefer main game binary over server/test)
            pref = [c for c in native_candidates if 'server' not in c.lower() and 'test' not in c.lower()]
            chosen = pref[0] if pref else native_candidates[0]
            return (found_dir, chosen, "native")

        # Check for Windows .exe in found directory
        exe_candidates = [f.name for f in all_files if f.name.lower().endswith('.exe')]
        if exe_candidates:
            pref_exe = [e for e in exe_candidates if 'server' not in e.lower() and 'crash' not in e.lower() and 'unity' not in e.lower()]
            chosen_exe = pref_exe[0] if pref_exe else exe_candidates[0]
            return (found_dir, chosen_exe, "umu")

    # 2. If folder not found on disk, consult curated dual-native catalog
    sid_str = str(steam_id) if steam_id else ""
    if sid_str in NATIVE_LINUX_GAMES_CATALOG:
        entry = NATIVE_LINUX_GAMES_CATALOG[sid_str]
        return (None, entry["linux_exec"], entry["runtime"])

    for sid, entry in NATIVE_LINUX_GAMES_CATALOG.items():
        if entry["name"].lower() == game_name.lower():
            return (None, entry["linux_exec"], entry["runtime"])

    return (None, None, "umu")


def auto_configure_partydeck_proton():
    """
    Checks PartyDeck's settings.json. If proton_version is unset or empty,
    automatically configures it to use the best locally installed Proton version
    so that umu-run never attempts an on-the-fly 1.5GB background download.
    """
    home = Path.home()
    settings_file = home / ".local" / "share" / "partydeck" / "settings.json"
    if not settings_file.exists():
        return

    try:
        data = json.loads(settings_file.read_text(encoding="utf-8"))
        curr_ver = data.get("proton_version", "").strip()
        if curr_ver:
            return  # Already configured

        # Search for installed Proton versions
        candidates = []
        compat_dirs = [
            home / ".local" / "share" / "Steam" / "compatibilitytools.d",
            home / ".steam" / "root" / "compatibilitytools.d",
            home / ".steam" / "steam" / "compatibilitytools.d"
        ]
        for cdir in compat_dirs:
            if cdir.exists():
                for item in cdir.iterdir():
                    if item.is_dir() and (item / "proton").exists():
                        candidates.append(item.name)

        # Look in Steam common
        for sdir in find_steam_common_dirs():
            for item in sdir.glob("Proton*"):
                if item.is_dir() and (item / "proton").exists():
                    candidates.append(item.name)

        if candidates:
            # Sort by newest / GE-Proton first
            candidates.sort(key=lambda x: ("GE-Proton" in x, "Experimental" in x, x), reverse=True)
            chosen = candidates[0]
            data["proton_version"] = chosen
            settings_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"Error auto-configuring PartyDeck Proton: {e}")


def parse_lenient_handler(content: str, filename: str = "", meta: dict = None) -> dict:
    """
    Intelligent lenient parser for official and unofficial handlers.
    Optimizes configurations specifically for Linux / PartyDeck execution.
    """
    meta = meta or {}

    # Proactively ensure PartyDeck has a valid Proton version selected
    auto_configure_partydeck_proton()

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
        game_name = re.sub(r'[_.-]+', ' ', stem).title()
    if not game_name:
        game_name = "Custom Game"

    clean_name = re.sub(r'[\/:*?"<>|]', '', game_name).strip()

    # 2. Steam AppID
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

    # 3. Detect Game Installation on disk & native Linux executable
    detected_game_dir, detected_exec, detected_runtime = detect_game_installation(clean_name, steam_id)

    # 4. Executable Name Resolution
    if detected_exec:
        exec_name = detected_exec
        runtime = detected_runtime
    else:
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
        runtime = "umu" if exec_name.lower().endswith(".exe") else "native"

    # 5. Startup Arguments with Gamescope Windowed Assurance
    args = get_str([
        r'Game\.StartArguments\s*=\s*[\"\']([^\"\']*)[\"\']',
        r'Game\.CommandLine\s*=\s*[\"\']([^\"\']*)[\"\']',
        r'(?:var|let|const)\s+(?:args|cmd|arguments)\s*=\s*[\"\']([^\"\']*)[\"\']'
    ])

    # Guarantee windowed mode flag for Gamescope compositing
    has_windowed = any(w in args.lower() for w in ["-window", "-windowed", "-noborder", "-popupwindow", "/w"])
    if not has_windowed:
        sid_str = str(steam_id) if steam_id else ""
        if sid_str in NATIVE_LINUX_GAMES_CATALOG and NATIVE_LINUX_GAMES_CATALOG[sid_str]["default_args"]:
            def_args = NATIVE_LINUX_GAMES_CATALOG[sid_str]["default_args"]
            args = f"{args} {def_args}".strip() if args else def_args
        else:
            # Default windowed flag for PC titles
            args = f"{args} -windowed".strip() if args else "-windowed"

    # 6. Pause Timing (Smart Clamping)
    # Nucleus handlers frequently set 30-40s pauses as Windows DLL focus workarounds.
    # In PartyDeck / Gamescope, each instance runs in its own Wayland socket.
    # Clamping pause to 3.0s prevents the black screen timeout hang!
    raw_pause = get_int([
        r'Game\.PauseBetweenStarts\s*=\s*(\d+)',
        r'Game\.HandlerInterval\s*=\s*(\d+)'
    ], default=3)

    if raw_pause is None or raw_pause > 5:
        pause = 3.0
    elif raw_pause < 1:
        pause = 2.0
    else:
        pause = float(raw_pause)

    # 7. Goldberg / Steam LAN Emulation Precision
    # Look for explicit negation in the handler:
    has_explicit_no_steam = bool(
        re.search(r'Game\.NeedsSteamEmulation\s*=\s*false', content, re.IGNORECASE) or
        re.search(r'Game\.UseGoldberg\s*=\s*false', content, re.IGNORECASE)
    )

    has_explicit_yes_steam = bool(
        re.search(r'Game\.NeedsSteamEmulation\s*=\s*true', content, re.IGNORECASE) or
        re.search(r'Game\.UseGoldberg\s*=\s*true', content, re.IGNORECASE)
    )

    if has_explicit_no_steam:
        use_goldberg = False
    elif has_explicit_yes_steam:
        use_goldberg = True
    elif runtime == "native":
        # Native Linux games generally handle local sockets natively unless specified
        use_goldberg = False
    else:
        # For Windows/UMU games, enable Goldberg if explicitly named in text
        use_goldberg = bool(re.search(r'\bgoldberg\b', content, re.IGNORECASE))

    # 8. Author
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
    detected.append(f"Runtime: {runtime.upper()}")
    detected.append(f"Executable: {exec_name}")
    if detected_game_dir:
        detected.append(f"Game Directory: {detected_game_dir.name}")
    if use_goldberg:
        detected.append("Goldberg Steam LAN Emulation")
    else:
        detected.append("Direct IP / Native LAN Mode")
    if args:
        detected.append(f"Launch Args: {args}")

    info = f"Optimized via CrossCoop for {runtime.upper()} execution (Author: {author})."
    if detected:
        info += f"\nDetected parameters: {', '.join(detected)}."
    if meta.get("description"):
        info += f"\n\nNotes: {meta.get('description')[:300]}"

    path_gameroot = str(detected_game_dir) if detected_game_dir else ""

    return {
        "name": clean_name,
        "author": f"CrossCoop ({author})",
        "version": "1.0-custom",
        "info": info,
        "spec_ver": 3,
        "path_gameroot": path_gameroot,
        "runtime": runtime,
        "exec": exec_name,
        "args": args,
        "env": "",
        "sdl2_override": "No",
        "pause_between_starts": pause,
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
    """Wrapper for backward compatibility, leveraging the intelligent parser."""
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
                    pd_data["_detected_features"].append(f"Steam AppID: {found_steam_id}")

                has_goldberg_files = any("goldberg" in n.lower() or "steam_api" in n.lower() for n in names)
                if has_goldberg_files and pd_data.get("runtime") == "umu":
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
    # If translating a native Linux binary back to Nucleus, revert to standard Windows .exe
    if exec_name.endswith(".bin.x86_64") or exec_name.endswith(".x86_64"):
        exec_name = exec_name.split(".bin")[0].split(".x86")[0] + ".exe"
    elif not exec_name.lower().endswith(".exe"):
        exec_name = f"{exec_name}.exe"

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
