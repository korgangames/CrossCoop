# 🎮 CrossCoop — Universal Split-Screen Bridge
**Bridging the PC Split-Screen Libraries of [Nucleus Co-op (Windows)](https://github.com/SplitScreen-Me/splitscreenme-nucleus) and [PartyDeck (Linux/SteamOS)](https://github.com/partydeck/partydeck)**

[![GitHub Release](https://img.shields.io/github/v/release/korgangames/CrossCoop?style=for-the-badge&color=6366f1)](https://github.com/korgangames/CrossCoop/releases)
[![Nobara Linux](https://img.shields.io/badge/Optimized%20for-Nobara%20%2F%20SteamOS-emerald?style=for-the-badge)](https://nobaraproject.org)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-darkgreen?style=for-the-badge)](https://www.riverbankcomputing.com/software/pyqt/)

---

## 📖 What is CrossCoop?

PC gaming has two incredible community-driven tools for playing non-split-screen games locally with friends on a single PC:
1. **[Nucleus Co-op](https://github.com/SplitScreen-Me/splitscreenme-nucleus)**: The mature Windows giant with over **895 community handlers** created over 8+ years.
2. **[PartyDeck](https://github.com/partydeck/partydeck)**: The native Linux/SteamOS launcher that uses **Gamescope** for window composition and **Bubblewrap (`bwrap`)** to isolate controllers with zero input bleed.

Historically, they have been locked in their own separate worlds:
* **The Problem:** Nucleus Co-op fails on Linux under Wine/Proton due to unsupported Win32 API DLL injections and window hooks. Meanwhile, PartyDeck is native and stable on Linux, but only has ~50 handlers created so far.
* **The Solution:** **CrossCoop** acts as a double-sided universal bridge. It takes the extensive collective intelligence from Nucleus Co-op’s 895 handlers and translates them into native PartyDeck manifests that run flawlessly on Linux. Furthermore, it allows Linux users to export PartyDeck handlers back into standard Nucleus Co-op scripts for Windows gamers!

---

## 🔗 Official Program Links

| Program | Platform | Core Technology | Official Link |
| :--- | :---: | :--- | :--- |
| **Nucleus Co-op** | Windows | Win32 API, ProtoInput, EasyHook, XInputPlus | [GitHub: SplitScreen-Me/splitscreenme-nucleus](https://github.com/SplitScreen-Me/splitscreenme-nucleus) |
| **PartyDeck** | Linux / SteamOS | Gamescope, Bubblewrap (`bwrap`), UMU, Proton-GE | [GitHub: partydeck/partydeck](https://github.com/partydeck/partydeck) |

---

## 🌟 Key Features

### 1. 🔄 Double-Sided Handler Translation
* **Nucleus Co-op ➜ PartyDeck:** Automatically downloads and parses any handler from the 895-game SplitScreen.Me Hub. Discards the fragile Windows-only hooks in favor of Linux kernel sandboxing, generating a ready-to-play PartyDeck configuration.
* **PartyDeck ➜ Nucleus Co-op:** Converts PartyDeck `.pd2` or `handler.json` files back into standard, compliant `handler.js` / `.zip` scripts ready to run in Nucleus Co-op on Windows.

### 2. 🛡️ Intensive Pre-Flight Stability Audit & Stress Test
Before launching a game, CrossCoop conducts a **7-phase stability check** to prevent crashes, input bleed, and save corruption:
1. **Executable & Library Integrity:** Scans Steam libraries and custom directories to verify game binary presence and architecture.
2. **Controller Enumeration & Masking:** Probes `/dev/input/` to ensure sufficient distinct gamepads are connected for the requested player count.
3. **Bubblewrap Sandbox Permissions:** Confirms `bwrap` can isolate device nodes without root privileges.
4. **Gamescope & Display Resolution Geometry:** Calculates exact split-screen dimensions (2P vertical/horizontal, 3P, or 4P quadrants) and checks for forced windowed mode flags (`-windowed`, `-noborder`).
5. **Steam AppID & Goldberg LAN Emulation:** Verifies AppID validity and local Steam networking socket configuration.
6. **Network Port Collision Test:** Probes local ports (Goldberg `47584`, game ports `27015`, `7777`) to ensure no background processes or orphaned instances are holding sockets.
7. **Proton / UMU Compatibility:** Verifies runner availability and prefix isolation.

### 3. 🐧 PartyDeck Community Handlers Browser
Browse PartyDeck community handlers just like the Nucleus Hub!
* Features a built-in curated database of verified PartyDeck titles (*Dark Souls III Seamless Co-op, Call of Duty Alt Launcher, System Shock 2, Left 4 Dead 2, Risk of Rain 2, Wreckfest, Spelunky 2*, and more).
* **Live GitHub Sync:** One-click synchronization directly queries the `partydeck/partydeck` GitHub repository for newly released community handlers and issue submissions.

### 4. 🎮 895-Game Nucleus Hub Browser
* Full live catalog search of all 895 games.
* Filter by genre (Action, RPG, FPS, Racing, Survival) and input compatibility.
* Single-click **"Convert & Install to PartyDeck"**.

---

## 📥 Releases & Download

### Option 1: Standalone Script (Recommended)
You can clone and run CrossCoop directly on Nobara Linux, Fedora, SteamOS, or Ubuntu without compiling:

```bash
# Clone the repository
git clone https://github.com/korgangames/CrossCoop.git
cd CrossCoop

# Launch CrossCoop GUI
./crosscoop.sh
```

### Option 2: Pre-Packaged Releases
Download prebuilt archives, tagged releases, and `.pd2` packages from the [GitHub Releases Page](https://github.com/korgangames/CrossCoop/releases).

---

## 🚀 Quick Start Guide (Nobara Linux & SteamOS)

1. **Launch CrossCoop:**
   ```bash
   ./crosscoop.sh
   ```
2. **Find a Game:**
   * Go to the **Browse Nucleus Hub** tab and search for any game (e.g., *Borderlands 2*, *Deep Rock Galactic*, *Risk of Rain 2*).
   * Click **"⚡ Convert & Install to PartyDeck"**.
3. **Run Pre-Flight Audit:**
   * Switch to the **Pre-Flight Stability Audit** tab.
   * Select the game, pick your player count (e.g., 2 or 4 players), and click **"Run Intensive Stability Audit"**.
   * Verify all tests return 🟢 PASS.
4. **Play:**
   * Click **"🚀 Run PartyDeck"** in the top bar.
   * Connect your controllers and enjoy split-screen gaming on Linux!

---

## 🛠️ Requirements
* **Operating System:** Nobara Linux, SteamOS, Fedora, Arch, or Ubuntu.
* **Compositor:** Wayland or X11 (Gamescope supported).
* **Dependencies:** Python 3.10+, `python3-pyqt6`, `bwrap`, `gamescope`.

---

## 🤝 Contributing & Community
Pull requests, community handler contributions, and feature suggestions are welcome!

* **GitHub Repository:** [https://github.com/korgangames/CrossCoop](https://github.com/korgangames/CrossCoop)
* **Author:** [Korgan Games](https://github.com/korgangames)
* **License:** MIT
