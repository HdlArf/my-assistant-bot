"""Command handlers for the assistant bot."""

import html
import logging

import httpx
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot import db
from bot.config import config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# Basic commands
# ─────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message."""
    user = update.effective_user
    name = html.escape(user.first_name or "there")

    text = (
        f"Hello <b>{name}</b>! 👋\n\n"
        "I'm your personal assistant bot. Here's what I can do:\n\n"
        "📝 <b>Notes</b> — /note, /notes, /delnote\n"
        "🌤 <b>Weather</b> — /weather &lt;city&gt;\n"
        "💱 <b>Currency</b> — /currency &lt;amount&gt; &lt;from&gt; &lt;to&gt;\n"
        "🤖 <b>AI</b> — /ask &lt;question&gt;\n\n"
        "Type /help for more details."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all available commands."""
    text = (
        "<b>Available Commands</b>\n\n"
        "/start — Welcome message\n"
        "/help — Show this help\n\n"
        "<b>📝 Notes</b>\n"
        "/note &lt;text&gt; — Save a note\n"
        "/notes — List your notes\n"
        "/delnote &lt;id&gt; — Delete a note\n\n"
        "<b>🌤 Weather</b>\n"
        "/weather &lt;city&gt; — Current weather\n\n"
        "<b>💱 Currency</b>\n"
        "/currency &lt;amount&gt; &lt;from&gt; &lt;to&gt;\n"
        "Example: /currency 100 USD EUR\n\n"
        "<b>🤖 AI</b>\n"
        "/ask &lt;question&gt; — Ask the AI assistant"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ─────────────────────────────────────────────────────────
# Notes
# ─────────────────────────────────────────────────────────

async def add_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save a new note."""
    user_id = update.effective_user.id
    content = " ".join(context.args).strip() if context.args else ""

    if not content:
        await update.message.reply_text(
            "Usage: <code>/note your text here</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    note_id = db.add_note(user_id, content)
    safe = html.escape(content)
    await update.message.reply_text(
        f"✅ Note saved (id: <b>{note_id}</b>)\n\n<i>{safe}</i>",
        parse_mode=ParseMode.HTML,
    )


async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all notes for the user."""
    user_id = update.effective_user.id
    notes = db.list_notes(user_id)

    if not notes:
        await update.message.reply_text(
            "You have no notes yet. Use /note to create one."
        )
        return

    lines = ["<b>Your Notes</b>\n"]
    for row in notes:
        safe = html.escape(row["content"])
        lines.append(f"<b>#{row['id']}</b> — {safe}")

    lines.append(f"\n<i>Total: {len(notes)}</i>")
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
    )


async def delete_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a note by id."""
    user_id = update.effective_user.id

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "Usage: <code>/delnote &lt;id&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    note_id = int(context.args[0])
    if db.delete_note(user_id, note_id):
        await update.message.reply_text(f"🗑 Note #{note_id} deleted.")
    else:
        await update.message.reply_text(f"Note #{note_id} not found.")


# ─────────────────────────────────────────────────────────
# Weather
# ─────────────────────────────────────────────────────────

async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get current weather for a city."""
    if not config.WEATHER_API_KEY:
        await update.message.reply_text(
            "Weather service is not configured. "
            "Please set <code>WEATHER_API_KEY</code> in your environment.",
            parse_mode=ParseMode.HTML,
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/weather &lt;city&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    city = " ".join(context.args)
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": config.WEATHER_API_KEY,
        "units": "metric",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError:
        await update.message.reply_text(f"City not found: {html.escape(city)}")
        return
    except httpx.HTTPError as exc:
        logger.exception("Weather request failed")
        await update.message.reply_text(f"Failed to fetch weather: {exc}")
        return

    name = html.escape(data.get("name", city))
    main = data.get("main", {})
    weather_info = (data.get("weather") or [{}])[0]

    temp = main.get("temp", "?")
    feels = main.get("feels_like", "?")
    humidity = main.get("humidity", "?")
    desc = html.escape(weather_info.get("description", "").title())

    text = (
        f"🌤 <b>Weather in {name}</b>\n\n"
        f"<b>Condition:</b> {desc}\n"
        f"<b>Temperature:</b> {temp}°C\n"
        f"<b>Feels like:</b> {feels}°C\n"
        f"<b>Humidity:</b> {humidity}%"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ─────────────────────────────────────────────────────────
# Currency
# ─────────────────────────────────────────────────────────

async def currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Convert between two currencies."""
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: <code>/currency &lt;amount&gt; &lt;from&gt; &lt;to&gt;</code>\n"
            "Example: <code>/currency 100 USD EUR</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Amount must be a number.")
        return

    frm = context.args[1].upper()
    to = context.args[2].upper()

    url = f"https://api.exchangerate-api.com/v4/latest/{frm}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.exception("Currency request failed")
        await update.message.reply_text(f"Failed to fetch rates: {exc}")
        return

    rates = data.get("rates", {})
    rate = rates.get(to)

    if rate is None:
        await update.message.reply_text(f"Unknown currency: {html.escape(to)}")
        return

    converted = amount * rate
    text = (
        f"💱 <b>Currency Conversion</b>\n\n"
        f"<b>{amount:,.2f}</b> {html.escape(frm)} = "
        f"<b>{converted:,.2f}</b> {html.escape(to)}\n\n"
        f"<i>1 {html.escape(frm)} = {rate:.4f} {html.escape(to)}</i>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ─────────────────────────────────────────────────────────
# AI Assistant (optional)
# ─────────────────────────────────────────────────────────

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask the AI assistant a question."""
    if not config.OPENAI_API_KEY:
        await update.message.reply_text(
            "AI service is not configured. "
            "Please set <code>OPENAI_API_KEY</code> in your environment.",
            parse_mode=ParseMode.HTML,
        )
        return

    question = " ".join(context.args).strip() if context.args else ""
    if not question:
        await update.message.reply_text(
            "Usage: <code>/ask &lt;your question&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    await update.message.chat.send_action("typing")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ],
        "max_tokens": 500,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.exception("AI request failed")
        await update.message.reply_text(f"AI service error: {exc}")
        return

    answer = data["choices"][0]["message"]["content"].strip()
    safe = html.escape(answer)
    await update.message.reply_text(safe, parse_mode=ParseMode.HTML)


# ─────────────────────────────────────────────────────────
# Error handler
# ─────────────────────────────────────────────────────────

async def error_handler(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Log errors that occur during update processing."""
    logger.error("Exception while handling update:", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Something went wrong. Please try again."
  )
