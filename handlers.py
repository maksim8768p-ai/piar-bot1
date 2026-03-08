from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

import database as db
from config import CHANNELS, ADMIN_IDS
from keyboards import (
    subscribe_kb, main_menu_kb, topics_kb, sub_ranges_kb,
    channel_card_kb, deal_kb, stars_kb, back_main_kb, my_channel_kb, TOPICS
)

router = Router()


# ── FSM ───────────────────────────────────────
class RegChannel(StatesGroup):
    title = State(); link = State(); topic = State()
    subscribers = State(); description = State()

class EditChannel(StatesGroup):
    title = State(); link = State(); topic = State()
    subscribers = State(); description = State()

class ChatState(StatesGroup):
    deal_id = State(); writing = State()

class ReviewState(StatesGroup):
    deal_id = State(); comment = State()


# ── Helpers ───────────────────────────────────
async def check_subs(bot: Bot, user_id: int) -> bool:
    for ch in CHANNELS:
        try:
            m = await bot.get_chat_member(ch, user_id)
            if m.status not in ("member", "administrator", "creator"):
                return False
        except Exception:
            return False
    return True

def fmt_stars(rating: float) -> str:
    f = int(round(rating))
    return "⭐️" * f + "☆" * (5 - f) + f" {rating:.1f}"

def fmt_channel(ch) -> str:
    # id,owner_id,title,link,topic,subscribers,description,rating,piar_count,created_at
    return (
        f"📢 <b>{ch[2]}</b>\n"
        f"🔗 {ch[3]}\n"
        f"🏷 {ch[4]}  |  👥 {ch[5]:,} подписчиков\n"
        f"{fmt_stars(ch[7])}  |  🤝 Пиаров: {ch[8]}\n"
        f"📝 {ch[6] or '—'}"
    )

def get_other_owner(deal, my_channel_id):
    """Return owner_id of the other side of the deal."""
    if deal[1] == my_channel_id:
        other = db.get_channel_by_id(deal[2])
    else:
        other = db.get_channel_by_id(deal[1])
    return other[1] if other else None


# ══════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════
@router.message(CommandStart())
async def cmd_start(msg: Message, bot: Bot, state: FSMContext):
    await state.clear()
    db.upsert_user(msg.from_user.id, msg.from_user.username, msg.from_user.full_name)
    if not await check_subs(bot, msg.from_user.id):
        await msg.answer(
            "👋 Привет! Я <b>ПиарБиржа</b> — бесплатная биржа взаимопиара для владельцев Telegram-каналов.\n\n"
            "🔒 Для доступа подпишись на оба канала:",
            reply_markup=subscribe_kb(), parse_mode="HTML"
        )
        return
    await msg.answer(
        "🤝 <b>ПиарБиржа</b> — найди партнёра для взаимопиара бесплатно!\n\nВыбери действие:",
        reply_markup=main_menu_kb(), parse_mode="HTML"
    )


@router.callback_query(F.data == "check_sub")
async def check_sub_cb(cb: CallbackQuery, bot: Bot):
    if not await check_subs(bot, cb.from_user.id):
        await cb.answer("❌ Ты ещё не подписан на все каналы!", show_alert=True)
        return
    await cb.message.edit_text(
        "✅ Отлично! Добро пожаловать в <b>ПиарБиржу</b>!\n\nВыбери действие:",
        reply_markup=main_menu_kb(), parse_mode="HTML"
    )


@router.callback_query(F.data == "back_main")
async def back_main(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("🏠 Главное меню:", reply_markup=main_menu_kb())


# ══════════════════════════════════════════════
#  МОЙ КАНАЛ
# ══════════════════════════════════════════════
@router.callback_query(F.data == "my_channel")
async def my_channel(cb: CallbackQuery):
    ch = db.get_channel_by_owner(cb.from_user.id)
    if ch:
        await cb.message.edit_text(
            f"📋 <b>Твой канал:</b>\n\n{fmt_channel(ch)}",
            reply_markup=my_channel_kb(True), parse_mode="HTML"
        )
    else:
        await cb.message.edit_text(
            "📋 У тебя ещё нет зарегистрированного канала.\n\nДобавь канал чтобы находить партнёров!",
            reply_markup=my_channel_kb(False)
        )


# ── Регистрация канала ────────────────────────
@router.callback_query(F.data == "reg_channel")
async def reg_channel_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(RegChannel.title)
    await cb.message.edit_text("✏️ <b>Шаг 1/5</b> — Введи название своего канала:", parse_mode="HTML")


@router.message(RegChannel.title)
async def reg_title(msg: Message, state: FSMContext):
    await state.update_data(title=msg.text)
    await state.set_state(RegChannel.link)
    await msg.answer("🔗 <b>Шаг 2/5</b> — Введи ссылку на канал (например @mychannel или https://t.me/mychannel):", parse_mode="HTML")


@router.message(RegChannel.link)
async def reg_link(msg: Message, state: FSMContext):
    link = msg.text.strip()
    if not link.startswith("@") and not link.startswith("https://"):
        await msg.answer("⚠️ Неверный формат. Введи @username или https://t.me/username")
        return
    await state.update_data(link=link)
    await state.set_state(RegChannel.topic)
    await msg.answer("🏷 <b>Шаг 3/5</b> — Выбери тематику канала:", reply_markup=topics_kb(), parse_mode="HTML")


@router.callback_query(F.data.startswith("reg_topic:"))
async def reg_topic(cb: CallbackQuery, state: FSMContext):
    topic = cb.data.split(":", 1)[1]
    await state.update_data(topic=topic)
    await state.set_state(RegChannel.subscribers)
    await cb.message.edit_text("👥 <b>Шаг 4/5</b> — Сколько подписчиков на канале?", reply_markup=sub_ranges_kb(), parse_mode="HTML")


@router.callback_query(F.data.startswith("reg_subs:"))
async def reg_subs(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    subs = int(parts[1])
    await state.update_data(subscribers=subs)
    await state.set_state(RegChannel.description)
    await cb.message.edit_text("📝 <b>Шаг 5/5</b> — Напиши краткое описание канала (2-3 предложения):", parse_mode="HTML")


@router.message(RegChannel.description)
async def reg_description(msg: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    cid = db.create_channel(
        msg.from_user.id, data["title"], data["link"],
        data["topic"], data["subscribers"], msg.text
    )
    ch = db.get_channel_by_id(cid)
    await msg.answer(
        f"✅ <b>Канал зарегистрирован!</b>\n\n{fmt_channel(ch)}\n\n🔍 Теперь можешь искать партнёров!",
        reply_markup=main_menu_kb(), parse_mode="HTML"
    )


# ── Редактирование канала ─────────────────────
@router.callback_query(F.data == "edit_channel")
async def edit_channel_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(EditChannel.title)
    ch = db.get_channel_by_owner(cb.from_user.id)
    await cb.message.edit_text(
        f"✏️ <b>Редактирование</b>\n\nТекущее название: <b>{ch[2]}</b>\n\nВведи новое название (или отправь «-» чтобы оставить текущее):",
        parse_mode="HTML"
    )


@router.message(EditChannel.title)
async def edit_title(msg: Message, state: FSMContext):
    ch = db.get_channel_by_owner(msg.from_user.id)
    title = ch[2] if msg.text.strip() == "-" else msg.text.strip()
    await state.update_data(title=title, old_link=ch[3], old_topic=ch[4], old_subs=ch[5], old_desc=ch[6], ch_id=ch[0])
    await state.set_state(EditChannel.link)
    await msg.answer(f"🔗 Текущая ссылка: <b>{ch[3]}</b>\n\nВведи новую (или «-»):", parse_mode="HTML")


@router.message(EditChannel.link)
async def edit_link(msg: Message, state: FSMContext):
    data = await state.get_data()
    link = data["old_link"] if msg.text.strip() == "-" else msg.text.strip()
    await state.update_data(link=link)
    await state.set_state(EditChannel.topic)
    await msg.answer("🏷 Выбери новую тематику:", reply_markup=topics_kb(prefix="edit_topic"))


@router.callback_query(F.data.startswith("edit_topic:"))
async def edit_topic(cb: CallbackQuery, state: FSMContext):
    topic = cb.data.split(":", 1)[1]
    await state.update_data(topic=topic)
    await state.set_state(EditChannel.subscribers)
    await cb.message.edit_text("👥 Выбери новый диапазон подписчиков:", reply_markup=sub_ranges_kb(prefix="edit_subs"))


@router.callback_query(F.data.startswith("edit_subs:"))
async def edit_subs(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    await state.update_data(subscribers=int(parts[1]))
    await state.set_state(EditChannel.description)
    await cb.message.edit_text("📝 Введи новое описание (или «-» чтобы оставить текущее):")


@router.message(EditChannel.description)
async def edit_description(msg: Message, state: FSMContext):
    data = await state.get_data()
    desc = data["old_desc"] if msg.text.strip() == "-" else msg.text.strip()
    db.update_channel(data["ch_id"], data["title"], data["link"], data["topic"], data["subscribers"], desc)
    await state.clear()
    ch = db.get_channel_by_id(data["ch_id"])
    await msg.answer(f"✅ Канал обновлён!\n\n{fmt_channel(ch)}", reply_markup=main_menu_kb(), parse_mode="HTML")


# ══════════════════════════════════════════════
#  ПОИСК ПАРТНЁРОВ
# ══════════════════════════════════════════════
@router.callback_query(F.data == "search")
async def search_start(cb: CallbackQuery):
    ch = db.get_channel_by_owner(cb.from_user.id)
    if not ch:
        await cb.answer("⚠️ Сначала зарегистрируй свой канал!", show_alert=True)
        return
    await cb.message.edit_text("🔍 Ищем по тематике твоего канала или выбери другую:", reply_markup=topics_kb(prefix="search_topic"))


@router.callback_query(F.data.startswith("search_topic:"))
async def search_by_topic(cb: CallbackQuery):
    topic = cb.data.split(":", 1)[1]
    my_ch = db.get_channel_by_owner(cb.from_user.id)
    subs = my_ch[5] if my_ch else 0
    min_s = max(0, int(subs * 0.3))
    max_s = int(subs * 3) + 1000
    results = db.search_channels(topic, min_s, max_s, cb.from_user.id)
    if not results:
        await cb.message.edit_text(
            f"😔 По теме <b>{topic}</b> партнёров пока нет.\n\nПопробуй другую тематику:",
            reply_markup=topics_kb(prefix="search_topic"), parse_mode="HTML"
        )
        return
    ch = results[0]
    await cb.message.edit_text(
        f"🔍 Найдено <b>{len(results)}</b> партнёров по теме {topic}\n\n{fmt_channel(ch)}",
        reply_markup=channel_card_kb(ch[0]), parse_mode="HTML"
    )


# ══════════════════════════════════════════════
#  ПРЕДЛОЖИТЬ ПИАР
# ══════════════════════════════════════════════
@router.callback_query(F.data.startswith("offer:"))
async def offer_piar(cb: CallbackQuery, bot: Bot):
    target_ch_id = int(cb.data.split(":")[1])
    my_ch = db.get_channel_by_owner(cb.from_user.id)
    if not my_ch:
        await cb.answer("⚠️ Сначала зарегистрируй свой канал!", show_alert=True)
        return
    target_ch = db.get_channel_by_id(target_ch_id)
    if not target_ch:
        await cb.answer("❌ Канал не найден", show_alert=True)
        return
    # Check existing deal
    existing = db.get_active_deal(my_ch[0], target_ch_id)
    if existing:
        await cb.answer("⚠️ У вас уже есть активные переговоры с этим каналом!", show_alert=True)
        return
    deal_id = db.create_deal(my_ch[0], target_ch_id)
    # Notify target owner
    try:
        await bot.send_message(
            target_ch[1],
            f"🤝 <b>Новое предложение о пиаре!</b>\n\n"
            f"Канал <b>{my_ch[2]}</b> хочет сделать с тобой взаимопиар.\n\n"
            f"{fmt_channel(my_ch)}",
            reply_markup=deal_kb(deal_id, is_receiver=True), parse_mode="HTML"
        )
    except Exception:
        pass
    await cb.message.edit_text(
        f"✅ Предложение отправлено каналу <b>{target_ch[2]}</b>!\n\n"
        f"Ожидай ответа. Уведомление придёт сразу.",
        reply_markup=main_menu_kb(), parse_mode="HTML"
    )


# ══════════════════════════════════════════════
#  МОИ ПЕРЕГОВОРЫ
# ══════════════════════════════════════════════
@router.callback_query(F.data == "my_deals")
async def my_deals(cb: CallbackQuery):
    my_ch = db.get_channel_by_owner(cb.from_user.id)
    if not my_ch:
        await cb.answer("⚠️ Сначала зарегистрируй свой канал!", show_alert=True)
        return
    deals = db.get_user_deals(my_ch[0])
    if not deals:
        await cb.message.edit_text("💬 У тебя пока нет переговоров.\n\nНайди партнёра!", reply_markup=main_menu_kb())
        return
    status_icons = {"pending": "⏳", "active": "💬", "completed": "✅", "declined": "❌"}
    lines = []
    for d in deals:
        icon = status_icons.get(d[3], "❓")
        partner_title = d[7] if d[1] != my_ch[0] else d[9]
        lines.append(f"{icon} <b>{partner_title}</b> — {d[3]}")
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for d in deals[:8]:
        icon = status_icons.get(d[3], "❓")
        partner_title = d[7] if d[1] != my_ch[0] else d[9]
        buttons.append([InlineKeyboardButton(text=f"{icon} {partner_title}", callback_data=f"view_deal:{d[0]}")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")])
    await cb.message.edit_text(
        "💬 <b>Мои переговоры:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("view_deal:"))
async def view_deal(cb: CallbackQuery):
    deal_id = int(cb.data.split(":")[1])
    deal = db.get_deal(deal_id)
    if not deal:
        await cb.answer("❌ Сделка не найдена", show_alert=True)
        return
    my_ch = db.get_channel_by_owner(cb.from_user.id)
    is_receiver = deal[2] == (my_ch[0] if my_ch else -1)
    from_ch = db.get_channel_by_id(deal[1])
    to_ch = db.get_channel_by_id(deal[2])
    msgs = db.get_messages(deal_id)
    chat_text = ""
    if msgs:
        chat_text = "\n\n💬 <b>Переписка:</b>\n"
        for m in msgs[-5:]:
            who = "Ты" if m[2] == cb.from_user.id else "Партнёр"
            chat_text += f"<b>{who}:</b> {m[3]}\n"
    await cb.message.edit_text(
        f"🤝 <b>Переговоры</b>\n\n"
        f"📤 {from_ch[2] if from_ch else '?'} → 📥 {to_ch[2] if to_ch else '?'}\n"
        f"Статус: {deal[3]}"
        f"{chat_text}",
        reply_markup=deal_kb(deal_id, is_receiver=is_receiver and deal[3] == "pending"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("deal_accept:"))
async def deal_accept(cb: CallbackQuery, bot: Bot):
    deal_id = int(cb.data.split(":")[1])
    db.activate_deal(deal_id)
    deal = db.get_deal(deal_id)
    from_ch = db.get_channel_by_id(deal[1])
    try:
        await bot.send_message(
            from_ch[1],
            f"🎉 <b>Предложение принято!</b>\n\nКанал <b>{db.get_channel_by_id(deal[2])[2]}</b> принял твоё предложение о пиаре!\n\nНачинайте договариваться 👇",
            reply_markup=deal_kb(deal_id), parse_mode="HTML"
        )
    except Exception:
        pass
    await cb.message.edit_text(
        "✅ Ты принял предложение! Начинайте договариваться:",
        reply_markup=deal_kb(deal_id), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("deal_decline:"))
async def deal_decline(cb: CallbackQuery, bot: Bot):
    deal_id = int(cb.data.split(":")[1])
    db.decline_deal(deal_id)
    deal = db.get_deal(deal_id)
    from_ch = db.get_channel_by_id(deal[1])
    try:
        await bot.send_message(from_ch[1], "😔 Твоё предложение о пиаре было отклонено. Попробуй найти другого партнёра!", reply_markup=main_menu_kb())
    except Exception:
        pass
    await cb.message.edit_text("❌ Предложение отклонено.", reply_markup=main_menu_kb())


# ── Чат внутри переговоров ────────────────────
@router.callback_query(F.data.startswith("deal_chat:"))
async def deal_chat_start(cb: CallbackQuery, state: FSMContext):
    deal_id = int(cb.data.split(":")[1])
    await state.set_state(ChatState.writing)
    await state.update_data(deal_id=deal_id)
    await cb.message.answer("✍️ Напиши сообщение партнёру:")


@router.message(ChatState.writing)
async def deal_chat_send(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    deal_id = data["deal_id"]
    db.add_message(deal_id, msg.from_user.id, msg.text)
    await state.clear()
    deal = db.get_deal(deal_id)
    my_ch = db.get_channel_by_owner(msg.from_user.id)
    other_owner = get_other_owner(deal, my_ch[0] if my_ch else -1)
    if other_owner:
        try:
            await bot.send_message(
                other_owner,
                f"💬 <b>Новое сообщение</b>\n\nОт: <b>{my_ch[2] if my_ch else 'Партнёр'}</b>\n\n{msg.text}",
                reply_markup=deal_kb(deal_id), parse_mode="HTML"
            )
        except Exception:
            pass
    await msg.answer("✅ Сообщение отправлено!", reply_markup=deal_kb(deal_id))


# ── Пиар состоялся ────────────────────────────
@router.callback_query(F.data.startswith("deal_done:"))
async def deal_done(cb: CallbackQuery, bot: Bot):
    deal_id = int(cb.data.split(":")[1])
    deal = db.get_deal(deal_id)
    if deal[3] == "completed":
        await cb.answer("✅ Пиар уже отмечен как завершённый!", show_alert=True)
        return
    db.complete_deal(deal_id)
    my_ch = db.get_channel_by_owner(cb.from_user.id)
    other_owner = get_other_owner(deal, my_ch[0] if my_ch else -1)
    if other_owner:
        try:
            await bot.send_message(
                other_owner,
                f"🏆 Пиар с каналом <b>{my_ch[2] if my_ch else '?'}</b> отмечен как завершённый!\n\nОставь отзыв:",
                reply_markup=stars_kb(deal_id), parse_mode="HTML"
            )
        except Exception:
            pass
    await cb.message.edit_text(
        "🏆 Отлично! Пиар завершён! Оставь оценку партнёру:",
        reply_markup=stars_kb(deal_id)
    )


@router.callback_query(F.data.startswith("stars:"))
async def stars_cb(cb: CallbackQuery, state: FSMContext):
    _, deal_id_s, stars_s = cb.data.split(":")
    await state.set_state(ReviewState.comment)
    await state.update_data(deal_id=int(deal_id_s), stars=int(stars_s))
    await cb.message.edit_text(f"{'⭐️' * int(stars_s)} Напиши короткий отзыв о партнёре (или отправь «-» чтобы пропустить):")


@router.message(ReviewState.comment)
async def review_comment(msg: Message, state: FSMContext):
    data = await state.get_data()
    comment = "" if msg.text.strip() == "-" else msg.text.strip()
    db.add_review(data["deal_id"], msg.from_user.id, data["stars"], comment)
    await state.clear()
    await msg.answer("✅ Отзыв сохранён! Спасибо!", reply_markup=main_menu_kb())


# ══════════════════════════════════════════════
#  РЕЙТИНГ
# ══════════════════════════════════════════════
@router.callback_query(F.data == "rating")
async def rating_cb(cb: CallbackQuery):
    top = db.get_top_channels(10)
    if not top:
        await cb.message.edit_text("😔 Каналов пока нет. Зарегистрируй первым!", reply_markup=back_main_kb())
        return
    lines = ["🏆 <b>Топ-10 каналов ПиарБиржи:</b>\n"]
    medals = ["🥇", "🥈", "🥉"] + ["4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    for i, ch in enumerate(top):
        lines.append(f"{medals[i]} <b>{ch[2]}</b> {ch[3]}\n   {fmt_stars(ch[7])} | 🤝 {ch[8]} пиаров | 👥 {ch[5]:,}")
    await cb.message.edit_text("\n".join(lines), reply_markup=back_main_kb(), parse_mode="HTML")


# ══════════════════════════════════════════════
#  ИСТОРИЯ ПИАРОВ
# ══════════════════════════════════════════════
@router.callback_query(F.data == "history")
async def history_cb(cb: CallbackQuery):
    my_ch = db.get_channel_by_owner(cb.from_user.id)
    if not my_ch:
        await cb.answer("⚠️ Сначала зарегистрируй канал!", show_alert=True)
        return
    deals = db.get_user_deals(my_ch[0])
    completed = [d for d in deals if d[3] == "completed"]
    if not completed:
        await cb.message.edit_text("📊 У тебя пока нет завершённых пиаров.", reply_markup=back_main_kb())
        return
    lines = [f"📊 <b>История пиаров ({len(completed)}):</b>\n"]
    for d in completed[:10]:
        partner = d[7] if d[1] != my_ch[0] else d[9]
        date = d[5][:10] if d[5] else d[4][:10]
        lines.append(f"✅ <b>{partner}</b> — {date}")
    await cb.message.edit_text("\n".join(lines), reply_markup=back_main_kb(), parse_mode="HTML")


# ══════════════════════════════════════════════
#  АДМИН
# ══════════════════════════════════════════════
@router.message(Command("admin"))
async def admin_panel(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    users = db.fetchall("SELECT COUNT(*) FROM users")[0][0]
    channels = db.fetchall("SELECT COUNT(*) FROM channels")[0][0]
    deals = db.fetchall("SELECT COUNT(*) FROM deals")[0][0]
    completed = db.fetchall("SELECT COUNT(*) FROM deals WHERE status='completed'")[0][0]
    await msg.answer(
        f"👑 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: {users}\n"
        f"📢 Каналов: {channels}\n"
        f"🤝 Переговоров: {deals}\n"
        f"✅ Завершённых пиаров: {completed}",
        parse_mode="HTML"
    )
