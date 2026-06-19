import logging
from datetime import datetime, time, timedelta, timezone
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, JobQueue, CallbackQueryHandler
import json
import os
import random
import threading
import requests

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8240444405:AAGulbNBUspFbtIFAu55XDqmMTLBQ4uF17g"
MOSCOW_TZ = timezone(timedelta(hours=3))
ADMINS_FILE = "admins.json"
COMPLAINTS_FILE = "complaints.json"
MARRIAGES_FILE = "marriages.json"
PROPOSALS_FILE = "proposals.json"
CHATS_FILE = "active_chats.json"
CREATOR_ID = 8432323388
CHAT_ID = -1002753124436
EXAMPLE_APPLICATION = "https://t.me/c/2945439331/605"
APPLICATION_LINK = "https://t.me/+92SODWh2fc41NTdi"
RENDER_URL = "https://support-bot-dwl0.onrender.com"

def load_json(filename, default):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f: return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(user_id):
    return user_id in load_json(ADMINS_FILE, [CREATOR_ID])

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot: continue
        await update.message.reply_text(
            f"👋 Добро пожаловать, {member.first_name}!\n\n"
            "📜 Правила: без 18+, без рекламы, без оскорблений\n"
            "🎉 Судные выходные: Суббота 12:00 - Понедельник 6:00\n\nПриятного общения! 😊")

async def filter_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private': return
    if update.effective_user and update.effective_user.is_bot:
        try: await update.message.delete()
        except: pass

async def message_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private': return
    if not update.message or not update.message.text: return
    message_text = update.message.text.lower()
    user_id = update.effective_user.id
    if is_admin(user_id) or user_id == CREATOR_ID: return
    nsfw_words = ["порно","porn","xxx","секс","sex","член","пизда","хуй","ебать","шлюха","интим","минет","анус",
        "мастурбация","лесби","гей","транс","фетиш","бдсм","оргия","голые","обнаженные","эротика","изнасилование",
        "18+","18 +","для взрослых","adult","жесткое","трах","кончил","сперма","голая","голый","нюдс","nudes","nude",
        "слив","сливы","приват","приваты","onlyfans","only fans"]
    for word in nsfw_words:
        if word in message_text:
            try:
                await update.message.delete()
                await context.bot.restrict_chat_member(chat_id=update.effective_chat.id, user_id=user_id,
                    permissions=ChatPermissions(can_send_messages=False), until_date=datetime.now()+timedelta(hours=3))
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🚫 {update.effective_user.first_name} мут 3 часа за 18+!")
            except: pass
            return
    if any(x in message_text for x in ["http://","https://","t.me/"]):
        try:
            cm = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            if cm.status in ['administrator','creator']: return
        except: pass
        try:
            await update.message.delete()
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🚫 {update.effective_user.first_name}, ссылки запрещены!")
        except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        keyboard = [[InlineKeyboardButton("🆘 Поддержка", callback_data="support")]]
        await update.message.reply_text("👋 Привет! Я бот-администратор.\nНажмите «Поддержка» чтобы написать администраторам.", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await help_command(update, context)

async def support_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "support":
        await query.message.reply_text("📝 Напишите ваше сообщение. Администраторы увидят его и ответят.")
        context.user_data['waiting_for_complaint'] = True

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id) and user_id != CREATOR_ID: return
    data = query.data
    complaints = load_json(COMPLAINTS_FILE, {})
    if data.startswith("take_"):
        cid = data.replace("take_","")
        if cid in complaints and complaints[cid]["status"]=="open":
            complaints[cid]["status"]="in_progress"
            complaints[cid]["admin_id"]=user_id
            save_json(COMPLAINTS_FILE, complaints)
            chats = load_json(CHATS_FILE, {})
            chats[str(complaints[cid]["user_id"])]=cid
            chats[str(user_id)]=cid
            save_json(CHATS_FILE, chats)
            try: await context.bot.send_message(chat_id=complaints[cid]["user_id"], text="✅ Администратор взял обращение. Пишите ваш вопрос.")
            except: pass
            await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Завершить", callback_data=f"close_{cid}")]]))
    elif data.startswith("close_"):
        cid = data.replace("close_","")
        if cid in complaints:
            uid=complaints[cid]["user_id"]; aid=complaints[cid].get("admin_id","")
            complaints[cid]["status"]="closed"
            save_json(COMPLAINTS_FILE, complaints)
            chats = load_json(CHATS_FILE, {})
            if str(uid) in chats: del chats[str(uid)]
            if str(aid) in chats: del chats[str(aid)]
            save_json(CHATS_FILE, chats)
            try: await context.bot.send_message(chat_id=uid, text="✅ Обращение закрыто. Спасибо!")
            except: pass
            await query.message.edit_reply_markup(reply_markup=None)

async def admin_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id) and query.from_user.id != CREATOR_ID: return
    r = {"admin_ban":"🚫 Бан: ответьте на сообщение и напишите Бан [время]",
         "admin_mute":"🔇 Мут: ответьте на сообщение и напишите Мут [время]",
         "admin_warn":"⚠️ Пред: ответьте на сообщение и напишите Пред [причина]",
         "admin_unban":"✅ Разбан: ответьте на сообщение и напишите Разбан",
         "admin_unmute":"🔊 Размут: ответьте на сообщение и напишите Размут",
         "admin_clear":"🧹 Очистка: напишите Очистка [количество]"}
    if query.data in r: await query.message.reply_text(r[query.data])

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) and update.effective_user.id != CREATOR_ID:
        await update.message.reply_text("❌ Нет прав!"); return
    kb = [[InlineKeyboardButton("🚫 Бан", callback_data="admin_ban"), InlineKeyboardButton("🔇 Мут", callback_data="admin_mute")],
          [InlineKeyboardButton("⚠️ Пред", callback_data="admin_warn"), InlineKeyboardButton("✅ Разбан", callback_data="admin_unban")],
          [InlineKeyboardButton("🔊 Размут", callback_data="admin_unmute"), InlineKeyboardButton("🧹 Очистка", callback_data="admin_clear")]]
    await update.message.reply_text("👮 АДМИН-ПАНЕЛЬ\n\nВыберите действие:", reply_markup=InlineKeyboardMarkup(kb))

async def clear_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) and update.effective_user.id != CREATOR_ID: return
    count = int(context.args[0]) if context.args and context.args[0].isdigit() else 10
    try:
        msgs = []
        async for m in context.bot.get_chat_history(update.effective_chat.id, limit=count+1): msgs.append(m.message_id)
        d=0
        for mid in msgs:
            try: await context.bot.delete_message(update.effective_chat.id, mid); d+=1
            except: pass
        await update.message.reply_text(f"🧹 Удалено {d} сообщений!")
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

async def private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private': return
    user_id = update.effective_user.id
    message_text = update.message.text
    user_data = context.user_data
    
    if update.message.reply_to_message and (is_admin(user_id) or user_id == CREATOR_ID):
        reply_text = update.message.reply_to_message.text or ""
        if "ЖАЛОБА #" in reply_text or "📩" in reply_text:
            try:
                if "ЖАЛОБА #" in reply_text: cid = reply_text.split("ЖАЛОБА #")[1].split("\n")[0].strip()
                else: cid = reply_text.split("#")[1].split("\n")[0].strip()
                complaints = load_json(COMPLAINTS_FILE, {})
                if cid in complaints:
                    await context.bot.send_message(chat_id=complaints[cid]["user_id"], text=f"📩 Администратор:\n{message_text}")
                    await update.message.reply_text("✅ Ответ отправлен!")
                    return
            except: pass
    
    if user_data.get('waiting_for_complaint'):
        complaints = load_json(COMPLAINTS_FILE, {})
        cid = str(len(complaints)+1)
        complaints[cid] = {"user_id":user_id,"username":update.effective_user.first_name,"text":message_text,"status":"open","admin_id":None}
        save_json(COMPLAINTS_FILE, complaints)
        await update.message.reply_text("✅ Отправлено! Администраторы скоро ответят.")
        user_data['waiting_for_complaint'] = False
        admins = load_json(ADMINS_FILE, [CREATOR_ID])
        kb = [[InlineKeyboardButton("🔧 Заняться", callback_data=f"take_{cid}")]]
        for aid in admins:
            if aid != user_id:
                try: await context.bot.send_message(chat_id=aid, text=f"📩 НОВАЯ ЖАЛОБА #{cid}\nОт: {update.effective_user.first_name}\n\n{message_text}", reply_markup=InlineKeyboardMarkup(kb))
                except: pass
        return
    
    chats = load_json(CHATS_FILE, {})
    if str(user_id) in chats:
        complaints = load_json(COMPLAINTS_FILE, {})
        cid = chats[str(user_id)]
        if cid in complaints and complaints[cid]["status"]=="in_progress":
            if is_admin(user_id) or user_id==CREATOR_ID:
                try: await context.bot.send_message(chat_id=complaints[cid]["user_id"], text=f"📩 Администратор:\n{message_text}")
                except: pass
            else:
                aid = complaints[cid].get("admin_id")
                if aid:
                    try: await context.bot.send_message(chat_id=aid, text=f"📩 {update.effective_user.first_name}:\n{message_text}")
                    except: pass
            return
    
    if not (is_admin(user_id) or user_id==CREATOR_ID):
        kb = [[InlineKeyboardButton("🆘 Поддержка", callback_data="support")]]
        await update.message.reply_text("Нажмите кнопку для обращения.", reply_markup=InlineKeyboardMarkup(kb))
# Бан
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    user = update.message.reply_to_message.from_user
    if user.id == CREATOR_ID: return
    if is_admin(user.id) and update.effective_user.id != CREATOR_ID: return
    ban_time = 0
    if context.args:
        try:
            if len(context.args) == 1 and context.args[0].isdigit(): ban_time = int(context.args[0])
            elif len(context.args) >= 2:
                num = int(context.args[0]); unit = context.args[1].lower()
                if unit in ["м","мин","минута","минуты","минут"]: ban_time = num
                elif unit in ["ч","час","часа","часов"]: ban_time = num * 60
                elif unit in ["д","день","дня","дней"]: ban_time = num * 1440
                elif unit in ["н","нед","неделя","недели","недель"]: ban_time = num * 10080
        except: pass
    try:
        if ban_time > 0:
            await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=user.id, until_date=datetime.now()+timedelta(minutes=ban_time))
            if ban_time>=10080: t=f"{ban_time//10080} нед"
            elif ban_time>=1440: t=f"{ban_time//1440} дн"
            elif ban_time>=60: t=f"{ban_time//60} ч"
            else: t=f"{ban_time} мин"
            await update.message.reply_text(f"🚫 {user.first_name} забанен на {t}!")
        else:
            await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=user.id)
            await update.message.reply_text(f"🚫 {user.first_name} забанен навсегда!")
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

# Разбан
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    user = update.message.reply_to_message.from_user
    try:
        await context.bot.unban_chat_member(chat_id=update.effective_chat.id, user_id=user.id)
        await update.message.reply_text(f"✅ {user.first_name} разбанен!")
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

# Мут
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    user = update.message.reply_to_message.from_user
    if user.id == CREATOR_ID: return
    if is_admin(user.id) and update.effective_user.id != CREATOR_ID: return
    mute_time = 60
    if context.args:
        try:
            if len(context.args) == 1 and context.args[0].isdigit(): mute_time = int(context.args[0])
            elif len(context.args) >= 2:
                num = int(context.args[0]); unit = context.args[1].lower()
                if unit in ["м","мин","минута","минуты","минут"]: mute_time = num
                elif unit in ["ч","час","часа","часов"]: mute_time = num * 60
                elif unit in ["д","день","дня","дней"]: mute_time = num * 1440
                elif unit in ["н","нед","неделя","недели","недель"]: mute_time = num * 10080
        except: pass
    if mute_time>=10080: t=f"{mute_time//10080} нед"
    elif mute_time>=1440: t=f"{mute_time//1440} дн"
    elif mute_time>=60: t=f"{mute_time//60} ч"
    else: t=f"{mute_time} мин"
    try:
        await context.bot.restrict_chat_member(chat_id=update.effective_chat.id, user_id=user.id,
            permissions=ChatPermissions(can_send_messages=False), until_date=datetime.now()+timedelta(minutes=mute_time))
        await update.message.reply_text(f"🔇 {user.first_name} замучен на {t}!")
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

# Размут
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    user = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(chat_id=update.effective_chat.id, user_id=user.id,
            permissions=ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True,
            can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True,
            can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True))
        await update.message.reply_text(f"🔊 {user.first_name} размучен!")
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

# Пред
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    user = update.message.reply_to_message.from_user
    reason = " ".join(context.args) if context.args else "Нарушение правил"
    await update.message.reply_text(f"⚠️ ПРЕДУПРЕЖДЕНИЕ\nПользователь: @{user.username or user.first_name}\nПричина: {reason}")

# Выдача админа
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != CREATOR_ID: return
    if not update.message.reply_to_message: return
    new_admin = update.message.reply_to_message.from_user
    admins = load_json(ADMINS_FILE, [CREATOR_ID])
    if new_admin.id in admins: return
    admins.append(new_admin.id)
    save_json(ADMINS_FILE, admins)
    await update.message.reply_text(f"✅ {new_admin.first_name} теперь администратор!")

# Снятие админа
async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != CREATOR_ID:
        await update.message.reply_text("❌ Только создатель может снимать администраторов!"); return
    if not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    admins = load_json(ADMINS_FILE, [CREATOR_ID])
    if target.id == CREATOR_ID: return
    if target.id not in admins:
        await update.message.reply_text(f"❌ {target.first_name} не администратор!"); return
    admins.remove(target.id)
    save_json(ADMINS_FILE, admins)
    await update.message.reply_text(f"✅ {target.first_name} больше не администратор!")

# Брак
async def marry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    if a.id == b.id: return
    m = load_json(MARRIAGES_FILE, {})
    if str(a.id) in m: await update.message.reply_text(f"❌ Вы уже в браке с {m[str(a.id)]['name']}!"); return
    if str(b.id) in m: await update.message.reply_text(f"❌ {b.first_name} уже в браке!"); return
    p = load_json(PROPOSALS_FILE, {})
    p[str(b.id)] = {"from_id":a.id,"from_name":a.first_name,"to_name":b.first_name}
    save_json(PROPOSALS_FILE, p)
    kb = [[InlineKeyboardButton("💍 Согласиться", callback_data=f"accept_marry_{a.id}"),
           InlineKeyboardButton("❌ Отказаться", callback_data=f"decline_marry_{a.id}")]]
    await update.message.reply_text(f"💍 {a.first_name} предложил(а) {b.first_name} вступить в брак!\n{b.first_name}, нажмите кнопку:", reply_markup=InlineKeyboardMarkup(kb))

async def marry_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data
    if data.startswith("accept_marry_"):
        fid = int(data.replace("accept_marry_",""))
        p = load_json(PROPOSALS_FILE, {})
        if str(uid) in p and p[str(uid)]["from_id"]==fid:
            m = load_json(MARRIAGES_FILE, {})
            m[str(fid)] = {"partner_id":uid,"name":p[str(uid)]["to_name"]}
            m[str(uid)] = {"partner_id":fid,"name":p[str(uid)]["from_name"]}
            save_json(MARRIAGES_FILE, m)
            await query.message.edit_text(f"💒 {p[str(uid)]['from_name']} и {p[str(uid)]['to_name']} теперь в браке! 🎉💍")
            del p[str(uid)]
            save_json(PROPOSALS_FILE, p)
    elif data.startswith("decline_marry_"):
        p = load_json(PROPOSALS_FILE, {})
        if str(uid) in p:
            await query.message.edit_text(f"💔 {p[str(uid)]['to_name']} отказал(а) {p[str(uid)]['from_name']}.")
            del p[str(uid)]
            save_json(PROPOSALS_FILE, p)

# Развод
async def divorce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    m = load_json(MARRIAGES_FILE, {})
    if str(u.id) not in m: await update.message.reply_text("❌ Вы не в браке!"); return
    kb = [[InlineKeyboardButton("💔 Да", callback_data=f"confirm_divorce_{u.id}"), InlineKeyboardButton("❤️ Нет", callback_data="cancel_divorce")]]
    await update.message.reply_text(f"💔 Развестись с {m[str(u.id)]['name']}?", reply_markup=InlineKeyboardMarkup(kb))

async def divorce_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    if query.data.startswith("confirm_divorce_"):
        m = load_json(MARRIAGES_FILE, {})
        if str(uid) in m:
            pid = m[str(uid)]["partner_id"]; pname = m[str(uid)]["name"]
            del m[str(uid)]
            if str(pid) in m: del m[str(pid)]
            save_json(MARRIAGES_FILE, m)
            await query.message.edit_text(f"💔 {query.from_user.first_name} развёлся с {pname} 😢")
    elif query.data == "cancel_divorce":
        await query.message.edit_text("❤️ Развод отменён!")

# Семья
async def marriage_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = load_json(MARRIAGES_FILE, {})
    if str(update.effective_user.id) in m: await update.message.reply_text(f"💍 Вы в браке с {m[str(update.effective_user.id)]['name']}")
    else: await update.message.reply_text("💔 Вы не в браке")

# Обнять
async def hug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    e = ["🫂","🤗","🥰","💕","🫶"]
    await update.message.reply_text(f"{random.choice(e)} {a.first_name} обнял(а) {b.first_name}!")

# Поцеловать
async def kiss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    e = ["💋","😘","😚","💏","❤️"]
    await update.message.reply_text(f"{random.choice(e)} {a.first_name} поцеловал(а) {b.first_name}!")

# Укусить
async def bite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    e = ["🦷","😬","🫦","😈","🦊"]
    await update.message.reply_text(f"{random.choice(e)} {a.first_name} укусил(а) {b.first_name}!")

# Кто
async def who(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    t = update.message.reply_to_message.from_user
    actions = [f"🍕 {t.first_name} сегодня угощает всех пиццей!", f"💩 {t.first_name} сегодня ходит в туалет чаще всех!",
        f"🎂 {t.first_name} сегодня именинник!", f"🤡 {t.first_name} сегодня главный клоун!",
        f"💤 {t.first_name} сегодня проспал всё!", f"🦸 {t.first_name} сегодня спасает мир!",
        f"🎮 {t.first_name} сегодня задрот дня!", f"🍔 {t.first_name} сегодня съел больше всех!",
        f"💸 {t.first_name} сегодня платит за всех!", f"🎉 {t.first_name} сегодня душа компании!"]
    await update.message.reply_text(random.choice(actions))

# Шар
async def ball(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = " ".join(context.args) if context.args else "Без вопроса"
    answers = ["✅ Да","❌ Нет","🤔 Возможно","🌟 Определённо да","💔 Не сейчас","🎱 Спроси позже","👍 Хорошие шансы","👎 Плохие шансы"]
    await update.message.reply_text(f"🎱 {question}\n{random.choice(answers)}")

# Монетка
async def coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🪙 {random.choice(['Орёл','Решка'])}!")

# Выбери
async def choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: await update.message.reply_text("❌ Напишите: Выбери вариант1 или вариант2"); return
    text = " ".join(context.args)
    options = [x.strip() for x in text.split("или")]
    if len(options) < 2: await update.message.reply_text("❌ Нужно минимум 2 варианта через «или»"); return
    await update.message.reply_text(f"🤔 Я выбираю: {random.choice(options)}!")
# Судные выходные
async def send_weekend_message(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_photo(chat_id=context.job.chat_id, photo="https://photos.app.goo.gl/1Zw5wMqT7nmZZAtq6",
        caption="🎉 СУДНЫЕ ВЫХОДНЫЕ! 🎉\n\nМожно всё кроме:\n❌ Вреда чату\n❌ Порнографии\n❌ Насилия\n❌ Расчленёнки\n❌ Рекламы\n\n⏰ Суббота 12:00 - Понедельник 6:00\n\n🔥 Время веселья началось! 🔥")

async def schedule_weekend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    cid = update.effective_chat.id
    for j in context.job_queue.jobs():
        if j.name and j.name.startswith(f"weekend_{cid}"): j.schedule_removal()
    context.job_queue.run_daily(send_weekend_message, time=time(hour=12, minute=0, tzinfo=MOSCOW_TZ), days=(5,), chat_id=cid)
    context.job_queue.run_daily(send_weekend_message, time=time(hour=12, minute=0, tzinfo=MOSCOW_TZ), days=(6,), chat_id=cid)
    await update.message.reply_text("✅ Судные выходные запланированы!")

# Набор в админы
async def admin_recruitment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("📋 Пример анкеты", url=EXAMPLE_APPLICATION)],
          [InlineKeyboardButton("📝 Подать заявку", url=APPLICATION_LINK)]]
    await update.message.reply_text("👑 НАБОР В АДМИНИСТРАЦИЮ!\n\n📋 Требования: 14+, активность, ответственность\n\n📸 Пример анкеты\n📝 Подать заявку", reply_markup=InlineKeyboardMarkup(kb))

# Помощь
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 КОМАНДЫ БОТА:\n\n"
        "👑 Создатель: Админ, Снять — выдать/снять админа (ответом)\n"
        "👮 Админы: Админка, Бан, Разбан, Мут, Размут, Пред, Очистка, Выходные\n"
        "🎉 Развлечения: Обнять, Поцеловать, Укусить, Брак, Развод, Семья\n"
        "🎮 Игры: Кто, Шар, Монетка, Выбери\n"
        "📢 Общие: Помощь, Правила, Набор\n"
        "🆘 ЛС: кнопка Поддержка\n\n"
        "ℹ️ Бот отзывается на: Бот, Боты, Bot"
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
        "❌ Оскорбление участников — 3 предупреждения/мут 1 час. Относится и к администрации!\n\n"
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
    if not update.message or not update.message.text: return
    msg = update.message.text.lower().strip()
    
    if msg in ["бот", "боты", "bot"]:
        await update.message.reply_text("👋 Я здесь! Напишите «Помощь» чтобы увидеть список команд.")
        return
    
    if msg in ["помощь","правила","набор","старт"]:
        if msg=="помощь": await help_command(update, context)
        elif msg=="правила": await rules(update, context)
        elif msg=="набор": await admin_recruitment(update, context)
        else: await start(update, context)
    elif msg=="админка": await admin_panel(update, context)
    elif msg=="развод": await divorce(update, context)
    elif msg in ["семья","моя семья"]: await marriage_info(update, context)
    elif msg.startswith("очистка"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []
        await clear_messages(update, context)
    elif msg=="админ": await add_admin(update, context)
    elif msg=="снять": await remove_admin(update, context)
    elif msg.startswith("бан"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []
        await ban(update, context)
    elif msg=="разбан": await unban(update, context)
    elif msg.startswith("мут"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []
        await mute(update, context)
    elif msg=="размут": await unmute(update, context)
    elif msg.startswith("пред"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []
        await warn(update, context)
    elif msg=="выходные": await schedule_weekend(update, context)
    elif msg=="обнять": await hug(update, context)
    elif msg=="поцеловать": await kiss(update, context)
    elif msg=="укусить": await bite(update, context)
    elif msg=="брак": await marry(update, context)
    elif msg=="кто": await who(update, context)
    elif msg=="шар":
        context.args = msg.split()[1:] if len(msg.split())>1 else []
        await ball(update, context)
    elif msg=="монетка": await coin(update, context)
    elif msg.startswith("выбери"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []
        await choose(update, context)

def main():
    application = Application.builder().token(TOKEN).build()
    
    # Самопинг каждые 5 минут
    def self_ping():
        while True:
            try: requests.get(RENDER_URL, timeout=10)
            except: pass
            time.sleep(300)
    threading.Thread(target=self_ping, daemon=True).start()
    
    # Автозапуск судных выходных
    application.job_queue.run_daily(send_weekend_message, time=time(hour=12, minute=0, tzinfo=MOSCOW_TZ), days=(5,), chat_id=CHAT_ID, name="weekend_sat")
    application.job_queue.run_daily(send_weekend_message, time=time(hour=12, minute=0, tzinfo=MOSCOW_TZ), days=(6,), chat_id=CHAT_ID, name="weekend_sun")
    
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
    application.add_handler(CommandHandler("who", who))
    application.add_handler(CommandHandler("ball", ball))
    application.add_handler(CommandHandler("coin", coin))
    application.add_handler(CommandHandler("choose", choose))
    application.add_handler(CommandHandler("marry", marry))
    application.add_handler(CommandHandler("divorce", divorce))
    application.add_handler(CommandHandler("clear", clear_messages))
    application.add_handler(CommandHandler("admin", admin_recruitment))
    application.add_handler(CommandHandler("admin_panel", admin_panel))
    application.add_handler(CommandHandler("remove_admin", remove_admin))
    application.add_handler(CallbackQueryHandler(support_button, pattern="^support$"))
    application.add_handler(CallbackQueryHandler(admin_buttons, pattern="^(take_|close_)"))
    application.add_handler(CallbackQueryHandler(admin_menu_buttons, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(marry_buttons, pattern="^(accept_marry_|decline_marry_)"))
    application.add_handler(CallbackQueryHandler(divorce_buttons, pattern="^(confirm_divorce_|cancel_divorce)"))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, filter_bots), group=0)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.ChatType.PRIVATE, message_filter), group=1)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, private_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.ChatType.PRIVATE, text_commands), group=2)
    
    print("✅ Бот запущен! (с самопингом каждые 5 минут)")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
