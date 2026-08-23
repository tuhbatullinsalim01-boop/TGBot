# -*- coding: utf-8 -*-
"""
Бот «Starson» — зарабатывай звёзды за задания и приглашения.
Вывод через канал WHITE RUSSIA (ручная модерация).
Работает на Railway / Render / любом хостинге.
"""

import os
import sqlite3
import random
import time
import json
from datetime import datetime, timedelta

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== КОНФИГУРАЦИЯ (ТВОИ ДАННЫЕ) ==========
TOKEN = '8671763414:AAExZWe_2ax-CUWnVD1HGOqilkHKAzdJAUA'
CHANNEL_ID = '@crmp_whitee'  # канал для выводов
ADMIN_ID = 5141751465  # твой Telegram ID

bot = telebot.TeleBot(TOKEN)

# ========== БАЗА ДАННЫХ (SQLite) ==========
DB_NAME = 'stars_bot.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    # Пользователи
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0,
            referrer_id INTEGER DEFAULT 0,
            ref_count INTEGER DEFAULT 0,
            daily_bonus_date TEXT,
            tasks_done TEXT DEFAULT '[]'
        )
    ''')
    
    # Заявки на вывод
    cur.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            status TEXT DEFAULT 'pending',
            date TEXT
        )
    ''')
    
    # Задания (админ-панель)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            reward REAL,
            channel_link TEXT,
            type TEXT DEFAULT 'subscribe'
        )
    ''')
    
    conn.commit()
    conn.close()

# ========== РАБОТА С БАЗОЙ ==========
def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cur.fetchone()
    conn.close()
    return user

def create_user(user_id, username='', referrer_id=0):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR IGNORE INTO users (user_id, username, referrer_id)
        VALUES (?, ?, ?)
    ''', (user_id, username, referrer_id))
    
    # Если есть реферер — начисляем бонус
    if referrer_id:
        cur.execute('UPDATE users SET balance = balance + 2 WHERE user_id = ?', (referrer_id,))
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

def get_ref_count(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT ref_count FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else 0

def get_tasks_done(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT tasks_done FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    if result and result[0]:
        return json.loads(result[0])
    return []

def add_task_done(user_id, task_id):
    tasks = get_tasks_done(user_id)
    if task_id not in tasks:
        tasks.append(task_id)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute('UPDATE users SET tasks_done = ? WHERE user_id = ?', (json.dumps(tasks), user_id))
        conn.commit()
        conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT user_id FROM users')
    users = cur.fetchall()
    conn.close()
    return [u[0] for u in users]

def get_leaderboard(limit=10):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT username, ref_count FROM users ORDER BY ref_count DESC LIMIT ?', (limit,))
    result = cur.fetchall()
    conn.close()
    return result

def get_withdrawal_requests():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT id, user_id, amount, date FROM withdrawals WHERE status = "pending" ORDER BY date ASC')
    result = cur.fetchall()
    conn.close()
    return result

def create_withdrawal(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('INSERT INTO withdrawals (user_id, amount, date) VALUES (?, ?, ?)',
                (user_id, amount, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def update_withdrawal_status(w_id, status):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE withdrawals SET status = ? WHERE id = ?', (status, w_id))
    conn.commit()
    conn.close()

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

def get_task_by_id(task_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    result = cur.fetchone()
    conn.close()
    return result

def get_all_tasks():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT * FROM tasks')
    result = cur.fetchall()
    conn.close()
    return result

# ========== КНОПКИ (инлайн) ==========
def main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎁 Задания", callback_data="tasks"),
        InlineKeyboardButton("👥 Рефералы", callback_data="referrals"),
        InlineKeyboardButton("💰 Баланс", callback_data="balance"),
        InlineKeyboardButton("🎰 Игры", callback_data="games"),
        InlineKeyboardButton("📤 Вывод", callback_data="withdraw"),
        InlineKeyboardButton("🏆 Рейтинг", callback_data="rating")
    )
    return markup

def tasks_menu(tasks_done):
    markup = InlineKeyboardMarkup(row_width=1)
    tasks = get_all_tasks()
    for task in tasks:
        task_id, name, desc, reward, channel, _ = task
        if task_id in tasks_done:
            markup.add(InlineKeyboardButton(f"✅ {name} (+{reward}★)", callback_data=f"task_{task_id}"))
        else:
            markup.add(InlineKeyboardButton(f"⬜ {name} (+{reward}★)", callback_data=f"task_{task_id}"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back"))
    return markup

def games_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎰 Слоты", callback_data="slot"),
        InlineKeyboardButton("🃏 Карты", callback_data="cards"),
        InlineKeyboardButton("🎯 Дартс", callback_data="darts"),
        InlineKeyboardButton("🏀 Баскетбол", callback_data="basketball"),
        InlineKeyboardButton("⚽ Футбол", callback_data="football"),
        InlineKeyboardButton("🔙 Назад", callback_data="back")
    )
    return markup

def withdraw_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    amounts = [15, 25, 50, 100, 150, 300, 350, 500, 1000, 5000]
    for amt in amounts:
        markup.add(InlineKeyboardButton(f"{amt}★", callback_data=f"withdraw_{amt}"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back"))
    return markup

def admin_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("📤 Заявки на вывод", callback_data="admin_withdrawals"),
        InlineKeyboardButton("➕ Создать задание", callback_data="admin_add_task"),
        InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
        InlineKeyboardButton("🔙 Назад", callback_data="back")
    )
    return markup

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Пользователь"
    referrer_id = 0
    
    # Проверяем реферальную ссылку
    if len(message.text.split()) > 1:
        try:
            referrer_id = int(message.text.split()[1])
            if referrer_id == user_id:
                referrer_id = 0
        except:
            pass
    
    # Проверяем, есть ли пользователь
    user = get_user(user_id)
    if not user:
        create_user(user_id, username, referrer_id)
        # Бонус за регистрацию
        update_balance(user_id, 2)
    
    bot.send_message(
        user_id,
        f"🌟 Добро пожаловать в Starson, {username}!\n\n"
        f"💰 Твой баланс: {get_balance(user_id)}★\n"
        f"👥 Приглашено друзей: {get_ref_count(user_id)}\n\n"
        f"Выбери действие:",
        reply_markup=main_menu()
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    
    if data == "back":
        bot.edit_message_text(
            "🌟 Выбери действие:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu()
        )
        return
    
    # ===== БАЛАНС =====
    if data == "balance":
        balance = get_balance(user_id)
        refs = get_ref_count(user_id)
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            f"💰 Твой баланс: {balance}★\n"
            f"👥 Приглашено друзей: {refs}\n"
            f"📌 1 друг = +2★ за регистрацию",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu()
        )
        return
    
    # ===== ЗАДАНИЯ =====
    if data == "tasks":
        tasks_done = get_tasks_done(user_id)
        bot.edit_message_text(
            "📋 Список заданий:\n\n"
            "✅ — выполнено\n"
            "⬜ — не выполнено\n\n"
            "Нажми на задание, чтобы проверить.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=tasks_menu(tasks_done)
        )
        return
    
    if data.startswith("task_"):
        task_id = int(data.split("_")[1])
        tasks_done = get_tasks_done(user_id)
        
        if task_id in tasks_done:
            bot.answer_callback_query(call.id, "✅ Ты уже выполнил это задание!")
            return
        
        task = get_task_by_id(task_id)
        if not task:
            bot.answer_callback_query(call.id, "❌ Задание не найдено!")
            return
        
        task_id, name, desc, reward, channel, _ = task
        
        # Проверяем подписку на канал
        try:
            member = bot.get_chat_member(f"@{channel}", user_id)
            if member.status in ['member', 'administrator', 'creator']:
                # Начисляем награду
                update_balance(user_id, reward)
                add_task_done(user_id, task_id)
                bot.answer_callback_query(call.id, f"✅ Задание выполнено! +{reward}★")
                
                tasks_done_updated = get_tasks_done(user_id)
                bot.edit_message_text(
                    "📋 Список заданий:\n\n"
                    "✅ — выполнено\n"
                    "⬜ — не выполнено",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=tasks_menu(tasks_done_updated)
                )
            else:
                bot.answer_callback_query(call.id, "❌ Ты не подписан на канал!")
        except:
            bot.answer_callback_query(call.id, "❌ Ошибка проверки. Попробуй позже.")
        return
    
    # ===== РЕФЕРАЛЫ =====
    if data == "referrals":
        refs = get_ref_count(user_id)
        balance = get_balance(user_id)
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        bot.edit_message_text(
            f"👥 Твои рефералы: {refs}\n\n"
            f"🔗 Твоя реферальная ссылка:\n{ref_link}\n\n"
            f"📌 За каждого друга ты получишь +2★ на баланс!\n"
            f"💰 Твой баланс: {balance}★",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu()
        )
        return
    
    # ===== ИГРЫ =====
    if data == "games":
        bot.edit_message_text(
            "🎰 Выбери игру:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=games_menu()
        )
        return
    
    # ===== СЛОТЫ =====
    if data == "slot":
        bet = 1
        balance = get_balance(user_id)
        if balance < bet:
            bot.answer_callback_query(call.id, "❌ Недостаточно звёзд!")
            return
        
        symbols = ['🍒', '🍋', '🍊', '🍉', '⭐', '💎']
        result = [random.choice(symbols) for _ in range(3)]
        
        if result[0] == result[1] == result[2]:
            win = bet * 5
            update_balance(user_id, win)
            msg = f"🎰 ДЖЕКПОТ! {result[0]}{result[1]}{result[2]}\n💰 Ты выиграл {win}★!"
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            win = bet * 2
            update_balance(user_id, win)
            msg = f"🎰 {result[0]}{result[1]}{result[2]}\n💰 Ты выиграл {win}★!"
        else:
            update_balance(user_id, -bet)
            msg = f"🎰 {result[0]}{result[1]}{result[2]}\n😢 Ты проиграл {bet}★"
        
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=games_menu()
        )
        return
    
    # ===== КАРТЫ =====
    if data == "cards":
        bet = 1
        balance = get_balance(user_id)
        if balance < bet:
            bot.answer_callback_query(call.id, "❌ Недостаточно звёзд!")
            return
        
        cards = ['♠️', '♥️', '♦️', '♣️']
        user_card = random.choice(cards)
        bot_card = random.choice(cards)
        
        if user_card == bot_card:
            win = bet * 3
            update_balance(user_id, win)
            msg = f"🃏 Твоя карта: {user_card}\n🤖 Моя карта: {bot_card}\n🎉 Ничья! Ты выиграл {win}★!"
        else:
            update_balance(user_id, -bet)
            msg = f"🃏 Твоя карта: {user_card}\n🤖 Моя карта: {bot_card}\n😢 Ты проиграл {bet}★"
        
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=games_menu()
        )
        return
    
    # ===== ДАРТС =====
    if data == "darts":
        bet = 1
        balance = get_balance(user_id)
        if balance < bet:
            bot.answer_callback_query(call.id, "❌ Недостаточно звёзд!")
            return
        
        score = random.randint(0, 50)
        if score >= 40:
            win = bet * 3
            update_balance(user_id, win)
            msg = f"🎯 Ты попал в центр! Очки: {score}\n💰 Выигрыш: {win}★"
        elif score >= 25:
            win = bet * 2
            update_balance(user_id, win)
            msg = f"🎯 Хороший бросок! Очки: {score}\n💰 Выигрыш: {win}★"
        else:
            update_balance(user_id, -bet)
            msg = f"🎯 Промах! Очки: {score}\n😢 Ты проиграл {bet}★"
        
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=games_menu()
        )
        return
    
    # ===== БАСКЕТБОЛ =====
    if data == "basketball":
        bet = 1
        balance = get_balance(user_id)
        if balance < bet:
            bot.answer_callback_query(call.id, "❌ Недостаточно звёзд!")
            return
        
        shots = [random.choice(['🏀', '❌']) for _ in range(3)]
        hits = shots.count('🏀')
        
        if hits == 3:
            win = bet * 4
            update_balance(user_id, win)
            msg = f"🏀🏀🏀 ИДЕАЛЬНО! {shots[0]}{shots[1]}{shots[2]}\n💰 Выигрыш: {win}★"
        elif hits == 2:
            win = bet * 2
            update_balance(user_id, win)
            msg = f"🏀🏀❌ {shots[0]}{shots[1]}{shots[2]}\n💰 Выигрыш: {win}★"
        else:
            update_balance(user_id, -bet)
            msg = f"❌❌❌ {shots[0]}{shots[1]}{shots[2]}\n😢 Ты проиграл {bet}★"
        
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=games_menu()
        )
        return
    
    # ===== ФУТБОЛ =====
    if data == "football":
        bet = 1
        balance = get_balance(user_id)
        if balance < bet:
            bot.answer_callback_query(call.id, "❌ Недостаточно звёзд!")
            return
        
        goals = random.randint(0, 5)
        if goals >= 3:
            win = bet * 3
            update_balance(user_id, win)
            msg = f"⚽ Голы: {goals}! Хет-трик!\n💰 Выигрыш: {win}★"
        elif goals >= 1:
            win = bet * 2
            update_balance(user_id, win)
            msg = f"⚽ Голы: {goals}\n💰 Выигрыш: {win}★"
        else:
            update_balance(user_id, -bet)
            msg = f"⚽ Голы: 0\n😢 Ты проиграл {bet}★"
        
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=games_menu()
        )
        return
    
    # ===== ВЫВОД =====
    if data == "withdraw":
        balance = get_balance(user_id)
        bot.edit_message_text(
            f"💸 Вывод звёзд\n\n"
            f"💰 Твой баланс: {balance}★\n"
            f"📤 Минимальная сумма вывода: 15★\n"
            f"📌 Вывод происходит вручную в канал {CHANNEL_ID}\n\n"
            f"Выбери сумму:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=withdraw_menu()
        )
        return
    
    if data.startswith("withdraw_"):
        amount = float(data.split("_")[1])
        balance = get_balance(user_id)
        
        if amount > balance:
            bot.answer_callback_query(call.id, f"❌ Недостаточно звёзд! У тебя {balance}★")
            return
        
        # Создаём заявку
        create_withdrawal(user_id, amount)
        update_balance(user_id, -amount)
        
        # Уведомление в канал
        msg = f"📤 НОВАЯ ЗАЯВКА НА ВЫВОД\n\n"
        msg += f"👤 Пользователь: @{call.from_user.username or 'без юзернейма'}\n"
        msg += f"🆔 ID: {user_id}\n"
        msg += f"💰 Сумма: {amount}★\n"
        msg += f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        msg += f"✅ Для подтверждения нажмите кнопку ниже."
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_withdraw_{user_id}_{amount}")
        )
        
        bot.send_message(CHANNEL_ID, msg, reply_markup=markup)
        
        bot.answer_callback_query(call.id, f"✅ Заявка на {amount}★ отправлена!")
        bot.edit_message_text(
            "🌟 Выбери действие:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu()
        )
        return
    
    # ===== РЕЙТИНГ =====
    if data == "rating":
        leaderboard = get_leaderboard(10)
        text = "🏆 ТОП-10 ПО РЕФЕРАЛАМ\n\n"
        for i, (username, count) in enumerate(leaderboard, 1):
            text += f"{i}. @{username or 'Аноним'} — {count}\n"
        
        # Твоё место
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM users WHERE ref_count > (SELECT ref_count FROM users WHERE user_id = ?)', (user_id,))
        position = cur.fetchone()[0] + 1
        conn.close()
        
        text += f"\n📌 Твоя позиция: {position}"
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu()
        )
        return
    
    # ===== АДМИН-ПАНЕЛЬ =====
    if data == "admin_stats":
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ Доступ запрещён!")
            return
        
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM users')
        users_count = cur.fetchone()[0]
        cur.execute('SELECT SUM(balance) FROM users')
        total_balance = cur.fetchone()[0] or 0
        cur.execute('SELECT COUNT(*) FROM withdrawals WHERE status = "pending"')
        pending_wd = cur.fetchone()[0]
        conn.close()
        
        bot.edit_message_text(
            f"📊 СТАТИСТИКА\n\n"
            f"👥 Пользователей: {users_count}\n"
            f"💰 Всего звёзд: {total_balance}\n"
            f"📤 Заявок на вывод: {pending_wd}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_menu()
        )
        return
    
    if data == "admin_withdrawals":
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ Доступ запрещён!")
            return
        
        withdrawals = get_withdrawal_requests()
        if not withdrawals:
            bot.edit_message_text(
                "📤 Нет активных заявок на вывод.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=admin_menu()
            )
            return
        
        text = "📤 ЗАЯВКИ НА ВЫВОД\n\n"
        for w_id, user_id_w, amount, date in withdrawals:
            text += f"🆔 {user_id_w} — {amount}★ ({date[:16]})\n"
            text += f"   /confirm_{w_id} | /decline_{w_id}\n"
        
        text += "\n📌 Используй команды:\n/confirm_ИД — подтвердить\n/decline_ИД — отклонить"
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_menu()
        )
        return
    
    if data == "admin_add_task":
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ Доступ запрещён!")
            return
        
        bot.send_message(user_id, "📝 Введите данные задания в формате:\n\nНазвание\nОписание\nНаграда (число)\nКанал (без @)")
        bot.register_next_step_handler(call.message, add_task_step)
        return
    
    if data == "admin_broadcast":
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ Доступ запрещён!")
            return
        
        bot.send_message(user_id, "📢 Введите текст для рассылки:")
        bot.register_next_step_handler(call.message, broadcast_step)
        return
    
    if data.startswith("confirm_withdraw_"):
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ Доступ запрещён!")
            return
        
        parts = data.split("_")
        w_user_id = int(parts[2])
        amount = float(parts[3])
        
        # Проверяем, есть ли заявка
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute('SELECT id FROM withdrawals WHERE user_id = ? AND amount = ? AND status = "pending"',
                    (w_user_id, amount))
        w = cur.fetchone()
        conn.close()
        
        if w:
            update_withdrawal_status(w[0], "completed")
            bot.send_message(w_user_id, f"✅ Заявка на вывод {amount}★ подтверждена и выполнена!")
            bot.answer_callback_query(call.id, "✅ Вывод подтверждён!")
        else:
            bot.answer_callback_query(call.id, "❌ Заявка не найдена или уже обработана.")

# ========== АДМИН-КОМАНДЫ ==========
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Доступ запрещён!")
        return
    bot.reply_to(message, "🔧 Админ-панель", reply_markup=admin_menu())

@bot.message_handler(commands=['confirm'])
def confirm_withdrawal(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Используй: /confirm_ИД")
        return
    try:
        w_id = int(parts[0].split("_")[1])
        update_withdrawal_status(w_id, "completed")
        bot.reply_to(message, f"✅ Заявка {w_id} подтверждена!")
    except:
        bot.reply_to(message, "❌ Ошибка!")

@bot.message_handler(commands=['decline'])
def decline_withdrawal(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Используй: /decline_ИД")
        return
    try:
        w_id = int(parts[0].split("_")[1])
        # Возвращаем деньги пользователю
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute('SELECT user_id, amount FROM withdrawals WHERE id = ?', (w_id,))
        result = cur.fetchone()
        if result:
            cur.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (result[1], result[0]))
        cur.execute('UPDATE withdrawals SET status = "declined" WHERE id = ?', (w_id,))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"❌ Заявка {w_id} отклонена, деньги возвращены!")
    except:
        bot.reply_to(message, "❌ Ошибка!")

def add_task_step(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return
    lines = message.text.split('\n')
    if len(lines) < 4:
        bot.reply_to(message, "❌ Нужно 4 строки: название, описание, награда, канал")
        return
    
    name = lines[0].strip()
    desc = lines[1].strip()
    try:
        reward = float(lines[2].strip())
    except:
        reward = 1
    channel = lines[3].strip().replace('@', '')
    
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('INSERT INTO tasks (name, description, reward, channel) VALUES (?, ?, ?, ?)',
                (name, desc, reward, channel))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ Задание «{name}» создано!\nНаграда: {reward}★\nКанал: @{channel}")

def broadcast_step(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return
    text = message.text
    users = get_all_users()
    sent = 0
    for uid in users:
        try:
            bot.send_message(uid, f"📢 РАССЫЛКА STArSON\n\n{text}")
            sent += 1
        except:
            pass
    bot.reply_to(message, f"✅ Рассылка отправлена {sent} пользователям.")

# ========== ДОПОЛНИТЕЛЬНАЯ КОМАНДА ==========
@bot.message_handler(commands=['daily'])
def daily_bonus(message):
    user_id = message.from_user.id
    today = datetime.now().date().isoformat()
    last_bonus = get_daily_bonus_date(user_id)
    
    if last_bonus == today:
        bot.reply_to(message, "❌ Ты уже получил ежедневный бонус сегодня!")
        return
    
    bonus = random.uniform(0.5, 2.0)
    bonus = round(bonus, 2)
    update_balance(user_id, bonus)
    set_daily_bonus_date(user_id, today)
    bot.reply_to(message, f"🎁 Ежедневный бонус: +{bonus}★\n💰 Твой баланс: {get_balance(user_id)}★")

# ========== ЗАПУСК БОТА ==========
if __name__ == '__main__':
    print("🚀 Бот «Starson» запущен!")
    init_db()
    bot.infinity_polling()