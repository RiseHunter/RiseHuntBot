import os
import sqlite3
import logging
from datetime import datetime
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("risehunt.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в .env")

bot = TeleBot(BOT_TOKEN)
DB_FILE = "risehunt.db"
user_states: dict[str, dict] = {}

VALID_DIRECTIONS = {"PV", "IQ", "EQ", "SQ", "AQ", "XQ"}

DIRECTION_META = {
    "PV": {"emoji": "💪", "name": "Физическая витальность"},
    "IQ": {"emoji": "🧠", "name": "Когнитивный интеллект"},
    "EQ": {"emoji": "❤️", "name": "Эмоциональный интеллект"},
    "SQ": {"emoji": "👥", "name": "Социальный интеллект"},
    "AQ": {"emoji": "🔄", "name": "Адаптивный интеллект"},
    "XQ": {"emoji": "🧘", "name": "Экзистенциальная осознанность"},
}

ADVANCED_TEST_URLS = {
    "PV": "https://www.nsca.com/certification/cscs/",
    "IQ": "https://test.mensa.no/Home/Test/ru-RU",
    "EQ": "https://psytests.org/eq/schutte-run.html",
    "SQ": "https://psytests.org/iq/guilford.html",
    "AQ": "https://psytests.org/mmpi/mloam.html",
    "XQ": "https://tally.so/r/obyye1",
}

TEST_URLS = {
    "PV": "https://www.health.harvard.edu/physical-vitality-test",
    "IQ": "https://test.mensa.no/Home/Test/ru-RU",
    "EQ": "https://psytests.org/eq/schutte-run.html",
    "SQ": "https://psytests.org/iq/guilford.html",
    "AQ": "https://psytests.org/mmpi/mloam.html",
    "XQ": "https://tally.so/r/obyye1",
}

PERIOD_BONUS = {"day": 0.1, "week": 0.3, "month": 0.5}
TYPE_EMOJI   = {"emotions": "❤️", "reflection": "🕯️", "workout": "🏋️"}
TESTS_CONFIG = {
    "test_EQ": {
        "direction":   "EQ",
        "emoji":       "❤️",
        "name":        "Эмоциональный интеллект",
        "url":         "https://psytests.org/eq/schutte.html",   # ← замените ссылку
        "instruction": (
            "Пройди тест по ссылке выше.\n\n"
            "После завершения Tally покажет *итоговый балл* (число от 33 до 165).\n\n"
            "✏️ Введи этот балл сюда:"
        ),
        "hint":        "Число от *33 до 165*",
        "validate":    lambda x: 33 <= x <= 165,
        "convert":     lambda x: round(max(0.1, min(10.0, ((x - 33) / 132) * 9.9 + 0.1)), 1),
        "label":       lambda s: (
            "🌟 Исключительный EQ"  if s >= 9.1 else
            "🚀 Высокий уровень"    if s >= 8.1 else
            "✅ Хороший (норма)"    if s >= 6.1 else
            "⚠️ Требует развития"   if s >= 4.1 else
            "⬇️ Низкий уровень"
        ),
    },
    "test_SQ": {
        "direction":   "SQ",
        "emoji":       "👥",
        "name":        "Социальный интеллект",
        "url":         "https://psytests.org/iq/guilford.html",
        "instruction": (
            "Пройди тест Гилфорда–О'Салливана по ссылке выше.\n\n"
            "После завершения Tally покажет *количество правильных ответов* (число от 0 до 55).\n\n"
            "✏️ Введи это число сюда:"
        ),
        "hint":        "Число от *0 до 55*",
        "validate":    lambda x: 0 <= x <= 55,
        "convert":     lambda x: round(max(0.1, min(10.0, (x / 55) * 9.9 + 0.1)), 1),
        "label":       lambda s: (
            "🌟 Мастер социальных ситуаций" if s >= 9.1 else
            "🚀 Лидер по умолчанию"         if s >= 8.1 else
            "✅ Читаешь людей уверенно"     if s >= 7.1 else
            "👥 Нормальные соц. навыки"     if s >= 6.1 else
            "⚠️ Есть пробелы в общении"     if s >= 4.1 else
            "📉 Соц. навыки в развитии"     if s >= 2.1 else
            "🚨 Экстремально низкий SQ"
        ),
    },
    "test_AQ": {
        "direction":   "AQ",
        "emoji":       "🔄",
        "name":        "Адаптивный интеллект",
        "url":         "https://psytests.org/mmpi/mloam.html",        # ← psytests.org/mlq или нужная страница
        "instruction": (
            "Пройди тест на psytests.org по ссылке выше.\n\n"
            "В результатах найди раздел *«Личностный адаптивный потенциал»* "
            "и посмотри на строку *«Стены»* — это число от 0 до 10.\n\n"
            "✏️ Введи это число сюда:"
        ),
        "hint":        "Число от *0 до 10*",
        "validate":    lambda x: 0 <= x <= 10,
        "convert":     lambda x: round(max(0.1, min(10.0, float(x) if x > 0 else 0.1)), 1),
        "label":       lambda s: (
            "🌟 Высокий адаптивный потенциал" if s >= 7.0 else
            "✅ Средний уровень адаптации"    if s >= 4.0 else
            "⚠️ Низкий адаптивный потенциал"
        ),
    },
    "test_XQ": {
        "direction":   "XQ",
        "emoji":       "🧘",
        "name":        "Экзистенциальная осознанность",
        "url":         "https://tally.so/r/obyye1",   # ← замените ссылку
        "instruction": (
            "Пройди опросник по ссылке выше.\n\n"
            "После завершения Tally покажет *итоговый балл EZ* (число от -4 до 4, "
            "может быть дробным, например: 1.5 или -0.8).\n\n"
            "✏️ Введи этот балл сюда:"
        ),
        "hint":        "Число от *-4 до 4* (можно дробное, например: `1.5`)",
        "validate":    lambda x: -4.0 <= x <= 4.0,
        "convert":     lambda x: round(max(0.1, min(10.0, ((x + 4) / 8) * 9.9 + 0.1)), 1),
        "label":       lambda s: (
            "🟢 Сформированная осознанность"    if s >= 7.5 else
            "🟡 Переходная стадия"              if s >= 5.0 else
            "🟠 Активный кризис поиска"         if s >= 3.0 else
            "🔴 Критическое напряжение"
        ),
    },
    # PV, IQ — через стандартный тест (score 1–100), уже есть в боте
    "test_PV": {
        "direction":   "PV",
        "emoji":       "💪",
        "name":        "Физическая витальность",
        "url":         "https://www.health.harvard.edu/physical-vitality-test",
        "instruction": (
            "Пройди тест по ссылке выше.\n\n"
            "В конце ты увидишь *итоговый процент или балл* (от 1 до 100).\n\n"
            "✏️ Введи этот балл сюда:"
        ),
        "hint":        "Число от *1 до 100*",
        "validate":    lambda x: 1 <= x <= 100,
        "convert":     lambda x: round(max(0.1, min(10.0, x / 10)), 1),
        "label":       lambda s: (
            "🌟 Отличная физическая форма" if s >= 8.0 else
            "✅ Хороший уровень"           if s >= 6.0 else
            "⚠️ Есть зоны роста"           if s >= 4.0 else
            "⬇️ Требует внимания"
        ),
    },
    "test_IQ": {
    "direction":   "IQ",
    "emoji":       "🧠",
    "name":        "Когнитивный интеллект",
    "url":         "http://test.mensa.no/Home/Test/",  # ← вставь свою ссылку сюда
    "instruction": (
        "Пройди тест Mensa Norway по ссылке выше.\n\n"
        "После завершения тест покажет твой *IQ балл* (от 70 до 145).\n\n"
        "✏️ Введи этот балл сюда:"
    ),
    "hint":     "Число от *70 до 145*",
    "validate": lambda x: 70 <= x <= 145,
    "convert": lambda x: round(max(0.1, min(10.0, (x - 100) / 9 + 5.0)), 1),
    "label":    lambda s: (
        "🌟 Гениальность"          if s >= 9.5 else
        "🚀 Очень высокий IQ"      if s >= 8.0 else
        "✅ Выше среднего"         if s >= 6.0 else
        "📊 Средний уровень"       if s >= 4.0 else
        "⚠️ Есть куда развиваться"
    ),
},
}

# ── Database ──────────────────────────────────────────────────────────────────
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     TEXT PRIMARY KEY,
                PV          REAL    DEFAULT 5.0,
                IQ          REAL    DEFAULT 5.0,
                EQ          REAL    DEFAULT 5.0,
                SQ          REAL    DEFAULT 5.0,
                AQ          REAL    DEFAULT 5.0,
                XQ          REAL    DEFAULT 5.0,
                level       INTEGER DEFAULT 1,
                name        TEXT    DEFAULT NULL,
                age         INTEGER DEFAULT NULL,
                gender      TEXT    DEFAULT NULL,
                tg_username TEXT    DEFAULT NULL,
                onboarded   INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS journal (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT NOT NULL,
                type       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS goals (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT NOT NULL,
                period     TEXT NOT NULL CHECK(period IN ('day','week','month')),
                direction  TEXT NOT NULL DEFAULT 'PV',
                title      TEXT NOT NULL,
                done       INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
        """)
        for ddl in [
            "ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1",
            "ALTER TABLE users ADD COLUMN name TEXT DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN age INTEGER DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN gender TEXT DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN tg_username TEXT DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN onboarded INTEGER DEFAULT 0",
            "ALTER TABLE goals ADD COLUMN direction TEXT NOT NULL DEFAULT 'PV'",
        ]:
            try:
                conn.execute(ddl)
            except Exception:
                pass
        conn.execute("DELETE FROM journal WHERE created_at < datetime('now', '-30 days')")
    log.info("БД инициализирована: %s", DB_FILE)


def get_user(user_id: str) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return dict(row)
        conn.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
    return {"user_id": user_id, "PV": 5.0, "IQ": 5.0, "EQ": 5.0, "SQ": 5.0,
            "AQ": 5.0, "XQ": 5.0, "level": 1, "name": None, "age": None,
            "gender": None, "tg_username": None, "onboarded": 0}


def update_user_fields(user_id: str, **kwargs) -> None:
    allowed = {"name", "age", "gender", "tg_username", "onboarded"}
    fields  = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [user_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE users SET {clause} WHERE user_id = ?", values)


def update_direction(user_id: str, direction: str, value: float) -> None:
    if direction not in VALID_DIRECTIONS:
        raise ValueError(f"Недопустимое направление: {direction}")
    with get_conn() as conn:
        conn.execute(f"UPDATE users SET {direction} = ? WHERE user_id = ?", (value, user_id))


def do_level_up(user_id: str, direction: str) -> int:
    with get_conn() as conn:
        conn.execute(
            f"UPDATE users SET level = level + 1, {direction} = 5.0 WHERE user_id = ?", (user_id,)
        )
        row = conn.execute("SELECT level FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return row["level"]


def save_journal(user_id: str, journal_type: str, content: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO journal (user_id, type, content) VALUES (?, ?, ?)",
            (user_id, journal_type, content)
        )


def get_journal_history(user_id: str) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, type, content, created_at FROM journal "
            "WHERE user_id = ? AND created_at >= datetime('now', '-7 days') "
            "ORDER BY created_at DESC LIMIT 15",
            (user_id,)
        ).fetchall()


def get_journal_entry(entry_id: int, user_id: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM journal WHERE id = ? AND user_id = ?", (entry_id, user_id)
        ).fetchone()


def get_goals(user_id: str, period: str) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM goals WHERE user_id = ? AND period = ? ORDER BY id",
            (user_id, period)
        ).fetchall()


def get_goal_by_id(goal_id: int, user_id: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id)
        ).fetchone()


def add_goal(user_id: str, period: str, direction: str, title: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO goals (user_id, period, direction, title) VALUES (?, ?, ?, ?)",
            (user_id, period, direction, title)
        )


def complete_goal(goal_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE goals SET done = 1 WHERE id = ?", (goal_id,))


def uncomplete_goal(goal_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE goals SET done = 0 WHERE id = ?", (goal_id,))


def delete_goal(goal_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))


# ── Helpers ───────────────────────────────────────────────────────────────────
def bar(value: float, width: int = 10) -> str:
    filled = max(0, min(width, round(value)))
    return "█" * filled + "░" * (width - filled)


def calc_cores(u: dict) -> tuple[float, float, float]:
    return u["PV"], (u["IQ"] + u["EQ"] + u["AQ"] + u["SQ"]) / 4, u["XQ"]


def score_to_scale(score: float) -> float:
    return round(max(0.1, min(10.0, score / 10)), 1)


def clamp(value: float) -> float:
    return round(max(0.1, min(10.0, value)), 1)


def fmt_goals_plain(goals: list) -> str:
    if not goals:
        return "  _Целей пока нет. Добавьте первую!_"
    return "\n".join(
        f"  {'✅' if g['done'] else '⬜'} {DIRECTION_META[g['direction']]['emoji']} {g['title']}"
        for g in goals
    )


def user_display(u: dict) -> str:
    return u.get("name") or "—"


# ── Level-up ──────────────────────────────────────────────────────────────────
def check_and_level_up(chat_id, user_id: str, direction: str, new_val: float) -> bool:
    if new_val < 10.0:
        return False
    new_level = do_level_up(user_id, direction)
    meta    = DIRECTION_META[direction]
    adv_url = ADVANCED_TEST_URLS.get(direction, "https://google.com")
    markup  = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(f"🚀 Продвинутый тест {direction}", url=adv_url),
        InlineKeyboardButton("🧭 Главное меню", callback_data="main_menu"),
    )
    bot.send_message(
        chat_id,
        f"🏆 *УРОВЕНЬ {new_level} ДОСТИГНУТ!*\n\n"
        f"{meta['emoji']} *{meta['name']}* достигла максимума `10.0`!\n\n"
        f"✨ Шкала сброшена до `5.0` — новый цикл роста начат\n"
        f"🎯 Вам открыт *продвинутый тест* для {direction}\n\n"
        f"_Базовый уровень пройден — впереди новые вершины!_",
        reply_markup=markup,
        parse_mode="Markdown",
    )
    return True


# ── Keyboards ─────────────────────────────────────────────────────────────────
def kb_main() -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=1)
    m.add(
        InlineKeyboardButton("📊 Профиль",  callback_data="profile"),
        InlineKeyboardButton("📓 Журнал",   callback_data="journal"),
        InlineKeyboardButton("📋 Анкеты",   callback_data="tests_menu"),
        InlineKeyboardButton("🎯 Цели",     callback_data="goals"),
    )
    return m


def kb_back_main() -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
    return m


def kb_back(cb: str, label: str = "🔙 Назад") -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton(label, callback_data=cb))
    return m


def kb_profile() -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=1)
    m.add(
        InlineKeyboardButton("✏️ Изменить имя",  callback_data="edit_name"),
        InlineKeyboardButton("📋 Пройти анкеты", callback_data="tests_menu"),
        InlineKeyboardButton("🔙 Главное меню",  callback_data="main_menu"),
    )
    return m


def kb_tests() -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=1)
    for d, meta in DIRECTION_META.items():
        m.add(InlineKeyboardButton(f"{meta['emoji']} {d} — {meta['name']}", callback_data=f"test_{d.lower()}"))
    m.add(InlineKeyboardButton("🔙 Профиль", callback_data="profile"))
    return m


def kb_test_action(direction: str, user_level: int) -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=1)
    url = ADVANCED_TEST_URLS[direction] if user_level > 1 else TEST_URLS[direction]
    m.add(
        InlineKeyboardButton("📋 Пройти тест",     url=url),
        InlineKeyboardButton("✅ Ввести результат", callback_data=f"enter_{direction.lower()}"),
        InlineKeyboardButton("🔙 Назад",            callback_data="tests_menu"),
    )
    return m


def kb_journal() -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=1)
    m.add(
        InlineKeyboardButton("🏋️ Тренировка",       callback_data="journal_workout"),
        InlineKeyboardButton("❤️ Дневник эмоций",   callback_data="journal_emotions"),
        InlineKeyboardButton("🕯️ Рефлексия",        callback_data="journal_reflection"),
        InlineKeyboardButton("📜 История (7 дней)", callback_data="journal_history"),
        InlineKeyboardButton("🔙 Главное меню",     callback_data="main_menu"),
    )
    return m


def kb_training() -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=2)
    for n in (2, 3, 4, 5):
        m.add(InlineKeyboardButton(f"{n} раза/нед", callback_data=f"training_{n}"))
    m.add(InlineKeyboardButton("🔙 Журнал", callback_data="journal"))
    return m


def kb_history_list(entries: list) -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=1)
    for e in entries:
        emoji = TYPE_EMOJI.get(e["type"], "📝")
        dt    = e["created_at"][:16]
        m.add(InlineKeyboardButton(f"{emoji} {dt}", callback_data=f"jentry_{e['id']}"))
    m.add(InlineKeyboardButton("🔙 Журнал", callback_data="journal"))
    return m


def kb_entry_back() -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=1)
    m.add(
        InlineKeyboardButton("🔙 К списку записей", callback_data="journal_history"),
        InlineKeyboardButton("🏠 Главное меню",     callback_data="main_menu"),
    )
    return m


def kb_goal_direction(period: str) -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=2)
    for d, meta in DIRECTION_META.items():
        m.add(InlineKeyboardButton(f"{meta['emoji']} {d}", callback_data=f"goal_dir_{period}_{d}"))
    m.add(InlineKeyboardButton("🔙 Назад", callback_data=f"goals_{period}"))
    return m


def kb_goal_manage(goal_id: int, period: str) -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("✅ Выполнено", callback_data=f"goal_done_{goal_id}_{period}"),
        InlineKeyboardButton("↩️ Отменить",  callback_data=f"goal_undo_{goal_id}_{period}"),
        InlineKeyboardButton("🗑 Удалить",   callback_data=f"goal_del_{goal_id}_{period}"),
        InlineKeyboardButton("🔙 К целям",   callback_data=f"goals_{period}"),
    )
    return m


# ── Registration keyboards ────────────────────────────────────────────────────
def kb_gender() -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("👨 Мужской",      callback_data="reg_gender_М"),
        InlineKeyboardButton("👩 Женский",       callback_data="reg_gender_Ж"),
        InlineKeyboardButton("🌀 Другой",        callback_data="reg_gender_Другой"),
        InlineKeyboardButton("⏭ Не указывать",  callback_data="reg_gender_skip"),
    )
    return m


def kb_skip(next_cb: str) -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("⏭ Пропустить", callback_data=next_cb))
    return m


def kb_reg_finish() -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup(row_width=1)
    m.add(
        InlineKeyboardButton("📋 Написать цели на неделю",   callback_data="reg_action_goals"),
        InlineKeyboardButton("🏋️ Создать план тренировок",  callback_data="reg_action_workout"),
        InlineKeyboardButton("🧭 Перейти в главное меню",    callback_data="main_menu"),
    )
    return m


# ── Screen builders ───────────────────────────────────────────────────────────
def build_profile(u: dict) -> str:
    body, mind, spirit = calc_cores(u)
    level  = u.get("level", 1)
    name   = u.get("name") or "—"
    age    = u.get("age")
    gender = u.get("gender")
    tg     = u.get("tg_username")

    extra  = f" · {age} лет" if age else ""
    extra += f" · {gender}"   if gender else ""
    tg_line = f"\n🔗 @{tg}"  if tg else ""

    lines = [
        f"👤 *{name}*  🏅 Уровень {level}{extra}{tg_line}\n",
        "💡 *3 ЯДРА*",
        f"• Тело  (PV): `{body:.1f}/10` {bar(body)}",
        f"• Разум:      `{mind:.1f}/10` {bar(mind)}",
        f"• Дух   (XQ): `{spirit:.1f}/10` {bar(spirit)}\n",
        "🧠 *6 НАПРАВЛЕНИЙ*",
    ]
    for d, meta in DIRECTION_META.items():
        val = u[d]
        lines.append(f"• {meta['emoji']} {d}: `{val:.1f}/10` {bar(val)}")
    return "\n".join(lines)


def build_goals_view(user_id: str, period: str) -> tuple[str, InlineKeyboardMarkup]:
    label      = {"day": "ДЕНЬ", "week": "НЕДЕЛЯ", "month": "МЕСЯЦ"}[period]
    bonus_hint = {"day": "+0.1", "week": "+0.3", "month": "+0.5"}[period]
    goals      = get_goals(user_id, period)
    done       = sum(1 for g in goals if g["done"])

    text = (
        f"🎯 *ЦЕЛИ — {label}* _({bonus_hint} к направлению за выполнение)_\n\n"
        + fmt_goals_plain(goals)
        + f"\n\n✅ Выполнено: {done}/{len(goals)}"
        + "\n_Нажмите на цель для управления_"
    )

    m = InlineKeyboardMarkup(row_width=1)
    for g in goals:
        meta  = DIRECTION_META[g["direction"]]
        check = "✅" if g["done"] else "⬜"
        m.add(InlineKeyboardButton(
            f"{check} {meta['emoji']} {g['title'][:35]}",
            callback_data=f"goal_manage_{g['id']}_{period}"
        ))
    for lbl, cb in [("📅 День", "goals_day"), ("📋 Неделя", "goals_week"), ("📆 Месяц", "goals_month")]:
        m.add(InlineKeyboardButton(lbl, callback_data=cb))
    m.add(
        InlineKeyboardButton("➕ Добавить цель", callback_data=f"goal_add_{period}"),
        InlineKeyboardButton("🔙 Главное меню",  callback_data="main_menu"),
    )
    return text, m


# ── Handlers ──────────────────────────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def cmd_start(message):
    user_id = str(message.from_user.id)
    u = get_user(user_id)
    log.info("Старт: user_id=%s", user_id)

    if not u.get("onboarded"):
        tg_first = message.from_user.first_name or ""
        user_states[user_id] = {"type": "reg_name"}
        bot.reply_to(
            message,
            f"👋 Привет{', ' + tg_first if tg_first else ''}! Добро пожаловать в *RiseHunt* 🔥\n\n"
            "Давай познакомимся — займёт меньше минуты.\n\n"
            "1️⃣ *Как тебя зовут?*\n_Можно псевдоним или имя_",
            parse_mode="Markdown",
        )
    else:
        bot.reply_to(
            message,
            f"👋 С возвращением, *{user_display(u)}*! 🏅 Уровень {u.get('level', 1)}\n\n"
            "Выберите раздел:",
            reply_markup=kb_main(),
            parse_mode="Markdown",
        )


@bot.message_handler(commands=["help"])
def cmd_help(message):
    bot.reply_to(
        message,
        "ℹ️ *Помощь RiseHunt*\n\n"
        "• /start — главное меню\n"
        "• /profile — ваш профиль\n"
        "• /reset — сбросить зависшее состояние\n\n"
        "*Цели*: при добавлении выбирается направление.\n"
        "Выполнение: день +0.1 · неделя +0.3 · месяц +0.5\n\n"
        "*Уровни*: достигните 10.0 → уровень ↑, шкала сбросится до 5.0.",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["profile"])
def cmd_profile(message):
    u = get_user(str(message.from_user.id))
    bot.reply_to(message, build_profile(u), reply_markup=kb_profile(), parse_mode="Markdown")


@bot.message_handler(commands=["reset"])
def cmd_reset(message):
    user_states.pop(str(message.from_user.id), None)
    bot.reply_to(message, "✅ Состояние сброшено.", reply_markup=kb_main())


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data    = call.data
    user_id = str(call.from_user.id)
    cid     = call.message.chat.id
    mid     = call.message.message_id
    log.info("Callback: %s from %s", data, user_id)

    def edit(text, markup=None):
        bot.edit_message_text(text, cid, mid, reply_markup=markup, parse_mode="Markdown")

    try:
        if data == "main_menu":
            user_states.pop(user_id, None)
            edit("🧭 *Главное меню*\nВыберите действие:", kb_main())

        elif data == "profile":
            edit(build_profile(get_user(user_id)), kb_profile())

        elif data == "edit_name":
            user_states[user_id] = {"type": "edit_name"}
            edit("✏️ *Изменить имя*\n\nНапишите новое имя или псевдоним:", kb_back(cb="profile"))

        # ── Registration: age skip ────────────────────────────────────────────
        elif data == "reg_age_skip":
            user_states[user_id] = {"type": "reg_gender_wait"}
            edit("3️⃣ *Укажи пол:*", kb_gender())

        # ── Registration: gender ──────────────────────────────────────────────
        elif data.startswith("reg_gender_"):
            val    = data[len("reg_gender_"):]
            gender = None if val == "skip" else val
            update_user_fields(user_id, gender=gender)
            user_states[user_id] = {"type": "reg_tg"}
            edit(
                "4️⃣ *Ваш Telegram username*\n\n"
                "Напишите @username или нажмите «Пропустить»:",
                kb_skip(next_cb="reg_tg_skip"),
            )

        elif data == "reg_tg_skip":
            user_states.pop(user_id, None)
            edit(
                "🎉 *Отлично! Профиль заполнен*\n\nС чего начнём прямо сейчас?",
                kb_reg_finish(),
            )

        # ── Registration finish ───────────────────────────────────────────────
        elif data == "reg_action_goals":
            update_user_fields(user_id, onboarded=1)
            user_states[user_id] = {"type": "reg_week_goals", "goals": []}
            edit(
                "📋 *ЦЕЛИ НА НЕДЕЛЮ*\n\n"
                "Пиши цели по одной — каждую отдельным сообщением.\n"
                "Когда закончишь — нажми *«Готово»*:",
                InlineKeyboardMarkup().add(
                    InlineKeyboardButton("✅ Готово", callback_data="reg_goals_done")
                ),
            )

        elif data == "reg_goals_done":
            state      = user_states.get(user_id, {})
            goals_list = state.get("goals", [])
            for title in goals_list:
                add_goal(user_id, "week", "PV", title)
            user_states.pop(user_id, None)
            u     = get_user(user_id)
            count = len(goals_list)
            edit(
                f"🎉 *Готово, {user_display(u)}!*\n\n"
                f"Сохранено целей на неделю: *{count}*\n\n"
                "Добро пожаловать в RiseHunt! 🚀",
                kb_main(),
            )

        elif data == "reg_action_workout":
            update_user_fields(user_id, onboarded=1)
            user_states.pop(user_id, None)
            edit(
                "🏋️ *ПЛАН ТРЕНИРОВОК*\n\n"
                "_ВОЗ рекомендует 150 мин/нед умеренной нагрузки_\n\n"
                "Выберите частоту тренировок в неделю:",
                kb_training(),
            )

        elif data == "tests_menu":
            # Показываем меню выбора теста
            m = InlineKeyboardMarkup(row_width=1)
            for cb, cfg in TESTS_CONFIG.items():
                m.add(InlineKeyboardButton(
                    f"{cfg['emoji']} {cfg['direction']} — {cfg['name']}",
                    callback_data=cb
                ))
            m.add(InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            edit(
                "📋 *АНКЕТЫ И ТЕСТЫ*\n\n"
                "Выбери направление → перейди по ссылке → "
                "пройди тест → вернись и введи результат:",
                m,
            )

        elif data in TESTS_CONFIG:
            # Показываем конкретный тест с кнопкой-ссылкой
            cfg = TESTS_CONFIG[data]
            direction = cfg["direction"]
            u = get_user(user_id)
            level = u.get("level", 1)
            old = u[direction]

            m = InlineKeyboardMarkup(row_width=1)
            m.add(
                InlineKeyboardButton(
                    f"🌐 Перейти к тесту {direction}",
                    url=cfg["url"]
                ),
                InlineKeyboardButton("🔙 Назад", callback_data="tests_menu"),
            )

            tier = "продвинутый (Ур.2+)" if level > 1 else "базовый"
            edit(
                f"{cfg['emoji']} *{direction} — {cfg['name']}* _{tier}_\n\n"
                f"Текущий уровень: `{old:.1f}/10` {bar(old)}\n\n"
                f"{cfg['instruction']}\n\n"
                f"💡 {cfg['hint']}",
                m,
            )
            # Ждём ввода числа
            user_states[user_id] = {
                "type": "test_input",
                "test_key": data,
                "direction": direction,
            }

        # ── Journal ───────────────────────────────────────────────────────────
        elif data == "journal":
            edit("📓 *ЖУРНАЛ*\nВыберите раздел:", kb_journal())

        elif data == "journal_emotions":
            user_states[user_id] = {"type": "emotions"}
            edit(
                "❤️ *ДНЕВНИК ЭМОЦИЙ*\n\n"
                "• Что сегодня чувствовали?\n"
                "• Какие эмоции доминировали?\n"
                "• Что помогло справиться?\n\n"
                "✍️ Напишите запись:",
                kb_back_main(),
            )

        elif data == "journal_reflection":
            user_states[user_id] = {"type": "reflection"}
            edit(
                "🕯️ *РЕФЛЕКСИЯ*\n\n"
                "• Лучший момент дня?\n"
                "• Что можно улучшить?\n"
                "• Главный инсайт?\n\n"
                "💭 Ваши мысли:",
                kb_back_main(),
            )

        elif data == "journal_workout":
            edit(
                "🏋️ *ТРЕНИРОВКА*\n\n"
                "_ВОЗ рекомендует 150 мин/нед умеренной нагрузки_\n\n"
                "Выберите частоту тренировок в неделю:",
                kb_training(),
            )

        elif data == "journal_history":
            entries = get_journal_history(user_id)
            if not entries:
                edit("📜 *История пуста* — записей за 7 дней нет.", kb_back(cb="journal"))
            else:
                lines = ["📜 *ЗАПИСИ ЗА 7 ДНЕЙ*\n", "_Нажмите на запись, чтобы открыть полностью:_\n"]
                for e in entries:
                    emoji   = TYPE_EMOJI.get(e["type"], "📝")
                    dt      = e["created_at"][:16]
                    raw     = e["content"]
                    preview = raw[raw.find("\n\n")+2:][:55].replace("\n", " ") if "\n\n" in raw else raw[:55]
                    lines.append(f"{emoji} `{dt}` — _{preview}..._")
                edit("\n".join(lines), kb_history_list(entries))

        elif data.startswith("jentry_"):
            entry_id = int(data[7:])
            entry    = get_journal_entry(entry_id, user_id)
            if not entry:
                edit("❌ Запись не найдена.", kb_back(cb="journal_history"))
            else:
                emoji   = TYPE_EMOJI.get(entry["type"], "📝")
                dt      = entry["created_at"][:16]
                content = entry["content"]
                if len(content) > 3600:
                    content = content[:3600] + "\n\n_[текст обрезан]_"
                edit(f"{emoji} *Запись от {dt}*\n\n{content}", kb_entry_back())

        elif data.startswith("training_"):
            freq = int(data.split("_")[1])
            user_states[user_id] = {"type": "workout", "days": freq, "current_day": 1, "entries": []}
            edit(
                f"✅ *{freq} ДНЕЙ/НЕДЕЛЮ*\n\n"
                f"📅 *День 1 из {freq}*\n"
                "Напишите упражнения для этого дня:",
                kb_back_main(),
            )

        # ── Goals ─────────────────────────────────────────────────────────────
        elif data in ("goals", "goals_day", "goals_week", "goals_month"):
            period = "day" if data in ("goals", "goals_day") else data.split("_")[1]
            user_states[user_id] = {"type": "goals_view", "period": period}
            text, markup = build_goals_view(user_id, period)
            edit(text, markup)

        elif data.startswith("goal_add_"):
            period = data[9:]
            lbl    = {"day": "на день", "week": "на неделю", "month": "на месяц"}[period]
            edit(
                f"➕ *Новая цель {lbl}*\n\n"
                "Выберите направление, к которому относится цель:",
                kb_goal_direction(period),
            )

        elif data.startswith("goal_dir_"):
            parts     = data.split("_")
            period    = parts[2]
            direction = parts[3]
            user_states[user_id] = {"type": "goal_add", "period": period, "direction": direction}
            meta = DIRECTION_META[direction]
            lbl  = {"day": "на день", "week": "на неделю", "month": "на месяц"}[period]
            edit(
                f"➕ *Новая цель {lbl}*\n"
                f"Направление: {meta['emoji']} *{direction} — {meta['name']}*\n\n"
                "Напишите текст цели одним сообщением:",
                kb_back(cb=f"goal_add_{period}"),
            )

        elif data.startswith("goal_manage_"):
            parts   = data.split("_")
            goal_id = int(parts[2])
            period  = parts[3]
            goal    = get_goal_by_id(goal_id, user_id)
            if not goal:
                edit("❌ Цель не найдена.", kb_back(cb=f"goals_{period}"))
            else:
                d      = goal["direction"]
                meta   = DIRECTION_META[d]
                bonus  = PERIOD_BONUS[period]
                status = "✅ выполнена" if goal["done"] else "⬜ активна"
                edit(
                    f"🎯 *Цель #{goal_id}*\n\n"
                    f"{meta['emoji']} *{d} — {meta['name']}*\n\n"
                    f"_{goal['title']}_\n\n"
                    f"Статус: {status}\n"
                    f"💡 За выполнение: *+{bonus}* к {d}",
                    kb_goal_manage(goal_id, period),
                )

        elif data.startswith("goal_done_"):
            parts   = data.split("_")
            goal_id = int(parts[2])
            period  = parts[3]
            goal    = get_goal_by_id(goal_id, user_id)
            if not goal:
                edit("❌ Цель не найдена.", kb_back(cb=f"goals_{period}"))
            elif goal["done"]:
                bot.answer_callback_query(call.id, "Цель уже отмечена выполненной!")
                return
            else:
                complete_goal(goal_id)
                direction = goal["direction"]
                bonus     = PERIOD_BONUS[period]
                u         = get_user(user_id)
                old_val   = u[direction]
                new_val   = clamp(old_val + bonus)
                update_direction(user_id, direction, new_val)
                meta    = DIRECTION_META[direction]
                leveled = check_and_level_up(cid, user_id, direction, new_val)
                text, markup = build_goals_view(user_id, period)
                if leveled:
                    edit(text, markup)
                else:
                    edit(
                        f"🎉 *Выполнено!* {meta['emoji']} {direction}: "
                        f"`{old_val:.1f}` → `{new_val:.1f}` *(+{bonus})*\n\n" + text,
                        markup,
                    )

        elif data.startswith("goal_undo_"):
            parts   = data.split("_")
            goal_id = int(parts[2])
            period  = parts[3]
            goal    = get_goal_by_id(goal_id, user_id)
            if goal and goal["done"]:
                uncomplete_goal(goal_id)
                u         = get_user(user_id)
                direction = goal["direction"]
                new_val   = clamp(u[direction] - PERIOD_BONUS[period])
                update_direction(user_id, direction, new_val)
            text, markup = build_goals_view(user_id, period)
            edit(text, markup)

        elif data.startswith("goal_del_"):
            parts   = data.split("_")
            goal_id = int(parts[2])
            period  = parts[3]
            delete_goal(goal_id)
            text, markup = build_goals_view(user_id, period)
            edit(f"🗑 *Цель удалена*\n\n{text}", markup)

        else:
            log.warning("Неизвестный callback: %s", data)

    except Exception as e:
        log.exception("Ошибка в callback_handler: %s", e)
        bot.answer_callback_query(call.id, "⚠️ Произошла ошибка, попробуйте снова.")
        return

    bot.answer_callback_query(call.id)


@bot.message_handler(content_types=["text"])
def handle_text(message):
    user_id = str(message.from_user.id)
    text    = message.text.strip()

    if user_id not in user_states:
        bot.reply_to(message, "🔙 Используйте меню кнопок.", reply_markup=kb_main())
        return

    state = user_states[user_id]
    stype = state["type"]

    # ── Registration ──────────────────────────────────────────────────────────
    if stype == "reg_name":
        name = text[:50]
        update_user_fields(user_id, name=name)
        user_states[user_id] = {"type": "reg_age"}
        bot.reply_to(
            message,
            f"✅ Приятно познакомиться, *{name}*!\n\n"
            "2️⃣ *Сколько тебе лет?*\n_Напиши число_",
            reply_markup=kb_skip(next_cb="reg_age_skip"),
            parse_mode="Markdown",
        )

    elif stype == "reg_age":
        try:
            age = int(text)
            if not (5 <= age <= 120):
                raise ValueError
            update_user_fields(user_id, age=age)
        except ValueError:
            bot.reply_to(message, "❌ Введи корректный возраст (число).",
                         reply_markup=kb_skip(next_cb="reg_age_skip"))
            return
        user_states[user_id] = {"type": "reg_gender_wait"}
        bot.reply_to(message, "3️⃣ *Укажи пол:*", reply_markup=kb_gender(), parse_mode="Markdown")

    elif stype == "reg_tg":
        tg = text.lstrip("@")[:50]
        update_user_fields(user_id, tg_username=tg)
        user_states.pop(user_id, None)
        bot.reply_to(
            message,
            "🎉 *Отлично! Профиль заполнен*\n\nС чего начнём прямо сейчас?",
            reply_markup=kb_reg_finish(),
            parse_mode="Markdown",
        )

    elif stype == "reg_week_goals":
        state["goals"].append(text[:200])
        count = len(state["goals"])
        bot.reply_to(
            message,
            f"✅ *Цель {count} добавлена!*\n_{text[:60]}_\n\n"
            "Напиши следующую или нажми *«Готово»*:",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("✅ Готово", callback_data="reg_goals_done")
            ),
            parse_mode="Markdown",
        )

    # ── Edit name ─────────────────────────────────────────────────────────────
    elif stype == "edit_name":
        name = text[:50]
        update_user_fields(user_id, name=name)
        del user_states[user_id]
        bot.reply_to(
            message,
            f"✅ *Имя обновлено!*\n\nТеперь тебя зовут: *{name}*",
            reply_markup=kb_profile(),
            parse_mode="Markdown",
        )
    elif stype == "test_input":
        test_key = state["test_key"]
        direction = state["direction"]
        cfg = TESTS_CONFIG[test_key]

        # Парсим число (поддерживаем и дробные для XQ)
        try:
            value = float(text.replace(",", "."))
        except ValueError:
            bot.reply_to(
                message,
                f"❌ Введи *число*.\n💡 {cfg['hint']}",
                parse_mode="Markdown",
                reply_markup=kb_back_main(),
            )
            return

        # Валидация диапазона
        if not cfg["validate"](value):
            bot.reply_to(
                message,
                f"❌ Число вне диапазона.\n💡 {cfg['hint']}",
                parse_mode="Markdown",
                reply_markup=kb_back_main(),
            )
            return

        # Считаем новый уровень
        u = get_user(user_id)
        old_val = u[direction]
        new_val = cfg["convert"](value)
        update_direction(user_id, direction, new_val)

        meta = DIRECTION_META[direction]
        change = "📈" if new_val >= old_val else "📉"
        label = cfg["label"](new_val)

        bot.reply_to(
            message,
            f"✅ *{direction} обновлено!*\n\n"
            f"{meta['emoji']} {label}\n\n"
            f"{change} Было:  `{old_val:.1f}` {bar(old_val)}\n"
            f"   Стало: `{new_val:.1f}` {bar(new_val)}",
            reply_markup=kb_profile(),
            parse_mode="Markdown",
        )
        del user_states[user_id]

        # Проверка level-up
        check_and_level_up(message.chat.id, user_id, direction, new_val)

    # ── Journal ───────────────────────────────────────────────────────────────
    elif stype in ("emotions", "reflection"):
        ts    = datetime.now().strftime("%d.%m.%Y %H:%M")
        entry = f"{ts}\n\n{text}"
        save_journal(user_id, stype, entry)
        emoji = "❤️" if stype == "emotions" else "🕯️"
        bot.reply_to(
            message,
            f"✅ *{emoji} Сохранено!*\n\n`{ts}`\n\n"
            f"_{text[:80]}{'...' if len(text) > 80 else ''}_\n\n💾 Хранится 30 дней",
            reply_markup=kb_main(),
            parse_mode="Markdown",
        )
        del user_states[user_id]

    # ── Workout ───────────────────────────────────────────────────────────────
    elif stype == "workout":
        day   = state["current_day"]
        total = state["days"]
        state["entries"].append(f"День {day}: {text}")
        if day < total:
            state["current_day"] += 1
            bot.reply_to(
                message,
                f"✅ *День {day} записан*\n\n"
                f"📅 *День {day + 1} из {total}*\nНапишите упражнения:",
                reply_markup=kb_back_main(),
                parse_mode="Markdown",
            )
        else:
            ts      = datetime.now().strftime("%d.%m.%Y %H:%M")
            content = f"{ts}\n\nПлан {total} дней:\n" + "\n".join(state["entries"])
            save_journal(user_id, "workout", content)
            bot.reply_to(
                message,
                f"🎉 *ПЛАН НА {total} ДНЕЙ ГОТОВ!*\n\n"
                + "\n".join(f"• {e}" for e in state["entries"])
                + "\n\n💾 Сохранено в журнале",
                reply_markup=kb_main(),
                parse_mode="Markdown",
            )
            del user_states[user_id]

    # ── Goal add ──────────────────────────────────────────────────────────────
    elif stype == "goal_add":
        period    = state["period"]
        direction = state["direction"]
        add_goal(user_id, period, direction, text)
        del user_states[user_id]
        user_states[user_id] = {"type": "goals_view", "period": period}
        meta = DIRECTION_META[direction]
        goal_text, markup = build_goals_view(user_id, period)
        bot.reply_to(
            message,
            f"✅ *Цель добавлена!*\n{meta['emoji']} {direction} — {meta['name']}\n\n" + goal_text,
            reply_markup=markup,
            parse_mode="Markdown",
        )

    else:
        bot.reply_to(message, "🔙 Используйте меню кнопок.", reply_markup=kb_main())


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    log.info("🤖 RiseHunt Bot v2.0 запущен")
    bot.infinity_polling(skip_pending=True)
