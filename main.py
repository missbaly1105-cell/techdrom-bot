import os
import asyncio
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, Update
from fastapi import FastAPI, Request
import uvicorn
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

SYSTEM_PROMPT = "Ты — помощник школы Технодром"

user_sessions = {}

async def ask_llm(user_id, text):
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3.1-8B-Instruct",
            headers={"Authorization": f"Bearer {HF_API_KEY}"},
            json={"inputs": "Привет", "parameters": {"max_new_tokens": 10}},
            timeout=10
        )
        return f"Статус: {response.status_code}\nОтвет: {response.text[:200]}"
    except Exception as e:
        return f"Исключение: {str(e)[:200]}"

@router.message(F.text)
async def handle_message(message: Message):
    answer = await ask_llm(message.from_user.id, message.text)
    await message.answer(answer)

dp.include_router(router)

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    base_url = os.getenv('RENDER_EXTERNAL_URL', 'https://techdrom-bot.onrender.com')
    webhook_url = f"{base_url}/webhook"
    await bot.set_webhook(url=webhook_url)

@app.post("/webhook")
async def webhook(request: Request):
    update = Update(**await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.get("/")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
