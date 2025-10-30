import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)

ABUSIVE_WORDS = [
    "chutiya", "madarchod", "bhosdike", "bitch", "fuck", "mc", "bc",
    "gaand", "lund", "randi", "kutte", "harami", "slut", "nude",
    "gandu", "kuttiya", "kamina", "chakka", "behenchod", "tera baap"
]

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("🚫 I delete abusive messages and mute the user permanently!")

@dp.message()
async def detect_abuse(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return

    text = message.text.lower() if message.text else ""

    if any(word in text for word in ABUSIVE_WORDS):
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)

        # Ignore admins
        if member.status in ["administrator", "creator"]:
            return

        try:
            await message.delete()
        except:
            pass

        try:
            await bot.restrict_chat_member(
                message.chat.id,
                message.from_user.id,
                permissions=types.ChatPermissions(can_send_messages=False)
            )
            await message.answer(
                f"🚨 <b>{message.from_user.full_name}</b> was muted permanently for abusive language."
            )
        except Exception as e:
            print(f"Error: {e}")

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not found!")
        return
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
