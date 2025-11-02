# 💰 Telegram Crypto Price Bot 🇮🇷

A Telegram bot that shows **real-time cryptocurrency prices in Iranian Rial (IRR)**.  
It fetches live USD prices from **CoinGecko** and converts them to IRR using the **USDT/IRR rate** from **Nobitex**.  
The bot also includes a **user database** and an **admin panel** with broadcast features.

---

## ⚙️ Features
- 🔹 Fetch real-time prices from the CoinGecko API  
- 🔹 Convert prices to IRR using the Nobitex API  
- 🔹 Display **Top 10 gainers** among the top 250 coins  
- 🔹 Get live prices by typing a coin symbol (e.g. `btc`, `eth`)  
- 🔹 Store users in a local SQLite database  
- 🔹 Admin broadcast messages to all users  
- 🔹 Separate menus for **users** and **admins**

---

## 🧠 Tech Stack
- **Language:** Python 3  
- **Libraries:**  
  - `pyTelegramBotAPI` — Telegram Bot framework  
  - `requests` — API communication  
  - `sqlite3` — Local database  
  - `logging` — Logging and error tracking  

---

## 🚀 Installation & Setup

### 1️⃣ Clone or download this repository
```bash
git clone https://github.com/YOUR_USERNAME/telegram-crypto-price-bot.git
cd telegram-crypto-price-bot
