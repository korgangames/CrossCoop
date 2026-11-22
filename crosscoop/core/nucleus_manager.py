"""
Nucleus Co-op local installation and handler directory manager.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_NUCLEUS_HANDLERS_DIR = WORKSPACE_DIR / "nucleus_coop" / "handlers"

class NucleusManager:
    def __init__(self, handlers_dir=None):
        self.handlers_dir = Path(handlers_dir) if handlers_dir else DEFAULT_NUCLEUS_HANDLERS_DIR
        self.handlers_dir.mkdir(parents=True, exist_ok=True)

    def get_installed_handlers(self):
        """Scan and return all handlers inside nucleus_coop/handlers."""
        handlers = []
        if not self.handlers_dir.exists():
            return handlers

        for item in sorted(self.handlers_dir.iterdir()):
            if item.is_file():
                ext = item.suffix.lower()
                if ext in [".js", ".zip", ".nc"] and item.name != "MasterHandler.js":
                    handlers.append({
                        "file_name": item.name,
                        "path": str(item),
                        "is_archive": ext in [".zip", ".nc"],
                        "size": item.stat().st_size
                    })
        return handlers

    def is_installed(self, game_name: str) -> bool:
        """Check if a handler matching game_name exists in nucleus_coop/handlers."""
        if not self.handlers_dir.exists():
            return False
        clean = re.sub(r'[^a-zA-Z0-9]', '', game_name).lower()
        for item in self.handlers_dir.iterdir():
            if item.is_file() and item.suffix.lower() in [".js", ".zip", ".nc"]:
                item_clean = re.sub(r'[^a-zA-Z0-9]', '', item.stem).lower()
                if clean in item_clean or item_clean in clean:
                    return True
        return False

    def read_handler_code(self, file_path: str) -> str:
        """Read .js content from file or archive."""
        p = Path(file_path)
        if not p.exists():
            return ""

        if p.suffix.lower() in [".zip", ".nc"]:
            import zipfile
            try:
                with zipfile.ZipFile(p, "r") as zf:
                    for name in zf.namelist():
                        if name.endswith("handler.js"):
                            return zf.read(name).decode("utf-8", errors="ignore")
            except Exception as e:
                return f"// Error reading archive: {e}"
        else:
            try:
                return p.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                return f"// Error reading file: {e}"

        return ""

    def save_handler_code(self, file_path: str, code: str) -> bool:
        """Save edited code back to .js file."""
        p = Path(file_path)
        try:
            p.write_text(code, encoding="utf-8")
            return True
        except Exception as e:
            print(f"Error saving {file_path}: {e}")
            return False

    def save_handler_js(self, handler_name: str, js_content: str) -> str:
        """Save a Nucleus handler script (.js) into nucleus_coop/handlers/."""
        clean_name = re.sub(r'[\/:*?"<>|]', '', handler_name).strip()
        filename = f"{clean_name}.js"
        target_path = self.handlers_dir / filename
        target_path.write_text(js_content, encoding="utf-8")
        return str(target_path)

    def save_handler_package(self, package_name: str, pkg_bytes: bytes) -> str:
        """Save a downloaded Nucleus package (.zip / .nc) into nucleus_coop/handlers/."""
        clean_name = re.sub(r'[\/:*?"<>|]', '', package_name).strip()
        filename = f"{clean_name}.zip"
        target_path = self.handlers_dir / filename
        target_path.write_bytes(pkg_bytes)
        return str(target_path)

    def delete_handler(self, file_path: str) -> bool:
        """Delete a local handler file."""
        p = Path(file_path)
        if p.exists() and p.is_file():
            p.unlink()
            return True
        return False

    def import_external_handler(self, src_file_path: str) -> str:
        """Copies an external file (.js, .zip, .nc) into the local nucleus handlers directory."""
        src = Path(src_file_path)
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src_file_path}")
        dest = self.handlers_dir / src.name
        if dest.exists() and dest != src:
            stem = src.stem
            suffix = src.suffix
            counter = 1
            while dest.exists():
                dest = self.handlers_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        if dest != src:
            shutil.copy2(src, dest)
        return str(dest)
