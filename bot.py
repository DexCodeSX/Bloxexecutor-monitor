#!/usr/bin/env python3
"""
revision.lol executor update monitor -> discord webhook
credit by bisam
"""

import sys
import os
import subprocess
import platform
import json
import time
import threading
from datetime import datetime, timezone

# global stop flag for clean shutdown
_stop = threading.Event()

# ──────────── platform detect + auto install ────────────

def get_platform():
    s = platform.system().lower()
    if s == "linux":
        if os.environ.get("PREFIX", "").startswith("/data/data/com.termux"):
            return "termux"
        return "linux"
    elif s == "darwin":
        return "macos"
    elif s == "windows":
        return "windows"
    return s

def pip_cmd():
    return [sys.executable, "-m", "pip"]

def install_pkg(name):
    cmd = pip_cmd() + ["install", "--quiet", name]
    try:
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        try:
            subprocess.check_call(pip_cmd() + ["install", name])
            return True
        except Exception as e:
            print(f"  \033[91m✗ failed to install {name}: {e}\033[0m")
            return False

def ensure_deps():
    deps = {"requests": "requests"}
    missing = []
    for mod, pkg in deps.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append((mod, pkg))

    if not missing:
        print(f"  \033[92m✓\033[0m dependencies already installed, skipping")
        return True

    for mod, pkg in missing:
        print(f"  \033[93m⟳\033[0m installing {pkg}...")
        if not install_pkg(pkg):
            return False
        print(f"  \033[92m✓\033[0m {pkg} installed")
    return True

# ──────────── config + version file ────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CFG_FILE = os.path.join(SCRIPT_DIR, "config.json")
VER_FILE = os.path.join(SCRIPT_DIR, "version.txt")

def load_cfg():
    if os.path.exists(CFG_FILE):
        with open(CFG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cfg(cfg):
    with open(CFG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def load_versions():
    """read version.txt into {name: version} dict"""
    vers = {}
    if not os.path.exists(VER_FILE):
        return vers
    with open(VER_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # format: Platform | Name | Version
            parts = line.split("|")
            if len(parts) == 3:
                vers[parts[1].strip()] = parts[2].strip()
    return vers

def save_versions(ver_data):
    """write all executor versions to version.txt, sorted by name
    ver_data = {name: (platform, version)}"""
    with open(VER_FILE, "w", encoding="utf-8") as f:
        f.write(f"# revision.lol executor versions\n")
        f.write(f"# last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"# format: Platform | Name | Version\n\n")
        for name in sorted(ver_data.keys()):
            plat, ver = ver_data[name]
            f.write(f"{plat} | {name} | {ver}\n")

def validate_webhook(url):
    import requests
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if "id" in data and "token" in data:
                return True, data.get("name", "webhook")
        return False, "invalid response"
    except Exception as e:
        return False, str(e)

# ──────────── setup wizard ────────────

def setup():
    cfg = load_cfg()

    while True:
        existing = cfg.get("webhook_url", "")
        if existing:
            print(f"\n  current webhook: \033[90m{existing[:50]}...\033[0m")
            choice = input("  keep it? (y/n): ").strip().lower()
            if choice in ("y", "yes", ""):
                break

        url = input("\n  \033[97mYOUR DISCORD WEBHOOK URL:\033[0m ").strip()
        if not url:
            print("  \033[91m✗ FAIL\033[0m — cannot be empty, try again")
            continue
        if not url.startswith("https://discord.com/api/webhooks/"):
            print("  \033[91m✗ FAIL\033[0m — must start with https://discord.com/api/webhooks/")
            continue

        print("  validating...", end=" ", flush=True)
        ok, info = validate_webhook(url)
        if ok:
            print(f"\033[92m✓\033[0m connected to \"{info}\"")
            cfg["webhook_url"] = url
            save_cfg(cfg)
            break
        else:
            print(f"\033[91m✗ FAIL\033[0m — {info}")
            print("  try again!")

    if "interval" not in cfg:
        cfg["interval"] = 300
        save_cfg(cfg)

    return cfg

# ──────────── revision.lol api ────────────

API_URL = "https://public-r2-download.peytonusingebay.workers.dev/"

def fetch_executors():
    import requests
    r = requests.get(API_URL, timeout=15)
    r.raise_for_status()
    return r.json()

def get_plat(extype):
    mapping = {
        "wexecutor": "Windows", "wexternal": "Windows",
        "mexecutor": "macOS", "aexecutor": "Android",
        "iexecutor": "iOS"
    }
    return mapping.get(extype, "Unknown")

# ──────────── embed builder ────────────

PLAT_COLORS = {
    "Windows": 0x00ff6a,
    "macOS": 0x5865f2,
    "Android": 0xff9800,
    "iOS": 0xffffff,
}

PLAT_EMOJI = {
    "Windows": "🖥️",
    "macOS": "🍎",
    "Android": "📱",
    "iOS": "📱",
}

def build_embed(ex, old_ver=None):
    plat = get_plat(ex.get("extype", ""))
    name = ex.get("title", "Unknown")
    ver = ex.get("version", "?")
    color = PLAT_COLORS.get(plat, 0x2b2d31)
    emoji = PLAT_EMOJI.get(plat, "🔧")

    is_up = ex.get("updateStatus", False)
    status_txt = "🟢 Updated" if is_up else "🔴 Down"

    is_free = ex.get("free", False)
    cost_raw = ex.get("cost", "")
    if is_free:
        price_txt = "✨ Free"
    elif cost_raw:
        price_txt = f"💰 {cost_raw}"
    else:
        price_txt = "💰 Paid"

    if old_ver and old_ver != ver:
        title = f"{emoji} {name} — Updated!"
        desc = f"```ansi\n\u001b[2;31m{old_ver}\u001b[0m → \u001b[2;32m{ver}\u001b[0m\n```"
    else:
        title = f"{emoji} {name} — v{ver}"
        desc = f"New executor data detected"

    fields = [
        {"name": "Platform", "value": f"`{plat}`", "inline": True},
        {"name": "Version", "value": f"`{ver}`", "inline": True},
        {"name": "Status", "value": status_txt, "inline": True},
        {"name": "Price", "value": price_txt, "inline": True},
    ]

    updated = ex.get("updatedDate", "")
    if updated:
        fields.append({"name": "Last Updated", "value": f"`{updated}`", "inline": True})

    rbxver = ex.get("rbxversion", "")
    if rbxver:
        short = rbxver if len(rbxver) < 25 else rbxver[:24] + "…"
        fields.append({"name": "Roblox Version", "value": f"`{short}`", "inline": True})

    sunc = ex.get("suncPercentage")
    if sunc is not None:
        if sunc >= 80:
            sunc_txt = f"🟢 {sunc}%"
        elif sunc >= 50:
            sunc_txt = f"🟡 {sunc}%"
        else:
            sunc_txt = f"🔴 {sunc}%"
        fields.append({"name": "sUNC Score", "value": sunc_txt, "inline": True})

    decomp = ex.get("decompiler")
    if decomp is not None:
        fields.append({"name": "Decompiler", "value": "✅ Yes" if decomp else "❌ No", "inline": True})

    multi = ex.get("multiInject")
    if multi is not None:
        fields.append({"name": "Multi-Inject", "value": "✅ Yes" if multi else "❌ No", "inline": True})

    thumb = {}
    slug = ex.get("slug", {})
    if isinstance(slug, dict) and slug.get("logo"):
        thumb = {"url": slug["logo"]}

    embed = {
        "title": title,
        "description": desc,
        "color": color,
        "fields": fields,
        "footer": {
            "text": "credit by bisam • revision.lol"
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if thumb:
        embed["thumbnail"] = thumb

    return embed

# ──────────── send webhook ────────────

def send_webhook(webhook_url, embeds):
    import requests
    chunks = [embeds[i:i+10] for i in range(0, len(embeds), 10)]
    for chunk in chunks:
        payload = {
            "username": "darkgg monitorr",
            "avatar_url": "https://revision.lol/revisionlogo.png",
            "embeds": chunk
        }
        r = requests.post(webhook_url, json=payload, timeout=15)
        if r.status_code == 204:
            pass
        elif r.status_code == 429:
            retry_after = r.json().get("retry_after", 5)
            print(f"  \033[93m⟳\033[0m rate limited, waiting {retry_after}s...")
            time.sleep(retry_after + 0.5)
            requests.post(webhook_url, json=payload, timeout=15)
        else:
            print(f"  \033[91m✗\033[0m webhook returned {r.status_code}: {r.text[:100]}")
        if len(chunks) > 1:
            time.sleep(1)

# ──────────── main monitor logic ────────────

def check_updates(cfg):
    versions = load_versions()

    print(f"\n  \033[94m⟳\033[0m fetching revision.lol api...", end=" ", flush=True)
    try:
        executors = fetch_executors()
    except Exception as e:
        print(f"\033[91m✗\033[0m {e}")
        return cfg

    print(f"\033[92m✓\033[0m got {len(executors)} executors")

    hidden = {
        'Synapse Z (Closed Beta)', 'Velocity', 'Valex', 'Nucleus',
        'Lovreware (Closed Beta)', 'Melatonin', 'Assembly', 'Photon',
        'Matrix Hub', 'DX9WARE V2', 'Synapse Mac'
    }

    updates = []
    first_run = len(versions) == 0
    all_vers = {}  # fresh copy from api: {name: (platform, version)}

    for ex in executors:
        name = ex.get("title", "")
        if not name or name in hidden:
            continue
        if ex.get("hidden", False):
            continue

        ver = ex.get("version", "")
        plat = get_plat(ex.get("extype", ""))
        all_vers[name] = (plat, ver)
        old_ver = versions.get(name)

        if old_ver is None:
            if first_run:
                continue  # dont spam on first run
            updates.append(build_embed(ex))
        elif old_ver != ver:
            print(f"  \033[93m↑\033[0m {name}: {old_ver} → {ver}")
            updates.append(build_embed(ex, old_ver))

    # always write full version.txt from api (source of truth)
    save_versions(all_vers)

    if updates:
        print(f"  \033[92m✓\033[0m sending {len(updates)} update(s) to discord...")
        send_webhook(cfg["webhook_url"], updates)
        print(f"  \033[92m✓\033[0m done!")
    elif first_run:
        print(f"  \033[92m✓\033[0m first run — saved {len(all_vers)} executor versions to version.txt")
        print(f"  \033[90m  next run will detect changes\033[0m")
    else:
        print(f"  \033[90m—\033[0m no updates detected")

    return cfg

# ──────────── banner ────────────

BANNER = """
\033[92m
  ██████╗ ███████╗██╗   ██╗██╗███████╗██╗ ██████╗ ███╗   ██╗
  ██╔══██╗██╔════╝██║   ██║██║██╔════╝██║██╔═══██╗████╗  ██║
  ██████╔╝█████╗  ██║   ██║██║███████╗██║██║   ██║██╔██╗ ██║
  ██╔══██╗██╔══╝  ╚██╗ ██╔╝██║╚════██║██║██║   ██║██║╚██╗██║
  ██║  ██║███████╗ ╚████╔╝ ██║███████║██║╚██████╔╝██║ ╚████║
  ╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚═╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝
\033[0m
\033[90m  ─────────────── executor update monitor ───────────────\033[0m
\033[90m  credit by bisam                        revision.lol\033[0m
"""

def countdown(secs):
    """countdown that actually stops when you hit ctrl+c"""
    for remaining in range(secs, 0, -1):
        if _stop.is_set():
            return
        mins, s = divmod(remaining, 60)
        timer = f"{mins:02d}:{s:02d}"
        print(f"\r  \033[90m⏳ next check in {timer}\033[0m", end="", flush=True)
        # sleep in small chunks so _stop gets checked fast
        if _stop.wait(1.0):
            return
    print("\r" + " " * 40 + "\r", end="", flush=True)

# ──────────── entry ────────────

def main():
    print(BANNER)

    plat = get_platform()
    plat_names = {"windows": "Windows", "linux": "Linux", "macos": "macOS", "termux": "Termux (Android)"}
    print(f"  \033[97mplatform:\033[0m {plat_names.get(plat, plat)}")
    print(f"  \033[97mpython:\033[0m   {sys.version.split()[0]}")
    print()

    print("  \033[97m[1/2]\033[0m checking dependencies...")
    if not ensure_deps():
        print("\n  \033[91m✗ could not install dependencies. install 'requests' manually:\033[0m")
        print("    pip install requests")
        sys.exit(1)

    print("  \033[97m[2/2]\033[0m configuration...")
    cfg = setup()

    interval = cfg.get("interval", 300)
    print(f"\n  \033[97mstarting monitor...\033[0m")
    print(f"  \033[90mpoll interval: {interval}s ({interval//60}m)\033[0m")
    print(f"  \033[90mversions saved to: version.txt\033[0m")
    print(f"  \033[90mpress Ctrl+C to stop\033[0m")

    while not _stop.is_set():
        cfg = check_updates(cfg)
        if _stop.is_set():
            break
        countdown(interval)

    print(f"\n\n  \033[93m✋ shutting down...\033[0m")
    print(f"  \033[92m✓\033[0m goodbye!\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        _stop.set()
        print(f"\n\n  \033[93m✋ shutting down...\033[0m")
        print(f"  \033[92m✓\033[0m goodbye!\n")
