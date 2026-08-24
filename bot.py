# -*- coding: utf-8 -*-
"""
Flow FC — коллекционная карточная игра в Telegram
"""

import os
import sqlite3
import json
import random
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== КОНФИГУРАЦИЯ ==========
TOKEN = "8801818795:AAHBFCheS8Yvk0-uge_Km5GOQTqp28s1SxU"
ADMIN_ID = 17194921  # твой Telegram ID

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

# ========== КАРТЫ ==========
CARDS = [
    {"name": "Килиан Мбаппе", "club": "Реал Мадрид", "ovr": 95, "rarity": "legendary"},
    {"name": "Виктор Дьокереш", "club": "Арсенал", "ovr": 89, "rarity": "epic"},
    {"name": "Эрлинг Холанд", "club": "Ман Сити", "ovr": 93, "rarity": "legendary"},
    {"name": "Антонио Рюдигер", "club": "Реал Мадрид", "ovr": 85, "rarity": "rare"},
    {"name": "Кэнто Шиога", "club": "Вольфсбург", "ovr": 83, "rarity": "rare"},
    {"name": "Артём Дзюба", "club": "Локомотив", "ovr": 78, "rarity": "common"},
    {"name": "Криштиану Роналду", "club": "Аль-Наср", "ovr": 92, "rarity": "legendary"},
    {"name": "Лионель Месси", "club": "Интер Майами", "ovr": 91, "rarity": "legendary"},
    {"name": "Джуд Беллингем", "club": "Реал Мадрид", "ovr": 88, "rarity": "epic"},
    {"name": "Ламин Ямаль", "club": "Барселона", "ovr": 85, "rarity": "epic"},
    {"name": "Букайо Сака", "club": "Арсенал", "ovr": 87, "rarity": "epic"},
    {"name": "Мартин Эдегор", "club": "Арсенал", "ovr": 84, "rarity": "rare"},
    {"name": "Родри", "club": "Ман Сити", "ovr": 86, "rarity": "epic"},
    {"name": "Федерико Вальверде", "club": "Реал Мадрид", "ovr": 85, "rarity": "epic"},
    {"name": "Винисиус Жуниор", "club": "Реал Мадрид", "ovr": 90, "rarity": "legendary"},
]

PACKS = {
    "basic": {"price": 120, "currency": "coins", "chances": {"common": 70, "rare": 27, "epic": 3, "legendary": 0}},
    "all_or_nothing": {"price": 150, "currency": "coins", "chances": {"common": 98, "rare": 0, "epic": 0, "legendary": 2}},
    "premium": {"price": 300, "currency": "coins", "chances": {"common": 50, "rare": 44, "epic": 5, "legendary": 1}},
    "elite": {"price": 600, "currency": "coins", "chances": {"common": 30, "rare": 59, "epic": 9, "legendary": 2}},
    "legendary": {"price": 1100, "currency": "coins", "chances": {"common": 0, "rare": 56, "epic": 39, "legendary": 5}},
}

# ========== РАБОТА С БАЗОЙ ==========
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

def get_leaderboard(limit=10):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT username, balance FROM users ORDER BY balance DESC LIMIT ?', (limit,))
    return cur.fetchall()

# ========== КНОПКИ ==========
def main_menu():
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Играть", callback_data="games")],
        [InlineKeyboardButton("📦 Паки", callback_data="packs")],
        [InlineKeyboardButton("🃏 Карточки", callback_data="cards")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")]
    ])
    return markup

def games_menu():
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽ Пенальти", callback_data="game_penalty")],
        [InlineKeyboardButton("🧠 Тактико", callback_data="game_tactics")],
        [InlineKeyboardButton("🧩 Memory", callback_data="game_memory")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ])
    return markup

def packs_menu():
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Basic Pack (120)", callback_data="pack_basic")],
        [InlineKeyboardButton("🎲 Все или ничего (150)", callback_data="pack_all_or_nothing")],
        [InlineKeyboardButton("✨ Premium Pack (300)", callback_data="pack_premium")],
        [InlineKeyboardButton("⭐ Elite Pack (600)", callback_data="pack_elite")],
        [InlineKeyboardButton("🏆 Легендарный (1100)", callback_data="pack_legendary")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ])
    return markup

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
    
    await update.message.reply_text(
        f"⚽ Добро пожаловать в Flow FC, {username}!\n\n"
        f"💰 Баланс: {get_balance(user_id)} монет\n"
        f"🃏 Карточек: {len(get_cards(user_id))}\n"
        f"👥 Приглашено: {get_ref_count(user_id)}\n\n"
        f"Выбери действие:",
        reply_markup=main_menu()
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if data == "back":
        await query.edit_message_text(
            "⚽ Главное меню:",
            reply_markup=main_menu()
        )
        return
    
    # ===== ИГРЫ =====
    if data == "games":
        await query.edit_message_text(
            "🎮 Выбери мини-игру:",
            reply_markup=games_menu()
        )
        return
    
    if data == "game_penalty":
        if get_balance(user_id) < 10:
            await query.edit_message_text("❌ Недостаточно монет! Нужно 10 для игры.", reply_markup=games_menu())
            return
        update_balance(user_id, -10)
        score = random.randint(0, 5)
        if score >= 3:
            win = random.randint(10, 30)
            update_balance(user_id, win)
            await query.edit_message_text(f"⚽ Пенальти! Ты забил {score} из 5! +{win} монет!", reply_markup=games_menu())
        else:
            await query.edit_message_text(f"⚽ Пенальти! Ты забил {score} из 5. Попробуй ещё!", reply_markup=games_menu())
        return
    
    if data == "game_tactics":
        if get_balance(user_id) < 10:
            await query.edit_message_text("❌ Недостаточно монет!", reply_markup=games_menu())
            return
        update_balance(user_id, -10)
        tactics = ["Атака", "Оборона", "Контратака"]
        bot_choice = random.choice(tactics)
        user_choice = random.choice(tactics)
        if user_choice == bot_choice:
            win = random.randint(10, 25)
            update_balance(user_id, win)
            await query.edit_message_text(f"🧠 Тактико! Ты выбрал {user_choice}, бот выбрал {bot_choice}. Ничья! +{win} монет!", reply_markup=games_menu())
        else:
            await query.edit_message_text(f"🧠 Тактико! Ты выбрал {user_choice}, бот выбрал {bot_choice}. Попробуй ещё!", reply_markup=games_menu())
        return
    
    if data == "game_memory":
        if get_balance(user_id) < 5:
            await query.edit_message_text("❌ Недостаточно монет!", reply_markup=games_menu())
            return
        update_balance(user_id, -5)
        seq = "".join([random.choice(["0","1"]) for _ in range(5)])
        win = random.randint(5, 15)
        update_balance(user_id, win)
        await query.edit_message_text(f"🧩 Memory! Запомни: {seq}... готово? +{win} монет!", reply_markup=games_menu())
        return
    
    # ===== ПАКИ =====
    if data == "packs":
        await query.edit_message_text(
            "📦 Доступные паки:",
            reply_markup=packs_menu()
        )
        return
    
    if data.startswith("pack_"):
        pack_name = data.replace("pack_", "")
        pack = PACKS.get(pack_name)
        if not pack:
            await query.edit_message_text("❌ Пак не найден!", reply_markup=packs_menu())
            return
        
        balance = get_balance(user_id)
        if balance < pack["price"]:
            await query.edit_message_text(
                f"❌ Недостаточно монет! Нужно {pack['price']}, у тебя {balance}.",
                reply_markup=packs_menu()
            )
            return
        
        update_balance(user_id, -pack["price"])
        
        # Открываем пак
        roll = random.randint(0, 100)
        rarity = "common"
        for r, chance in pack["chances"].items():
            if roll < chance:
                rarity = r
                break
            roll -= chance
        
        # Выбираем карту
        possible_cards = [c for c in CARDS if c["rarity"] == rarity]
        if not possible_cards:
            possible_cards = [c for c in CARDS if c["rarity"] == "common"]
        card = random.choice(possible_cards)
        add_card(user_id, card)
        
        await query.edit_message_text(
            f"🎉 Ты открыл пак {pack_name}!\n\n"
            f"🃏 {card['name']} ({card['club']})\n"
            f"⭐ OVR: {card['ovr']}\n"
            f"💎 Редкость: {rarity.upper()}\n\n"
            f"💰 Баланс: {get_balance(user_id)} монет",
            reply_markup=packs_menu()
        )
        return
    
    # ===== КАРТОЧКИ =====
    if data == "cards":
        cards = get_cards(user_id)
        if not cards:
            await query.edit_message_text("🃏 У тебя пока нет карточек. Открой паки!", reply_markup=main_menu())
            return
        text = f"🃏 Твои карточки ({len(cards)}):\n\n"
        for i, c in enumerate(cards[:10], 1):
            text += f"{i}. {c['name']} ({c['club']}) — OVR {c['ovr']} [{c['rarity']}]\n"
        if len(cards) > 10:
            text += f"\n...и ещё {len(cards)-10} карточек"
        await query.edit_message_text(text, reply_markup=main_menu())
        return
    
    # ===== ПРОФИЛЬ =====
    if data == "profile":
        balance = get_balance(user_id)
        cards = get_cards(user_id)
        refs = get_ref_count(user_id)
        unique = len(set(c["name"] for c in cards))
        
        # Ежедневная награда
        today = datetime.now().date().isoformat()
        last_bonus = get_daily_bonus_date(user_id)
        bonus_text = "✅ Забрать ежедневную награду (+50 монет)" if last_bonus != today else "⏳ Уже получено сегодня"
        
        text = f"👤 Твой профиль\n\n"
        text += f"💰 Баланс: {balance} монет\n"
        text += f"🃏 Карточек: {len(cards)}\n"
        text += f"⭐ Уникальных: {unique}\n"
        text += f"👥 Приглашено: {refs}\n"
        text += f"📦 Паков открыто: {len(cards)}\n\n"
        text += f"🎁 {bonus_text}\n\n"
        text += f"🔗 Реферальная ссылка:\n"
        text += f"https://t.me/{context.bot.username}?start={user_id}"
        
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Забрать бонус", callback_data="daily_bonus")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ])
        await query.edit_message_text(text, reply_markup=markup)
        return
    
    # ===== ЕЖЕДНЕВНЫЙ БОНУС =====
    if data == "daily_bonus":
        today = datetime.now().date().isoformat()
        last_bonus = get_daily_bonus_date(user_id)
        if last_bonus == today:
            await query.edit_message_text("❌ Ты уже получил бонус сегодня!", reply_markup=main_menu())
            return
        update_balance(user_id, 50)
        set_daily_bonus_date(user_id, today)
        await query.edit_message_text(
            f"🎁 Ты получил 50 монет!\n\n"
            f"💰 Новый баланс: {get_balance(user_id)} монет",
            reply_markup=main_menu()
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