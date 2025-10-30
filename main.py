import os
import re
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Comprehensive abusive / offensive / sexual slang list (Hindi + English) ---
ABUSIVE_WORDS = {
    # Hindi / Hinglish
    "chutiya","chutiye","chu*tiya","chut","madarchod","madharchod","madarchd",
    "behenchod","bhenchod","bhosdike","bhosadi","bhosdika","gandu","gaand","lund",
    "lavde","lavda","lavdoo","loda","randi","randii","rundi","rundii","kamina","kaminey","kamini",
    "kuttiya","kutti","haraami","harami","haramzada","haramzade","haramkhor",
    "chakka","chodu","chod","chudai","jhant","jhantu","tatti","saala","saale","saali",
    "raand","rakhail","maa-chod","maderchod","bhosda","gandmara","gandfat",
    "lundchod","lundmar","randwa","mc","bc","m c","b c","choot","chootiya",
    "ch0d","g@nd","l*nd","r@ndi","randee","gand@", "kutta","kutte","kutti","kuttiya",
    "rakhail","kamchor","ullu","ullu ke pathe","haram","bhosda","chakkar",
    "r@nd", "rand@","mad@rch0d","m@darchod","bh0sdike","m@derchod","bhos@di",
    "lund@", "gandu@", "b@stard","loda","chodna","chodne","chuda","chudi","chudwa",
    "chudti","chudega","chudegi","chodta","choda","chodi","chudaye","chudayega",
    "ma ki chut","behen ki chut","maa ka bhosda","maa ka lund",
    # English / Offensive / Sexual
    "fuck","fucked","fucking","motherfucker","mf","fuk","fuker","fcker",
    "bitch","bitches","whore","slut","hoe","asshole","dick","cock","pussy",
    "cunt","bastard","shit","jerk","fag","faggot","porn","boobs","boob","tits",
    "nipple","breast","suck","dildo","sex","sexual","nude","naked","vagina",
    "penis","anal","hentai","xvideos","xnxx","xhamster","pornhub","redtube",
    "sperm","cum","ejaculate","masturbate","masturbation","blowjob","handjob",
    "fuckboy","fuckgirl","pussyy","d1ck","p3nis","p0rn","s3x","boobies",
    "titty","boobie","a$$","b!tch","f@ck","d!ck","p@rn","s3xy","horny",
    "deepthroat","69","p0rn0","p0rno","sexy","fck","c0ck","c@ck","s@x",
    "b@ng","creampie","escort","hooker","stripper","fetish","lust","orgasm",
    "threesome","n1pple","t1ts","b@bs","hornyy","sexting","kamasutra","v!rgin",
    "virginity","milf","gilf","teen","stepmom","stepsis","incest","bj","hj",
    "anal","doggy","missionary","cumshot","facial","suckoff","handy","lapdance",
    "eros","boobjob","bang","rape","rapist","molest","slutty","nakedgirl",
    "sexyvideo","xrated","p0rnhub","tiktokporn","erotic","pornstar",
}

# --- Avoid false positives ---
SAFE_WORDS = {"chutney","shortcut","pitch","assistant","class","pass","cocktail","bass","grass","asset"}

# --- Regex builder to detect variations (g@nd, l*nd, etc.) ---
def build_pattern(word):
    word = re.escape(word)
    word = word.replace("\\*", "[^a-zA-Z0-9]{0,2}").replace("\\@", "a").replace("0","o")
    pattern = ""
    for ch in word:
        if ch.isalpha():
            pattern += f"[{ch}{ch.upper()}]+[^a-zA-Z0-9_]*"
        else:
            pattern += re.escape(ch)
    return pattern

ABUSE_REGEX = re.compile("|".join(build_pattern(w) for w in ABUSIVE_WORDS), re.IGNORECASE)

def is_abusive(text: str) -> bool:
    if not text:
        return False
    txt = text.lower()
    if any(safe in txt for safe in SAFE_WORDS):
        return False
    return bool(ABUSE_REGEX.search(txt))

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

@dp.message()
async def detect_abuse(message: types.Message):
    if message.chat.type not in ["group","supergroup"]:
        return
    if not message.from_user:
        return
    user_id = message.from_user.id
    chat_id = message.chat.id
    member = await bot.get_chat_member(chat_id, user_id)
    if member.status in ["administrator","creator"]:
        return

    text = message.text or message.caption or ""
    if is_abusive(text):
        try:
            await bot.delete_message(chat_id, message.message_id)
            await bot.restrict_chat_member(
                chat_id,
                user_id,
                permissions=types.ChatPermissions(can_send_messages=False)
            )
            await message.answer(
                f"🚫 <b>{message.from_user.first_name}</b> was muted permanently for using abusive or offensive words."
            )
        except Exception as e:
            print(f"Error: {e}")

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN missing in environment variables!")
        return
    print("🤖 Bot started successfully and watching for abuses...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

