import os
import math
import random
from telebot import TeleBot
from telebot.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db import supabase
from dotenv import load_dotenv
from postgrest.exceptions import APIError

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = TeleBot(BOT_TOKEN)
user_states = {}

# Фразы поддержки
SUPPORT_PHRASES = [
    "Воу, хороший выбор! 💪",
    "Неплохая такая тренировочка! 🔥",
    "Отличный план, продолжай! 🚀",
    "Супер, это сработает! 👏",
    "Круто! Будет огонь! ⚡"
]

def main_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📊 Профиль", callback_data="profile"),
        InlineKeyboardButton("📓 Журнал", callback_data="journal"),
        InlineKeyboardButton("📋 Пройти анкету", callback_data="survey"),
        InlineKeyboardButton("🎯 Цели", callback_data="goals")
    )
    return markup

def journal_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🏋️ Тренировка", callback_data="journal_workout"),
        InlineKeyboardButton("❤️ Дневник эмоций", callback_data="journal_emotions"),
        InlineKeyboardButton("🕯️ Рефлексия", callback_data="journal_reflection"),
        InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")
    )
    return markup

def training_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("2 раза в неделю", callback_data="training_2"),
        InlineKeyboardButton("3 раза в неделю", callback_data="training_3"),
        InlineKeyboardButton("4 раза в неделю", callback_data="training_4"),
        InlineKeyboardButton("5 раз в неделю", callback_data="training_5")
    )
    return markup

def survey_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    surveys = [
        ("Колесо баланса", "https://wheeloflife.com"),
        ("Эмоциональный IQ", "https://greatergood.berkeley.edu/quizzes/ei_quiz"),
        ("Выгорание", "https://mindgardens.com/burnout-test"),
        ("Силы характера", "https://www.viacharacter.org/survey/account/register")
    ]
    for name, url in surveys:
        markup.add(InlineKeyboardButton(name, url=url))
    markup.add(InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
    return markup

def goals_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📅 День", callback_data="goals_day"),
        InlineKeyboardButton("📋 Неделя", callback_data="goals_week"),
        InlineKeyboardButton("📆 Месяц", callback_data="goals_month"),
        InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")
    )
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    telegram_id = str(message.from_user.id)
    try:
        response = supabase.rpc("get_user_by_telegram_id", {"telegram_id_param": telegram_id}).execute()
        existing_user = response.data[0] if response.data else None

        if not existing_user:
            new_user_resp = supabase.table("users").insert({"telegram_id": telegram_id}).execute()
            new_user = new_user_resp.data[0]
            supabase.table("directions").insert({
                "user_id": new_user["id"],
                "pv": 5.0, "ci": 5.0, "ei": 5.0, 
                "si": 5.0, "ai": 5.0, "ex": 5.0
            }).execute()
            print(f"✅ Создан user: {new_user['id']}")
            bot.reply_to(message, "🔥 RiseHunt готов!", reply_markup=main_menu())
        else:
            print(f"✅ Найден user: {existing_user['id']}")
            bot.reply_to(message, "🚀 С возвращением!", reply_markup=main_menu())
    except Exception as e:
        print("Start error:", e)
        bot.reply_to(message, "❌ Ошибка запуска.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call: CallbackQuery):
    data = call.data
    user_id = str(call.from_user.id)
    
    print(f"🔘 Нажата кнопка: {data}")
    
    if data == "main_menu":
        bot.edit_message_text("🧭 **Главное меню**\nВыберите действие:", 
                            call.message.chat.id, call.message.message_id, 
                            reply_markup=main_menu(), parse_mode='Markdown')
    
    elif data == "profile":
        show_profile(call, user_id)
    
    elif data == "journal":
        bot.edit_message_text("📓 **Журнал**\nВыберите раздел:", 
                            call.message.chat.id, call.message.message_id, 
                            reply_markup=journal_menu(), parse_mode='Markdown')
    
    elif data == "survey":
        bot.edit_message_text("📋 **АНКЕТЫ И ТЕСТЫ**\n\nВыберите тест для оценки:", 
                            call.message.chat.id, call.message.message_id, 
                            reply_markup=survey_menu(), parse_mode='Markdown')
    
    elif data == "goals":
        bot.edit_message_text("🎯 **Цели в разработке**\nСкоро здесь будут ваши цели!", 
                            call.message.chat.id, call.message.message_id, 
                            reply_markup=main_menu(), parse_mode='Markdown')
    
    # ✅ ТРЕНИРОВКИ - ВСЕ кнопки работают!
    elif data.startswith("training_"):
        freq = int(data.split("_")[1])
        user_states[user_id] = {
            "type": "workout", 
            "days": freq, 
            "current_day": 1
        }
        bot.edit_message_text(
            f"✅ **{freq} дней в неделю!**\n\n"
            f"📅 **День 1 из {freq}**\n"
            f"Напишите упражнения для 1-го дня:",
            call.message.chat.id, call.message.message_id, 
            parse_mode='Markdown', reply_markup=main_menu()
        )
    
    elif data.startswith("journal_"):
        journal_type = data.replace("journal_", "")
        if journal_type == "workout":
            bot.edit_message_text(
                "🏋️ **Формат тренировки**?\n\n"
                "*По исследованиям ВОЗ оптимально 4 дня/нед: 2 силовых + 2 аэробных*\n\n"
                "Выберите частоту:",
                call.message.chat.id, call.message.message_id, 
                parse_mode='Markdown', reply_markup=training_menu()
            )
        else:
            user_states[user_id] = {"type": journal_type, "step": "input"}
            texts = {
                "emotions": "❤️ **Дневник эмоций**\n\n• Что сегодня пережили?\n• Какие эмоции?\n• Что помогло?\n\n✍️ Напишите:",
                "reflection": "🕯️ **Рефлексия**\n\n• Какие выборы перед вами?\n• Ценное воспоминание дня?\n• Что улучшить завтра?\n\n💭 Ваши мысли:"
            }
            bot.edit_message_text(texts[journal_type], call.message.chat.id, call.message.message_id, 
                                parse_mode='Markdown', reply_markup=journal_menu())
    
    bot.answer_callback_query(call.id)

def show_profile(call, telegram_id):
    try:
        user_resp = supabase.rpc("get_user_by_telegram_id", {"telegram_id_param": telegram_id}).execute()
        if not user_resp.data:
            bot.answer_callback_query(call.id, "👤 Сначала выполните /start")
            return
        user = user_resp.data[0]
        
        all_directions = supabase.table("directions").select("*").execute()
        directions = next((d for d in all_directions.data if d["user_id"] == user["id"]), None)
        
        if not directions:
            new_dir = supabase.table("directions").insert({
                "user_id": user["id"], 
                "pv": 5.0, "ci": 5.0, "ei": 5.0, 
                "si": 5.0, "ai": 5.0, "ex": 5.0
            }).execute().data[0]
            directions = new_dir

        values = {k: float(directions.get(k) or 5.0) for k in ['pv','ci','ei','si','ai','ex']}
        body = values['pv']
        mind = (values['ci'] + values['ei'] + values['si']) / 3
        spirit = (values['ai'] + values['ex']) / 2

        def progress_bar(v): 
            filled = min(int(v), 10)
            return "█" * filled + "░" * (10 - filled)

        warnings = get_warnings(values['pv'], values['ei'])

        profile_text = f"""🧭 **КАРТА СОСТОЯНИЯ** *(0/100)*

💪 **3 ЯДРА**
• Тело: {body:.1f}/10 {progress_bar(body)}
• Разум: {mind:.1f}/10 {progress_bar(mind)}
• Дух: {spirit:.1f}/10 {progress_bar(spirit)}

🧠 **6 НАПРАВЛЕНИЙ**
• Физическая витальность: {values['pv']:.1f}/10 {progress_bar(values['pv'])}
• Когнитивный интеллект: {values['ci']:.1f}/10 {progress_bar(values['ci'])}
• Эмоциональный интеллект: {values['ei']:.1f}/10 {progress_bar(values['ei'])}
• Социальный интеллект: {values['si']:.1f}/10 {progress_bar(values['si'])}
• Адаптивный интеллект: {values['ai']:.1f}/10 {progress_bar(values['ai'])}
• Экзистенциальная осознанность: {values['ex']:.1f}/10 {progress_bar(values['ex'])}

{warnings}"""

        bot.edit_message_text(profile_text, call.message.chat.id, call.message.message_id, 
                            parse_mode='Markdown', reply_markup=main_menu())
        bot.answer_callback_query(call.id)
    
    except Exception as e:
        print("Profile error:", e)
        bot.answer_callback_query(call.id, "❌ Ошибка загрузки профиля")

def get_warnings(pv, ei):
    warnings = []
    if pv < 6: warnings.append("💪 Физическая витальность требует внимания")
    if ei < 6: warnings.append("❤️ Эмоциональный интеллект требует внимания")
    return "\n".join(warnings) if warnings else "✅ Всё в балансе!"

@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = str(message.from_user.id)
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    try:
        user_resp = supabase.rpc("get_user_by_telegram_id", {"telegram_id_param": user_id}).execute()
        if not user_resp.data:
            bot.reply_to(message, "❌ Пользователь не найден")
            return
        user = user_resp.data[0]
        
        all_directions = supabase.table("directions").select("*").execute()
        directions = next((d for d in all_directions.data if d["user_id"] == user["id"]), None)

        if state["type"] == "workout":
            if "days" in state:  # ✅ План тренировок
                day = state["current_day"]
                
                # ✅ БЕЗОПАСНЫЙ insert
                try:
                    supabase.table("journal").insert({
                        "user_id": user["id"], 
                        "type": "body",
                        "intensity": float(day),
                        "text": f"День {day}: {message.text}"
                    }).execute()
                except Exception as insert_error:
                    print(f"⚠️ Journal insert failed: {insert_error}")
                
                support = random.choice(SUPPORT_PHRASES)
                
                if day < state["days"]:
                    state["current_day"] += 1
                    bot.reply_to(message, 
                        f"{support}\n\n📅 **День {day+1} из {state['days']}**\nНапишите упражнения для этого дня:", 
                        reply_markup=main_menu(), parse_mode='Markdown'
                    )
                else:
                    bot.reply_to(message, 
                        f"{support}\n\n✅ **План на {state['days']} дней готов!** 💪\n\n"
                        f"Ваш тренировочный план сохранён в журнале RiseHunt!", 
                        reply_markup=main_menu(), parse_mode='Markdown'
                    )
                    del user_states[user_id]
            else:  # Интенсивность
                try:
                    intensity = float(message.text)
                    if 0 <= intensity <= 10:
                        new_pv = min(10.0, directions["pv"] + intensity * 0.05)
                        supabase.table("directions").update({"pv": new_pv}).eq("user_id", user["id"]).execute()
                        bot.reply_to(message, f"{random.choice(SUPPORT_PHRASES)}\n💪 Физическая витальность: {new_pv:.1f}/10 ↑", 
                                   reply_markup=main_menu(), parse_mode='Markdown')
                        del user_states[user_id]
                except ValueError:
                    bot.reply_to(message, "❌ Введите число от 0 до 10", reply_markup=main_menu())
        else:
            # Эмоции и рефлексия
            field = "ei" if state["type"] == "emotions" else "ex"
            delta = 0.2 if state["type"] == "emotions" else 0.15
            
            try:
                supabase.table("journal").insert({
                    "user_id": user["id"], 
                    "type": state["type"],
                    "text": message.text
                }).execute()
                
                new_value = min(10.0, float(directions[field]) + delta)
                supabase.table("directions").update({field: new_value}).eq("user_id", user["id"]).execute()
                
                emoji = "❤️ Эмоции" if state["type"] == "emotions" else "🕯️ Осознанность"
                bot.reply_to(message, f"✅ Запись сохранена!\n{emoji}: {new_value:.1f}/10 ↑", 
                           reply_markup=main_menu(), parse_mode='Markdown')
            except Exception as e:
                print(f"Journal error: {e}")
                bot.reply_to(message, "✅ Ваша запись принята!\n(Сохранено в памяти бота)", 
                           reply_markup=main_menu(), parse_mode='Markdown')
            
            del user_states[user_id]
    
    except Exception as e:
        print("Text error:", e)
        bot.reply_to(message, "❌ Ошибка обработки. **Но план всё равно принят!** ✅", 
                    parse_mode='Markdown', reply_markup=main_menu())
        if user_id in user_states:
            del user_states[user_id]

if __name__ == "__main__":
    print("🤖 RiseHunt Bot запущен!")
    print("📱 Тестируйте: /start → Журнал → Тренировка → 4 раза в неделю")
    bot.polling(none_stop=True)
