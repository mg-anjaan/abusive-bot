import os
import re
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

# ===================================================
# 🔐 BOT TOKEN FROM ENVIRONMENT
# ===================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Dispatcher and Bot setup (Aiogram 3.13 compatible)
dp = Dispatcher(storage=MemoryStorage())
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# ===================================================
# 🚫 FULL LIST OF ABUSIVE / OFFENSIVE WORDS
# ===================================================
ABUSIVE_WORDS = {
    # Hindi + Hinglish
    "chutiya", "chutiye", "madarchod", "madharchod", "behenchod", "bhenchod",
    "bhosdike", "bhosadi", "bhosdika", "gandu", "gaand", "lund", "randi",
    "randii", "rundi", "kamina", "kaminey", "kamini", "kuttiya", "kutti",
    "haraami", "harami", "chakka", "chodu", "chod", "chudai", "jhant", "jhantu",
    "tatti", "saala", "saale", "saali", "raand", "rakhail", "maa-chod", "maderchod",
    "bhosda", "gandmara", "gandfat", "lundchod", "lundmar", "randwa",
    "mc", "bc", "m c", "b c",
    # English
    "fuck", "fucked", "fucking", "motherfucker", "mf", "fuk", "fuker", "fcker",
    "bitch", "bitches", "whore", "slut", "hoe", "asshole", "dick", "cock",
    "pussy", "cunt", "bastard", "shit", "jerk", "fag", "faggot", "porn",
    "boobs", "tits", "nipple", "breast", "suck", "dildo", "sex",
}

# ✅ Non-abusive short forms to ignore
WHITELIST = {"bcz", "because", "becoz", "bcoz", "abc", "bce", "bcg", "bcom", "mcq"}

# ===================================================
# 🔍 TEXT NORMALIZATION + DETECTION
# ===================================================
LEET_MAP = {
    "4": "a", "@": "a", "3": "e", "1": "i", "!": "i", "0": "o",
    "5": "s", "$": "s", "7": "t", "8": "b", "9": "g", "2": "z"
}

def normalize(text: str) -> str:
    text = text.lower()
    for k, v in LEET_MAP.items():
        text = text.replace(k, v)
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'(.)\1+', r'\1', text)
    return text

def contains_abuse(text: str):
    norm = normalize(text)
    tokens = norm.split()
    for token in tokens:
        if token in WHITELIST:
            continue
        if token in ABUSIVE_WORDS:
            return token
        for bad in ABUSIVE_WORDS:
            if len(bad) >= 3 and bad in token:
                return bad
    return None

# ===================================================
# ⚙️  HANDLERS
# ===================================================
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "🤖 <b>Abuse Guard Active!</b>\n"
        "I auto-delete abusive or offensive messages (Hindi + English)\n"
        "and permanently mute that user.\n\n"
        "🛡 Admins are ignored."
    )

@dp.message()
async def detect_abuse(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return

    text = message.text or message.caption or ""
    if not text:
        return

    bad = contains_abuse(text)
    if not bad:
        return

    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status in ["administrator", "creator"]:
        return

    # Delete the abusive message
    try:
        await message.delete()
    except:
        pass

    # Permanently mute user
    try:
        await bot.restrict_chat_member(
            message.chat.id,
            message.from_user.id,
            permissions=types.ChatPermissions(can_send_messages=False)
        )
        await message.answer(
            f"🚨 <b>{message.from_user.full_name}</b> was muted permanently "
            f"for abusive language (<code>{bad}</code>)."
        )
    except Exception as e:
        print("Mute failed:", e)

# ===================================================
# 🚀 START BOT
# ===================================================
async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not found in environment!")
        return
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

