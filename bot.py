# -*- coding: utf-8 -*-
"""
ChatGPT-бот на KeylessAI (бесплатно, без API-ключа)
С контекстом, настройками и памятью в SQLite
"""

import os
import sqlite3
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

from openai import OpenAI

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_TOKEN = "8602006844:AAEFpU-2yWR0SQJiC5IUvU3lBScm6hENPVw"
ADMIN_ID = 17194921

# KeylessAI — НЕ НУЖЕН API-КЛЮЧ!
client = OpenAI(
    api_key="not-needed",  # можно вообще ничего не писать
    base_url="https://keylessai.thryx.workers.dev/v1"
)

# ========== БАЗА ДАННЫХ ==========
DB_NAME = "chat_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            model TEXT DEFAULT 'gpt-4o-mini',
            system_prompt TEXT DEFAULT 'Ты полезный и вежливый ассистент.'
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ База данных готова")

# ========== РАБОТА С БАЗОЙ ==========
def get_user_settings(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT model, system_prompt FROM user_settings WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    if result:
        return {"model": result[0], "system_prompt": result[1]}
    return {"model": "gpt-4o-mini", "system_prompt": "Ты полезный и вежливый ассистент."}

def save_user_settings(user_id, model=None, system_prompt=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    current = get_user_settings(user_id)
    new_model = model if model else current["model"]
    new_prompt = system_prompt if system_prompt else current["system_prompt"]
    cur.execute('''
        INSERT OR REPLACE INTO user_settings (user_id, model, system_prompt)
        VALUES (?, ?, ?)
    ''', (user_id, new_model, new_prompt))
    conn.commit()
    conn.close()

def get_chat_history(user_id, limit=10):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT role, content FROM chat_history
        WHERE user_id = ?
        ORDER BY timestamp DESC LIMIT ?
    ''', (user_id, limit * 2))
    rows = cur.fetchall()
    conn.close()
    messages = []
    for role, content in reversed(rows):
        messages.append({"role": role, "content": content})
    return messages

def save_message(user_id, role, content):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO chat_history (user_id, role, content)
        VALUES (?, ?, ?)
    ''', (user_id, role, content))
    conn.commit()
    conn.close()

def clear_history(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM chat_history WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT user_id FROM chat_history')
    users = cur.fetchall()
    conn.close()
    return [u[0] for u in users]

# ========== КОМАНДЫ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🧠 Привет, {user.first_name}!\n\n"
        f"Я — ИИ-помощник на KeylessAI (бесплатно, без API-ключа).\n"
        f"Я запоминаю историю диалога и могу продолжать разговор.\n\n"
        f"📌 Команды:\n"
        f"/start — показать это меню\n"
        f"/clear — очистить историю\n"
        f"/settings — настройки модели\n"
        f"/stats — статистика диалога\n\n"
        f"Просто напиши мне что-нибудь!"
    )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clear_history(user_id)
    await update.message.reply_text("🗑️ История диалога очищена!")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    history = get_chat_history(user_id, limit=100)
    msg_count = len(history)
    settings = get_user_settings(user_id)
    await update.message.reply_text(
        f"📊 Статистика:\n\n"
        f"👤 Пользователь: {update.effective_user.first_name}\n"
        f"💬 Сообщений в истории: {msg_count}\n"
        f"🧠 Модель: {settings['model']}\n"
        f"📝 Системный промпт: {settings['system_prompt'][:50]}..."
    )

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧠 Сменить модель", callback_data="change_model")],
        [InlineKeyboardButton("✍️ Изменить системный промпт", callback_data="change_prompt")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⚙️ Настройки:", reply_markup=reply_markup)

# ========== ОБРАБОТЧИК СООБЩЕНИЙ ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    if context.user_data.get('awaiting_prompt'):
        new_prompt = user_message
        save_user_settings(user_id, system_prompt=new_prompt)
        context.user_data['awaiting_prompt'] = False
        await update.message.reply_text(f"✅ Системный промпт обновлён!\n\n«{new_prompt}»")
        return

    save_message(user_id, "user", user_message)

    settings = get_user_settings(user_id)
    system_prompt = settings["system_prompt"]
    model = settings["model"]

    history = get_chat_history(user_id, limit=10)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append(msg)
    if not messages or messages[-1]["role"] != "user":
        messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2000
        )
        reply = response.choices[0].message.content

        save_message(user_id, "assistant", reply)

        if len(reply) > 4000:
            for i in range(0, len(reply), 4000):
                await update.message.reply_text(reply[i:i+4000])
        else:
            await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# ========== КНОПКИ ==========
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "change_model":
        keyboard = [
            [InlineKeyboardButton("gpt-4o-mini (быстрый)", callback_data="model_gpt-4o-mini")],
            [InlineKeyboardButton("gpt-4o (умный)", callback_data="model_gpt-4o")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🧠 Выбери модель:", reply_markup=reply_markup)

    elif data.startswith("model_"):
        model = data.replace("model_", "")
        save_user_settings(user_id, model=model)
        await query.edit_message_text(f"✅ Модель изменена на: {model}")

    elif data == "change_prompt":
        await query.edit_message_text(
            "✍️ Введите новый системный промпт:\n\n"
            "Например: «Ты — эксперт по Python».\n\n"
            "Пришли текст в следующем сообщении."
        )
        context.user_data['awaiting_prompt'] = True

    elif data == "back_to_settings":
        keyboard = [
            [InlineKeyboardButton("🧠 Сменить модель", callback_data="change_model")],
            [InlineKeyboardButton("✍️ Изменить системный промпт", callback_data="change_prompt")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("⚙️ Настройки:", reply_markup=reply_markup)

    elif data == "back_to_menu":
        await start(update, context)

# ========== ЗАПУСК ==========
def main():
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("stats", stats_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🚀 KeylessAI-бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()