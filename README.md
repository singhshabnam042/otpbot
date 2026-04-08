# 🤖 Gmail OTP Telegram Bot (5sim.net)

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://python.org)
[![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot-20%2B-green)](https://python-telegram-bot.org)

> **Telegram Bot** jo aapko Gmail signup ke liye **fresh virtual numbers** aur **OTP** automatically deta hai — powered by **5sim.net API**.

---

## 🇮🇳 Hindi + English Guide

---

## 📱 Bot Kya Karta Hai? (What this bot does)

| Feature | Detail |
|---|---|
| 💰 Check Balance | 5sim.net account ka balance dekho |
| 📱 Buy Gmail OTP Number | Sabse sasta fresh number auto-kharido (< $0.15) |
| 🔄 Multi-OTP Support | Ek number pe 2-3 baar OTP lo — jab tak Finish na dabao |
| ⏱ Auto OTP Polling | Har 5 second check karta hai, OTP aate hi Telegram pe bhejta hai |
| ❌ Cancel Number | Order cancel karo, refund milega |
| ✅ Finish Order | Kaam ho gaya? Order finish karo |
| 📋 My Active Orders | Sab active orders dekho |
| 🌍 Auto Country Select | Khud sabse sasta + available country choose karta hai |
| 📞 Country Code | Number hamesha `+91XXXXXXXXXX` format mein milega |

---

## ⚙️ Setup Guide

### Step 1: Prerequisites

```bash
# Python 3.9+ install karo
python --version   # should be 3.9+

# Repo clone karo
git clone https://github.com/singhshabnam042/otpbot.git
cd otpbot
```

### Step 2: Dependencies Install karo

```bash
pip install -r requirements.txt
```

### Step 3: Environment Variables Set karo

```bash
# .env.example ko copy karo
cp .env.example .env

# .env file kholo aur apni values daalo
nano .env   # ya koi bhi text editor use karo
```

`.env` file mein yeh daalo:

```
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
FIVESIM_API_KEY=your-5sim-api-key-here
MAX_PRICE=15
```

### Step 4: Telegram Bot Token Lena

1. Telegram pe **[@BotFather](https://t.me/BotFather)** ko open karo
2. `/newbot` command bhejo
3. Bot ka naam do (e.g. `My OTP Bot`)
4. Username do (e.g. `myotp_bot`) — `_bot` se end hona chahiye
5. BotFather aapko ek **token** dega — isko `.env` mein daalo

### Step 5: 5sim.net API Key Lena

1. **[5sim.net](https://5sim.net)** pe register karo aur login karo
2. Profile page pe jao → **API** section
3. API key copy karo
4. `.env` mein `FIVESIM_API_KEY=` ke baad daalo

### Step 6: Bot Run Karo

```bash
python bot.py
```

Bot shuru ho jayega! Telegram pe apne bot ko `/start` bhejo.

---

## 🤖 Bot Commands

| Command | Kaam |
|---|---|
| `/start` | Main menu dikhao |
| `/help` | Help message |

### Inline Buttons:

| Button | Kaam |
|---|---|
| 💰 Check Balance | Account balance dekho |
| 📱 Buy Gmail OTP Number | Fresh number kharido |
| ❌ Cancel Number | Active order cancel karo |
| ✅ Finish Order | Order finish karo |
| 📋 My Active Orders | Active orders ki list |
| 🔄 Check OTP Again | New OTP check karo (same number pe) |

---

## 🔄 Usage Flow (Kaise Use Kare)

```
1. /start → Main Menu dikhega

2. "📱 Buy Gmail OTP Number" dabao
   → Bot: "🔍 Sabse sasta fresh number dhoond raha hu..."
   → Bot: "✅ Number mil gaya! +91XXXXXXXXXX (India) $0.05"
   → Bot: "⏳ OTP ka wait kar raha hu..."

3. Is number ko Gmail signup form mein daalo

4. Gmail OTP bhejega → Bot automatically receive karega
   → Bot: "📩 OTP Aa Gaya! 🔢 Code: 123456"

5. Aur OTP chahiye? (2nd/3rd Gmail account ke liye)
   → "🔄 Check OTP Again" dabao — same number pe naya OTP aayega

6. Kaam ho gaya?
   → "✅ Finish Order" dabao

7. Number kaam nahi kar raha?
   → "❌ Cancel" dabao → Refund milega
```

---

## 🧠 Smart Features (Technical Details)

### Fresh Number Strategy
- `activation` type use karta hai — ye hamesha **nayi/fresh numbers** deta hai
- Recycled ya used numbers nahi milte

### Auto Country Selection
1. `GET /v1/guest/prices?product=google` se sab prices fetch karta hai
2. Sirf `< $0.15` aur `count > 10` wale filter karta hai
3. Sabse saste country/operator se start karta hai
4. Agar pehla try fail ho → automatically next cheapest try karta hai (max 3 retries)

### Multi-OTP Support
- Number khareedne ke baad `finish` **nahi** karta jab tak user button na dabaaye
- Number active rahta hai = ek hi number pe 2-3 Gmail OTP le sakte ho

### Auto OTP Polling
- Har `5 seconds` pe `GET /v1/user/check/{order_id}` call karta hai
- OTP aate hi **immediately** Telegram pe message bhejta hai
- 120 seconds baad timeout → user se poochta hai kya karna hai

---

## ❗ Troubleshooting

| Problem | Solution |
|---|---|
| `TELEGRAM_BOT_TOKEN set nahi hai` | `.env` mein token daalo |
| `FIVESIM_API_KEY set nahi hai` | `.env` mein API key daalo |
| Balance kam hai | 5sim.net account recharge karo |
| No numbers under $0.15 | `MAX_PRICE=20` ya zyada karo `.env` mein |
| OTP nahi aaya 2 min mein | Number cancel karo, naya try karo |
| Bot chal nahi raha | `pip install -r requirements.txt` dobara run karo |

---

## 📁 File Structure

```
otpbot/
├── bot.py              # Main Telegram bot — handlers, buttons, OTP polling
├── fivesim_api.py      # 5sim.net API wrapper (buy, check, cancel, prices)
├── config.py           # Configuration (tokens, settings, price limit)
├── utils.py            # Helper functions (format number, parse OTP, etc.)
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables (copy to .env)
├── README.md           # Yeh file!
└── .gitignore          # .env aur __pycache__ ignore karo
```

---

## 🔐 Security

- `.env` file **kabhi bhi** GitHub pe push mat karo — already `.gitignore` mein hai
- API keys private rakho
- `ADMIN_USER_IDS` set karke bot access limit kar sakte ho

---

## 📄 License

MIT License — Free to use, modify, and distribute.

---

*Made with ❤️ for the Indian developer community 🇮🇳*