import os
import re
import unicodedata
import asyncio
import time
from collections import defaultdict
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery  # ✅ added for button

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
    "lodu","lavde","harami","kutte","kamina","rakhail","randwa","suar","sasura","dogla","saala","tatti","chod",
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
    "blowme","wanker","screw","bollocks","bugger","slag","trollop","arse","arsehole","goddamn",
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
    s = re.sub(r'[\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff]+', "", s)
    EXTRA_CHAR_MAP = {
        "©": "c", "ʋ": "u", "ʌ": "u", "ν": "u", "ⅴ": "v", "v̇": "v",
        "ɯ": "m", "ɡ": "g", "ɩ": "i", "ɪ": "i", "ʜ": "h", "ᴜ": "u", "ᴛ": "t", "ᴠ": "v",
        "ᴡ": "w", "ᴋ": "k", "ḩ": "h", "ů": "u", "ŧ": "t", "ꜱ": "s", "ᴄ": "c", "ᴀ": "a",
        "ʙ": "b", "ᴅ": "d", "ᴇ": "e", "ꜰ": "f", "ɢ": "g", "ʟ": "l", "ᴍ": "m", "ɴ": "n",
        "ᴏ": "o", "ᴘ": "p", "ᴊ": "j", "ʀ": "r", "ᴢ": "z", "ʏ": "y"
    }
    mapped_chars = []
    for ch in s:
        if ch in EXTRA_CHAR_MAP:
            mapped_chars.append(EXTRA_CHAR_MAP[ch])
            continue
        name = unicodedata.name(ch, "")
        if any(tag in name for tag in ("MATHEMATICAL","FULLWIDTH","CIRCLED","DOUBLE-STRUCK","SQUARED","MONOSPACE","BOLD","ITALIC")):
            parts = name.split()
            for token in reversed(parts):
                if len(token) == 1 and token.isalpha():
                    mapped_chars.append(token.lower())
                    break
            else:
                mapped_chars.append(" ")
            continue
        if ord(ch) < 128:
            mapped_chars.append(ch)
        else:
            mapped_chars.append(" ")
    s = "".join(mapped_chars)
    s = re.sub(r"[^a-z0-9\s]", " ", s.lower())
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(.)\1{2,}", r"\1\1", s)
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
    return r"[\W_]*".join(parts)

def build_pattern(words):
    fragments = []
    for w in words:
        if not w.strip():
            continue
        if " " in w:
            subtokens = [tolerant_token_pattern(tok) for tok in w.split()]
            frag = r"[\W_]*".join(subtokens)
        else:
            frag = tolerant_token_pattern(w)
        fragments.append(frag)
    pattern = r"(?<![A-Za-z0-9])(?:" + "|".join(fragments) + r")(?![A-Za-z0-9])"
    return re.compile(pattern, re.IGNORECASE | re.UNICODE)

combined_words = hindi_words + english_words
combo_words = [f"{p} {c}" for p in family_prefixes for c in combined_words]
final_word_list = combined_words + phrases + combo_words
abuse_pattern = build_pattern(final_word_list)

# ---------------------- HELPERS ----------------------
async def gather_message_text_for_matching(message: types.Message) -> str:
    text = " ".join(filter(None, [message.text, message.caption]))
    return normalize_text_for_match(text)

# ---------------------- ANTI-SPAM / USERBOT BLOCKER ----------------------
_user_times = defaultdict(list)
USERBOT_CMD_TRIGGERS = {"raid","spam","ping","eval","exec","repeat","dox","flood","bomb"}

@dp.message(lambda m: m.text and m.text.startswith((".", "/")))
async def block_userbot_commands(message: types.Message):
    if message.chat.type not in ("group","supergroup"):
        return
    try:
        member = await message.chat.get_member(message.from_user.id)
        if member.status in ("administrator","creator"):
            return
    except Exception:
        pass
    txt = message.text.strip().lower()
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
    return await detect_abuse(message)

# ---------------------- ABUSE DETECTOR ----------------------
@dp.message()
async def detect_abuse(message: types.Message):
    if message.chat.type not in ["group","supergroup"]:
        return
    text = await gather_message_text_for_matching(message)
    if not text or not message.from_user or message.from_user.is_bot:
        return
    try:
        member = await message.chat.get_member(message.from_user.id)
        if member.status in ("administrator","creator"):
            return
    except Exception:
        pass

    now = time.time()
    uid = message.from_user.id
    _user_times[uid] = [t for t in _user_times[uid] if now - t < 5]
    _user_times[uid].append(now)
    if len(_user_times[uid]) >= 3:
        await message.delete()
        await message.chat.restrict(uid, permissions=types.ChatPermissions(can_send_messages=False))
        await message.answer(f"⚠️ <b>{message.from_user.first_name}</b> was muted for flooding.")
        _user_times[uid].clear()
        return

    if abuse_pattern.search(text):
        await message.delete()
        await message.chat.restrict(
            uid, permissions=types.ChatPermissions(can_send_messages=False)
        )
        # ✅ Send mute message with Unmute button
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔓 Unmute User", callback_data=f"unmute_{uid}")]]
        )
        await message.answer(
            f"🚫 <b>{message.from_user.first_name}</b> was muted permanently for using abusive/offensive language.",
            reply_markup=keyboard
        )

# ---------------------- UNMUTE BUTTON HANDLER ----------------------
@dp.callback_query(lambda c: c.data and c.data.startswith("unmute_"))
async def handle_unmute_button(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    chat = callback.message.chat
    try:
        member = await chat.get_member(callback.from_user.id)
        if member.status not in ("administrator","creator"):
            await callback.answer("❌ Only admins can unmute users.", show_alert=True)
            return
    except Exception:
        await callback.answer("⚠️ Could not verify admin status.", show_alert=True)
        return

    try:
        await chat.restrict(
            user_id,
            permissions=types.ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_invite_users=True,
                can_change_info=False,
                can_pin_messages=False
            )
        )
        await callback.message.reply(
            f"✅ <b>User has been unmuted by {callback.from_user.first_name}.</b>"
        )
        await callback.answer("User unmuted ✅")
    except Exception as e:
        await callback.answer(f"⚠️ Failed to unmute: {e}", show_alert=True)

# ---------------------- RUN BOT ----------------------
async def main():
    print("🤖 Bot started successfully and watching for abuses...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())