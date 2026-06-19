import logging
from datetime import datetime, time, timedelta
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, JobQueue, CallbackQueryHandler
from datetime import timezone
import json
import os
import random

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = "8240444405:AAEo_DpaFXmG-N6NbcOCW5PU2vqut9DRRnM"

# Московское время
MOSCOW_TZ = timezone(timedelta(hours=3))

# Фото для набора в администрацию
ADMIN_PHOTO_URL = "https://photos.app.goo.gl/1Zw5wMqT7nmZZAtq6"

# Файл для хранения администраторов
ADMINS_FILE = "admins.json"

# Файл для хранения жалоб
COMPLAINTS_FILE = "complaints.json"

# Файл для хранения браков
MARRIAGES_FILE = "marriages.json"

# Создатель бота
CREATOR_ID = 8432323388

# ID чата
CHAT_ID = -1002753124436

# Ссылки
EXAMPLE_APPLICATION = "https://t.me/c/2945439331/605"
APPLICATION_LINK = "https://t.me/+92SODWh2fc41NTdi"

def load_admins():
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return [CREATOR_ID]

def save_admins(admins):
    with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
        json.dump(admins, f)

def is_admin(user_id):
    admins = load_admins()
    return user_id in admins

def load_complaints():
    if os.path.exists(COMPLAINTS_FILE):
        with open(COMPLAINTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_complaints(complaints):
    with open(COMPLAINTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(complaints, f, ensure_ascii=False, indent=2)

def load_marriages():
    if os.path.exists(MARRIAGES_FILE):
        with open(MARRIAGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_marriages(marriages):
    with open(MARRIAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(marriages, f, ensure_ascii=False, indent=2)

# Приветствие новых участников (как у Ириса)
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        
        welcome_text = f"""
👋 Добро пожаловать, {member.first_name}!

📜 У нас есть правила, пожалуйста ознакомься:
• Запрещён контент 18+
• Запрещена реклама и ссылки
• Запрещены оскорбления
• Будь вежлив и уважай участников

🎉 Судные выходные: Суббота 12:00 - Понедельник 6:00

Приятного общения! 😊
"""
        await update.message.reply_text(welcome_text)

# Фильтр ботов - удаление сообщений от других ботов
async def filter_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    user = update.effective_user
    if user.is_bot:
        try:
            await update.message.delete()
            logger.info(f"Удалено сообщение от бота @{user.username or user.first_name}")
        except:
            pass

# Фильтр 18+ и ссылок
async def message_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return
    
    message_text = update.message.text.lower() if update.message.text else ""
    user_id = update.effective_user.id
    
    if is_admin(user_id) or user_id == CREATOR_ID:
        return
    
    # Проверка на фото/видео 18+
    if update.message.photo or update.message.video:
        caption = update.message.caption.lower() if update.message.caption else ""
        nsfw_caption_words = ["18+", "порно", "xxx", "нюдс", "nude", "nudes", "голые", "интим"]
        for word in nsfw_caption_words:
            if word in caption:
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
    
    # Список 18+ слов
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
    
    # Проверка на ссылки
    if "http://" in message_text or "https://" in message_text or "t.me/" in message_text:
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
        return
# Команда старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        keyboard = [[InlineKeyboardButton("🆘 Поддержка", callback_data="support")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "👋 Привет! Я бот-администратор чата.\n\n"
            "Если у вас есть жалоба или вопрос — нажмите кнопку «Поддержка» и напишите ваше обращение.",
            reply_markup=reply_markup
        )
    else:
        await help_command(update, context)

# Обработчик кнопки поддержки
async def support_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "support":
        await query.message.reply_text(
            "📝 Напишите вашу жалобу или вопрос одним сообщением.\n"
            "Администраторы рассмотрят обращение в ближайшее время."
        )
        context.user_data['waiting_for_complaint'] = True

# Обработчик кнопок администратора (жалобы)
async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id) and user_id != CREATOR_ID:
        await query.message.reply_text("❌ У вас нет прав!")
        return
    
    data = query.data
    
    if data.startswith("take_"):
        complaint_id = data.replace("take_", "")
        complaints = load_complaints()
        if complaint_id in complaints and complaints[complaint_id]["status"] == "open":
            complaints[complaint_id]["status"] = "in_progress"
            complaints[complaint_id]["admin_id"] = user_id
            save_complaints(complaints)
            
            user_complaint_id = complaints[complaint_id]["user_id"]
            try:
                await context.bot.send_message(
                    chat_id=user_complaint_id,
                    text=f"✅ Администратор взял ваше обращение в работу.\n\n"
                         f"Ваше обращение: {complaints[complaint_id]['text']}\n\n"
                         f"Ожидайте ответа."
                )
            except:
                pass
            
            await query.message.reply_text("✅ Вы взяли обращение в работу! Чтобы ответить - просто ответьте на это сообщение.")
            
            new_keyboard = [[InlineKeyboardButton("✅ Завершить", callback_data=f"close_{complaint_id}")]]
            await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(new_keyboard))
    
    elif data.startswith("close_"):
        complaint_id = data.replace("close_", "")
        complaints = load_complaints()
        if complaint_id in complaints and complaints[complaint_id]["status"] == "in_progress":
            complaints[complaint_id]["status"] = "closed"
            save_complaints(complaints)
            
            user_complaint_id = complaints[complaint_id]["user_id"]
            try:
                await context.bot.send_message(
                    chat_id=user_complaint_id,
                    text=f"✅ Ваше обращение рассмотрено и закрыто.\n\nСпасибо за обращение!"
                )
            except:
                pass
            
            await query.message.edit_reply_markup(reply_markup=None)
            await query.message.reply_text("✅ Обращение завершено!")

# Обработчик кнопок админ-меню
async def admin_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id) and user_id != CREATOR_ID:
        await query.message.reply_text("❌ У вас нет прав!")
        return
    
    data = query.data
    
    if data == "admin_ban":
        await query.message.reply_text("Для бана ответьте на сообщение пользователя и напишите: Бан [время]")
    elif data == "admin_mute":
        await query.message.reply_text("Для мута ответьте на сообщение пользователя и напишите: Мут [время]")
    elif data == "admin_warn":
        await query.message.reply_text("Для предупреждения ответьте на сообщение пользователя и напишите: Пред [причина]")
    elif data == "admin_unban":
        await query.message.reply_text("Для разбана ответьте на сообщение пользователя и напишите: Разбан")
    elif data == "admin_unmute":
        await query.message.reply_text("Для размута ответьте на сообщение пользователя и напишите: Размут")
    elif data == "admin_clear":
        await query.message.reply_text("Для очистки напишите: Очистка [количество]")

# Команда "Админка" - меню с кнопками как у Ириса
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id) and user_id != CREATOR_ID:
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
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👮 АДМИН-ПАНЕЛЬ\n\nВыберите действие:",
        reply_markup=reply_markup
    )

# Команда очистки сообщений
async def clear_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id) and user_id != CREATOR_ID:
        await update.message.reply_text("❌ У вас нет прав!")
        return
    
    count = 10
    if context.args:
        try:
            count = int(context.args[0])
        except:
            pass
    
    try:
        messages = []
        async for message in context.bot.get_chat_history(update.effective_chat.id, limit=count + 1):
            messages.append(message.message_id)
        
        for msg_id in messages:
            try:
                await context.bot.delete_message(update.effective_chat.id, msg_id)
            except:
                pass
        
        await update.message.reply_text(f"🧹 Удалено {len(messages)} сообщений!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# Обработчик текстовых сообщений в ЛС
async def private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    
    user_id = update.effective_user.id
    user_data = context.user_data
    message_text = update.message.text
    
    # Если админ отвечает на сообщение с жалобой
    if update.message.reply_to_message and (is_admin(user_id) or user_id == CREATOR_ID):
        reply_text = update.message.reply_to_message.text or ""
        if "НОВОЕ ОБРАЩЕНИЕ #" in reply_text:
            try:
                complaint_id = reply_text.split("НОВОЕ ОБРАЩЕНИЕ #")[1].split("\n")[0].strip()
                complaints = load_complaints()
                if complaint_id in complaints:
                    user_complaint_id = complaints[complaint_id]["user_id"]
                    await context.bot.send_message(
                        chat_id=user_complaint_id,
                        text=f"📩 Ответ от администратора:\n\n{message_text}"
                    )
                    await update.message.reply_text(f"✅ Ответ отправлен пользователю по обращению #{complaint_id}!")
                else:
                    await update.message.reply_text("❌ Обращение не найдено!")
            except:
                await update.message.reply_text("❌ Не удалось отправить ответ!")
            return
    
    # Если пользователь ждёт отправки жалобы
    if user_data.get('waiting_for_complaint'):
        complaint_text = message_text
        
        complaints = load_complaints()
        complaint_id = str(len(complaints) + 1)
        complaints[complaint_id] = {
            "user_id": user_id,
            "username": update.effective_user.username or update.effective_user.first_name,
            "text": complaint_text,
            "status": "open",
            "admin_id": None,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_complaints(complaints)
        
        await update.message.reply_text("✅ Ваше обращение отправлено администраторам. Ожидайте ответа.")
        user_data['waiting_for_complaint'] = False
        
        admins = load_admins()
        keyboard = [[InlineKeyboardButton("🔧 Заняться", callback_data=f"take_{complaint_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        for admin_id in admins:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"📩 НОВОЕ ОБРАЩЕНИЕ #{complaint_id}\n\n"
                         f"От: {update.effective_user.username or update.effective_user.first_name}\n"
                         f"ID: {user_id}\n\n"
                         f"Текст: {complaint_text}",
                    reply_markup=reply_markup
                )
            except:
                pass

# Команда для ответа на жалобу
async def reply_to_complaint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id) and user_id != CREATOR_ID:
        await update.message.reply_text("❌ У вас нет прав!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение с жалобой и напишите: Ответ ваш текст")
        return
    
    reply_text = update.message.reply_to_message.text or ""
    if "НОВОЕ ОБРАЩЕНИЕ #" not in reply_text:
        await update.message.reply_text("❌ Ответьте на сообщение с жалобой!")
        return
    
    try:
        complaint_id = reply_text.split("НОВОЕ ОБРАЩЕНИЕ #")[1].split("\n")[0].strip()
    except:
        await update.message.reply_text("❌ Не удалось определить номер обращения!")
        return
    
    complaints = load_complaints()
    if complaint_id not in complaints:
        await update.message.reply_text("❌ Обращение не найдено!")
        return
    
    response_text = " ".join(context.args) if context.args else update.message.text.split(" ", 1)[1] if len(update.message.text.split()) > 1 else ""
    
    if not response_text:
        await update.message.reply_text("❌ Напишите: Ответ ваш текст")
        return
    
    user_complaint_id = complaints[complaint_id]["user_id"]
    try:
        await context.bot.send_message(
            chat_id=user_complaint_id,
            text=f"📩 Ответ от администратора:\n\n{response_text}"
        )
        await update.message.reply_text(f"✅ Ответ отправлен пользователю по обращению #{complaint_id}!")
    except Exception as e:
        await update.message.reply_text(f"❌ Не удалось отправить ответ: {str(e)}")

# Команда для выдачи администратора
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != CREATOR_ID:
        await update.message.reply_text("❌ Только создатель бота может выдавать администраторов!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Используйте эту команду как ответ на сообщение пользователя, которому хотите выдать администратора!")
        return
    
    new_admin = update.message.reply_to_message.from_user
    admins = load_admins()
    
    if new_admin.id in admins:
        await update.message.reply_text(f"❌ Пользователь {new_admin.username or new_admin.first_name} уже является администратором!")
        return
    
    admins.append(new_admin.id)
    save_admins(admins)
    
    await update.message.reply_text(f"✅ Пользователь {new_admin.username or new_admin.first_name} теперь администратор и может использовать все команды бота!")
# Команда для бана
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    banned_user = update.message.reply_to_message.from_user
    
    if banned_user.id == CREATOR_ID:
        await update.message.reply_text("❌ Нельзя забанить создателя!")
        return
    
    if is_admin(banned_user.id) and user_id != CREATOR_ID:
        await update.message.reply_text("❌ Нельзя забанить администратора!")
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
                user_id=banned_user.id,
                until_date=until_date
            )
            
            if ban_time >= 10080:
                time_str = f"{ban_time // 10080} недель"
            elif ban_time >= 1440:
                time_str = f"{ban_time // 1440} дней"
            elif ban_time >= 60:
                time_str = f"{ban_time // 60} часов"
            else:
                time_str = f"{ban_time} минут"
            
            await update.message.reply_text(f"🚫 {banned_user.first_name} забанен на {time_str}!")
        else:
            await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=banned_user.id
            )
            await update.message.reply_text(f"🚫 {banned_user.first_name} забанен навсегда!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# Команда для разбана
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    unbanned_user = update.message.reply_to_message.from_user
    
    try:
        await context.bot.unban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=unbanned_user.id
        )
        await update.message.reply_text(f"✅ {unbanned_user.first_name} разбанен!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# Команда для мута
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    muted_user = update.message.reply_to_message.from_user
    
    if muted_user.id == CREATOR_ID:
        await update.message.reply_text("❌ Нельзя замутить создателя!")
        return
    
    if is_admin(muted_user.id) and user_id != CREATOR_ID:
        await update.message.reply_text("❌ Нельзя замутить администратора!")
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
    
    until_date = datetime.now() + timedelta(minutes=mute_time)
    
    if mute_time >= 10080:
        time_str = f"{mute_time // 10080} недель"
    elif mute_time >= 1440:
        time_str = f"{mute_time // 1440} дней"
    elif mute_time >= 60:
        time_str = f"{mute_time // 60} часов"
    else:
        time_str = f"{mute_time} минут"
    
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=muted_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        await update.message.reply_text(f"🔇 {muted_user.first_name} замучен на {time_str}!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# Команда для размута
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    unmuted_user = update.message.reply_to_message.from_user
    
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=unmuted_user.id,
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
        await update.message.reply_text(f"🔊 {unmuted_user.first_name} размучен!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# Команда для предупреждения
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    warned_user = update.message.reply_to_message.from_user
    reason = " ".join(context.args) if context.args else "Нарушение правил"
    
    await update.message.reply_text(
        f"⚠️ ПРЕДУПРЕЖДЕНИЕ\n\n"
        f"Пользователь: @{warned_user.username or warned_user.first_name}\n"
        f"Причина: {reason}\n\n"
        f"При повторных нарушениях - бан!"
    )

# Команда "брак"
async def marry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя, с которым хотите заключить брак!")
        return
    
    from_user = update.effective_user
    to_user = update.message.reply_to_message.from_user
    
    if from_user.id == to_user.id:
        await update.message.reply_text("❌ Нельзя жениться на себе!")
        return
    
    marriages = load_marriages()
    
    if str(from_user.id) in marriages:
        await update.message.reply_text(f"❌ Вы уже в браке с {marriages[str(from_user.id)]['name']}! Используйте Развод.")
        return
    
    if str(to_user.id) in marriages:
        await update.message.reply_text(f"❌ {to_user.first_name} уже в браке!")
        return
    
    marriages[str(from_user.id)] = {"partner_id": to_user.id, "name": to_user.first_name}
    marriages[str(to_user.id)] = {"partner_id": from_user.id, "name": from_user.first_name}
    save_marriages(marriages)
    
    await update.message.reply_text(
        f"💒 {from_user.first_name} и {to_user.first_name} теперь в браке!\n"
        f"Поздравляем! 🎉💍"
    )

# Команда "развод"
async def divorce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from_user = update.effective_user
    marriages = load_marriages()
    
    if str(from_user.id) not in marriages:
        await update.message.reply_text("❌ Вы не в браке!")
        return
    
    partner_id = marriages[str(from_user.id)]["partner_id"]
    partner_name = marriages[str(from_user.id)]["name"]
    
    del marriages[str(from_user.id)]
    if str(partner_id) in marriages:
        del marriages[str(partner_id)]
    save_marriages(marriages)
    
    await update.message.reply_text(f"💔 {from_user.first_name} развёлся с {partner_name} 😢")

# Команда "моя семья"
async def marriage_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from_user = update.effective_user
    marriages = load_marriages()
    
    if str(from_user.id) in marriages:
        partner_name = marriages[str(from_user.id)]["name"]
        await update.message.reply_text(f"💍 Вы в браке с {partner_name}")
    else:
        await update.message.reply_text("💔 Вы не в браке")
# Команда "обнять"
async def hug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    from_user = update.effective_user
    to_user = update.message.reply_to_message.from_user
    
    hugs_gifs = [
        "https://media.giphy.com/media/od5H3PmEG4EVq/giphy.gif",
        "https://media.giphy.com/media/ZQN9jsRWp1M76/giphy.gif",
        "https://media.giphy.com/media/wnsgren9NtITS/giphy.gif",
        "https://media.giphy.com/media/l2QDM9Jnim1YVILXa/giphy.gif",
        "https://media.giphy.com/media/3o7TKO3AC9oZqVbNQQ/giphy.gif"
    ]
    
    await update.message.reply_animation(
        animation=random.choice(hugs_gifs),
        caption=f"🫂 {from_user.first_name} обнял(а) {to_user.first_name}!"
    )

# Команда "поцеловать"
async def kiss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    from_user = update.effective_user
    to_user = update.message.reply_to_message.from_user
    
    kisses_gifs = [
        "https://media.giphy.com/media/G3va31oEEnIkM/giphy.gif",
        "https://media.giphy.com/media/12VXIxKaIEarL2/giphy.gif",
        "https://media.giphy.com/media/jR22gdcPiOLaE/giphy.gif",
        "https://media.giphy.com/media/bm2O3nXTcKJeU/giphy.gif",
        "https://media.giphy.com/media/nyGFcsP0kAobm/giphy.gif"
    ]
    
    await update.message.reply_animation(
        animation=random.choice(kisses_gifs),
        caption=f"💋 {from_user.first_name} поцеловал(а) {to_user.first_name}!"
    )

# Команда "укусить"
async def bite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
        return
    
    from_user = update.effective_user
    to_user = update.message.reply_to_message.from_user
    
    bites_gifs = [
        "https://media.giphy.com/media/l4FGH2AqGg0O4LTkA/giphy.gif",
        "https://media.giphy.com/media/3o7TKqoVPf7K1M8T9K/giphy.gif",
        "https://media.giphy.com/media/xT0BKnZ6dO6FCxDtBK/giphy.gif",
        "https://media.giphy.com/media/3o7TKDx2DvzF3qK6M8/giphy.gif",
        "https://media.giphy.com/media/3o7TKCUvD4HWzUZ3LW/giphy.gif"
    ]
    
    await update.message.reply_animation(
        animation=random.choice(bites_gifs),
        caption=f"🦷 {from_user.first_name} укусил(а) {to_user.first_name}!"
    )

# Функция для отправки сообщения о судных выходных
async def send_weekend_message(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    
    weekend_message = """
🎉 СУДНЫЕ ВЫХОДНЫЕ! 🎉

Простыми словами можно делать всё что угодно, кроме:
❌ Вреда чату
❌ Порнографии
❌ Насилия
❌ Расчленёнки
❌ Рекламы

⏰ Начинается: Суббота 12:00
⏰ Заканчивается: Понедельник 6:00

🔥 Время веселья началось! 🔥
"""
    await context.bot.send_photo(
        chat_id=chat_id,
        photo="https://photos.app.goo.gl/1Zw5wMqT7nmZZAtq6",
        caption=weekend_message
    )

# Функция для планирования судных выходных
async def schedule_weekend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
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
        name=f"weekend_{chat_id}"
    )
    
    context.job_queue.run_daily(
        send_weekend_message,
        time=time(hour=12, minute=0, tzinfo=MOSCOW_TZ),
        days=(6,),
        chat_id=chat_id,
        name=f"weekend_{chat_id}_sun"
    )
    
    await update.message.reply_text("✅ Судные выходные запланированы!")

# Команда для набора в администрацию
async def admin_recruitment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📋 Пример анкеты", url=EXAMPLE_APPLICATION)],
        [InlineKeyboardButton("📝 Подать заявку", url=APPLICATION_LINK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👑 НАБОР В АДМИНИСТРАЦИЮ ЧАТА! 👑\n\n"
        "📋 Требования:\n"
        "• Возраст: 14+ лет\n"
        "• Активность в чате\n"
        "• Ответственность и адекватность\n"
        "• Готовность следить за порядком\n\n"
        "📸 Нажмите «Пример анкеты» чтобы посмотреть оформление\n"
        "📝 Нажмите «Подать заявку» чтобы отправить анкету\n\n"
        "⚠️ Возрастные ограничения: 14+",
        reply_markup=reply_markup
    )

# Команда помощи
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 КОМАНДЫ БОТА:\n\n"
        "👑 Для создателя:\n"
        "Админ - Выдать администратора (ответом)\n\n"
        "👮 Администраторам:\n"
        "Админка - Панель управления\n"
        "Бан [время] - Бан (ответом)\n"
        "Разбан - Разбан (ответом)\n"
        "Мут [время] - Мут (ответом)\n"
        "Размут - Размут (ответом)\n"
        "Пред [причина] - Предупреждение (ответом)\n"
        "Очистка [число] - Удалить сообщения\n"
        "Выходные - Запланировать судные выходные\n\n"
        "⏰ Форматы времени:\n"
        "30, 30 минут, 2 часа, 1 день, 1 неделя\n\n"
        "🎉 Развлечения (ответом):\n"
        "Обнять, Поцеловать, Укусить\n"
        "Брак, Развод, Семья\n\n"
        "📢 Общие:\n"
        "Набор, Помощь, Правила, Старт\n\n"
        "🆘 В ЛС: кнопка «Поддержка»"
    )

# Команда правил
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
        "❌ Шок-контент — мут 4 часа/бан.\n\n"
        "❌ Оскорбление участников — 3 предупреждения/мут 1 час.\n\n"
        "❌ Провокации, троллинг — 3 предупреждения, мут 1 час.\n\n"
        "❌ Обход наказания — бан 24 часа.\n\n"
        "❌ Продажа аккаунтов запрещена — 1 предупреждение/мут 3 часа.\n\n"
        "👮 ПРАВИЛА АДМИНИСТРАЦИИ:\n"
        "• Запрещено угрожать баном/мутом — 3 предупреждения/снятие.\n"
        "• Соблюдать субординацию.\n"
        "• Агрессия/провокации — 4 предупреждение/снятие.\n\n"
        "🎉 СУДНЫЕ ВЫХОДНЫЕ:\n"
        "Суббота 12:00 - Понедельник 6:00\n"
        "Можно всё, кроме: вреда чату, порнографии, насилия, расчленёнки, рекламы\n\n"
        "Приятного общения!"
    )

# Функция для обработки текстовых команд без слеша
async def text_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text.lower().strip()
    user_id = update.effective_user.id
    
    # Команды без ответа
    if message_text == "помощь":
        await help_command(update, context)
    elif message_text == "правила":
        await rules(update, context)
    elif message_text == "набор":
        await admin_recruitment(update, context)
    elif message_text == "старт":
        await start(update, context)
    elif message_text == "админка":
        await admin_panel(update, context)
    elif message_text == "развод":
        await divorce(update, context)
    elif message_text == "семья" or message_text == "моя семья":
        await marriage_info(update, context)
    elif message_text.startswith("очистка"):
        args = message_text.split()[1:] if len(message_text.split()) > 1 else []
        context.args = args
        await clear_messages(update, context)
    
    # Команды с ответом на сообщение
    elif message_text == "админ":
        await add_admin(update, context)
    elif message_text.startswith("бан"):
        args = message_text.split()[1:] if len(message_text.split()) > 1 else []
        context.args = args
        await ban(update, context)
    elif message_text == "разбан":
        await unban(update, context)
    elif message_text.startswith("мут"):
        args = message_text.split()[1:] if len(message_text.split()) > 1 else []
        context.args = args
        await mute(update, context)
    elif message_text == "размут":
        await unmute(update, context)
    elif message_text.startswith("пред"):
        args = message_text.split()[1:] if len(message_text.split()) > 1 else []
        context.args = args
        await warn(update, context)
    elif message_text == "выходные":
        await schedule_weekend(update, context)
    elif message_text == "обнять":
        await hug(update, context)
    elif message_text == "поцеловать":
        await kiss(update, context)
    elif message_text == "укусить":
        await bite(update, context)
    elif message_text == "брак":
        await marry(update, context)
    elif message_text.startswith("ответ"):
        args = message_text.split()[1:] if len(message_text.split()) > 1 else []
        context.args = args
        await reply_to_complaint(update, context)

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
    
    # Приветствие новых участников
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    
    # Команды со слешем
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add_admin", add_admin))
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
    application.add_handler(CommandHandler("marriage", marriage_info))
    application.add_handler(CommandHandler("schedule_weekend", schedule_weekend))
    application.add_handler(CommandHandler("admin", admin_recruitment))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(CommandHandler("reply", reply_to_complaint))
    application.add_handler(CommandHandler("admin_panel", admin_panel))
    application.add_handler(CommandHandler("clear", clear_messages))
    
    # Кнопки
    application.add_handler(CallbackQueryHandler(support_button, pattern="^support$"))
    application.add_handler(CallbackQueryHandler(admin_buttons, pattern="^(take_|close_)"))
    application.add_handler(CallbackQueryHandler(admin_menu_buttons, pattern="^admin_"))
    
    # Фильтр ботов
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, filter_bots), group=0)
    
    # Фильтр 18+ и ссылок
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.ChatType.PRIVATE, message_filter), group=1)
    
    # ЛС
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, private_message))
    
    # Команды в группах
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.ChatType.PRIVATE, text_commands), group=2)
    
    print("✅ Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
