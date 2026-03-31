# 🎤 Telegram Voice → Text Bot

Расшифровка голосовых и кружков через Groq Whisper.

---

## Файлы для GitHub

```
bot.py
requirements.txt
README.md
```

---

## Деплой на Render.com

### 1. Залей файлы на GitHub

Создай репозиторий и загрузи `bot.py`, `requirements.txt`, `README.md`.

### 2. Создай сервис на Render

- [render.com](https://render.com) → New → **Web Service**
- Connect your GitHub repo
- Настройки:

| Поле | Значение |
|---|---|
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python bot.py` |
| **Instance Type** | Free |

### 3. Добавь переменные окружения

Render → твой сервис → **Environment** → Add Environment Variable:

```
TELEGRAM_TOKEN = токен_от_BotFather
GROQ_API_KEY   = ключ_от_console.groq.com
```

### 4. Задеплой

Нажми **Deploy** — через минуту бот запустится.  
Во вкладке **Logs** должно появиться `Bot started!`

---

## Чтобы бот не засыпал (UptimeRobot)

Бесплатный Render засыпает через 15 минут без запросов.  
UptimeRobot будет пинговать его каждые 5 минут — бесплатно.

1. Зайди на [uptimerobot.com](https://uptimerobot.com) → Register (бесплатно)
2. **Add New Monitor**:
   - Monitor Type: **HTTP(s)**
   - Friendly Name: любое имя
   - URL: `https://ИМЯ_ТВОЕГО_СЕРВИСА.onrender.com` (берёшь из Render dashboard)
   - Monitoring Interval: **5 minutes**
3. Сохрани → готово

Теперь бот работает 24/7 бесплатно.
