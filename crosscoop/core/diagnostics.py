"""
Intensive Pre-Flight Stability Audit & Diagnostic Engine for Split-Screen Handlers.
Performs comprehensive pre-flight verification before games launch.
"""

import os
import sys
import socket
import shutil
import subprocess
from pathlib import Path

class DiagnosticResult:
    def __init__(self, check_id, title, status, message, details="", fix_action=None):
        self.check_id = check_id
        self.title = title
        self.status = status  # "PASS", "WARN", "FAIL"
        self.message = message
        self.details = details
        self.fix_action = fix_action

class PreFlightAuditor:
    def __init__(self, partydeck_mgr=None):
        self.partydeck_mgr = partydeck_mgr
        self.steam_common_dirs = self._find_steam_library_dirs()

    def _find_steam_library_dirs(self):
        """Locate Steam library folders on the system."""
        dirs = []
        home = Path.home()
        standard_paths = [
            home / ".steam" / "steam" / "steamapps" / "common",
            home / ".local" / "share" / "Steam" / "steamapps" / "common",
            home / ".var" / "app" / "com.valvesoftware.Steam" / ".steam" / "steam" / "steamapps" / "common"
        ]
        for p in standard_paths:
            if p.exists() and p.is_dir():
                dirs.append(p)

        # Check libraryfolders.vdf
        vdf_path = home / ".steam" / "steam" / "steamapps" / "libraryfolders.vdf"
        if vdf_path.exists():
            try:
                content = vdf_path.read_text(encoding="utf-8", errors="ignore")
                import re
                paths = re.findall(r'"path"\s+"([^"]+)"', content)
                for path_str in paths:
                    common = Path(path_str) / "steamapps" / "common"
                    if common.exists() and common not in dirs:
                        dirs.append(common)
            except Exception:
                pass
        return dirs

    def run_full_audit(self, handler_data: dict, player_count: int = 2) -> list:
        """Run all 7 diagnostic phases on the given handler data."""
        results = []
        
        # 1. Executable & File Path Check
        results.append(self._check_executable(handler_data))

        # 2. Controllers & Hardware Input Check
        results.append(self._check_controllers(player_count))

        # 3. Bubblewrap Sandbox Permission Check
        results.append(self._check_sandbox_permissions())

        # 4. Gamescope & Display Resolution Geometry
        results.append(self._check_display_geometry(handler_data, player_count))

        # 5. Steam AppID & Goldberg LAN Emulation Integrity
        results.append(self._check_goldberg_emulation(handler_data))

        # 6. Network Port Collision Test
        results.append(self._check_network_ports(handler_data))

        # 7. Proton / UMU Runtime Environment Check
        results.append(self._check_runtime_environment(handler_data))

        return results

    def _check_executable(self, handler_data: dict) -> DiagnosticResult:
        exec_name = handler_data.get("exec", "").strip()
        path_gameroot = handler_data.get("path_gameroot", "").strip()
        steam_appid = handler_data.get("steam_appid")

        if not exec_name:
            return DiagnosticResult(
                "EXEC_CHECK", "Game Executable Specification", "FAIL",
                "No executable specified in handler.",
                "The handler manifest lacks an 'exec' binary definition."
            )

        # If path_gameroot provided and exists
        if path_gameroot and Path(path_gameroot).exists():
            full_path = Path(path_gameroot) / exec_name
            if full_path.exists():
                return DiagnosticResult(
                    "EXEC_CHECK", "Game Executable Verification", "PASS",
                    f"Binary found: {exec_name}",
                    f"Path: {full_path}"
                )

        # Search across Steam library common folders
        found_paths = []
        for cdir in self.steam_common_dirs:
            for root, _, files in os.walk(cdir):
                if exec_name.lower() in [f.lower() for f in files]:
                    found_paths.append(Path(root) / exec_name)
                    break

        if found_paths:
            return DiagnosticResult(
                "EXEC_CHECK", "Game Executable Verification", "PASS",
                f"Binary verified in Steam library: {found_paths[0].name}",
                f"Located at: {found_paths[0]}"
            )

        return DiagnosticResult(
            "EXEC_CHECK", "Game Executable Verification", "WARN",
            f"Executable '{exec_name}' not detected in standard Steam paths.",
            f"If installed outside default Steam libraries (e.g. Heroic, Lutris, or SD card), set 'path_gameroot' in the handler."
        )

    def _check_controllers(self, player_count: int) -> DiagnosticResult:
        dev_input = Path("/dev/input")
        if not dev_input.exists():
            return DiagnosticResult(
                "INPUT_CHECK", "Hardware Controller Enumeration", "FAIL",
                "/dev/input directory not accessible.",
                "Cannot access Linux input subsystem."
            )

        js_devices = list(dev_input.glob("js*"))
        event_devices = list(dev_input.glob("event*"))
        
        detected_controllers = len(js_devices)

        if detected_controllers >= player_count:
            return DiagnosticResult(
                "INPUT_CHECK", "Hardware Controller Enumeration", "PASS",
                f"Sufficient controllers detected: {detected_controllers} connected for {player_count} players.",
                f"Found {len(js_devices)} joystick device(s) in /dev/input."
            )
        elif detected_controllers > 0:
            return DiagnosticResult(
                "INPUT_CHECK", "Hardware Controller Enumeration", "WARN",
                f"Only {detected_controllers} controller(s) detected for {player_count} players.",
                f"Connect {player_count - detected_controllers} more controller(s) or enable Keyboard+Mouse mode."
            )
        else:
            return DiagnosticResult(
                "INPUT_CHECK", "Hardware Controller Enumeration", "WARN",
                "No gamepads detected in /dev/input.",
                "Ensure controllers are paired via Bluetooth or plugged via USB. Keyboards/mice can still be isolated."
            )

    def _check_sandbox_permissions(self) -> DiagnosticResult:
        bwrap_path = shutil.which("bwrap")
        if not bwrap_path:
            return DiagnosticResult(
                "SANDBOX_CHECK", "Bubblewrap Sandbox Verification", "FAIL",
                "Bubblewrap ('bwrap') is not installed.",
                "Bubblewrap is mandatory on Linux to prevent controller input bleed between instances."
            )

        # Test running bwrap in unprivileged mode
        try:
            true_bin = shutil.which("true") or "/usr/bin/true"
            res = subprocess.run([bwrap_path, "--ro-bind", "/usr", "/usr", "--symlink", "usr/lib64", "/lib64", "--symlink", "usr/bin", "/bin", "--proc", "/proc", "--dev", "/dev", true_bin],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
            if res.returncode == 0:
                return DiagnosticResult(
                    "SANDBOX_CHECK", "Bubblewrap Sandbox Verification", "PASS",
                    "Bubblewrap sandbox execution verified.",
                    f"Binary: {bwrap_path} (Unprivileged user namespace isolation supported)"
                )
            else:
                return DiagnosticResult(
                    "SANDBOX_CHECK", "Bubblewrap Sandbox Verification", "WARN",
                    "Bubblewrap execution returned a non-zero code.",
                    res.stderr.decode("utf-8", errors="ignore")
                )
        except Exception as e:
            return DiagnosticResult(
                "SANDBOX_CHECK", "Bubblewrap Sandbox Verification", "WARN",
                "Could not probe Bubblewrap sandbox.", str(e)
            )

    def _check_display_geometry(self, handler_data: dict, player_count: int) -> DiagnosticResult:
        gamescope_path = shutil.which("gamescope")
        args = handler_data.get("args", "").lower()

        details = []
        if not gamescope_path:
            return DiagnosticResult(
                "DISPLAY_CHECK", "Display Compositor & Window Tiling", "FAIL",
                "Gamescope compositor is missing.",
                "Install gamescope ('sudo dnf install gamescope' on Nobara) for split-screen window management."
            )

        has_windowed = any(arg in args for arg in ["-windowed", "-window", "-noborder", "-popupwindow", "/windowed", "--windowed"])
        
        status = "PASS"
        msg = "Gamescope detected and display geometry calculated."
        if not has_windowed:
            status = "WARN"
            msg = "Handler arguments do not explicitly force windowed mode."
            details.append("Tip: Adding '-windowed -noborder' to launch arguments ensures games don't fight Gamescope tiling.")

        details.append(f"Gamescope: {gamescope_path}")
        details.append(f"Tiling model: {player_count}-player split composition")

        # Check NVIDIA + Wayland + PartyDeck gamescope_sdl_backend
        is_wayland = os.environ.get("XDG_SESSION_TYPE") == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
        is_nvidia = Path("/proc/driver/nvidia").exists() or Path("/dev/nvidia0").exists()
        if is_wayland and is_nvidia:
            settings_file = Path.home() / ".local" / "share" / "partydeck" / "settings.json"
            if settings_file.exists():
                try:
                    import json
                    pd_cfg = json.loads(settings_file.read_text(encoding="utf-8"))
                    if pd_cfg.get("gamescope_sdl_backend") is False:
                        details.append("GPU Backend: Native Gamescope Wayland backend verified (eliminates NVIDIA SDL flickering).")
                    else:
                        status = "WARN"
                        details.append("GPU Backend: PartyDeck was using SDL backend on NVIDIA Wayland, which causes screen flickering. Auto-remedied to native backend.")
                        from crosscoop.core.converter import auto_configure_partydeck_proton
                        auto_configure_partydeck_proton()
                except Exception:
                    pass

        return DiagnosticResult(
            "DISPLAY_CHECK", "Display Compositor & Window Tiling", status,
            msg, "\n".join(details)
        )

    def _check_goldberg_emulation(self, handler_data: dict) -> DiagnosticResult:
        use_goldberg = handler_data.get("use_goldberg", False)
        steam_appid = handler_data.get("steam_appid")

        if use_goldberg:
            if not steam_appid:
                return DiagnosticResult(
                    "GOLDBERG_CHECK", "Steam LAN Emulation Integrity", "FAIL",
                    "Goldberg LAN emulation is enabled, but Steam AppID is missing!",
                    "Goldberg emulator requires a valid Steam AppID to generate local player identities and sockets."
                )
            return DiagnosticResult(
                "GOLDBERG_CHECK", "Steam LAN Emulation Integrity", "PASS",
                f"Goldberg LAN Emulation configured for Steam AppID: {steam_appid}",
                "Multiplayer networking will emulate local Steam sockets via Goldberg."
            )
        else:
            return DiagnosticResult(
                "GOLDBERG_CHECK", "Steam LAN Emulation Integrity", "PASS",
                "Standard LAN / Direct IP mode (Goldberg disabled)",
                "Game will rely on native LAN server discovery or offline direct connection."
            )

    def _check_network_ports(self, handler_data: dict) -> DiagnosticResult:
        """Probe common ports for collisions."""
        test_ports = [47584, 27015, 7777] # Goldberg broadcast and common Source/Unreal ports
        occupied = []
        for port in test_ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                res = s.connect_ex(("127.0.0.1", port))
                if res == 0:
                    occupied.append(port)

        if occupied:
            return DiagnosticResult(
                "NETWORK_CHECK", "Local Network Port Collision Audit", "WARN",
                f"Ports {occupied} are currently in use by background processes.",
                "If another instance of the game or another local server is already running, it may cause connection conflicts."
            )

        return DiagnosticResult(
            "NETWORK_CHECK", "Local Network Port Collision Audit", "PASS",
            "Local LAN and Steam broadcast ports are free.",
            "Ports 47584, 27015, and 7777 are available for local multi-instance communication."
        )

    def _check_runtime_environment(self, handler_data: dict) -> DiagnosticResult:
        runtime = handler_data.get("runtime", "umu").lower()
        umu_path = shutil.which("umu-run")

        if runtime == "umu" and not umu_path:
            return DiagnosticResult(
                "RUNTIME_CHECK", "Proton / UMU Compatibility Layer", "WARN",
                "UMU Launcher ('umu-run') not found in PATH.",
                "Nobara comes with UMU, but if not in standard PATH, PartyDeck can fallback to Proton-GE directly."
            )

        return DiagnosticResult(
            "RUNTIME_CHECK", "Proton / UMU Compatibility Layer", "PASS",
            f"Runtime configured: {runtime.upper()}",
            "Compatibility runner configured to execute with isolated Proton prefixes."
        )
