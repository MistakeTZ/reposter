# Reposter
Telegram bot to repost from channels
## Installation
1. Clone the repo
   ```sh
   git clone https://github.com/MistakeTZ/reposter.git
   ```
2. Rename example.env to .env
3. Go to https://t.me/BotFather and create new bot. Copy token of bot
4. Paste your token to `.env`
   ```
   token=YOUR_TOKEN_HERE
   ```
5. Create venv and install requirements
   ```sh
   python3 -m venv .venv
   .venv/Scripts/activate
   pip install -r requirements
   ```
6. Run the bot
   ```sh
   python3 main.py
   ```
