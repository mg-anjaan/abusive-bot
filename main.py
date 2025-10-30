import os
import asyncio
from aiogram import os
import re
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)

# =====================================
# 🧩 1️⃣  FULL ABUSIVE / OFFENSIVE WORD LIST
# =====================================
ABUSIVE_WORDS = {
    # HINDI + HINGLISH
    "chutiya", "chutiye", "chutiyaa", "madarchod", "madharchod", "behenchod", "bhenchod",
    "bhosdike", "bhosadi", "bhosdika", "gandu", "gaand", "lund", "lunde", "randi",
    "runda", "randii", "rundi", "rund", "kamina", "kaminey", "kamini", "kuttiya", "kutti",
    "kutte", "kuttey", "haraami", "harami", "chakka", "chodu", "chod", "chudai", "chudaiya",
    "jhant", "jhantu", "tatti", "kutta", "saala", "saale", "saali", "raand", "rakhail",
    "randiya", "rundii", "behenchod", "maa", "maa-chod", "maderchod", "madarchod",
    "bhosda", "bhosdaap", "gandmara", "gandu", "gandfat", "lundchod", "lundkha", "lundmar",
    "kutta", "kutti", "kuttiya", "kutte", "kuttey", "randi", "randwa",
    # Short forms
    "mc", "bc", "b c", "m c",
    # ENGLISH
    "fuck", "fucked", "fucking", "motherfucker", "mf", "fuk", "fuker", "fcker",
    "bitch", "bitches", "bitchy", "whore", "slut", "sluts", "hoe", "hoes",
    "ass", "asses", "asshole", "dick", "dicks", "dickhead", "cock", "cocks",
    "pussy", "cunt", "bastard", "bastards", "shit", "shitty", "jerk", "jerkoff",
    "fag", "faggot", "gayfuck", "retard", "nude", "porn", "porno", "horny",
    "boobs", "tits", "nipple", "breast", "suck", "sucking", "dildo", "orgasm", "sex",
}

# ✅ Non-abusive short forms we should ignore
WHITELIST = {
    "bcz", "because", "becoz", "bcoz", "abc", "bce", "bcg", "bcom", "mca", "mcq"
}

# =====================================
# 🧠 2️⃣  NORMALIZATION LOGIC
# =====================================
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

# =====================================
# ⚙️ 3️⃣  HANDLERS
# =====================================
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("🚫 I detect abusive words (Hindi + English) and mute users permanently.\nAdmins are ignored.")

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

    # Delete message
    try:
        await message.delete()
    except:
        pass

    # Mute permanently
    try:
        await bot.restrict_chat_member(
            message.chat.id,
            message.from_user.id,
            permissions=types.ChatPermissions(can_send_messages=False)
        )
        await message.answer(
            f"🚨 <b>{message.from_user.full_name}</b> was muted permanently for abusive language (<code>{bad}</code>)."
        )
    except Exception as e:
        print("Mute failed:", e)

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not found in environment!")
        return
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

