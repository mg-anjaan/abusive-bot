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

# ---------------------- ABUSIVE WORD LIST (preserved + can be expanded) ----------------------
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
# These will be combined during matching to catch "teri maa ki ..." style patterns.
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

# ---------------------- NORMALIZATION HELPERS ----------------------
# A map to normalize common homoglyphs (Cyrillic/accents → Latin)
HOMOGLYPH_MAP = {
    # Cyrillic to latin
    ord("а"): "a", ord("е"): "e", ord("о"): "o", ord("і"): "i", ord("ѕ"): "s",
    ord("р"): "p", ord("с"): "c", ord("у"): "y", ord("х"): "x", ord("м"): "m",
    ord("к"): "k", ord("т"): "t", ord("б"): "b",
    # Latin accented letters to base
    ord("á"): "a", ord("à"): "a", ord("â"): "a", ord("ä"): "a", ord("ã"): "a",
    ord("é"): "e", ord("è"): "e", ord("ë"): "e", ord("ê"): "e",
    ord("í"): "i", ord("ì"): "i", ord("ï"): "i", ord("î"): "i",
    ord("ó"): "o", ord("ò"): "o", ord("ö"): "o", ord("ô"): "o",
    ord("ú"): "u", ord("ù"): "u", ord("ü"): "u", ord("û"): "u",
    ord("ñ"): "n", ord("ç"): "c", ord("ß"): "ss"
}

# regex to remove combining marks (accents) and many symbol emojis
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
    """Normalize incoming text to a simplified latin-only, lowercased form.
       Removes emojis, combining marks, maps homoglyphs, replaces non-alnum with spaces,
       compresses repeated characters, and trims.
    """
    if not s:
        return ""
    # Unicode normalization
    s = unicodedata.normalize("NFKD", s)
    # Remove combining marks
    s = COMBINING_MARKS_RE.sub("", s)
    # Map homoglyphs and accented chars to latin base
    s = s.translate(HOMOGLYPH_MAP)
    # Lowercase
    s = s.lower()
    # Remove emojis
    s = EMOJI_RE.sub(" ", s)
    # Replace any character that's not a-z or 0-9 with a space
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    # Collapse many spaces
    s = re.sub(r"\s+", " ", s).strip()
    # Reduce long repeated sequences of the same character (keep up to 2)
    s = re.sub(r"(.)\1{2,}", r"\1\1", s)
    return s

# ---------------------- PATTERN BUILDER (very tolerant) ----------------------
def tolerant_token_pattern(token: str) -> str:
    """Return a regex fragment that matches token even with arbitrary non-word chars,
       spaces, emojis, or inserted glyphs between letters.
       Approach: insert [\W_]* between every letter/digit so that obfuscation won't break it.
    """
    token = token.strip().lower()
    # escape token for regex, but we will insert flexible separators between characters
    escaped = re.escape(token)
    # Insert flexible separator after each escaped char (handles multichar escapes too)
    # We'll treat the escaped string as sequence of characters to interleave [\W_]* between letters/digits.
    parts = []
    i = 0
    while i < len(escaped):
        ch = escaped[i]
        # handle escaped sequences like \uXXXX or \x.. or \.
        if ch == "\\":
            # take backslash and the next char as a unit
            if i + 1 < len(escaped):
                unit = escaped[i:i+2]
                parts.append(unit)
                i += 2
            else:
                parts.append(ch)
                i += 1
        else:
            parts.append(ch)
            i += 1
    # Build pattern: after each unit allow arbitrary non-word separators [\W_]* (this also allows spaces, emojis removed earlier)
    joined = r"[\W_]*".join(parts)
    return joined

def build_pattern(words):
    fragments = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        # For multi-word phrases, allow arbitrary separators between words too
        if " " in w:
            # split and build tolerant fragments for each subtoken, allow separators between
            subtokens = [tolerant_token_pattern(tok) for tok in w.split()]
            frag = r"[\W_]*".join(subtokens)
        else:
            frag = tolerant_token_pattern(w)
        fragments.append(frag)
    # create final regex. Use lookarounds to avoid matching inside larger alphanumeric words,
    # but since we allow separators between letters, require not alnum immediately before/after (or start/end)
    pattern = r"(?<![A-Za-z0-9])(?:" + "|".join(fragments) + r")(?![A-Za-z0-9])"
    try:
        return re.compile(pattern, re.IGNORECASE | re.UNICODE)
    except re.error:
        # fallback to a simpler OR-joined escaped pattern if compilation fails for some reason
        return re.compile(r"(?:" + "|".join(re.escape(w) for w in words if w) + r")", re.IGNORECASE)

# Build combined abusive/phrase patterns using the tolerant builder
# Keep original lists untouched, but also add family prefix combinations to catch "teri maa ki chut" etc.
combined_words = list(hindi_words) + list(english_words)

# also create phrase-like combos: e.g. "teri maa ki" + abusive_word -> many combos
combo_words = []
for prefix in family_prefixes:
    for core in combined_words:
        combo = (prefix + " " + core).strip()
        combo_words.append(combo)

# Final word list to compile: original words + phrases + prefix combos + explicit phrases
final_word_list = combined_words + phrases + combo_words

abuse_pattern = build_pattern(final_word_list)

# ---------------------- MESSAGE TEXT AGGREGATION ----------------------
async def gather_message_text_for_matching(message: types.Message) -> str:
    parts = []
    # text
    if getattr(message, "text", None):
        parts.append(message.text)
    # caption (media)
    if getattr(message, "caption", None):
        parts.append(message.caption)
    # forward signature or forward_from names
    if getattr(message, "forward_signature", None):
        parts.append(message.forward_signature)
    if getattr(message, "forward_from", None):
        try:
            ff = message.forward_from
            parts.append(" ".join(filter(None, [getattr(ff, "first_name", ""), getattr(ff, "last_name", "")])))
        except Exception:
            pass
    # reply/quoted message content
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
    # only act in groups/supergroups
    if message.chat.type not in ["group", "supergroup"]:
        return

    # gather text from all fields and normalize
    text = await gather_message_text_for_matching(message)
    if not text:
        return

    # Skip if message has no sender or is a bot
    if not message.from_user or getattr(message.from_user, "is_bot", False):
        return

    # Skip admins/creators — keep original behavior
    try:
        member = await message.chat.get_member(message.from_user.id)
        if getattr(member, "status", None) in ("administrator", "creator"):
            return
    except Exception:
        # If fetching member fails, do not crash — continue to check (this mirrors your old logic)
        # but if you prefer to skip when fetch fails, uncomment the next line:
        # return
        pass

    # Final detection using the tolerant compiled pattern
    try:
        if abuse_pattern.search(text):
            # attempt to delete (preserve your original behavior)
            try:
                await message.delete()
            except Exception:
                pass

            # permanent mute as before
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
        # If something unexpected happens during matching, fail silently to avoid crashing bot
        pass

# ---------------------- RUN BOT ----------------------
async def main():
    print("🤖 Bot started successfully and watching for abuses...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())