from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_LINKS

TOPICS = [
    "💼 Бизнес", "💰 Финансы", "🎮 Игры", "🎨 Творчество",
    "📱 Технологии", "🏋️ Спорт", "🍔 Еда", "✈️ Путешествия",
    "🎵 Музыка", "📚 Образование", "😂 Юмор", "🌿 Здоровье",
    "🐾 Животные", "🏠 Недвижимость", "👗 Мода", "🎬 Кино",
    "🗞 Новости", "🧠 Психология", "💻 IT/Программирование", "🔥 Другое"
]


def subscribe_kb():
    buttons = [[InlineKeyboardButton(text=name, url=url)] for name, url in CHANNEL_LINKS]
    buttons.append([InlineKeyboardButton(text="✅ Я подписался — проверить", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мой канал", callback_data="my_channel")],
        [InlineKeyboardButton(text="🔍 Найти партнёра", callback_data="search")],
        [InlineKeyboardButton(text="💬 Мои переговоры", callback_data="my_deals")],
        [InlineKeyboardButton(text="⭐️ Рейтинг каналов", callback_data="rating")],
        [InlineKeyboardButton(text="📊 История пиаров", callback_data="history")],
    ])


def topics_kb(prefix="reg_topic"):
    buttons = []
    row = []
    for t in TOPICS:
        row.append(InlineKeyboardButton(text=t, callback_data=f"{prefix}:{t}"))
        if len(row) == 2:
            buttons.append(row); row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def sub_ranges_kb(prefix="reg_subs"):
    ranges = [
        ("до 1 000", "0:1000"),
        ("1 000 – 5 000", "1000:5000"),
        ("5 000 – 20 000", "5000:20000"),
        ("20 000 – 100 000", "20000:100000"),
        ("100 000+", "100000:9999999"),
    ]
    buttons = [[InlineKeyboardButton(text=l, callback_data=f"{prefix}:{v}")] for l, v in ranges]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def channel_card_kb(channel_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤝 Предложить пиар", callback_data=f"offer:{channel_id}")],
        [InlineKeyboardButton(text="🔍 Ещё партнёры", callback_data="search")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")],
    ])


def deal_kb(deal_id: int, is_receiver: bool = False):
    buttons = []
    if is_receiver:
        buttons.append([
            InlineKeyboardButton(text="✅ Принять", callback_data=f"deal_accept:{deal_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"deal_decline:{deal_id}"),
        ])
    buttons.append([InlineKeyboardButton(text="💬 Написать партнёру", callback_data=f"deal_chat:{deal_id}")])
    buttons.append([InlineKeyboardButton(text="🏆 Пиар состоялся!", callback_data=f"deal_done:{deal_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="my_deals")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def stars_kb(deal_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"{'⭐️'*i}", callback_data=f"stars:{deal_id}:{i}")
        for i in range(1, 6)
    ]])


def back_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
    ])


def my_channel_kb(has_channel: bool):
    if has_channel:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_channel")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Зарегистрировать канал", callback_data="reg_channel")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")],
    ])
