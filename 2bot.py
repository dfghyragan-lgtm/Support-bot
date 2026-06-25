import logging, os, json, random
from datetime import datetime, time, timedelta, timezone
from collections import defaultdict
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, JobQueue, CallbackQueryHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8240444405:AAGulbNBUspFbtIFAu55XDqmMTLBQ4uF17g"
MOSCOW_TZ = timezone(timedelta(hours=3))
ADMINS_FILE = "admins.json"
COMPLAINTS_FILE = "complaints.json"
MARRIAGES_FILE = "marriages.json"
PROPOSALS_FILE = "proposals.json"
CHATS_FILE = "active_chats.json"
STATS_FILE = "stats.json"
NICKNAMES_FILE = "nicknames.json"
TITLES_FILE = "titles.json"
REP_FILE = "reputation.json"
PROFILES_FILE = "profiles.json"
RP_SETTINGS_FILE = "rp_settings.json"
WARNS_FILE = "warns.json"
WARN_SETTINGS_FILE = "warn_settings.json"
BAN_REASONS_FILE = "ban_reasons.json"
MUTE_REASONS_FILE = "mute_reasons.json"
CAPTCHA_FILE = "captcha.json"
CREATOR_ID = 8432323388
CHAT_ID = -1002753124436
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

def update_profile(uid, uname, cid=None):
    p = load_json(PROFILES_FILE, {})
    u = str(uid)
    n = datetime.now().strftime("%Y-%m-%d %H:%M")
    t = datetime.now().strftime("%Y-%m-%d")
    w = datetime.now().strftime("%Y-W%U")
    m = datetime.now().strftime("%Y-%m")
    if u not in p:
        p[u] = {"first_seen": n, "first_date": t, "last_seen": n, "total": 0, "total_chat": 0,
                "daily": {}, "weekly": {}, "monthly": {}, "daily_chat": {}, "weekly_chat": {}, "monthly_chat": {}}
    p[u]["last_seen"] = n
    p[u]["total"] += 1
    p[u]["name"] = uname
    p[u]["daily"][t] = p[u]["daily"].get(t, 0) + 1
    p[u]["weekly"][w] = p[u]["weekly"].get(w, 0) + 1
    p[u]["monthly"][m] = p[u]["monthly"].get(m, 0) + 1
    if cid:
        ck = str(cid)
        p[u]["total_chat"] = p[u].get("total_chat", 0) + 1
        if "daily_chat" not in p[u]: p[u]["daily_chat"] = {}
        if "weekly_chat" not in p[u]: p[u]["weekly_chat"] = {}
        if "monthly_chat" not in p[u]: p[u]["monthly_chat"] = {}
        p[u]["daily_chat"][f"{ck}_{t}"] = p[u]["daily_chat"].get(f"{ck}_{t}", 0) + 1
        p[u]["weekly_chat"][f"{ck}_{w}"] = p[u]["weekly_chat"].get(f"{ck}_{w}", 0) + 1
        p[u]["monthly_chat"][f"{ck}_{m}"] = p[u]["monthly_chat"].get(f"{ck}_{m}", 0) + 1
    save_json(PROFILES_FILE, p)
    count_message(uid, uname, cid)

def count_message(uid, uname, cid=None):
    s = load_json(STATS_FILE, {})
    w = datetime.now().strftime("%Y-W%U")
    if w not in s: s[w] = {"total": {}, "chats": {}}
    u = str(uid)
    if u not in s[w]["total"]: s[w]["total"][u] = {"name": uname, "count": 0}
    s[w]["total"][u]["count"] += 1
    s[w]["total"][u]["name"] = uname
    if cid:
        ck = str(cid)
        if ck not in s[w]["chats"]: s[w]["chats"][ck] = {}
        if u not in s[w]["chats"][ck]: s[w]["chats"][ck][u] = {"name": uname, "count": 0}
        s[w]["chats"][ck][u]["count"] += 1
        s[w]["chats"][ck][u]["name"] = uname
    save_json(STATS_FILE, s)

def rp_enabled(): return load_json(RP_SETTINGS_FILE, {"rp": True, "marriages": True}).get("rp", True)
def marriages_enabled(): return load_json(RP_SETTINGS_FILE, {"rp": True, "marriages": True}).get("marriages", True)

# СИСТЕМА ВАРНОВ
def add_warn(user_id, chat_id, reason="", period_days=7):
    w = load_json(WARNS_FILE, {})
    ck = str(chat_id); uk = str(user_id)
    if ck not in w: w[ck] = {}
    if uk not in w[ck]: w[ck][uk] = []
    w[ck][uk].append({"reason": reason, "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "expire": (datetime.now() + timedelta(days=period_days)).strftime("%Y-%m-%d %H:%M"), "active": True})
    save_json(WARNS_FILE, w)
    return len(w[ck][uk])

def remove_last_warn(user_id, chat_id):
    w = load_json(WARNS_FILE, {})
    ck = str(chat_id); uk = str(user_id)
    if ck in w and uk in w[ck] and w[ck][uk]:
        w[ck][uk][-1]["active"] = False
        save_json(WARNS_FILE, w)
        return True
    return False

def remove_warns_count(user_id, chat_id, count):
    w = load_json(WARNS_FILE, {})
    ck = str(chat_id); uk = str(user_id)
    if ck in w and uk in w[ck]:
        removed = 0
        for warn in reversed(w[ck][uk]):
            if warn["active"] and removed < count:
                warn["active"] = False
                removed += 1
        save_json(WARNS_FILE, w)
        return removed
    return 0

def remove_warn_by_number(user_id, chat_id, num):
    w = load_json(WARNS_FILE, {})
    ck = str(chat_id); uk = str(user_id)
    if ck in w and uk in w[ck] and len(w[ck][uk]) >= num:
        w[ck][uk][num-1]["active"] = False
        save_json(WARNS_FILE, w)
        return True
    return False

def remove_all_warns(user_id, chat_id):
    w = load_json(WARNS_FILE, {})
    ck = str(chat_id); uk = str(user_id)
    if ck in w and uk in w[ck]:
        for warn in w[ck][uk]:
            warn["active"] = False
        save_json(WARNS_FILE, w)
        return True
    return False

def get_active_warns(user_id, chat_id):
    w = load_json(WARNS_FILE, {})
    ck = str(chat_id); uk = str(user_id)
    if ck in w and uk in w[ck]:
        return [warn for warn in w[ck][uk] if warn["active"]]
    return []

def get_warn_count(user_id, chat_id):
    return len(get_active_warns(user_id, chat_id))

def check_warn_limit(user_id, chat_id):
    ws = load_json(WARN_SETTINGS_FILE, {})
    ck = str(chat_id)
    limit = ws.get(ck, {}).get("limit", 3)
    return get_warn_count(user_id, chat_id) >= limit

def get_warn_ban_time(chat_id):
    ws = load_json(WARN_SETTINGS_FILE, {})
    ck = str(chat_id)
    return ws.get(ck, {}).get("ban_time", 1440)

def get_warn_period(chat_id):
    ws = load_json(WARN_SETTINGS_FILE, {})
    ck = str(chat_id)
    return ws.get(ck, {}).get("period", 7)

# Приветствие
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for m in update.message.new_chat_members:
        if m.is_bot: continue
        captcha = load_json(CAPTCHA_FILE, {})
        if str(update.effective_chat.id) in captcha and captcha[str(update.effective_chat.id)].get("enabled", False):
            kb = [[InlineKeyboardButton("✅ Я не робот", callback_data=f"captcha_pass_{m.id}")]]
            await update.message.reply_html(
                f"👋 Привет {get_user_link(m)}! Я помощник чата!\n"
                "Это для системы антибот.\n"
                "Нажми пожалуйста кнопку чтобы я понял что ты не робот!",
                reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.message.reply_html(f"👋 Добро пожаловать, {get_user_link(m)}!\n\n📜 Правила: без 18+, без рекламы, без оскорблений\n🎉 Судные выходные: Суббота 12:00 - Понедельник 6:00\n\nПриятного общения! 😊")

# Капча кнопка
async def captcha_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data.startswith("captcha_pass_"):
        uid = int(q.data.replace("captcha_pass_", ""))
        if uid == q.from_user.id:
            try:
                await context.bot.approve_chat_join_request(chat_id=update.effective_chat.id, user_id=uid)
                await q.message.delete()
            except: pass

# Привязка чата
async def bind_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        if context.args:
            code = context.args[0]
            chats = load_json(CHATS_FILE, {})
            for cid, cdata in chats.items():
                if cdata.get("code") == code:
                    chats[str(update.effective_user.id)] = cid
                    save_json(CHATS_FILE, chats)
                    await update.message.reply_text(f"✅ ЛС привязаны к чату {cid}!")
                    return
            await update.message.reply_text("❌ Чат с таким кодом не найден!")
        else:
            await update.message.reply_text("❌ Напишите: Привязать [код]")
    else:
        import random, string
        code = ''.join(random.choices(string.digits, k=6))
        chats = load_json(CHATS_FILE, {})
        chats[str(update.effective_chat.id)] = {"code": code, "name": update.effective_chat.title or "Чат"}
        save_json(CHATS_FILE, chats)
        await update.message.reply_text(f"🔗 Код чата: `{code}`\nВ ЛС бота напишите: Привязать {code}", parse_mode='Markdown')

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
        d = 0
        chat_id = update.effective_chat.id
        msg_id = update.message.message_id
        for _ in range(min(cnt, 100)):
            try: await context.bot.delete_message(chat_id, msg_id - 1 - _); d += 1
            except: pass
        await update.message.reply_text(f"🧹 Удалено {d}!")
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

async def delete_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    try:
        await update.message.delete()
        await update.message.reply_to_message.delete()
    except: pass

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
# БАН с причиной
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    if u.id == CREATOR_ID: return
    if is_admin(u.id) and update.effective_user.id != CREATOR_ID: return
    bt = 0; reason = ""
    if context.args:
        try:
            parts = " ".join(context.args).split("\n")
            args_text = parts[0]
            if len(parts) > 1: reason = parts[1].strip()
            args_list = args_text.split()
            if len(args_list)==1 and args_list[0].isdigit(): bt=int(args_list[0])
            elif len(args_list)>=2:
                n=int(args_list[0]); un=args_list[1].lower()
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
            txt = f"🚫 {get_user_link(u)} забанен на {t}!"
            if reason: txt += f"\n📝 Причина: {reason}"
            await update.message.reply_html(txt)
        else:
            await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=u.id)
            txt = f"🚫 {get_user_link(u)} забанен навсегда!"
            if reason: txt += f"\n📝 Причина: {reason}"
            await update.message.reply_html(txt)
        if reason:
            br = load_json(BAN_REASONS_FILE, {})
            ck = str(update.effective_chat.id); uk = str(u.id)
            if ck not in br: br[ck] = {}
            br[ck][uk] = {"reason": reason, "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "admin": update.effective_user.first_name}
            save_json(BAN_REASONS_FILE, br)
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    try:
        await context.bot.unban_chat_member(chat_id=update.effective_chat.id, user_id=u.id)
        await update.message.reply_html(f"✅ {get_user_link(u)} разбанен!")
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

async def ban_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    br = load_json(BAN_REASONS_FILE, {})
    ck = str(update.effective_chat.id); uk = str(u.id)
    if ck in br and uk in br[ck]:
        data = br[ck][uk]
        await update.message.reply_text(f"📋 Причина бана {get_display_name(u)}:\n📝 {data['reason']}\n👮 Модератор: {data['admin']}\n📅 {data['date']}")
    else:
        await update.message.reply_text("❌ Причина не найдена")

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

# МУТ с причиной
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    if u.id == CREATOR_ID: return
    if is_admin(u.id) and update.effective_user.id != CREATOR_ID: return
    mt = 10080; reason = ""
    if context.args:
        try:
            parts = " ".join(context.args).split("\n")
            args_text = parts[0]
            if len(parts) > 1: reason = parts[1].strip()
            args_list = args_text.split()
            if len(args_list)==1 and args_list[0].isdigit(): mt=int(args_list[0])
            elif len(args_list)>=2:
                n=int(args_list[0]); un=args_list[1].lower()
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
        txt = f"🔇 {get_user_link(u)} замучен на {t}!"
        if reason: txt += f"\n📝 Причина: {reason}"
        await update.message.reply_html(txt)
        if reason:
            mr = load_json(MUTE_REASONS_FILE, {})
            ck = str(update.effective_chat.id); uk = str(u.id)
            if ck not in mr: mr[ck] = {}
            mr[ck][uk] = {"reason": reason, "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "admin": update.effective_user.first_name}
            save_json(MUTE_REASONS_FILE, mr)
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(chat_id=update.effective_chat.id, user_id=u.id, permissions=ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True))
        await update.message.reply_html(f"🔊 {get_user_link(u)} размучен!")
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")

async def check_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    try:
        cm = await context.bot.get_chat_member(update.effective_chat.id, u.id)
        if cm.status == 'restricted' and not cm.permissions.can_send_messages:
            mr = load_json(MUTE_REASONS_FILE, {})
            ck = str(update.effective_chat.id); uk = str(u.id)
            txt = f"🔇 {get_display_name(u)} замучен"
            if ck in mr and uk in mr[ck]:
                txt += f"\n📝 Причина: {mr[ck][uk]['reason']}\n👮 Модератор: {mr[ck][uk]['admin']}\n📅 {mr[ck][uk]['date']}"
            await update.message.reply_text(txt)
        else:
            await update.message.reply_text(f"✅ {get_display_name(u)} не замучен")
    except: pass

async def mutelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("📋 Список замученных: проверьте права участников в настройках чата.")

async def mute_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args: return
    try:
        n=int(context.args[0]); un=context.args[1].lower() if len(context.args)>1 else "н"
        if un in ["м","мин"]: mt=n
        elif un in ["ч","час"]: mt=n*60
        elif un in ["д","день"]: mt=n*1440
        elif un in ["н","нед"]: mt=n*10080
        else: mt=n*10080
        await update.message.reply_text(f"✅ Период мута по умолчанию: {mt} минут")
    except: pass

# СИСТЕМА ВАРНОВ
async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    period = get_warn_period(update.effective_chat.id)
    reason = ""
    if context.args:
        parts = " ".join(context.args).split("\n")
        if len(parts) > 1: reason = parts[1].strip()
        elif len(parts) == 1: reason = parts[0]
    count = add_warn(u.id, update.effective_chat.id, reason, period)
    txt = f"⚠️ ПРЕДУПРЕЖДЕНИЕ #{count}\nПользователь: {get_user_link(u)}\nПричина: {reason}"
    await update.message.reply_html(txt)
    if check_warn_limit(u.id, update.effective_chat.id):
        ban_time = get_warn_ban_time(update.effective_chat.id)
        try:
            await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=u.id, until_date=datetime.now()+timedelta(minutes=ban_time))
            await update.message.reply_html(f"🚫 {get_user_link(u)} забанен на {ban_time} минут за {count} предупреждений!")
        except: pass

async def warn_list_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    warns = get_active_warns(u.id, update.effective_chat.id)
    if not warns: await update.message.reply_text(f"✅ У {get_display_name(u)} нет предупреждений!"); return
    txt = f"⚠️ Предупреждения {get_display_name(u)}:\n\n"
    for i, w in enumerate(warns, 1):
        txt += f"{i}. {w['reason']} | {w['date']}\n"
    await update.message.reply_text(txt)

async def my_warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    warns = get_active_warns(u.id, update.effective_chat.id)
    if not warns: await update.message.reply_text("✅ У вас нет предупреждений!"); return
    txt = f"⚠️ Ваши предупреждения:\n\n"
    for i, w in enumerate(warns, 1):
        txt += f"{i}. {w['reason']} | {w['date']}\n"
    await update.message.reply_text(txt)

async def warnlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    w = load_json(WARNS_FILE, {})
    ck = str(update.effective_chat.id)
    if ck not in w or not w[ck]: await update.message.reply_text("📋 Нет предупреждений!"); return
    txt = "📋 ПОСЛЕДНИЕ ПРЕДУПРЕЖДЕНИЯ:\n\n"
    for uk, warns in list(w[ck].items())[-20:]:
        active = [x for x in warns if x["active"]]
        if active:
            txt += f"• {active[-1].get('name', uk)}: {active[-1]['reason']} | {active[-1]['date']}\n"
    await update.message.reply_text(txt if txt else "📋 Нет активных предупреждений!")

async def remove_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    if remove_last_warn(u.id, update.effective_chat.id):
        await update.message.reply_html(f"✅ Последнее предупреждение {get_user_link(u)} снято!")
    else:
        await update.message.reply_text(f"❌ У {get_display_name(u)} нет предупреждений!")

async def remove_warns_count_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    if not context.args or not context.args[0].isdigit(): return
    u = update.message.reply_to_message.from_user
    count = int(context.args[0])
    removed = remove_warns_count(u.id, update.effective_chat.id, count)
    await update.message.reply_html(f"✅ Снято {removed} предупреждений с {get_user_link(u)}!")

async def remove_warn_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    if not context.args or not context.args[0].isdigit(): return
    u = update.message.reply_to_message.from_user
    num = int(context.args[0])
    if remove_warn_by_number(u.id, update.effective_chat.id, num):
        await update.message.reply_html(f"✅ Предупреждение #{num} снято с {get_user_link(u)}!")
    else:
        await update.message.reply_text(f"❌ Предупреждение #{num} не найдено!")

async def remove_all_warns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not update.message.reply_to_message: return
    u = update.message.reply_to_message.from_user
    if remove_all_warns(u.id, update.effective_chat.id):
        await update.message.reply_html(f"✅ Все предупреждения {get_user_link(u)} сняты!")
    else:
        await update.message.reply_text(f"❌ У {get_display_name(u)} нет предупреждений!")

async def warn_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args or not context.args[0].isdigit(): return
    limit = int(context.args[0])
    ws = load_json(WARN_SETTINGS_FILE, {})
    ck = str(update.effective_chat.id)
    if ck not in ws: ws[ck] = {}
    ws[ck]["limit"] = limit
    save_json(WARN_SETTINGS_FILE, ws)
    await update.message.reply_text(f"✅ Лимит предупреждений: {limit}")

async def warn_ban_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args: return
    try:
        n=int(context.args[0]); un=context.args[1].lower() if len(context.args)>1 else "ч"
        if un in ["м","мин"]: bt=n
        elif un in ["ч","час"]: bt=n*60
        elif un in ["д","день"]: bt=n*1440
        elif un in ["н","нед"]: bt=n*10080
        else: bt=n*60
        ws = load_json(WARN_SETTINGS_FILE, {})
        ck = str(update.effective_chat.id)
        if ck not in ws: ws[ck] = {}
        ws[ck]["ban_time"] = bt
        save_json(WARN_SETTINGS_FILE, ws)
        await update.message.reply_text(f"✅ Срок бана за предупреждения: {bt} минут")
    except: pass

async def warn_period_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args or not context.args[0].isdigit(): return
    period = int(context.args[0])
    ws = load_json(WARN_SETTINGS_FILE, {})
    ck = str(update.effective_chat.id)
    if ck not in ws: ws[ck] = {}
    ws[ck]["period"] = period
    save_json(WARN_SETTINGS_FILE, ws)
    await update.message.reply_text(f"✅ Срок хранения предупреждений: {period} дней")

async def toggle_rp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    s = load_json(RP_SETTINGS_FILE, {"rp":True,"marriages":True})
    m = update.message.text.lower().strip()
    if m in ["+рп","+rp"]: s["rp"]=True; await update.message.reply_text("✅ РП включены!")
    elif m in ["-рп","-rp"]: s["rp"]=False; await update.message.reply_text("❌ РП выключены!")
    elif m in ["+браки","+брак"]: s["marriages"]=True; await update.message.reply_text("✅ Браки включены!")
    elif m in ["-браки","-брак"]: s["marriages"]=False; await update.message.reply_text("❌ Браки выключены!")
    save_json(RP_SETTINGS_FILE, s)

async def ban_period_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args: return
    try:
        n=int(context.args[0]); un=context.args[1].lower() if len(context.args)>1 else "н"
        if un in ["м","мин"]: bt=n
        elif un in ["ч","час"]: bt=n*60
        elif un in ["д","день"]: bt=n*1440
        elif un in ["н","нед"]: bt=n*10080
        elif un in ["мес"]: bt=n*43200
        else: bt=0
        await update.message.reply_text(f"✅ Период бана: {'навсегда' if bt==0 else f'{bt} минут'}")
    except: pass
# ПРОФИЛЬ
async def who_am_i(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user; uid = str(u.id)
    p = load_json(PROFILES_FILE, {}); r = load_json(REP_FILE, {})
    t = load_json(TITLES_FILE, {})
    name = get_display_name(u); prof = p.get(uid, {})
    total = prof.get("total", 0); total_chat = prof.get("total_chat", 0)
    first = prof.get("first_date", "неизвестно"); last = prof.get("last_seen", "неизвестно")
    today = datetime.now().strftime("%Y-%m-%d")
    week = datetime.now().strftime("%Y-W%U")
    month = datetime.now().strftime("%Y-%m")
    ck = str(update.effective_chat.id)
    dc = prof.get("daily_chat", {}).get(f"{ck}_{today}", 0)
    wc = prof.get("weekly_chat", {}).get(f"{ck}_{week}", 0)
    mc = prof.get("monthly_chat", {}).get(f"{ck}_{month}", 0)
    ur = r.get(uid, {"plus":0,"minus":0})
    warns = get_active_warns(u.id, update.effective_chat.id)
    txt = f"👤 Это пользователь {get_user_link(u)}\n"
    if is_admin(u.id): txt += "👨🏻‍💼 Администратор чата\n"
    if uid == str(CREATOR_ID): txt += "👑 Создатель чата\n"
    txt += f"\n⭐ [{total_chat}] Ранг: {get_rank(total_chat)}\n"
    txt += f"Репутация: ✨ {ur.get('plus',0)} | ➕ {ur.get('plus',0)-ur.get('minus',0)}\n"
    if warns: txt += f"⚠️ Предупреждений: {len(warns)}\n"
    txt += f"Первое появление: {first}\nПоследний актив: {last}\n"
    txt += f"Актив (д|н|м|весь): {dc} | {wc} | {mc} | {total_chat}\n"
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
    ck = str(update.effective_chat.id)
    if w not in s or ck not in s[w].get("chats", {}) or not s[w]["chats"][ck]:
        await update.message.reply_text("📊 Нет данных за эту неделю!"); return
    su = sorted(s[w]["chats"][ck].items(), key=lambda x: x[1]["count"], reverse=True)
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
async def send_weekend_message(update: Update = None, context: ContextTypes.DEFAULT_TYPE = None):
    if update:
        chat_id = update.effective_chat.id
    else:
        chat_id = context.job.chat_id if context else CHAT_ID
    await context.bot.send_photo(chat_id=chat_id, photo="https://photos.app.goo.gl/1Zw5wMqT7nmZZAtq6",
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
        "⚙ +Рп/-Рп, +Браки/-Браки\n"
        "🔗 Привязать\n\n"
        "🚫 Бан [время]\\nПричина, !ban, ЧС, Разбан, Вернуть, Кик, Кик тихо, !Амнистия, Банлист, Причина\n"
        "🔇 Мут [время]\\nПричина, Заткнуть, mute, Размут, Говори, unmute, -Мут, Муты, Проверить мут\n"
        "⚠️ Варн [причина], Варны, Мои варны, Варнлист, -Варн, Снять варны, Варны лимит\n"
        "🧹 Очистка, -Смс, Выходные\n\n"
        "💍 Брак, Развод, Семья, Браки\n"
        "👤 Кто я, +, -, +ник, Наградить, !ид, Топ репутации\n"
        "📊 Стата, Статистика, Топ\n"
        "🎮 Кто, Шар, Монетка, Выбери, Рулетка\n\n"
        "🎭 РП: Обнять\\nТекст, Поцеловать\\nТекст, Укусить, Ударить, Погладить, Лизнуть, Тыкнуть, Шлёпнуть, Задушить, Подмигнуть, Похвалить, Обидеть, Убежать, Вернуться, Смеяться, Плакать, Злиться, Радоваться, Грустить, Спать, Кушать, Пить, Выебать, Потрогать, Украсть, Отдать, Бросить, Поднять\n\n"
        "📢 Помощь, Правила, Набор\n🆘 ЛС: Поддержка\nℹ️ Бот, Боты, Bot"
    )

# ПРАВИЛА
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🗓 ПРАВИЛА ЧАТА\n\nДобро пожаловать в чат!\n\n"
        "❌ Реклама — бан.\n❌ Контент 18+ — мут 3ч/бан.\n❌ Оскорбление админов — мут 2ч/бан.\n"
        "❌ Оскорбление религии/нации — мут 30мин.\n❌ Спам/флуд — мут 30мин.\n"
        "❌ Попрошайничество — мут 30мин.\n❌ Политика — мут 2ч.\n❌ Шок-контент — мут 4ч/бан.\n"
        "❌ Оскорбление участников — мут 1ч.\n❌ Провокации — мут 1ч.\n"
        "❌ Обход наказания — бан 24ч.\n❌ Продажа аккаунтов — мут 3ч.\n\n"
        "👮 Админы: без угроз, соблюдать субординацию\n\n"
        "🎉 Судные выходные: Суббота 12:00 - Понедельник 6:00\nПриятного общения!"
)
# РП-КОМАНДЫ с поддержкой текста на следующей строке
async def hug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"🫂 {get_user_link(a)} нежно обнял(а) {get_user_link(b)}!{extra}")

async def kiss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"💋 {get_user_link(a)} страстно поцеловал(а) {get_user_link(b)}!{extra}")

async def bite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"🦷 {get_user_link(a)} больно укусил(а) {get_user_link(b)}!{extra}")

async def slap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"👋 {get_user_link(a)} с размаху ударил(а) {get_user_link(b)}!{extra}")

async def pat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"🤚 {get_user_link(a)} ласково погладил(а) {get_user_link(b)}!{extra}")

async def lick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"👅 {get_user_link(a)} игриво лизнул(а) {get_user_link(b)}!{extra}")

async def poke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"👉 {get_user_link(a)} настойчиво тыкнул(а) {get_user_link(b)}!{extra}")

async def spank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"🍑 {get_user_link(a)} звонко шлёпнул(а) {get_user_link(b)}!{extra}")

async def choke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"😤 {get_user_link(a)} в ярости задушил(а) {get_user_link(b)}!{extra}")

async def wink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"😉 {get_user_link(a)} кокетливо подмигнул(а) {get_user_link(b)}!{extra}")

async def praise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"👏 {get_user_link(a)} искренне похвалил(а) {get_user_link(b)}!{extra}")

async def insult(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"😠 {get_user_link(a)} сильно обидел(а) {get_user_link(b)}!{extra}")

async def run_away(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    extra = ""
    if context.args: extra = f"\n💬 {' '.join(context.args)}"
    await update.message.reply_html(f"🏃 {get_user_link(update.effective_user)} в панике убегает!{extra}")

async def come_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    extra = ""
    if context.args: extra = f"\n💬 {' '.join(context.args)}"
    await update.message.reply_html(f"🚶 {get_user_link(update.effective_user)} медленно возвращается...{extra}")

async def laugh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    extra = ""
    if context.args: extra = f"\n💬 {' '.join(context.args)}"
    await update.message.reply_html(f"😂 {get_user_link(update.effective_user)} громко смеётся!{extra}")

async def cry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    extra = ""
    if context.args: extra = f"\n💬 {' '.join(context.args)}"
    await update.message.reply_html(f"😭 {get_user_link(update.effective_user)} горько плачет...{extra}")

async def angry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    extra = ""
    if context.args: extra = f"\n💬 {' '.join(context.args)}"
    await update.message.reply_html(f"😡 {get_user_link(update.effective_user)} в бешенстве!{extra}")

async def happy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    extra = ""
    if context.args: extra = f"\n💬 {' '.join(context.args)}"
    await update.message.reply_html(f"😊 {get_user_link(update.effective_user)} радуется как ребёнок!{extra}")

async def sad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    extra = ""
    if context.args: extra = f"\n💬 {' '.join(context.args)}"
    await update.message.reply_html(f"😔 {get_user_link(update.effective_user)} грустит в уголке...{extra}")

async def sleep_rp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    extra = ""
    if context.args: extra = f"\n💬 {' '.join(context.args)}"
    await update.message.reply_html(f"😴 {get_user_link(update.effective_user)} сладко спит...{extra}")

async def eat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    extra = ""
    if context.args: extra = f"\n💬 {' '.join(context.args)}"
    await update.message.reply_html(f"🍽 {get_user_link(update.effective_user)} с аппетитом кушает!{extra}")

async def drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    extra = ""
    if context.args: extra = f"\n💬 {' '.join(context.args)}"
    await update.message.reply_html(f"🍹 {get_user_link(update.effective_user)} с удовольствием пьёт!{extra}")

async def fuck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"😩 | {get_user_link(a)} принудил к жёсткому интиму {get_user_link(b)}!{extra}")

async def touch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"🖐 {get_user_link(a)} осторожно потрогал(а) {get_user_link(b)}!{extra}")

async def steal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"🦹 {get_user_link(a)} хитро украл(а) у {get_user_link(b)} всё!{extra}")

async def give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"🎁 {get_user_link(a)} щедро отдал(а) подарок {get_user_link(b)}!{extra}")

async def throw_rp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"🤾 {get_user_link(a)} метко бросил(а) в {get_user_link(b)} чем-то!{extra}")

async def lift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rp_enabled(): return
    if not update.message.reply_to_message: return
    a, b = update.effective_user, update.message.reply_to_message.from_user
    extra = ""
    if context.args: extra = f"\n💬 {get_display_name(a)}: {' '.join(context.args)}"
    await update.message.reply_html(f"💪 {get_user_link(a)} легко поднял(а) {get_user_link(b)}!{extra}")
# ОБРАБОТЧИК КОМАНД
async def text_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    msg = update.message.text.lower().strip()
    update_profile(update.effective_user.id, update.effective_user.first_name, update.effective_chat.id)
    
    if msg in ["бот","боты","bot"]:
        await update.message.reply_text("👋 Я здесь! Напишите «Помощь» для списка команд.")
        return
    
    # Общие
    if msg=="помощь": await help_command(update, context)
    elif msg=="правила": await rules(update, context)
    elif msg=="набор": await admin_recruitment(update, context)
    elif msg=="старт": await start(update, context)
    elif msg=="админка": await admin_panel(update, context)
    elif msg=="привязать" or msg.startswith("привязать"): 
        context.args = msg.split()[1:] if len(msg.split())>1 else []
        await bind_chat(update, context)
    
    # Админ
    elif msg in ["выдать админа", "сделать админом"]: await add_admin(update, context)
    elif msg in ["разжаловать", "снять", "снять админа", "убрать админа"]: await remove_admin(update, context)
    elif msg.startswith("повысить"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await promote(update, context)
    elif msg in ["+рп","-рп","+браки","-браки","+rp","-rp"]: await toggle_rp(update, context)
    elif msg.startswith("мут период"):
        context.args = msg.split()[2:] if len(msg.split())>2 else []; await mute_period(update, context)
    elif msg.startswith("бан период"):
        context.args = msg.split()[2:] if len(msg.split())>2 else []; await ban_period_cmd(update, context)
    
    # Бан
    elif msg.startswith("бан") or msg in ["чс","!ban","!permban"]:
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await ban(update, context)
    elif msg in ["разбан","вернуть","!unban"]: await unban(update, context)
    elif msg=="кик" or msg=="!kick": await kick(update, context)
    elif msg=="кик тихо": await kick_silent(update, context)
    elif msg=="!амнистия": await amnesty(update, context)
    elif msg=="банлист": await banlist(update, context)
    elif msg=="причина": await ban_reason(update, context)
    
    # Мут
    elif msg.startswith("мут") or msg in ["заткнуть","mute"]:
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await mute(update, context)
    elif msg in ["размут","снять мут","говори","unmute","-мут"]: await unmute(update, context)
    elif msg in ["муты","мутлист"]: await mutelist(update, context)
    elif msg=="проверить мут": await check_mute(update, context)
    
    # Варны
    elif msg in ["варн","пред","предупреждение","!warn","!пред"] or msg.startswith("варн ") or msg.startswith("пред "):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await warn_cmd(update, context)
    elif msg in ["варны","вarns"]: await warn_list_user(update, context)
    elif msg in ["мои варны","мои преды"]: await my_warns(update, context)
    elif msg=="варнлист": await warnlist(update, context)
    elif msg=="-варн": await remove_warn(update, context)
    elif msg.startswith("снять варны") and not msg.startswith("снять варны номер"):
        context.args = msg.split()[2:] if len(msg.split())>2 else []; await remove_warns_count_cmd(update, context)
    elif msg.startswith("снять варн номер"):
        context.args = msg.split()[3:] if len(msg.split())>3 else []; await remove_warn_num(update, context)
    elif msg=="снять все варны": await remove_all_warns_cmd(update, context)
    elif msg.startswith("варны лимит"):
        context.args = msg.split()[2:] if len(msg.split())>2 else []; await warn_limit(update, context)
    elif msg.startswith("варны чс"):
        context.args = msg.split()[2:] if len(msg.split())>2 else []; await warn_ban_time(update, context)
    elif msg.startswith("варны период"):
        context.args = msg.split()[2:] if len(msg.split())>2 else []; await warn_period_cmd(update, context)
    
    # Очистка
    elif msg.startswith("очистка"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await clear_messages(update, context)
    elif msg=="-смс": await delete_msg(update, context)
    elif msg=="выходные": await schedule_weekend(update, context)
    elif msg in ["судные выходные","отправить выходные"]: await send_weekend_message(update=update, context=context)
    
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
    elif msg=="обнять" or msg.startswith("обнять"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await hug(update, context)
    elif msg=="поцеловать" or msg.startswith("поцеловать"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await kiss(update, context)
    elif msg=="укусить" or msg.startswith("укусить"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await bite(update, context)
    elif msg=="ударить" or msg.startswith("ударить"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await slap(update, context)
    elif msg=="погладить" or msg.startswith("погладить"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await pat(update, context)
    elif msg=="лизнуть" or msg.startswith("лизнуть"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await lick(update, context)
    elif msg=="тыкнуть" or msg.startswith("тыкнуть"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await poke(update, context)
    elif msg=="шлёпнуть" or msg.startswith("шлёпнуть"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await spank(update, context)
    elif msg=="задушить" or msg.startswith("задушить"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await choke(update, context)
    elif msg=="подмигнуть" or msg.startswith("подмигнуть"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await wink(update, context)
    elif msg=="похвалить" or msg.startswith("похвалить"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await praise(update, context)
    elif msg=="обидеть" or msg.startswith("обидеть"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await insult(update, context)
    elif msg=="убежать":
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await run_away(update, context)
    elif msg=="вернуться":
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await come_back(update, context)
    elif msg=="смеяться":
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await laugh(update, context)
    elif msg=="плакать":
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await cry(update, context)
    elif msg=="злиться":
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await angry(update, context)
    elif msg=="радоваться":
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await happy(update, context)
    elif msg=="грустить":
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await sad(update, context)
    elif msg=="спать":
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await sleep_rp(update, context)
    elif msg=="кушать":
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await eat(update, context)
    elif msg=="пить":
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await drink(update, context)
    elif msg=="выебать" or msg.startswith("выебать"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await fuck(update, context)
    elif msg=="потрогать" or msg.startswith("потрогать"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await touch(update, context)
    elif msg=="украсть" or msg.startswith("украсть"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await steal(update, context)
    elif msg=="отдать" or msg.startswith("отдать"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await give(update, context)
    elif msg=="бросить" or msg.startswith("бросить"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await throw_rp(update, context)
    elif msg=="поднять" or msg.startswith("поднять"):
        context.args = msg.split()[1:] if len(msg.split())>1 else []; await lift(update, context)
def main():
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("kick", kick))
    application.add_handler(CommandHandler("amnesty", amnesty))
    application.add_handler(CommandHandler("banlist", banlist))
    application.add_handler(CommandHandler("ban_reason", ban_reason))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("unmute", unmute))
    application.add_handler(CommandHandler("check_mute", check_mute))
    application.add_handler(CommandHandler("mutelist", mutelist))
    application.add_handler(CommandHandler("mute_period", mute_period))
    application.add_handler(CommandHandler("warn", warn_cmd))
    application.add_handler(CommandHandler("warns", warn_list_user))
    application.add_handler(CommandHandler("my_warns", my_warns))
    application.add_handler(CommandHandler("warnlist", warnlist))
    application.add_handler(CommandHandler("remove_warn", remove_warn))
    application.add_handler(CommandHandler("remove_warns_count", remove_warns_count_cmd))
    application.add_handler(CommandHandler("remove_warn_num", remove_warn_num))
    application.add_handler(CommandHandler("remove_all_warns", remove_all_warns_cmd))
    application.add_handler(CommandHandler("warn_limit", warn_limit))
    application.add_handler(CommandHandler("warn_ban_time", warn_ban_time))
    application.add_handler(CommandHandler("warn_period", warn_period_cmd))
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
    application.add_handler(CommandHandler("delete_msg", delete_msg))
    application.add_handler(CommandHandler("admin", admin_recruitment))
    application.add_handler(CommandHandler("admin_panel", admin_panel))
    application.add_handler(CommandHandler("remove_admin", remove_admin))
    application.add_handler(CommandHandler("bind_chat", bind_chat))
    application.add_handler(CommandHandler("schedule_weekend", schedule_weekend))
    application.add_handler(CommandHandler("send_weekend", send_weekend_message))
    application.add_handler(CallbackQueryHandler(support_button, pattern="^support$"))
    application.add_handler(CallbackQueryHandler(admin_buttons, pattern="^(take_|close_)"))
    application.add_handler(CallbackQueryHandler(admin_menu_buttons, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(marry_buttons, pattern="^(accept_marry_|decline_marry_)"))
    application.add_handler(CallbackQueryHandler(divorce_buttons, pattern="^(confirm_divorce_|cancel_divorce)"))
    application.add_handler(CallbackQueryHandler(captcha_button, pattern="^captcha_pass_"))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, filter_bots), group=0)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.ChatType.PRIVATE, message_filter), group=1)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, private_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.ChatType.PRIVATE, text_commands), group=2)
    
    # Вебхук
    PORT = int(os.environ.get("PORT", 8443))
    WEBHOOK_URL = "https://support-bot-ftsv.onrender.com"
    print("✅ Бот запущен!")
    application.run_webhook(listen="0.0.0.0", port=PORT, url_path="webhook", webhook_url=f"{WEBHOOK_URL}/webhook")

if __name__ == '__main__':
    main()
