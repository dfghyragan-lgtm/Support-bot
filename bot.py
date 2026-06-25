import os
import logging
from datetime import datetime, time, timedelta, timezone
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, JobQueue, CallbackQueryHandler
import json, os, random
from collections import defaultdict

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8240444405:AAGulbNBUspFbtIFAu55XDqmMTLBQ4uF17g"
MOSCOW_TZ = timezone(timedelta(hours=3))
ADMINS_FILE, COMPLAINTS_FILE, MARRIAGES_FILE, PROPOSALS_FILE = "admins.json", "complaints.json", "marriages.json", "proposals.json"
CHATS_FILE, STATS_FILE, NICKNAMES_FILE, TITLES_FILE = "active_chats.json", "stats.json", "nicknames.json", "titles.json"
REP_FILE, PROFILES_FILE, RP_SETTINGS_FILE = "reputation.json", "profiles.json", "rp_settings.json"
CREATOR_ID, CHAT_ID = 8432323388, -1002753124436
EXAMPLE_APPLICATION = "https://t.me/c/2945439331/605"
APPLICATION_LINK = "https://t.me/+92SODWh2fc41NTdi"

def load_json(f, d):
    if os.path.exists(f):
        with open(f, 'r', encoding='utf-8') as fl: return json.load(fl)
    return d

def save_json(f, d):
    with open(f, 'w', encoding='utf-8') as fl: json.dump(d, fl, ensure_ascii=False, indent=2)

def is_admin(uid): return uid in load_json(ADMINS_FILE, [CREATOR_ID])

def get_display_name(u):
    n = load_json(NICKNAMES_FILE, {})
    return n[str(u.id)]["nick"] if str(u.id) in n else u.first_name

def get_user_link(u): return f'<a href="tg://user?id={u.id}">{get_display_name(u)}</a>'

def get_rank(c):
    if c >= 10000: return "👑 Легенда"
    elif c >= 5000: return "🌟 Элита"
    elif c >= 2000: return "💎 Ветеран"
    elif c >= 1000: return "🔥 Активист"
    elif c >= 500: return "⭐ Продвинутый"
    elif c >= 100: return "👍 Участник"
    elif c >= 10: return "🆕 Новичок"
    else: return "💤 Гость"

def update_profile(uid, uname):
    p = load_json(PROFILES_FILE, {})
    u = str(uid)
    n = datetime.now().strftime("%Y-%m-%d %H:%M")
    t = datetime.now().strftime("%Y-%m-%d")
    if u not in p: p[u] = {"first_seen": n, "first_date": t, "last_seen": n, "total": 0, "daily": {}, "weekly": {}, "monthly": {}}
    p[u]["last_seen"], p[u]["total"], p[u]["name"] = n, p[u]["total"] + 1, uname
    p[u]["daily"][t] = p[u]["daily"].get(t, 0) + 1
    p[u]["weekly"][datetime.now().strftime("%Y-W%U")] = p[u]["weekly"].get(datetime.now().strftime("%Y-W%U"), 0) + 1
    p[u]["monthly"][datetime.now().strftime("%Y-%m")] = p[u]["monthly"].get(datetime.now().strftime("%Y-%m"), 0) + 1
    save_json(PROFILES_FILE, p)

def count_message(uid, uname):
    s = load_json(STATS_FILE, {})
    w = datetime.now().strftime("%Y-W%U")
    if w not in s: s[w] = {}
    u = str(uid)
    if u not in s[w]: s[w][u] = {"name": uname, "count": 0}
    s[w][u]["count"] += 1; s[w][u]["name"] = uname
    save_json(STATS_FILE, s)

def rp_enabled(): return load_json(RP_SETTINGS_FILE, {"rp": True, "marriages": True}).get("rp", True)
def marriages_enabled(): return load_json(RP_SETTINGS_FILE, {"rp": True, "marriages": True}).get("marriages", True)

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for m in update.message.new_chat_members:
        if m.is_bot: continue
        await update.message.reply_html(f"👋 Добро пожаловать, {get_user_link(m)}!\n\n📜 Правила: без 18+, без рекламы, без оскорблений\n🎉 Судные выходные: Суббота 12:00 - Понедельник 6:00\n\nПриятного общения! 😊")

async def filter_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private': return
    if update.effective_user and update.effective_user.is_bot:
        try: await update.message.delete()
        except: pass

async def message_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private': return
    if not update.message: return
    uid = update.effective_user.id
    if is_admin(uid) or uid == CREATOR_ID: return
    if update.message.photo or update.message.video or update.message.video_note:
        cap = update.message.caption.lower() if update.message.caption else ""
        for w in ["18+","порно","xxx","нюдс","nude","nudes","голые","интим","porn","adult","эротика","секс","sex","трах","слив","сливы","приват","приваты","onlyfans","only fans"]:
            if w in cap:
                try:
                    await update.message.delete()
                    await context.bot.restrict_chat_member(chat_id=update.effective_chat.id, user_id=uid, permissions=ChatPermissions(can_send_messages=False), until_date=datetime.now()+timedelta(hours=3))
                    await update.message.reply_html(f"🚫 {get_user_link(update.effective_user)} мут 3 часа за 18+!")
                except: pass
                return
        for w in ["убийство","смерть","самоубийство","расчленёнка","суицид","труп","жесть","кровь","кишки","отрезал","оторвал","смертельная","убил","зарезал"]:
            if w in cap:
                try:
                    await update.message.delete()
                    await context.bot.restrict_chat_member(chat_id=update.effective_chat.id, user_id=uid, permissions=ChatPermissions(can_send_messages=False), until_date=datetime.now()+timedelta(hours=4))
                    await update.message.reply_html(f"🚫 {get_user_link(update.effective_user)} мут 4 часа за шок-контент!")
                except: pass
                return
    if update.message.text:
        if any(x in update.message.text.lower() for x in ["http://","https://","t.me/"]):
            try:
                cm = await context.bot.get_chat_member(update.effective_chat.id, uid)
                if cm.status in ['administrator','creator']: return
            except: pass
            try:
                await update.message.delete()
                await update.message.reply_html(f"🚫 {get_user_link(update.effective_user)}, ссылки запрещены!")
            except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        kb = [[InlineKeyboardButton("🆘 Поддержка", callback_data="support")]]
        await update.message.reply_text("👋 Привет! Нажмите «Поддержка» чтобы написать администраторам.", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await help_command(update, context)

async def support_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "support":
        await q.message.reply_text("📝 Напишите ваше сообщение. Администраторы увидят его и ответят.")
        context.user_data['waiting_for_complaint'] = True

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    if not is_admin(uid) and uid != CREATOR_ID: return
    d = q.data; c = load_json(COMPLAINTS_FILE, {})
    if d.startswith("take_"):
        cid = d.replace("take_","")
        if cid in c and c[cid]["status"]=="open":
            c[cid]["status"]="in_progress"; c[cid]["admin_id"]=uid; save_json(COMPLAINTS_FILE, c)
            ch = load_json(CHATS_FILE, {}); ch[str(c[cid]["user_id"])]=cid; ch[str(uid)]=cid; save_json(CHATS_FILE, ch)
            try: await context.bot.send_message(chat_id=c[cid]["user_id"], text="✅ Администратор взял обращение.")
            except: pass
            await q.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Завершить", callback_data=f"close_{cid}")]]))
    elif d.startswith("close_"):
        cid = d.replace("close_","")
        if cid in c:
            u=c[cid]["user_id"]; a=c[cid].get("admin_id","")
            c[cid]["status"]="closed"; save_json(COMPLAINTS_FILE, c)
            ch = load_json(CHATS_FILE, {})
            if str(u) in ch: del ch[str(u)]
            if str(a) in ch: del ch[str(a)]
            save_json(CHATS_FILE, ch)
            try: await context.bot.send_message(chat_id=u, text="✅ Обращение закрыто. Спасибо!")
            except: pass
            await q.message.edit_reply_markup(reply_markup=None)

async def admin_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if not is_admin(q.from_user.id) and q.from_user.id != CREATOR_ID: return
    r = {"admin_ban":"🚫 Бан","admin_mute":"🔇 Мут","admin_warn":"⚠️ Пред","admin_unban":"✅ Разбан","admin_unmute":"🔊 Размут","admin_clear":"🧹 Очистка"}
    if q.data in r: await q.message.reply_text(f"{r[q.data]}: ответьте на сообщение и напишите команду.")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) and update.effective_user.id != CREATOR_ID:
        await update.message.reply_text("❌ Нет прав!"); return
    kb = [[InlineKeyboardButton("🚫 Бан", callback_data="admin_ban"), InlineKeyboardButton("🔇 Мут", callback_data="admin_mute")],
          [InlineKeyboardButton("⚠️ Пред", callback_data="admin_warn"), InlineKeyboardButton("✅ Разбан", callback_data="admin_unban")],
          [InlineKeyboardButton("🔊 Размут", callback_data="admin_unmute"), InlineKeyboardButton("🧹 Очистка", callback_data="admin_clear")]]
    await update.message.reply_text("👮 АДМИН-ПАНЕЛЬ", reply_markup=InlineKeyboardMarkup(kb))

async def clear_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) and update.effective_user.id != CREATOR_ID: return
    cnt = int(context.args[0]) if context.args and context.args[0].isdigit() else 10
    try:
        chat_id = update.effective_chat.id
        d = 0
        msg_id = update.message.message_id
        for _ in range(min(cnt, 100)):
            try:
                await context.bot.delete_message(chat_id, msg_id - 1 - _)
                d += 1
            except: pass
        await update.message.reply_text(f"🧹 Удалено {d}!")
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

async def private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private': return
    uid = update.effective_user.id; mt = update.message.text; ud = context.user_data
    if update.message.reply_to_message and (is_admin(uid) or uid == CREATOR_ID):
        rt = update.message.reply_to_message.text or ""
        if "ЖАЛОБА #" in rt:
            try:
                cid = rt.split("#")[1].split("\n")[0].strip()
                c = load_json(COMPLAINTS_FILE, {})
                if cid in c:
                    await context.bot.send_message(chat_id=c[cid]["user_id"], text=f"📩 Администратор:\n{mt}")
                    await update.message.reply_text("✅ Ответ отправлен!"); return
            except: pass
    if ud.get('waiting_for_complaint'):
        c = load_json(COMPLAINTS_FILE, {})
        cid = str(len(c)+1)
        c[cid] = {"user_id":uid,"username":update.effective_user.first_name,"text":mt,"status":"open","admin_id":None}
        save_json(COMPLAINTS_FILE, c)
        await update.message.reply_text("✅ Отправлено!"); ud['waiting_for_complaint'] = False
        adm = load_json(ADMINS_FILE, [CREATOR_ID])
        kb = [[InlineKeyboardButton("🔧 Заняться", callback_data=f"take_{cid}")]]
        for aid in adm:
            if aid != uid:
                try: await context.bot.send_message(chat_id=aid, text=f"📩 НОВАЯ ЖАЛОБА #{cid}\nОт: {update.effective_user.first_name}\n\n{mt}", reply_markup=InlineKeyboardMarkup(kb))
                except: pass
        return
    ch = load_json(CHATS_FILE, {})
    if str(uid) in ch:
        c = load_json(COMPLAINTS_FILE, {}); cid = ch[str(uid)]
        if cid in c and c[cid]["status"]=="in_progress":
            if is_admin(uid) or uid==CREATOR_ID:
                try: await context.bot.send_message(chat_id=c[cid]["user_id"], text=f"📩 Администратор:\n{mt}")
                except: pass
            else:
                aid = c[cid].get("admin_id")
                if aid:
                    try: await context.bot.send_message(chat_id=aid, text=f"📩 {update.effective_user.first_name}:\n{mt}")
                    except: pass
            return
    if not (is_admin(uid) or uid==CREATOR_ID):
        kb = [[InlineKeyboardButton("🆘 Поддержка", callback_data="support")]]
        await update.message.reply_text("Нажмите кнопку для обращения.", reply_markup=InlineKeyboardMarkup(kb))
# БАН
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    if u.id == CREATOR_ID: return
    if is_admin(u.id) and update.effective_user.id != CREATOR_ID: return
    bt = 0
    if context.args:
        try:
            if len(context.args)==1 and context.args[0].isdigit(): bt=int(context.args[0])
            elif len(context.args)>=2:
                n=int(context.args[0]); un=context.args[1].lower()
                if un in ["м","мин","минута","минуты","минут"]: bt=n
                elif un in ["ч","час","часа","часов"]: bt=n*60
                elif un in ["д","день","дня","дней"]: bt=n*1440
                elif un in ["н","нед","неделя","недели","недель"]: bt=n*10080
                elif un in ["мес","месяц","месяца","месяцев"]: bt=n*43200
        except: pass
    try:
        if bt>0:
            await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=u.id, until_date=datetime.now()+timedelta(minutes=bt))
            if bt>=43200: t=f"{bt//43200} мес"
            elif bt>=10080: t=f"{bt//10080} нед"
            elif bt>=1440: t=f"{bt//1440} дн"
            elif bt>=60: t=f"{bt//60} ч"
            else: t=f"{bt} мин"
            await update.message.reply_html(f"🚫 {get_user_link(u)} забанен на {t}!")
        else:
            await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=u.id)
            await update.message.reply_html(f"🚫 {get_user_link(u)} забанен навсегда!")
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    try:
        await context.bot.unban_chat_member(chat_id=update.effective_chat.id, user_id=u.id)
        await update.message.reply_html(f"✅ {get_user_link(u)} разбанен!")
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=u.id)
        await context.bot.unban_chat_member(chat_id=update.effective_chat.id, user_id=u.id)
        await update.message.reply_html(f"👢 {get_user_link(u)} исключён!")
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

async def kick_silent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    try:
        await update.message.delete()
        await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=u.id)
        await context.bot.unban_chat_member(chat_id=update.effective_chat.id, user_id=u.id)
    except: pass

async def amnesty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        c = 0
        async for m in context.bot.get_chat_members(update.effective_chat.id, filter="kicked"):
            try: await context.bot.unban_chat_member(chat_id=update.effective_chat.id, user_id=m.user.id); c+=1
            except: pass
        await update.message.reply_text(f"✅ Снято {c} банов!")
    except: pass

async def banlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        text = "📋 ЗАБАНЕННЫЕ:\n"; c=0
        async for m in context.bot.get_chat_members(update.effective_chat.id, filter="kicked"):
            text += f"• {m.user.first_name}\n"; c+=1
            if c>=50: break
        await update.message.reply_text(text if c>0 else "📋 Нет забаненных")
    except: pass

# МУТ
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    if u.id == CREATOR_ID: return
    if is_admin(u.id) and update.effective_user.id != CREATOR_ID: return
    mt = 10080
    if context.args:
        try:
            if len(context.args)==1 and context.args[0].isdigit(): mt=int(context.args[0])
            elif len(context.args)>=2:
                n=int(context.args[0]); un=context.args[1].lower()
                if un in ["м","мин","минута","минуты","минут"]: mt=n
                elif un in ["ч","час","часа","часов"]: mt=n*60
                elif un in ["д","день","дня","дней"]: mt=n*1440
                elif un in ["н","нед","неделя","недели","недель"]: mt=n*10080
        except: pass
    if mt>=10080: t=f"{mt//10080} нед"
    elif mt>=1440: t=f"{mt//1440} дн"
    elif mt>=60: t=f"{mt//60} ч"
    else: t=f"{mt} мин"
    try:
        await context.bot.restrict_chat_member(chat_id=update.effective_chat.id, user_id=u.id, permissions=ChatPermissions(can_send_messages=False), until_date=datetime.now()+timedelta(minutes=mt))
        await update.message.reply_html(f"🔇 {get_user_link(u)} замучен на {t}!")
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(chat_id=update.effective_chat.id, user_id=u.id, permissions=ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True))
        await update.message.reply_html(f"🔊 {get_user_link(u)} размучен!")
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

async def mutelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("📋 Список замученных: проверьте права участников в настройках чата.")

# ПРЕД
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    reason = " ".join(context.args) if context.args else "Нарушение правил"
    await update.message.reply_html(f"⚠️ ПРЕДУПРЕЖДЕНИЕ\nПользователь: {get_user_link(u)}\nПричина: {reason}")

# АДМИН-КОМАНДЫ
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != CREATOR_ID:
        await update.message.reply_text("❌ Только создатель!"); return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение!"); return
    u = update.message.reply_to_message.from_user
    a = load_json(ADMINS_FILE, [CREATOR_ID])
    if u.id in a: await update.message.reply_text("❌ Уже администратор!"); return
    a.append(u.id); save_json(ADMINS_FILE, a)
    await update.message.reply_html(f"✅ {get_user_link(u)} теперь администратор!")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != CREATOR_ID:
        await update.message.reply_text("❌ Только создатель!"); return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение!"); return
    u = update.message.reply_to_message.from_user
    a = load_json(ADMINS_FILE, [CREATOR_ID])
    if u.id == CREATOR_ID: await update.message.reply_text("❌ Нельзя снять создателя!"); return
    if u.id not in a: await update.message.reply_text(f"❌ {u.first_name} не администратор!"); return
    a.remove(u.id); save_json(ADMINS_FILE, a)
    await update.message.reply_html(f"✅ {get_user_link(u)} больше не администратор!")

async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    lvl = int(context.args[0]) if context.args and context.args[0].isdigit() else 1
    ranks = {1:"Младший модератор",2:"Старший модератор",3:"Младший администратор",4:"Старший администратор",5:"Создатель"}
    await update.message.reply_html(f"⬆ {get_user_link(u)} повышен до «{ranks.get(lvl, ranks[1])}»!")

# ПРОФИЛЬ
async def who_am_i(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user; uid = str(u.id)
    p = load_json(PROFILES_FILE, {}); n = load_json(NICKNAMES_FILE, {})
    t = load_json(TITLES_FILE, {}); r = load_json(REP_FILE, {})
    name = get_display_name(u); prof = p.get(uid, {})
    total = prof.get("total", 0); first = prof.get("first_date", "неизвестно")
    last = prof.get("last_seen", "неизвестно")
    today = datetime.now().strftime("%Y-%m-%d")
    week = datetime.now().strftime("%Y-W%U")
    month = datetime.now().strftime("%Y-%m")
    dc = prof.get("daily", {}).get(today, 0)
    wc = prof.get("weekly", {}).get(week, 0)
    mc = prof.get("monthly", {}).get(month, 0)
    ur = r.get(uid, {"plus":0,"minus":0})
    txt = f"👤 Это пользователь {get_user_link(u)}\n"
    if is_admin(u.id): txt += "👨🏻‍💼 Администратор чата\n"
    if uid == str(CREATOR_ID): txt += "👑 Создатель чата\n"
    txt += f"\n⭐ [{total}] Ранг: {get_rank(total)}\n"
    txt += f"Репутация: ✨ {ur.get('plus',0)} | ➕ {ur.get('plus',0)-ur.get('minus',0)}\n"
    txt += f"Первое появление: {first}\nПоследний актив: {last}\n"
    txt += f"Актив (д|н|м|весь): {dc} | {wc} | {mc} | {total}\n"
    if uid in t and t[uid]:
        txt += "\n🏆 НАГРАДЫ:\n"
        for tw in t[uid][-5:]: txt += f"🎗 {tw['title']} от {tw['from']}, {tw['date']}\n"
    await update.message.reply_html(txt)

async def award(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    if not context.args: return
    u = update.message.reply_to_message.from_user
    title = " ".join(context.args)
    t = load_json(TITLES_FILE, {})
    if str(u.id) not in t: t[str(u.id)] = []
    t[str(u.id)].append({"title":title,"from":update.effective_user.first_name,"date":datetime.now().strftime("%d.%m.%Y")})
    save_json(TITLES_FILE, t)
    await update.message.reply_html(f"🎖 {get_user_link(u)} получает звание «{title}» от {get_user_link(update.effective_user)}!")

async def set_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    nick = " ".join(context.args)
    n = load_json(NICKNAMES_FILE, {})
    n[str(update.effective_user.id)] = {"name":update.effective_user.first_name,"nick":nick}
    save_json(NICKNAMES_FILE, n)
    await update.message.reply_html(f"✅ Теперь вы «{nick}»!")

async def rep_plus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    if update.message.reply_to_message.from_user.id == update.effective_user.id: return
    u = update.message.reply_to_message.from_user
    r = load_json(REP_FILE, {})
    if str(u.id) not in r: r[str(u.id)] = {"plus":0,"minus":0}
    r[str(u.id)]["plus"] += 1; save_json(REP_FILE, r)
    await update.message.reply_html(f"✨ {get_user_link(update.effective_user)} повысил репутацию {get_user_link(u)}!")

async def rep_minus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    if update.message.reply_to_message.from_user.id == update.effective_user.id: return
    u = update.message.reply_to_message.from_user
    r = load_json(REP_FILE, {})
    if str(u.id) not in r: r[str(u.id)] = {"plus":0,"minus":0}
    r[str(u.id)]["minus"] += 1; save_json(REP_FILE, r)
    await update.message.reply_html(f"👎 {get_user_link(update.effective_user)} понизил репутацию {get_user_link(u)}!")

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        u = update.message.reply_to_message.from_user
        await update.message.reply_text(f"🆔 {get_display_name(u)}: `{u.id}`", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"🆔 Ваш ID: `{update.effective_user.id}`", parse_mode='Markdown')

# НАСТРОЙКИ
async def toggle_rp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    s = load_json(RP_SETTINGS_FILE, {"rp":True,"marriages":True})
    m = update.message.text.lower().strip()
    if m in ["+рп","+rp"]: s["rp"]=True; await update.message.reply_text("✅ РП включены!")
    elif m in ["-рп","-rp"]: s["rp"]=False; await update.message.reply_text("❌ РП выключены!")
    elif m in ["+браки","+брак"]: s["marriages"]=True; await update.message.reply_text("✅ Браки включены!")
    elif m in ["-браки","-брак"]: s["marriages"]=False; await update.message.reply_text("❌ Браки выключены!")
    save_json(RP_SETTINGS_FILE, s)
# БРАК
async def marry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not marriages_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    if a.id == b.id: return
    m = load_json(MARRIAGES_FILE, {})
    if str(a.id) in m: await update.message.reply_html(f"❌ Вы уже в браке с {m[str(a.id)]['name']}!"); return
    if str(b.id) in m: await update.message.reply_html(f"❌ {get_user_link(b)} уже в браке!"); return
    p = load_json(PROPOSALS_FILE, {})
    p[str(b.id)] = {"from_id":a.id,"from_name":a.first_name,"to_name":b.first_name}
    save_json(PROPOSALS_FILE, p)
    kb = [[InlineKeyboardButton("💍 Согласиться", callback_data=f"accept_marry_{a.id}"), InlineKeyboardButton("❌ Отказаться", callback_data=f"decline_marry_{a.id}")]]
    await update.message.reply_html(f"💍 {get_user_link(a)} предложил(а) {get_user_link(b)} вступить в брак!\n{b.first_name}, нажмите кнопку:", reply_markup=InlineKeyboardMarkup(kb))

async def marry_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid, d = q.from_user.id, q.data
    if d.startswith("accept_marry_"):
        fid = int(d.replace("accept_marry_",""))
        p = load_json(PROPOSALS_FILE, {})
        if str(uid) in p and p[str(uid)]["from_id"]==fid:
            m = load_json(MARRIAGES_FILE, {})
            m[str(fid)] = {"partner_id":uid,"name":p[str(uid)]["to_name"]}
            m[str(uid)] = {"partner_id":fid,"name":p[str(uid)]["from_name"]}
            save_json(MARRIAGES_FILE, m)
            await q.message.edit_text(f"💒 {p[str(uid)]['from_name']} и {p[str(uid)]['to_name']} теперь в браке! 🎉💍")
            del p[str(uid)]; save_json(PROPOSALS_FILE, p)
    elif d.startswith("decline_marry_"):
        p = load_json(PROPOSALS_FILE, {})
        if str(uid) in p:
            await q.message.edit_text(f"💔 {p[str(uid)]['to_name']} отказал(а) {p[str(uid)]['from_name']}.")
            del p[str(uid)]; save_json(PROPOSALS_FILE, p)

async def divorce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not marriages_enabled(): return
    u = update.effective_user; m = load_json(MARRIAGES_FILE, {})
    if str(u.id) not in m: await update.message.reply_text("❌ Вы не в браке!"); return
    kb = [[InlineKeyboardButton("💔 Да", callback_data=f"confirm_divorce_{u.id}"), InlineKeyboardButton("❤️ Нет", callback_data="cancel_divorce")]]
    await update.message.reply_text(f"💔 Развестись с {m[str(u.id)]['name']}?", reply_markup=InlineKeyboardMarkup(kb))

async def divorce_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    if q.data.startswith("confirm_divorce_"):
        m = load_json(MARRIAGES_FILE, {})
        if str(uid) in m:
            pid, pname = m[str(uid)]["partner_id"], m[str(uid)]["name"]
            del m[str(uid)]
            if str(pid) in m: del m[str(pid)]
            save_json(MARRIAGES_FILE, m)
            await q.message.edit_text(f"💔 {q.from_user.first_name} развёлся с {pname} 😢")
    elif q.data == "cancel_divorce": await q.message.edit_text("❤️ Развод отменён!")

async def marriage_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not marriages_enabled(): return
    m = load_json(MARRIAGES_FILE, {})
    if str(update.effective_user.id) in m: await update.message.reply_html(f"💍 Вы в браке с {m[str(update.effective_user.id)]['name']}")
    else: await update.message.reply_text("💔 Вы не в браке")

async def marriage_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not marriages_enabled(): return
    m = load_json(MARRIAGES_FILE, {})
    if not m: await update.message.reply_text("💔 В чате пока нет браков!"); return
    pairs, text = set(), "💍 СПИСОК БРАКОВ:\n\n"
    for uid, data in m.items():
        pid = str(data["partner_id"])
        pair = tuple(sorted([uid, pid]))
        if pair not in pairs:
            pairs.add(pair)
            text += f"• {data['name']} ❤️ {m[pid]['name']}\n"
    await update.message.reply_text(text)

# РП-КОМАНДЫ
async def hug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"🫂 {get_user_link(a)} обнял(а) {get_user_link(b)}!")

async def kiss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"💋 {get_user_link(a)} поцеловал(а) {get_user_link(b)}!")

async def bite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"🦷 {get_user_link(a)} укусил(а) {get_user_link(b)}!")

async def slap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"👋 {get_user_link(a)} ударил(а) {get_user_link(b)}!")

async def pat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"🤚 {get_user_link(a)} погладил(а) {get_user_link(b)}!")

async def lick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"👅 {get_user_link(a)} лизнул(а) {get_user_link(b)}!")

async def poke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"👉 {get_user_link(a)} тыкнул(а) {get_user_link(b)}!")

async def spank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"🍑 {get_user_link(a)} шлёпнул(а) {get_user_link(b)}!")

async def choke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"😤 {get_user_link(a)} задушил(а) {get_user_link(b)}!")

async def wink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"😉 {get_user_link(a)} подмигнул(а) {get_user_link(b)}!")

async def praise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"👏 {get_user_link(a)} похвалил(а) {get_user_link(b)}!")

async def insult(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"😠 {get_user_link(a)} обидел(а) {get_user_link(b)}!")

async def run_away(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    await update.message.reply_html(f"🏃 {get_user_link(update.effective_user)} убегает!")

async def come_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    await update.message.reply_html(f"🚶 {get_user_link(update.effective_user)} возвращается!")

async def laugh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    await update.message.reply_html(f"😂 {get_user_link(update.effective_user)} смеётся!")

async def cry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    await update.message.reply_html(f"😭 {get_user_link(update.effective_user)} плачет!")

async def angry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    await update.message.reply_html(f"😡 {get_user_link(update.effective_user)} злится!")

async def happy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    await update.message.reply_html(f"😊 {get_user_link(update.effective_user)} радуется!")

async def sad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    await update.message.reply_html(f"😔 {get_user_link(update.effective_user)} грустит!")

async def sleep_rp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    await update.message.reply_html(f"😴 {get_user_link(update.effective_user)} спит!")

async def eat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    await update.message.reply_html(f"🍽 {get_user_link(update.effective_user)} кушает!")

async def drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    await update.message.reply_html(f"🍹 {get_user_link(update.effective_user)} пьёт!")

async def fuck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"😩 | {get_user_link(a)} принудил к жёсткому интиму {get_user_link(b)}!")

async def touch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"🖐 {get_user_link(a)} потрогал(а) {get_user_link(b)}!")

async def steal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"🦹 {get_user_link(a)} украл(а) у {get_user_link(b)} всё!")

async def give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"🎁 {get_user_link(a)} отдал(а) подарок {get_user_link(b)}!")

async def throw_rp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"🤾 {get_user_link(a)} бросил(а) в {get_user_link(b)} чем-то!")

async def lift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a,b = update.effective_user, update.message.reply_to_message.from_user
    await update.message.reply_html(f"💪 {get_user_link(a)} поднял(а) {get_user_link(b)}!")
# ИГРЫ
async def who(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    t = update.message.reply_to_message.from_user
    name = get_user_link(t)
    actions = [f"🍕 {name} сегодня угощает всех пиццей!", f"💩 {name} сегодня ходит в туалет чаще всех!",
        f"🎂 {name} сегодня именинник!", f"🤡 {name} сегодня главный клоун!",
        f"💤 {name} сегодня проспал всё!", f"🦸 {name} сегодня спасает мир!",
        f"🎮 {name} сегодня задрот дня!", f"🍔 {name} сегодня съел больше всех!",
        f"💸 {name} сегодня платит за всех!", f"🎉 {name} сегодня душа компании!"]
    await update.message.reply_html(random.choice(actions))

async def ball(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = " ".join(context.args) if context.args else "Без вопроса"
    answers = ["✅ Да","❌ Нет","🤔 Возможно","🌟 Определённо да","💔 Не сейчас","🎱 Спроси позже","👍 Хорошие шансы","👎 Плохие шансы"]
    await update.message.reply_text(f"🎱 {question}\n{random.choice(answers)}")

async def coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🪙 {random.choice(['Орёл','Решка'])}!")

async def choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    text = " ".join(context.args)
    options = [x.strip() for x in text.split("или")]
    if len(options) < 2: return
    await update.message.reply_html(f"🤔 Я выбираю: <b>{random.choice(options)}</b>!")

async def roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    actions = [
        ("🔫 БАХ!", f"{get_user_link(u)} получает мут на 10 минут!"),
        ("💨 Промах!", f"{get_user_link(u)} повезло — пуля пролетела мимо!"),
        ("💥 Рикошет!", f"{get_user_link(update.effective_user)} попал в себя! Мут на 5 минут."),
    ]
    action, text = random.choice(actions)
    await update.message.reply_html(f"🎰 РУЛЕТКА\n{action}\n{text}")

# СТАТИСТИКА
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) and update.effective_user.id != CREATOR_ID: return
    s = load_json(STATS_FILE, {})
    w = datetime.now().strftime("%Y-W%U")
    if w not in s or not s[w]: await update.message.reply_text("📊 Нет данных за эту неделю!"); return
    su = sorted(s[w].items(), key=lambda x: x[1]["count"], reverse=True)
    text = f"📊 СТАТИСТИКА ЗА НЕДЕЛЮ:\n\n"
    for i, (uid, data) in enumerate(su[:20], 1): text += f"{i}. {data['name']} — {data['count']} сообщений\n"
    await update.message.reply_text(text)

async def top_rep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = load_json(REP_FILE, {})
    if not r: await update.message.reply_text("📊 Нет данных!"); return
    sr = sorted(r.items(), key=lambda x: x[1]["plus"]-x[1].get("minus",0), reverse=True)
    text = "🏆 ТОП РЕПУТАЦИИ:\n\n"
    for i, (uid, data) in enumerate(sr[:15], 1):
        nicks = load_json(NICKNAMES_FILE, {})
        name = nicks.get(uid, {}).get("nick", data.get("name","User"))
        text += f"{i}. {name} — ✨{data['plus']} ({data['plus']-data.get('minus',0)})\n"
    await update.message.reply_text(text)

# СУДНЫЕ ВЫХОДНЫЕ
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

# НАБОР
async def admin_recruitment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("📋 Пример анкеты", url=EXAMPLE_APPLICATION)],[InlineKeyboardButton("📝 Подать заявку", url=APPLICATION_LINK)]]
    await update.message.reply_text("👑 НАБОР В АДМИНИСТРАЦИЮ!\n\n📋 Требования: 14+, активность, ответственность\n\n📸 Пример анкеты\n📝 Подать заявку", reply_markup=InlineKeyboardMarkup(kb))

# ПОМОЩЬ
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 КОМАНДЫ БОТА:\n\n"
        "👑 Выдать админа, Разжаловать, Повысить [1-5]\n"
        "⚙ +Рп/-Рп, +Браки/-Браки\n\n"
        "🚫 Бан, !ban, ЧС, Разбан, !unban, Вернуть, Кик, !kick, Кик тихо, !Амнистия, Банлист\n"
        "🔇 Мут, Заткнуть, mute, Размут, Говори, unmute, -Мут\n"
        "⚠️ Пред, !warn\n"
        "🧹 Очистка, Выходные\n\n"
        "💍 Брак, Развод, Семья, Браки\n"
        "👤 Кто я, +, -, +ник, Наградить, !ид, Топ репутации\n"
        "📊 Стата, Статистика, Топ\n"
        "🎮 Кто, Шар, Монетка, Выбери, Рулетка\n\n"
        "🎭 РП: Обнять, Поцеловать, Укусить, Ударить, Погладить, Лизнуть, Тыкнуть, Шлёпнуть, Задушить, Подмигнуть, Похвалить, Обидеть, Убежать, Вернуться, Смеяться, Плакать, Злиться, Радоваться, Грустить, Спать, Кушать, Пить, Выебать, Потрогать, Украсть, Отдать, Бросить, Поднять\n\n"
        "📢 Помощь, Правила, Набор\n🆘 ЛС: Поддержка\nℹ️ Бот, Боты, Bot"
    )

# ПРАВИЛА
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🗓 ПРАВИЛА ЧАТА\n\nДобро пожаловать в чат! Мы рады всем новичкам.\n\n"
        "❌ Реклама — бан.\n❌ Контент 18+ — мут 3ч/бан.\n❌ Оскорбление админов — мут 2ч/бан.\n"
        "❌ Оскорбление религии/нации — мут 30мин.\n❌ Спам/флуд — мут 30мин.\n"
        "❌ Попрошайничество — мут 30мин.\n❌ Политика — мут 2ч.\n❌ Шок-контент — мут 4ч/бан.\n"
        "❌ Оскорбление участников — мут 1ч.\n❌ Провокации — мут 1ч.\n"
        "❌ Обход наказания — бан 24ч.\n❌ Продажа аккаунтов — мут 3ч.\n\n"
        "👮 Админы: без угроз, соблюдать субординацию\n\n"
        "🎉 Судные выходные: Суббота 12:00 - Понедельник 6:00\nПриятного общения!"
    )

# ОБРАБОТЧИК КОМАНД
async def text_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    msg = update.message.text.lower().strip()
    update_profile(update.effective_user.id, update.effective_user.first_name)
    
    if msg in ["бот","боты","bot"]:
        await update.message.reply_text("👋 Я здесь! Напишите «Помощь» для списка команд.")
        return
    
    # Общие
    if msg=="помощь": await help_command(update, context)
    elif msg=="правила": await rules(update, context)
    elif msg=="набор": await admin_recruitment(update, context)
    elif msg=="старт": await start(update, context)
    elif msg=="админка": await admin_panel(update, context)
    
    # Админ
    elif msg in ["выдать админа", "сделать админом"]: await add_admin(update, context)
    elif msg in ["разжаловать", "снять", "снять админа", "убрать админа"]: await remove_admin(update, context)
    elif msg.startswith("повысить"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await promote(update, context)
    elif msg in ["+рп","-рп","+браки","-браки","+rp","-rp"]: await toggle_rp(update, context)
    
    # Бан
    elif msg.startswith("бан") or msg in ["чс","!ban","!permban"]:
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await ban(update, context)
    elif msg in ["разбан","вернуть","!unban"]: await unban(update, context)
    elif msg=="кик" or msg=="!kick": await kick(update, context)
    elif msg=="кик тихо": await kick_silent(update, context)
    elif msg=="!амнистия": await amnesty(update, context)
    elif msg=="банлист": await banlist(update, context)
    
    # Мут
    elif msg.startswith("мут") or msg in ["заткнуть","mute"]:
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await mute(update, context)
    elif msg in ["размут","снять мут","говори","unmute","-мут"]: await unmute(update, context)
    elif msg=="муты": await mutelist(update, context)
    
    # Пред
    elif msg.startswith("пред") or msg=="!warn":
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await warn(update, context)
    elif msg.startswith("очистка"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await clear_messages(update, context)
    elif msg=="выходные": await schedule_weekend(update, context)
    elif msg in ["судные выходные", "отправить выходные"]: await send_weekend_message(update=update, context=context)
    
    # Брак
    elif msg=="брак": await marry(update, context)
    elif msg=="развод": await divorce(update, context)
    elif msg in ["семья","моя семья"]: await marriage_info(update, context)
    elif msg in ["браки","список браков"]: await marriage_list(update, context)
    
    # Профиль
    elif msg=="кто я": await who_am_i(update, context)
    elif msg=="+": await rep_plus(update, context)
    elif msg=="-": await rep_minus(update, context)
    elif msg.startswith("+ник") or msg.startswith("+ ник"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await set_nick(update, context)
    elif msg.startswith("наградить"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await award(update, context)
    elif msg=="!ид": await get_id(update, context)
    elif msg=="топ репутации": await top_rep(update, context)
    elif msg in ["стата","статистика","топ"]: await stats(update, context)
    
    # Игры
    elif msg=="кто": await who(update, context)
    elif msg=="шар":
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await ball(update, context)
    elif msg=="монетка": await coin(update, context)
    elif msg.startswith("выбери"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await choose(update, context)
    elif msg=="рулетка": await roulette(update, context)
    
    # РП
    elif msg=="обнять": await hug(update, context)
    elif msg=="поцеловать": await kiss(update, context)
    elif msg=="укусить": await bite(update, context)
    elif msg=="ударить": await slap(update, context)
    elif msg=="погладить": await pat(update, context)
    elif msg=="лизнуть": await lick(update, context)
    elif msg=="тыкнуть": await poke(update, context)
    elif msg=="шлёпнуть": await spank(update, context)
    elif msg=="задушить": await choke(update, context)
    elif msg=="подмигнуть": await wink(update, context)
    elif msg=="похвалить": await praise(update, context)
    elif msg=="обидеть": await insult(update, context)
    elif msg=="убежать": await run_away(update, context)
    elif msg=="вернуться": await come_back(update, context)
    elif msg=="смеяться": await laugh(update, context)
    elif msg=="плакать": await cry(update, context)
    elif msg=="злиться": await angry(update, context)
    elif msg=="радоваться": await happy(update, context)
    elif msg=="грустить": await sad(update, context)
    elif msg=="спать": await sleep_rp(update, context)
    elif msg=="кушать": await eat(update, context)
    elif msg=="пить": await drink(update, context)
    elif msg=="выебать": await fuck(update, context)
    elif msg=="потрогать": await touch(update, context)
    elif msg=="украсть": await steal(update, context)
    elif msg=="отдать": await give(update, context)
    elif msg=="бросить": await throw_rp(update, context)
    elif msg=="поднять": await lift(update, context)
def main():
    application = Application.builder().token(TOKEN).concurrent_updates(True).build()
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("kick", kick))
    application.add_handler(CommandHandler("amnesty", amnesty))
    application.add_handler(CommandHandler("banlist", banlist))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("unmute", unmute))
    application.add_handler(CommandHandler("warn", warn))
    application.add_handler(CommandHandler("hug", hug))
    application.add_handler(CommandHandler("kiss", kiss))
    application.add_handler(CommandHandler("bite", bite))
    application.add_handler(CommandHandler("slap", slap))
    application.add_handler(CommandHandler("pat", pat))
    application.add_handler(CommandHandler("lick", lick))
    application.add_handler(CommandHandler("poke", poke))
    application.add_handler(CommandHandler("spank", spank))
    application.add_handler(CommandHandler("choke", choke))
    application.add_handler(CommandHandler("wink", wink))
    application.add_handler(CommandHandler("praise", praise))
    application.add_handler(CommandHandler("insult", insult))
    application.add_handler(CommandHandler("run_away", run_away))
    application.add_handler(CommandHandler("come_back", come_back))
    application.add_handler(CommandHandler("laugh", laugh))
    application.add_handler(CommandHandler("cry", cry))
    application.add_handler(CommandHandler("angry", angry))
    application.add_handler(CommandHandler("happy", happy))
    application.add_handler(CommandHandler("sad", sad))
    application.add_handler(CommandHandler("sleep_rp", sleep_rp))
    application.add_handler(CommandHandler("eat", eat))
    application.add_handler(CommandHandler("drink", drink))
    application.add_handler(CommandHandler("fuck", fuck))
    application.add_handler(CommandHandler("touch", touch))
    application.add_handler(CommandHandler("steal", steal))
    application.add_handler(CommandHandler("give", give))
    application.add_handler(CommandHandler("throw_rp", throw_rp))
    application.add_handler(CommandHandler("lift", lift))
    application.add_handler(CommandHandler("who", who))
    application.add_handler(CommandHandler("ball", ball))
    application.add_handler(CommandHandler("coin", coin))
    application.add_handler(CommandHandler("choose", choose))
    application.add_handler(CommandHandler("roulette", roulette))
    application.add_handler(CommandHandler("marry", marry))
    application.add_handler(CommandHandler("divorce", divorce))
    application.add_handler(CommandHandler("marriages", marriage_list))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("top_rep", top_rep))
    application.add_handler(CommandHandler("award", award))
    application.add_handler(CommandHandler("set_nick", set_nick))
    application.add_handler(CommandHandler("who_am_i", who_am_i))
    application.add_handler(CommandHandler("get_id", get_id))
    application.add_handler(CommandHandler("rep_plus", rep_plus))
    application.add_handler(CommandHandler("rep_minus", rep_minus))
    application.add_handler(CommandHandler("promote", promote))
    application.add_handler(CommandHandler("toggle_rp", toggle_rp))
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
    PORT = int(os.environ.get("PORT", 8443))
    WEBHOOK_URL = "https://support-bot-dwl0.onrender.com"
    print("✅ Бот запущен!")
    application.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=f"{WEBHOOK_URL}/webhook", secret_token="mysecret123")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
