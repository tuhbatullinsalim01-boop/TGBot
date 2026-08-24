# -*- coding: utf-8 -*-
"""
Flow FC — Telegram Mini App
"""

import os
import sqlite3
import json
import random
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== КОНФИГУРАЦИЯ ==========
TOKEN = "8801818795:AAHBFCheS8Yvk0-uge_Km5GOQTqp28s1SxU"  # Твой токен

# ========== БАЗА ДАННЫХ ==========
DB_NAME = "flow_fc.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 100,
            cards TEXT DEFAULT '[]',
            packs_opened INTEGER DEFAULT 0,
            daily_bonus_date TEXT,
            ref_count INTEGER DEFAULT 0,
            referrer_id INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cur.fetchone()
    conn.close()
    return user

def create_user(user_id, username, referrer_id=0):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR IGNORE INTO users (user_id, username, referrer_id)
        VALUES (?, ?, ?)
    ''', (user_id, username, referrer_id))
    if referrer_id:
        cur.execute('UPDATE users SET balance = balance + 400 WHERE user_id = ?', (referrer_id,))
        cur.execute('UPDATE users SET ref_count = ref_count + 1 WHERE user_id = ?', (referrer_id,))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else 0

def get_cards(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT cards FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    if result and result[0]:
        return json.loads(result[0])
    return []

def add_card(user_id, card):
    cards = get_cards(user_id)
    cards.append(card)
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE users SET cards = ? WHERE user_id = ?', (json.dumps(cards), user_id))
    cur.execute('UPDATE users SET packs_opened = packs_opened + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_ref_count(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT ref_count FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else 0

def get_daily_bonus_date(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT daily_bonus_date FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None

def set_daily_bonus_date(user_id, date_str):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE users SET daily_bonus_date = ? WHERE user_id = ?', (date_str, user_id))
    conn.commit()
    conn.close()

# ========== КОМАНДЫ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Игрок"
    referrer_id = 0
    
    if len(update.message.text.split()) > 1:
        try:
            referrer_id = int(update.message.text.split()[1])
        except:
            pass
    
    if not get_user(user_id):
        create_user(user_id, username, referrer_id)
    
    # ===== КНОПКА С MINI APP =====
    keyboard = [
        [InlineKeyboardButton("🚀 Открыть Flow FC", web_app=WebAppInfo(url="https://tgbot-zkm6.onrender.com"))],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚽ Добро пожаловать в Flow FC, {username}!\n\n"
        f"💰 Баланс: {get_balance(user_id)} монет\n"
        f"🃏 Карточек: {len(get_cards(user_id))}\n"
        f"👥 Приглашено: {get_ref_count(user_id)}\n\n"
        f"Нажми кнопку ниже, чтобы открыть игру:",
        reply_markup=reply_markup
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if data == "profile":
        balance = get_balance(user_id)
        cards = get_cards(user_id)
        refs = get_ref_count(user_id)
        unique = len(set(c["name"] for c in cards))
        
        text = f"👤 Твой профиль\n\n"
        text += f"💰 Баланс: {balance} монет\n"
        text += f"🃏 Карточек: {len(cards)}\n"
        text += f"⭐ Уникальных: {unique}\n"
        text += f"👥 Приглашено: {refs}\n"
        text += f"📦 Паков открыто: {len(cards)}\n\n"
        text += f"🔗 Реферальная ссылка:\n"
        text += f"https://t.me/{context.bot.username}?start={user_id}"
        
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ])
        await query.edit_message_text(text, reply_markup=markup)
        return
    
    if data == "back":
        keyboard = [
            [InlineKeyboardButton("🚀 Открыть Flow FC", web_app=WebAppInfo(url="https://tgbot-zkm6.onrender.com"))],
            [InlineKeyboardButton("👤 Профиль", callback_data="profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚽ Главное меню:",
            reply_markup=reply_markup
        )
        return

# ========== ЗАПУСК ==========
def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    print("🚀 Flow FC запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
