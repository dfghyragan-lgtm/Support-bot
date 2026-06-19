import logging
from datetime import datetime, time, timedelta, timezone
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, JobQueue, CallbackQueryHandler
import json
import os
import random

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8240444405:AAEo_DpaFXmG-N6NbcOCW5PU2vqut9DRRnM"
MOSCOW_TZ = timezone(timedelta(hours=3))
ADMINS_FILE = "admins.json"
COMPLAINTS_FILE = "complaints.json"
MARRIAGES_FILE = "marriages.json"
CHATS_FILE = "active_chats.json"
CREATOR_ID = 8432323388
CHAT_ID = -1002753124436
EXAMPLE_APPLICATION = "https://t.me/c/2945439331/605"
APPLICATION_LINK = "https://t.me/+92SODWh2fc41NTdi"

def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(user_id):
    admins = load_json(ADMINS_FILE, [CREATOR_ID])
    return user_id in admins

# Приветствие новых участников
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        welcome_text = (
            f"👋 Добро пожаловать, {member.first_name}!\n\n"
            "📜 Правила чата:\n"
            "• Запрещён контент 18+\n"
            "• Запрещена реклама и ссылки\n"
            "• Запрещены оскорбления\n"
            "• Будь вежлив и уважай участников\n\n"
            "🎉 Судные выходные:\n"
            "Суббота 12:00 - Понедельник 6:00\n\n"
            "Приятного общения! 😊"
        )
        await update.message.reply_text(welcome_text)

# Фильтр ботов
async def filter_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    if update.effective_user and update.effective_user.is_bot:
        try:
            await update.message.delete()
        except:
            pass

# Фильтр 18+ и ссылок
async def message_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    if not update.message or not update.message.text:
        return
    
    message_text = update.message.text.lower()
    user_id = update.effective_user.id
    
    if is_admin(user_id) or user_id == CREATOR_ID:
        return
    
    nsfw_words = [
        "порно", "porn", "xxx", "секс", "sex", "член", "пизда", "хуй", "ебать",
        "шлюха", "интим", "минет", "анус", "мастурбация", "лесби", "гей",
        "транс", "фетиш", "бдсм", "оргия", "голые", "обнаженные", "эротика",
        "изнасилование", "18+", "18 +", "для взрослых", "adult", "жесткое",
        "трах", "трахать", "отсос", "кончил", "сперма", "влагалище",
        "клитор", "соски", "сиськи", "голая", "голый", "нюдс", "nudes",
        "nude", "слив", "сливы", "приват", "приваты", "onlyfans", "only fans"
    ]
    
    for word in nsfw_words:
        if word in message_text:
            try:
                await update.message.delete()
                await context.bot.restrict_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=datetime.now() + timedelta(hours=3)
                )
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"🚫 {update.effective_user.first_name} получил мут на 3 часа за контент 18+!"
                )
            except:
                pass
            return
    
    if any(x in message_text for x in ["http://", "https://", "t.me/"]):
        try:
            chat_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            if chat_member.status in ['administrator', 'creator']:
                return
        except:
            pass
        try:
            await update.message.delete()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🚫 {update.effective_user.first_name}, ссылки запрещены! Сообщение удалено."
            )
        except:
            pass

# Старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        keyboard = [[InlineKeyboardButton("🆘 Поддержка", callback_data="support")]]
        await update.message.reply_text(
            "👋 Привет! Я бот-помощник чата.\n\n"
            "Если у вас есть жалоба или вопрос — нажмите кнопку «Поддержка».",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await help_command(update, context)

# Кнопка поддержки
async def support_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "support":
        await query.message.reply_text("📝 Напишите ваше сообщение. Администраторы увидят его и ответят.")
        context.user_data['waiting_for_complaint'] = True

# Кнопки админа для жалоб
async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_admin(user_id) and user_id != CREATOR_ID:
        await query.message.reply_text("❌ У вас нет прав!")
        return
    
    data = query.data
    complaints = load_json(COMPLAINTS_FILE, {})
    
    if data.startswith("take_"):
        complaint_id = data.replace("take_", "")
        if complaint_id in complaints and complaints[complaint_id]["status"] == "open":
            complaints[complaint_id]["status"] = "in_progress"
            complaints[complaint_id]["admin_id"] = user_id
            save_json(COMPLAINTS_FILE, complaints)
            
            chats = load_json(CHATS_FILE, {})
            chats[str(complaints[complaint_id]["user_id"])] = complaint_id
            chats[str(user_id)] = complaint_id
            save_json(CHATS_FILE, chats)
            
            try:
                await context.bot.send_message(
                    chat_id=complaints[complaint_id]["user_id"],
                    text="✅ Администратор взял обращение в работу. Пишите ваш вопрос."
                )
            except:
                pass
            
            new_keyboard = [[InlineKeyboardButton("✅ Завершить", callback_data=f"close_{complaint_id}")]]
            await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(new_keyboard))
    
    elif data.startswith("close_"):
        complaint_id = data.replace("close_", "")
        if complaint_id in complaints:
            user_complaint_id = complaints[complaint_id]["user_id"]
            admin_id = complaints[complaint_id].get("admin_id", "")
            complaints[complaint_id]["status"] = "closed"
            save_json(COMPLAINTS_FILE, complaints)
            
            chats = load_json(CHATS_FILE, {})
            if str(user_complaint_id) in chats:
                del chats[str(user_complaint_id)]
            if str(admin_id) in chats:
                del chats[str(admin_id)]
            save_json(CHATS_FILE, chats)
            
            try:
                await context.bot.send_message(
                    chat_id=user_complaint_id,
                    text="✅ Ваше обращение рассмотрено и закрыто. Спасибо!"
                )
            except:
                pass
            await query.message.edit_reply_markup(reply_markup=None)

# Кнопки админ-меню
async def admin_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id) and query.from_user.id != CREATOR_ID:
        return
    
    responses = {
        "admin_ban": "Для бана ответьте на сообщение и напишите: Бан [время]",
        "admin_mute": "Для мута ответьте на сообщение и напишите: Мут [время]",
        "admin_warn": "Для предупреждения ответьте на сообщение и напишите: Пред [причина]",
        "admin_unban": "Для разбана ответьте на сообщение и напишите: Разбан",
        "admin_unmute": "Для размута ответьте на сообщение и напишите: Размут",
        "admin_clear": "Для очистки напишите: Очистка [количество]"
    }
    
    if query.data in responses:
        await query.message.reply_text(responses[query.data])

# Админ-панель
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) and update.effective_user.id != CREATOR_ID:
        await update.message.reply_text("❌ У вас нет прав!")
        return
    
    keyboard = [
        [InlineKeyboardButton("🚫 Бан", callback_data="admin_ban"),
         InlineKeyboardButton("🔇 Мут", callback_data="admin_mute")],
        [InlineKeyboardButton("⚠️ Пред", callback_data="admin_warn"),
         InlineKeyboardButton("✅ Разбан", callback_data="admin_unban")],
        [InlineKeyboardButton("🔊 Размут", callback_data="admin_unmute"),
         InlineKeyboardButton("🧹 Очистка", callback_data="admin_clear")]
    ]
    await update.message.reply_text(
        "👮 АДМИН-ПАНЕЛЬ\n\nВыберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Очистка сообщений
async def clear_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) and update.effective_user.id != CREATOR_ID:
        await update.message.reply_text("❌ У вас нет прав!")
        return
    
    count = 10
    if context.args and context.args[0].isdigit():
        count = int(context.args[0])
    
    try:
        messages = []
        async for msg in context.bot.get_chat_history(update.effective_chat.id, limit=count + 1):
            messages.append(msg.message_id)
        
        deleted = 0
        for msg_id in messages:
            try:
                await context.bot.delete_message(update.effective_chat.id, msg_id)
                deleted += 1
            except:
                pass
        
        await update.message.reply_text(f"🧹 Удалено {deleted} сообщений!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# ЛС обработчик
async def private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    
    user_id = update.effective_user.id
    message_text = update.message.text
    user_data = context.user_data
    
    # Если пользователь ждёт отправки жалобы
    if user_data.get('waiting_for_complaint'):
        complaints = load_json(COMPLAINTS_FILE, {})
        complaint_id = str(len(complaints) + 1)
        complaints[complaint_id] = {
            "user_id": user_id,
            "username": update.effective_user.first_name,
            "text": message_text,
            "status": "open",
            "admin_id": None
        }
        save_json(COMPLAINTS_FILE, complaints)
        await update.message.reply_text("✅ Ваше обращение отправлено администраторам. Ожидайте ответа.")
        user_data['waiting_for_complaint'] = False
        
        admins = load_json(ADMINS_FILE, [CREATOR_ID])
        keyboard = [[InlineKeyboardButton("🔧 Заняться", callback_data=f"take_{complaint_id}")]]
        
        for admin_id in admins:
            if admin_id != user_id:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"📩 НОВОЕ ОБРАЩЕНИЕ #{complaint_id}\n\nОт: {update.effective_user.first_name}\nID: {user_id}\n\nТекст: {message_text}",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except:
                    pass
        return
    
    # Переписка админ-пользователь
    chats = load_json(CHATS_FILE, {})
    user_id_str = str(user_id)
    
    if user_id_str in chats:
        complaints = load_json(COMPLAINTS_FILE, {})
        complaint_id = chats[user_id_str]
        
        if complaint_id in complaints and complaints[complaint_id]["status"] == "in_progress":
            if is_admin(user_id) or user_id == CREATOR_ID:
                target_id = complaints[complaint_id]["user_id"]
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=f"📩 Администратор:\n{message_text}"
                    )
                except:
                    pass
            else:
                admin_id = complaints[complaint_id].get("admin_id")
                if admin_id:
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=f"📩 {update.effective_user.first_name}:\n{message_text}"
                        )
                    except:
                        pass
            return
    
    # Обычное сообщение
    if not (is_admin(user_id) or user_id == CREATOR_ID):
        keyboard = [[InlineKeyboardButton("🆘 Поддержка", callback_data="support")]]
        await update.message.reply_text(
            "Нажмите кнопку «Поддержка» чтобы написать администраторам.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
# Бан
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    user = update.message.reply_to_message.from_user
    if user.id == CREATOR_ID:
        await update.message.reply_text("❌ Нельзя забанить создателя!")
        return
    if is_admin(user.id) and update.effective_user.id != CREATOR_ID:
        await update.message.reply_text("❌ Нельзя забанить другого администратора!")
        return
    
    ban_time = 0
    if context.args:
        try:
            if len(context.args) == 1 and context.args[0].isdigit():
                ban_time = int(context.args[0])
            elif len(context.args) >= 2:
                num = int(context.args[0])
                unit = context.args[1].lower()
                if unit in ["м", "мин", "минута", "минуты", "минут"]:
                    ban_time = num
                elif unit in ["ч", "час", "часа", "часов"]:
                    ban_time = num * 60
                elif unit in ["д", "день", "дня", "дней"]:
                    ban_time = num * 1440
                elif unit in ["н", "нед", "неделя", "недели", "недель"]:
                    ban_time = num * 10080
                else:
                    ban_time = num
        except:
            pass
    
    try:
        if ban_time > 0:
            until_date = datetime.now() + timedelta(minutes=ban_time)
            await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=user.id,
                until_date=until_date
            )
            if ban_time >= 10080:
                t = f"{ban_time // 10080} недель"
            elif ban_time >= 1440:
                t = f"{ban_time // 1440} дней"
            elif ban_time >= 60:
                t = f"{ban_time // 60} часов"
            else:
                t = f"{ban_time} минут"
            await update.message.reply_text(f"🚫 {user.first_name} забанен на {t}!")
        else:
            await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=user.id
            )
            await update.message.reply_text(f"🚫 {user.first_name} забанен навсегда!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# Разбан
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    user = update.message.reply_to_message.from_user
    try:
        await context.bot.unban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user.id
        )
        await update.message.reply_text(f"✅ {user.first_name} разбанен!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# Мут
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    user = update.message.reply_to_message.from_user
    if user.id == CREATOR_ID:
        await update.message.reply_text("❌ Нельзя замутить создателя!")
        return
    if is_admin(user.id) and update.effective_user.id != CREATOR_ID:
        await update.message.reply_text("❌ Нельзя замутить другого администратора!")
        return
    
    mute_time = 60
    if context.args:
        try:
            if len(context.args) == 1 and context.args[0].isdigit():
                mute_time = int(context.args[0])
            elif len(context.args) >= 2:
                num = int(context.args[0])
                unit = context.args[1].lower()
                if unit in ["м", "мин", "минута", "минуты", "минут"]:
                    mute_time = num
                elif unit in ["ч", "час", "часа", "часов"]:
                    mute_time = num * 60
                elif unit in ["д", "день", "дня", "дней"]:
                    mute_time = num * 1440
                elif unit in ["н", "нед", "неделя", "недели", "недель"]:
                    mute_time = num * 10080
                else:
                    mute_time = num
        except:
            pass
    
    if mute_time >= 10080:
        t = f"{mute_time // 10080} недель"
    elif mute_time >= 1440:
        t = f"{mute_time // 1440} дней"
    elif mute_time >= 60:
        t = f"{mute_time // 60} часов"
    else:
        t = f"{mute_time} минут"
    
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=datetime.now() + timedelta(minutes=mute_time)
        )
        await update.message.reply_text(f"🔇 {user.first_name} замучен на {t}!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# Размут
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    user = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )
        )
        await update.message.reply_text(f"🔊 {user.first_name} размучен!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# Предупреждение
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    user = update.message.reply_to_message.from_user
    reason = " ".join(context.args) if context.args else "Нарушение правил"
    
    await update.message.reply_text(
        f"⚠️ ПРЕДУПРЕЖДЕНИЕ\n\n"
        f"Пользователь: @{user.username or user.first_name}\n"
        f"Причина: {reason}\n\n"
        f"При повторных нарушениях — бан!"
    )

# Брак
async def marry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    from_user = update.effective_user
    to_user = update.message.reply_to_message.from_user
    
    if from_user.id == to_user.id:
        await update.message.reply_text("❌ Нельзя жениться на себе!")
        return
    
    marriages = load_json(MARRIAGES_FILE, {})
    
    if str(from_user.id) in marriages:
        await update.message.reply_text(f"❌ Вы уже в браке с {marriages[str(from_user.id)]['name']}! Используйте Развод.")
        return
    if str(to_user.id) in marriages:
        await update.message.reply_text(f"❌ {to_user.first_name} уже в браке!")
        return
    
    marriages[str(from_user.id)] = {"partner_id": to_user.id, "name": to_user.first_name}
    marriages[str(to_user.id)] = {"partner_id": from_user.id, "name": from_user.first_name}
    save_json(MARRIAGES_FILE, marriages)
    
    await update.message.reply_text(
        f"💒 {from_user.first_name} и {to_user.first_name} теперь в браке!\n"
        f"Поздравляем! 🎉💍"
    )

# Развод
async def divorce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    marriages = load_json(MARRIAGES_FILE, {})
    
    if str(user.id) not in marriages:
        await update.message.reply_text("❌ Вы не в браке!")
        return
    
    partner_id = marriages[str(user.id)]["partner_id"]
    partner_name = marriages[str(user.id)]["name"]
    
    del marriages[str(user.id)]
    if str(partner_id) in marriages:
        del marriages[str(partner_id)]
    save_json(MARRIAGES_FILE, marriages)
    
    await update.message.reply_text(f"💔 {user.first_name} развёлся с {partner_name} 😢")

# Семья
async def marriage_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    marriages = load_json(MARRIAGES_FILE, {})
    
    if str(user.id) in marriages:
        await update.message.reply_text(f"💍 Вы в браке с {marriages[str(user.id)]['name']}")
    else:
        await update.message.reply_text("💔 Вы не в браке")

# Обнять
async def hug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    from_user = update.effective_user
    to_user = update.message.reply_to_message.from_user
    
    gifs = [
        "https://media.giphy.com/media/od5H3PmEG4EVq/giphy.gif",
        "https://media.giphy.com/media/ZQN9jsRWp1M76/giphy.gif",
        "https://media.giphy.com/media/wnsgren9NtITS/giphy.gif",
        "https://media.giphy.com/media/l2QDM9Jnim1YVILXa/giphy.gif",
        "https://media.giphy.com/media/3o7TKO3AC9oZqVbNQQ/giphy.gif"
    ]
    
    await update.message.reply_animation(
        animation=random.choice(gifs),
        caption=f"🫂 {from_user.first_name} обнял(а) {to_user.first_name}!"
    )

# Поцеловать
async def kiss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    from_user = update.effective_user
    to_user = update.message.reply_to_message.from_user
    
    gifs = [
        "https://media.giphy.com/media/G3va31oEEnIkM/giphy.gif",
        "https://media.giphy.com/media/12VXIxKaIEarL2/giphy.gif",
        "https://media.giphy.com/media/jR22gdcPiOLaE/giphy.gif",
        "https://media.giphy.com/media/bm2O3nXTcKJeU/giphy.gif",
        "https://media.giphy.com/media/nyGFcsP0kAobm/giphy.gif"
    ]
    
    await update.message.reply_animation(
        animation=random.choice(gifs),
        caption=f"💋 {from_user.first_name} поцеловал(а) {to_user.first_name}!"
    )

# Укусить
async def bite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    from_user = update.effective_user
    to_user = update.message.reply_to_message.from_user
    
    gifs = [
        "https://media.giphy.com/media/l4FGH2AqGg0O4LTkA/giphy.gif",
        "https://media.giphy.com/media/3o7TKqoVPf7K1M8T9K/giphy.gif",
        "https://media.giphy.com/media/xT0BKnZ6dO6FCxDtBK/giphy.gif",
        "https://media.giphy.com/media/3o7TKDx2DvzF3qK6M8/giphy.gif",
        "https://media.giphy.com/media/3o7TKCUvD4HWzUZ3LW/giphy.gif"
    ]
    
    await update.message.reply_animation(
        animation=random.choice(gifs),
        caption=f"🦷 {from_user.first_name} укусил(а) {to_user.first_name}!"
    )
# Судные выходные
async def send_weekend_message(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    weekend_text = (
        "🎉 СУДНЫЕ ВЫХОДНЫЕ! 🎉\n\n"
        "Простыми словами можно делать всё что угодно, кроме:\n"
        "❌ Вреда чату\n"
        "❌ Порнографии\n"
        "❌ Насилия\n"
        "❌ Расчленёнки\n"
        "❌ Рекламы\n\n"
        "⏰ Начинается: Суббота 12:00\n"
        "⏰ Заканчивается: Понедельник 6:00\n\n"
        "🔥 Время веселья началось! 🔥"
    )
    await context.bot.send_photo(
        chat_id=chat_id,
        photo="https://photos.app.goo.gl/1Zw5wMqT7nmZZAtq6",
        caption=weekend_text
    )

# Планирование судных выходных
async def schedule_weekend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав!")
        return
    
    chat_id = update.effective_chat.id
    current_jobs = context.job_queue.jobs()
    for job in current_jobs:
        if job.name and job.name.startswith(f"weekend_{chat_id}"):
            job.schedule_removal()
    
    context.job_queue.run_daily(
        send_weekend_message,
        time=time(hour=12, minute=0, tzinfo=MOSCOW_TZ),
        days=(5,),
        chat_id=chat_id,
        name=f"weekend_{chat_id}_sat"
    )
    context.job_queue.run_daily(
        send_weekend_message,
        time=time(hour=12, minute=0, tzinfo=MOSCOW_TZ),
        days=(6,),
        chat_id=chat_id,
        name=f"weekend_{chat_id}_sun"
    )
    await update.message.reply_text("✅ Судные выходные запланированы! Сообщения будут отправляться в субботу и воскресенье в 12:00 по Москве!")

# Набор в администрацию
async def admin_recruitment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📋 Пример анкеты", url=EXAMPLE_APPLICATION)],
        [InlineKeyboardButton("📝 Подать заявку", url=APPLICATION_LINK)]
    ]
    await update.message.reply_text(
        "👑 НАБОР В АДМИНИСТРАЦИЮ ЧАТА! 👑\n\n"
        "📋 Требования:\n"
        "• Возраст: 14+ лет\n"
        "• Активность в чате\n"
        "• Ответственность и адекватность\n"
        "• Готовность следить за порядком\n\n"
        "📸 Нажмите «Пример анкеты» чтобы посмотреть как оформлять заявку\n\n"
        "📝 Нажмите «Подать заявку» чтобы отправить анкету\n\n"
        "⚠️ Возрастные ограничения: 14+",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Помощь
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 КОМАНДЫ БОТА:\n\n"
        "👑 Для создателя:\n"
        "Админ — Выдать администратора (ответом на сообщение)\n\n"
        "👮 Для администраторов:\n"
        "Админка — Панель управления\n"
        "Бан [время] — Забанить (ответом на сообщение)\n"
        "Разбан — Разбанить (ответом на сообщение)\n"
        "Мут [время] — Замутить (ответом на сообщение)\n"
        "Размут — Размутить (ответом на сообщение)\n"
        "Пред [причина] — Предупреждение (ответом на сообщение)\n"
        "Очистка [число] — Удалить сообщения\n"
        "Выходные — Запланировать судные выходные\n\n"
        "⏰ Форматы времени:\n"
        "30, 30 минут, 2 часа, 1 день, 1 неделя\n"
        "Можно: м/мин, ч/час, д/день, н/нед\n\n"
        "🎉 Развлекательные команды (ответом на сообщение):\n"
        "Обнять, Поцеловать, Укусить\n"
        "Брак, Развод, Семья\n\n"
        "📢 Общие команды:\n"
        "Набор, Помощь, Правила, Старт\n\n"
        "🆘 В ЛС с ботом:\n"
        "Кнопка «Поддержка» — отправить жалобу/вопрос админам"
    )

# Правила
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🗓 ПРАВИЛА ЧАТА\n\n"
        "Добро пожаловать в чат! Мы рады всем новичкам.\n\n"
        "❌ Реклама любого вида без согласия владельца или заместителя — бан.\n\n"
        "❌ Контент 18+ в любом виде запрещён — предупреждение/мут 3 часа/бан.\n\n"
        "❌ Оскорбление администрации — мут 2 часа/бан.\n\n"
        "❌ Оскорбление религии и нации запрещено — мут 30 минут.\n\n"
        "❌ Спам и флуд — 2 предупреждения/мут 30 минут.\n\n"
        "❌ Попрошайничество админки, звёзд, подарков и тд. запрещено — мут 30 минут.\n\n"
        "❌ Обсуждение, оскорбление политики запрещено — предупреждение/мут 2 часа.\n\n"
        "❌ Шок-контент (смерть, призывы к смерти, убийство, самоубийство) — мут 4 часа/бан.\n\n"
        "❌ Оскорбление участников — 3 предупреждения/мут 1 час.\n\n"
        "❌ Провокации, троллинг — 3 предупреждения, мут 1 час.\n\n"
        "❌ Обход наказания — бан 24 часа.\n\n"
        "❌ Продажа игровых аккаунтов запрещена — 1 предупреждение/мут 3 часа.\n\n"
        "👮 ПРАВИЛА АДМИНИСТРАЦИИ:\n"
        "• Запрещено угрожать баном/мутом — 3 устных предупреждения/снятие.\n"
        "• Соблюдать субординацию во время общения с участниками.\n"
        "• При не соблюдении субординации, проявление агрессии, провокации — 4 предупреждение/снятие.\n\n"
        "🎉 СУДНЫЕ ВЫХОДНЫЕ:\n"
        "Суббота 12:00 - Понедельник 6:00\n"
        "Можно всё, кроме: вреда чату, порнографии, насилия, расчленёнки, рекламы\n\n"
        "Приятного общения! Будьте уважительны как к админам, так и к простым участникам и не нарушайте правила!"
    )

# Обработчик команд в чате
async def text_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    msg = update.message.text.lower().strip()
    
    # Команды без ответа
    if msg == "помощь":
        await help_command(update, context)
    elif msg == "правила":
        await rules(update, context)
    elif msg == "набор":
        await admin_recruitment(update, context)
    elif msg == "старт":
        await start(update, context)
    elif msg == "админка":
        await admin_panel(update, context)
    elif msg == "развод":
        await divorce(update, context)
    elif msg in ["семья", "моя семья"]:
        await marriage_info(update, context)
    elif msg.startswith("очистка"):
        context.args = msg.split()[1:] if len(msg.split()) > 1 else []
        await clear_messages(update, context)
    
    # Команды с ответом
    elif msg == "админ":
        await add_admin(update, context)
    elif msg.startswith("бан"):
        context.args = msg.split()[1:] if len(msg.split()) > 1 else []
        await ban(update, context)
    elif msg == "разбан":
        await unban(update, context)
    elif msg.startswith("мут"):
        context.args = msg.split()[1:] if len(msg.split()) > 1 else []
        await mute(update, context)
    elif msg == "размут":
        await unmute(update, context)
    elif msg.startswith("пред"):
        context.args = msg.split()[1:] if len(msg.split()) > 1 else []
        await warn(update, context)
    elif msg == "выходные":
        await schedule_weekend(update, context)
    elif msg == "обнять":
        await hug(update, context)
    elif msg == "поцеловать":
        await kiss(update, context)
    elif msg == "укусить":
        await bite(update, context)
    elif msg == "брак":
        await marry(update, context)

# Выдача админа
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != CREATOR_ID:
        await update.message.reply_text("❌ Только создатель бота может выдавать администраторов!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Используйте эту команду как ответ на сообщение пользователя!")
        return
    
    new_admin = update.message.reply_to_message.from_user
    admins = load_json(ADMINS_FILE, [CREATOR_ID])
    
    if new_admin.id in admins:
        await update.message.reply_text(f"❌ Пользователь {new_admin.first_name} уже является администратором!")
        return
    
    admins.append(new_admin.id)
    save_json(ADMINS_FILE, admins)
    await update.message.reply_text(f"✅ Пользователь {new_admin.first_name} теперь администратор и может использовать все команды бота!")

def main():
    application = Application.builder().token(TOKEN).build()
    
    # Автозапуск судных выходных
    application.job_queue.run_daily(
        send_weekend_message,
        time=time(hour=12, minute=0, tzinfo=MOSCOW_TZ),
        days=(5,),
        chat_id=CHAT_ID,
        name="weekend_sat_auto"
    )
    application.job_queue.run_daily(
        send_weekend_message,
        time=time(hour=12, minute=0, tzinfo=MOSCOW_TZ),
        days=(6,),
        chat_id=CHAT_ID,
        name="weekend_sun_auto"
    )
    
    # Обработчики
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("unmute", unmute))
    application.add_handler(CommandHandler("warn", warn))
    application.add_handler(CommandHandler("hug", hug))
    application.add_handler(CommandHandler("kiss", kiss))
    application.add_handler(CommandHandler("bite", bite))
    application.add_handler(CommandHandler("marry", marry))
    application.add_handler(CommandHandler("divorce", divorce))
    application.add_handler(CommandHandler("clear", clear_messages))
    application.add_handler(CommandHandler("admin", admin_recruitment))
    application.add_handler(CommandHandler("admin_panel", admin_panel))
    application.add_handler(CallbackQueryHandler(support_button, pattern="^support$"))
    application.add_handler(CallbackQueryHandler(admin_buttons, pattern="^(take_|close_)"))
    application.add_handler(CallbackQueryHandler(admin_menu_buttons, pattern="^admin_"))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, filter_bots), group=0)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.ChatType.PRIVATE, message_filter), group=1)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, private_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.ChatType.PRIVATE, text_commands), group=2)
    
    print("✅ Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
