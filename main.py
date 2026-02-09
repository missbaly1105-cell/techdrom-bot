import os
import asyncio
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, Update
from fastapi import FastAPI, Request
import uvicorn
import openai

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))

openai.api_key = OPENAI_API_KEY
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# === ПРОСТОЙ ПРОМПТ ДЛЯ ТЕСТА ===
SYSTEM_PROMPT = "Ты — помощник детской IT-школы Технодром. Отвечай кратко и дружелюбно."

# Простая память (в реальности лучше использовать базу)
user_sessions = {}

async def ask_llm(user_id, text):
    if user_id not in user_sessions:
        user_sessions[user_id] = []
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += user_sessions[user_id]
    messages.append({"role": "user", "content": text})
    
    try:
        resp = await openai.ChatCompletion.acreate(
            model="gpt-4o",
            messages=messages,
            temperature=0.6
        )
        answer = resp.choices[0].message["content"].strip()
        
        # Сохраняем историю
        user_sessions[user_id].append({"role": "user", "content": text})
        user_sessions[user_id].append({"role": "assistant", "content": answer})
        
        # Эскалация на администратора
        if "уточню у администратора" in answer.lower():
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=f"⚠️ Нужна помощь!\n\nКлиент ID: {user_id}\n\nСообщение: {text}\n\nБот ответил: {answer}"
            )
        
        return answer
    except Exception as e:
        return "Секунду, проверяю информацию..."

@router.message(F.text)
async def handle_message(message: Message):
    answer = await ask_llm(message.from_user.id, message.text)
    await message.answer(answer)

dp.include_router(router)

# === FASTAPI для вебхуков ===
app = FastAPI()

@app.on_event("startup")
async def on_startup():
    # ИСПРАВЛЕНО: не добавляем https:// дважды
    base_url = os.getenv('RENDER_EXTERNAL_URL', 'https://techdrom-bot.onrender.com')
    webhook_url = f"{base_url}/webhook"
    await bot.set_webhook(url=webhook_url)

@app.post("/webhook")
async def webhook(request: Request):
    update_data = await request.json()
    update = Update(**update_data)
    await dp.feed_update(bot, update)
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
