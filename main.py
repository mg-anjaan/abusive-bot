import os
import re
import unicodedata
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
import time
from collections import defaultdict

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

# ---------------------- WORD LISTS ----------------------
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

family_prefixes = [
    "teri","teri ki","tera","tera ki","teri maa","teri behen","teri gf","teri sister",
    "teri maa ki","teri behen ki","gf","bf","mms","bana","banaa","banaya"
]

phrases = [
    "send nudes","horny dm","let's have sex","i am horny","want to fuck",
    "boobs pics","let’s bang","video call nude","send pic without cloth",
    "suck my","blow me","deep throat","show tits","open boobs","send nude",
    "you are hot send pic","show your body","let's do sex","horny girl","horny boy",
    "come to bed","nude video call","i want sex","let me fuck","sex chat","do sex with me",
    "send xxx","share porn","watch porn together","send your nude"
]

# ---------------------- NORMALIZATION ----------------------
def normalize_text_for_match(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r'[\u0300-\u036f]+', "", s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def tolerant_token_pattern(token: str) -> str:
    token = token.strip().lower()
    if not token:
        return ""
    escaped = re.escape(token)
    parts = []
    i = 0
    while i < len(escaped):
        ch = escaped[i]
        if ch == "\\" and i + 1 < len(escaped):
            parts.append(escaped[i:i+2])
            i += 2
        else:
            parts.append(ch)
            i += 1
    joined = r"[\W_]*".join(parts)
    return joined

def build_pattern(words):
    fragments = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        if " " in w:
            subtokens = [tolerant_token_pattern(tok) for tok in w.split()]
            frag = r"[\W_]*".join(subtokens)
        else:
            frag = tolerant_token_pattern(w)
        fragments.append(frag)
    pattern = r"(?<![A-Za-z0-9])(?:" + "|".join(fragments) + r")(?![A-Za-z0-9])"
    return re.compile(pattern, re.IGNORECASE | re.UNICODE)

combined_words = list(hindi_words) + list(english_words)
combo_words = []
for prefix in family_prefixes:
    for core in combined_words:
        combo = (prefix + " " + core).strip()
        combo_words.append(combo)
final_word_list = combined_words + phrases + combo_words
abuse_pattern = build_pattern(final_word_list)

# ---------------------- MESSAGE AGGREGATION ----------------------
async def gather_message_text_for_matching(message: types.Message) -> str:
    parts = []
    if getattr(message, "text", None):
        parts.append(message.text)
    if getattr(message, "caption", None):
        parts.append(message.caption)
    combined = " ".join([p for p in parts if p])
    return normalize_text_for_match(combined)

# ---------------------- USERBOT COMMAND BLOCKER ----------------------
_user_times = defaultdict(list)
USERBOT_CMD_TRIGGERS = {"raid","spam","ping","eval","exec","repeat","dox","flood","bomb"}

@dp.message(lambda m: m.text and m.text.startswith((".", "/")))
async def block_userbot_commands(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        return
    if not message.text:
        return

    try:
        member = await message.chat.get_member(message.from_user.id)
        if getattr(member, "status", None) in ("administrator","creator"):
            return
    except Exception:
        pass

    txt = message.text.strip().lower()
    if txt.startswith((".", "/")):
        cmd = txt[1:].split()[0] if len(txt) > 1 else ""
        if cmd in USERBOT_CMD_TRIGGERS:
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
                    f"⚠️ <b>{message.from_user.first_name}</b> muted for suspicious command ({cmd})."
                )
            except Exception:
                pass
            return
        # forward .chut etc. to abuse filter
        return await detect_abuse(message)

# ---------------------- ABUSE FILTER + FLOOD CONTROL ----------------------
@dp.message()
async def detect_abuse(message: types.Message):
    if message.chat.type not in ["group","supergroup"]:
        return

    text = await gather_message_text_for_matching(message)
    if not text:
        return
    if not message.from_user or getattr(message.from_user,"is_bot",False):
        return

    try:
        member = await message.chat.get_member(message.from_user.id)
        if getattr(member,"status",None) in ("administrator","creator"):
            return
    except Exception:
        pass

    # --- Anti-Flood: 3+ messages in 5 seconds ---
    now = time.time()
    uid = message.from_user.id
    _user_times[uid] = [t for t in _user_times[uid] if now - t < 5]
    _user_times[uid].append(now)
    if len(_user_times[uid]) >= 3:
        try:
            await message.delete()
        except Exception:
            pass
        try:
            await message.chat.restrict(
                uid,
                permissions=types.ChatPermissions(can_send_messages=False)
            )
            await message.answer(
                f"⚠️ <b>{message.from_user.first_name}</b> was muted for flooding (too many messages)."
            )
        except Exception:
            pass
        _user_times[uid].clear()
        return

    # --- Abuse detection ---
    try:
        if abuse_pattern.search(text):
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
    except Exception:
        pass

# ---------------------- RUN BOT ----------------------
async def main():
    print("🤖 Bot started successfully and watching for abuses...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())