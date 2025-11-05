import os
import re
import unicodedata
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

# ---------------------- ABUSIVE WORD LIST (preserved) ----------------------
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

# Add family-targeted prefixes/phrases that often appear together with slurs
family_prefixes = [
    "teri", "teri ki", "tera", "tera ki", "teri maa", "teri behen", "teri gf", "teri sister",
    "teri maa ki", "teri behen ki", "gf", "bf", "mms", "bana", "banaa", "banaya"
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

# ---------------------- NORMALIZATION HELPERS (robust) ----------------------
# A map for common homoglyphs & accented letters -> base latin
HOMOGLYPH_MAP = {
    ord("а"): "a", ord("А"): "a", ord("б"): "b", ord("Б"): "b", ord("в"): "v", ord("В"): "v",
    ord("е"): "e", ord("Е"): "e", ord("о"): "o", ord("О"): "o", ord("с"): "c", ord("С"): "c",
    ord("р"): "p", ord("Р"): "p", ord("у"): "y", ord("У"): "y", ord("х"): "x", ord("Х"): "x",
    ord("ι"): "i", ord("Ι"): "i", ord("ν"): "v", ord("Ν"): "v", ord("μ"): "m", ord("Μ"): "m",
    ord("т"): "t", ord("Т"): "t",
    # Latin accented letters to base
    ord("á"): "a", ord("à"): "a", ord("â"): "a", ord("ä"): "a", ord("ã"): "a",
    ord("é"): "e", ord("è"): "e", ord("ë"): "e", ord("ê"): "e",
    ord("í"): "i", ord("ì"): "i", ord("ï"): "i", ord("î"): "i",
    ord("ó"): "o", ord("ò"): "o", ord("ö"): "o", ord("ô"): "o",
    ord("ú"): "u", ord("ù"): "u", ord("ü"): "u", ord("û"): "u",
    ord("ñ"): "n", ord("ç"): "c", ord("ß"): "ss"
}

# Regex to remove combining marks (accents) and emoji blocks
COMBINING_MARKS_RE = re.compile(r'[\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff]+', flags=re.UNICODE)
EMOJI_RE = re.compile(
    "[" 
    "\U0001F300-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002700-\U000027BF"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE
)

def normalize_text_for_match(s: str) -> str:
    """
    Convert any Unicode stylised text to plain ASCII-like text before matching.
    Steps:
      1. Decompose & remove combining marks (accents)
      2. Map mathematical/fullwidth/circled/double-struck letters -> base letters using unicode names
      3. Translate common homoglyphs (Cyrillic/Greek) and accented Latin to base
      4. Remove emojis and non-alphanum, lowercase, compress repeats and spaces
    """
    if not s:
        return ""
    # 1) Unicode decomposition & remove combining marks
    s = unicodedata.normalize("NFKD", s)
    s = COMBINING_MARKS_RE.sub("", s)

    # 2) Map mathematical/fullwidth/circled/double-struck glyphs to ASCII base if possible
    mapped_chars = []
    for ch in s:
        name = unicodedata.name(ch, "")
        # If it's a MATHEMATICAL or FULLWIDTH or CIRCLED or DOUBLE-STRUCK letter, try to extract base letter
        if any(tag in name for tag in ("MATHEMATICAL", "FULLWIDTH", "CIRCLED", "DOUBLE-STRUCK", "SQUARED")):
            parts = name.split()
            # often the last token is the letter name e.g. "MATHEMATICAL BOLD CAPITAL A"
            last = parts[-1] if parts else ""
            if len(last) == 1 and last.isalpha():
                mapped_chars.append(last.lower())
                continue
            # sometimes last token could be "CAPITAL" with letter before — handle common layouts
            # fallback to trying to find a single-letter token
            letter_found = None
            for token in reversed(parts):
                if len(token) == 1 and token.isalpha():
                    letter_found = token.lower()
                    break
            if letter_found:
                mapped_chars.append(letter_found)
                continue
        # else map using HOMOGLYPH_MAP (covers many Cyrillic/accents)
        mapped_chars.append(HOMOGLYPH_MAP.get(ord(ch), ch))
    s = "".join(mapped_chars)

    # 3) Remove emojis and replace non-alnum with spaces
    s = EMOJI_RE.sub(" ", s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # compress long repeats (keep up to 2 characters, e.g., cooool -> coool -> coo)
    s = re.sub(r"(.)\1{2,}", r"\1\1", s)
    return s

# ---------------------- PATTERN BUILDER (very tolerant) ----------------------
def tolerant_token_pattern(token: str) -> str:
    r"""Return a regex fragment that matches token even with arbitrary non-word chars,
       spaces, emojis, or inserted glyphs between letters.
       Approach: insert [\W_]* between every letter/digit so that obfuscation won't break it.
       (raw docstring prevents SyntaxWarning on '\W')
    """
    token = token.strip().lower()
    if not token:
        return ""
    # escape token for regex
    escaped = re.escape(token)
    # split escaped into units keeping escape sequences intact
    parts = []
    i = 0
    while i < len(escaped):
        ch = escaped[i]
        if ch == "\\" and i + 1 < len(escaped):
            # keep backslash + next char together as a unit (e.g., \ )
            parts.append(escaped[i:i+2])
            i += 2
        else:
            parts.append(ch)
            i += 1
    # insert flexible separator to tolerate inserted non-word chars between any units
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
    # final regex: require not alnum immediately before/after to avoid matching inside other words
    pattern = r"(?<![A-Za-z0-9])(?:" + "|".join(fragments) + r")(?![A-Za-z0-9])"
    try:
        return re.compile(pattern, re.IGNORECASE | re.UNICODE)
    except re.error:
        # fallback: simpler OR-joined escaped pattern
        return re.compile(r"(?:" + "|".join(re.escape(w) for w in words if w) + r")", re.IGNORECASE)

# Build combined abusive/phrase patterns using the tolerant builder
combined_words = list(hindi_words) + list(english_words)
combo_words = []
for prefix in family_prefixes:
    for core in combined_words:
        combo = (prefix + " " + core).strip()
        combo_words.append(combo)
final_word_list = combined_words + phrases + combo_words
abuse_pattern = build_pattern(final_word_list)

# ---------------------- MESSAGE TEXT AGGREGATION ----------------------
async def gather_message_text_for_matching(message: types.Message) -> str:
    parts = []
    if getattr(message, "text", None):
        parts.append(message.text)
    if getattr(message, "caption", None):
        parts.append(message.caption)
    if getattr(message, "forward_signature", None):
        parts.append(message.forward_signature)
    if getattr(message, "forward_from", None):
        try:
            ff = message.forward_from
            parts.append(" ".join(filter(None, [getattr(ff, "first_name", ""), getattr(ff, "last_name", "")])))
        except Exception:
            pass
    if getattr(message, "reply_to_message", None):
        rt = message.reply_to_message
        if getattr(rt, "text", None):
            parts.append(rt.text)
        if getattr(rt, "caption", None):
            parts.append(rt.caption)
    combined = " ".join([p for p in parts if p])
    return normalize_text_for_match(combined)

# ---------------------- MESSAGE HANDLER (preserve existing behavior) ----------------------
@dp.message()
async def detect_abuse(message: types.Message):
    # only groups/supergroups
    if message.chat.type not in ["group", "supergroup"]:
        return

    # gather and normalize text
    text = await gather_message_text_for_matching(message)
    if not text:
        return

    # skip if no sender or sender is a bot
    if not message.from_user or getattr(message.from_user, "is_bot", False):
        return

    # skip admins/creators exactly like before
    try:
        member = await message.chat.get_member(message.from_user.id)
        if getattr(member, "status", None) in ("administrator", "creator"):
            return
    except Exception:
        # mirrored behavior: continue if fetch fails (like your original)
        pass

    # final detection & preserve delete + permanent mute + reply behavior
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
        # fail-safe: do not crash bot on unexpected regex/runtime issues
        pass

# ---------------------- RUN BOT ----------------------
async def main():
    print("🤖 Bot started successfully and watching for abuses...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())