from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("📊 Профиль", callback_data="profile"),
               InlineKeyboardButton("📓 Журнал", callback_data="journal"),
               InlineKeyboardButton("📋 Пройти анкету", callback_data="survey"),
               InlineKeyboardButton("🎯 Цели", callback_data="goals"))
    return markup

def journal_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🏋️ Тренировка", callback_data="journal_workout"),
               InlineKeyboardButton("❤️ Дневник эмоций", callback_data="journal_emotions"),
               InlineKeyboardButton("🕯️ Рефлексия", callback_data="journal_reflection"),
               InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
    return markup

def training_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("2 раза в неделю", callback_data="training_2"),
               InlineKeyboardButton("3 раза в неделю", callback_data="training_3"),
               InlineKeyboardButton("4 раза в неделю", callback_data="training_4"),
               InlineKeyboardButton("5 раз в неделю", callback_data="training_5"))
    return markup

def survey_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    surveys = [
        ("Колесо баланса", "https://wheeloflife.com"),
        ("Эмоциональный IQ", "https://greatergood.berkeley.edu/quizzes/ei_quiz"),
        ("Выгорание", "https://mindgardens.com/burnout-test"),
        ("Силы характера", "https://www.viacharacter.org/survey/account/register")
    ]
    buttons = [InlineKeyboardButton(name, callback_data=f"survey_{i}") for i, (name, _) in enumerate(surveys)]
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
    return markup

def goals_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("📅 День", callback_data="goals_day"),
               InlineKeyboardButton("📋 Неделя", callback_data="goals_week"),
               InlineKeyboardButton("📆 Месяц", callback_data="goals_month"),
               InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
    return markup
