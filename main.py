import os
import re
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart

# ---------------------- BOT SETUP ----------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found! Set it in Railway environment variables.")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# ---------------------- START COMMAND ----------------------
@dp.message(CommandStart())
async def start_command(message: types.Message):
    await message.answer(
        f"🤖 <b>Group Guardian Activated!</b>\n\n"
        f"Hello <b>{message.from_user.first_name}</b> 👋\n"
        "I'm here to keep this group clean and respectful.\n\n"
        "🚫 I instantly delete abusive, vulgar, or offensive messages.\n"
        "🔇 Offenders are muted permanently.\n\n"
        "Let's keep the chat peaceful and friendly! 💬✨"
    )

# ---------------------- ABUSIVE WORD LIST ----------------------
hindi_words = [
    "chutiya","madarchod","bhosdike","lund","gand","gaand","randi","behenchod","betichod","mc","bc",
    "lodu","lavde","harami","kutte","kamina","rakhail","randwa","suar","dogla","saala","tatti","chod",
    "chodne","rundi","bhadwe","nalayak","kamine","chinal","bhand","bhen ke","maa ke","behn ke","gandu",
    "chodna","choot","chut","chutmarike","chutiyapa","hijda","meetha","launda","laundiya","lavda","bevda",
    "nashedi","raand","kutti","kuttiya","haramzada","haramzadi","bhosri","bhosriwali","rand","mehnchod"
]

english_words = [
    "fuck","fucking","motherfucker","bitch","asshole","slut","porn","dick","pussy","sex","boobs","cock",
    "suck","fucker","whore","bastard","jerk","hoe","pervert","screwed","scumbag","balls","blowjob",
    "handjob","cum","sperm","vagina","dildo","horny","bang","banging","anal","nude","nsfw","shit","damn",
    "dumbass","retard","piss","douche","milf","boob","ass","booby","breast","naked","deepthroat","suckmy",
    "gay","lesbian","trans","blow","spank","fetish","orgasm","wetdream","masturbate","moan","ejaculate",
    "strip","whack","nipple","cumshot","lick","spitroast","tits","tit","hooker","escort","prostitute",
    "blowme","wanker","screw","bollocks","piss","bugger","slag","trollop","arse","arsehole","goddamn",
    "shithead","horniness"
]

# ---------------------- PHRASE DETECTION LIST ----------------------
phrases = [
    "send nudes","horny dm","let's have sex","i am horny","want to fuck",
    "boobs pics","let’s bang","video call nude","send pic without cloth",
    "suck my","blow me","deep throat","show tits","open boobs","send nude",
    "you are hot send pic","show your body","let's do sex","horny girl","horny boy",
    "come to bed","nude video call","i want sex","let me fuck","sex chat","do sex with me",
    "send xxx","share porn","watch porn together","send your nude"
]

# ---------------------- PATTERN BUILDER ----------------------
def build_pattern(words):
    safe = []
    for w in words:
        w = re.escape(w)
        w = (
            w.replace("a", "[a@4]")
             .replace("i", "[i1!|]")
             .replace("o", "[o0]")
             .replace("e", "[e3]")
             .replace("u", "[u*]")
        )
        safe.append(w)
    return r"\b(?:" + "|".join(safe) + r")\b"

abuse_pattern = re.compile(build_pattern(hindi_words + english_words), re.IGNORECASE)
phrase_pattern = re.compile(build_pattern(phrases), re.IGNORECASE)

# ---------------------- MESSAGE HANDLER ----------------------
@dp.message()
async def detect_abuse(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return

    text = (message.text or "").lower()

    # Skip admins
    try:
        member = await message.chat.get_member(message.from_user.id)
        if member.status in ("administrator", "creator"):
            return
    except Exception:
        return

    # Detect abusive words or phrases
    if abuse_pattern.search(text) or phrase_pattern.search(text):
        try:
            await message.delete()
        except Exception:
            pass

        try:
            await message.chat.restrict(
                message.from_user.id,
                permissions=types.ChatPermissions(can_send_messages=False)
            )
            await message.answer(
                f"🚫 <b>{message.from_user.first_name}</b> was muted permanently for using abusive/offensive language."
            )
        except Exception:
            pass

# ---------------------- RUN BOT ----------------------
async def main():
    print("🤖 Bot started successfully and watching for abuses...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

