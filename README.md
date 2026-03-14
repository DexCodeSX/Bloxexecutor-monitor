<div align="center">
  <img src="https://revision.lol/revisionlogo.png" width="100" />
  <h1>Bloxexecutor Monitor</h1>
  <p><strong>A Python Discord Webhook Monitor for Roblox Executors</strong></p>
  <p>Track live exploit updates directly from <a href="https://revision.lol/">revision.lol</a></p>
</div>

---

## ⚡ Features

- **Cross-Platform:** Works seamlessly on Windows, macOS, Linux, and **Termux (Android)**!
- **Zero Config Setup:** Automatically fetches the `requests` library and sets up your `config.json` via a CLI wizard.
- **Smart Tracking:** Prevents spam by saving versions locally to `version.txt` and only pushing webhooks when an update (or downgrade) is actually detected.
- **Rich Embeds:** Slices API data into beautifully color-coded Discord embeds showing Platform, Version, Update Status, sUNC Score, and Price.

## 🚀 Installation & Usage

1. **Clone the repository:**
   ```bash
   git clone https://github.com/DexCodeSX/Bloxexecutor-monitor.git
   cd Bloxexecutor-monitor
   ```

2. **Run the script:**
   ```bash
   python bot.py
   ```
   *(If you are on Linux/macOS, you may need to use `python3 bot.py`)*

3. **Follow the Setup Wizard:**
   The script will ask for your **Discord Webhook URL**. Paste it in, and the script will validate and save it.

4. **Let it run:**
   The bot checks for new executor updates automatically every 5 minutes (`300` seconds). You can safely use `Ctrl+C` to stop it at any time.

## 📁 Files Generated

When you run the script, it generates two files locally that you should **NOT** upload to GitHub (they contain your webhook token):
- `config.json` — Stores your Discord webhook URL and polling interval.
- `version.txt` — Stores the current known version of every executor to block duplicate webhook spam.

## 🛠️ Credits
- **Data Source:** [revision.lol](https://revision.lol/)
- **Code:** [bisam](https://github.com/DexCodeSX)
- **Open Source:** [bot.py](https://github.com/DexCodeSX/Bloxexecutor-monitor/blob/main/bot.py)
