import asyncio
import random
import smtplib
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
from datetime import datetime

# Load env vars
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ACCESS_CODE = os.getenv("ACCESS_CODE")

GMAIL_EVEN_EMAIL = os.getenv("GMAIL_EVEN_EMAIL")
GMAIL_EVEN_PASS = os.getenv("GMAIL_EVEN_PASS")
GMAIL_ODD_EMAIL = os.getenv("GMAIL_ODD_EMAIL")
GMAIL_ODD_PASS = os.getenv("GMAIL_ODD_PASS")

AYUSH_EVEN_EMAIL = os.getenv("AYUSH_EVEN_EMAIL")
AYUSH_EVEN_PASS = os.getenv("AYUSH_EVEN_PASS")
AYUSH_ODD_EMAIL = os.getenv("AYUSH_ODD_EMAIL")
AYUSH_ODD_PASS = os.getenv("AYUSH_ODD_PASS")

AUTHORIZED_USERS = {}  # Will store users who entered the correct access code
user_data = {}

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

start_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🔐 Enter Access Code")]], resize_keyboard=True
)

role_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Ankush Job")], [KeyboardButton(text="Ayush Job")]], resize_keyboard=True
)

done_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="✅ Done")]], resize_keyboard=True
)

@router.message(F.text == "/start")
async def start(message: Message):
    await message.answer("Welcome! Tap below to unlock the bot:", reply_markup=start_kb)

@router.message(F.text == "🔐 Enter Access Code")
async def ask_code(message: Message):
    await message.answer("🔑 Please send the access code:")

@router.message(F.text == ACCESS_CODE)
async def grant_access(message: Message):
    AUTHORIZED_USERS[message.from_user.id] = True
    await message.answer("✅ Access granted! Choose your role:", reply_markup=role_kb)

@router.message(lambda msg: msg.from_user.id not in AUTHORIZED_USERS)
async def not_authorized(message: Message):
    await message.answer("⛔ You are not authorized. Use /start and enter access code.")

@router.message(F.text.in_({"Ankush Job", "Ayush Job"}))
async def choose_role(message: Message):
    user_data[message.from_user.id] = {"role": message.text}
    await message.answer("📧 Send email addresses line by line. Tap ✅ Done when finished.", reply_markup=done_kb)

@router.message(F.text == "✅ Done")
async def ask_subject_body(message: Message):
    await message.answer("📝 Now send the Subject and Body in this format:\n\n<b>Subject: Your subject line</b>\nYour email body")

@router.message(lambda msg: "Subject:" in msg.text and msg.from_user.id in user_data)
async def parse_subject_body(message: Message):
    lines = message.text.strip().split("\n")
    subject_line = lines[0].replace("Subject:", "").strip()
    body_text = "\n".join(lines[1:])
    user_data[message.from_user.id]["subject"] = subject_line
    user_data[message.from_user.id]["body"] = body_text
    await message.answer("⏳ Enter minimum and maximum delay in seconds, separated by space (e.g. <code>5 10</code>):")

@router.message(lambda msg: msg.text and msg.text.replace(" ", "").isdigit())
async def parse_delay(message: Message):
    try:
        min_d, max_d = map(int, message.text.strip().split())
        user_data[message.from_user.id]["delay_range"] = (min_d, max_d)
        await message.answer("🚀 Sending emails... You’ll see live progress.")
        await send_emails(message)
    except:
        await message.answer("⚠️ Invalid format. Please send two numbers like: <code>5 15</code>")

@router.message()
async def collect_emails(message: Message):
    user_id = message.from_user.id
    emails = message.text.strip().splitlines()
    user_data.setdefault(user_id, {})
    user_data[user_id].setdefault("emails", []).extend([e.strip() for e in emails if e.strip()])
    await message.answer(f"✅ Collected {len(user_data[user_id]['emails'])} email(s). Tap ✅ Done when ready.")

async def send_emails(message: Message):
    data = user_data[message.from_user.id]
    subject = data["subject"]
    body = data["body"]
    emails = data["emails"]
    role = data["role"]
    min_d, max_d = data["delay_range"]

    today = datetime.now().day
    if role == "Ankush Job":
        sender_email = GMAIL_EVEN_EMAIL if today % 2 == 0 else GMAIL_ODD_EMAIL
        sender_pass = GMAIL_EVEN_PASS if today % 2 == 0 else GMAIL_ODD_PASS
    else:
        sender_email = AYUSH_EVEN_EMAIL if today % 2 == 0 else AYUSH_ODD_EMAIL
        sender_pass = AYUSH_EVEN_PASS if today % 2 == 0 else AYUSH_ODD_PASS

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, sender_pass)

    for i, email in enumerate(emails, 1):
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            server.sendmail(sender_email, email, msg.as_string())
            await message.answer(f"✅ Email {i}/{len(emails)} sent to: <b>{email}</b>")

            delay = random.randint(min_d, max_d)
            progress_msg = await message.answer(f"⏳ Next in {delay}s...")

            for remaining in range(delay - 1, 0, -1):
                await asyncio.sleep(1)
                await progress_msg.edit_text(f"⏳ Next in {remaining}s...")

        except Exception as e:
            await message.answer(f"❌ Failed to send to {email}\n{e}")
    await message.answer("✅ All emails sent!")

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot))
