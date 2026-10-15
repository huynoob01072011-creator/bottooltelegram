import telebot
from telebot import types
from telebot.types import BotCommand
from urllib.parse import quote
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import os
import time
import threading
from flask import Flask, render_template_string, send_file

# ==============================
# CẤU HÌNH BOT
# ==============================

BOT_TOKEN = "8638972575:AAGMXJqG2U3Ukg9aH6T0ngcNoDGR-tibZYI"
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# ==============================
# CẤU HÌNH ADMIN & GROUP
# ==============================

ADMIN_ID       = 8771034410
ADMIN_USERNAME = "@NguyenVanGiaHuyy"
GROUP_CHAT_ID  = -1004442084088
BOT_LINK       = "https://t.me/CNDDTX_BOT"
GROUP_LINK     = "https://t.me/HTDDTX"

# ==============================
# CẤU HÌNH NGÂN HÀNG
# ==============================

BANK_BIN     = "970422"
BANK_NAME    = "MB Bank"
ACCOUNT_NO   = "101072011"
ACCOUNT_NAME = "NGUYEN VAN GIA HUY"

# ==============================
# DANH SÁCH GÓI VIP
# ==============================

VIP_PACKAGES = {
    "1day":    {"name": "Key 1 Ngày",    "price": 25000,  "days": 1,    "emoji": "🥉"},
    "3day":    {"name": "Key 3 Ngày",    "price": 50000,  "days": 3,    "emoji": "🥈"},
    "1week":   {"name": "Key 1 Tuần",    "price": 70000,  "days": 7,    "emoji": "🥇"},
    "1month":  {"name": "Key 1 Tháng",   "price": 150000, "days": 30,   "emoji": "🏆"},
    "1year":   {"name": "Key 1 Năm",     "price": 200000, "days": 365,  "emoji": "👑"},
    "forever": {"name": "Key Vĩnh Viễn", "price": 350000, "days": -1,   "emoji": "💎"},
}

# ==============================
# DANH SÁCH GAME
# ==============================

GAMES = {
    "sunwin":  {"name": "Sunwin",   "emoji": "☀️", "link": "https://sunwin.com"},
    "b52":     {"name": "B52 Club", "emoji": "🎯", "link": "https://b52.club"},
    "go88":    {"name": "Go88",     "emoji": "🎰", "link": "https://go88.com"},
    "rikvip":  {"name": "Rikvip",   "emoji": "🎲", "link": "https://rikvip.com"},
    "manclub": {"name": "Manclub",  "emoji": "🃏", "link": "https://manclub.com"},
    "789club": {"name": "789 Club", "emoji": "🎴", "link": "https://789club.com"},
}

# ==============================
# FILE LƯU TRỮ
# ==============================

DATA_FILE     = "users.json"
ACTIVITY_FILE = "activities.json"

# ==============================
# HÀM ĐỌC / GHI JSON
# ==============================

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Lỗi đọc {path}: {e}")
            return default
    return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Lỗi ghi {path}: {e}")

users_db     = load_json(DATA_FILE, {})
activity_log = load_json(ACTIVITY_FILE, [])
pending_deposits = {}

def save_data():
    save_json(DATA_FILE, users_db)

def save_activities():
    # Chỉ giữ 500 hoạt động gần nhất để file nhẹ
    if len(activity_log) > 500:
        del activity_log[:-500]
    save_json(ACTIVITY_FILE, activity_log)

def log_activity(action, user_id, fullname, detail="", amount=0):
    activity_log.append({
        "time": get_vn_time(),
        "action": action,
        "user_id": str(user_id),
        "fullname": fullname,
        "detail": detail,
        "amount": amount
    })
    save_activities()

def get_user(user_id):
    uid = str(user_id)
    if uid not in users_db:
        users_db[uid] = {
            "fullname": "Thành viên",
            "username": "",
            "balance": 0,
            "vip_expiry": 0,
            "total_spent": 0,
            "purchases": [],
            "joined": get_vn_time()
        }
        save_data()
    users_db[uid].setdefault("vip_expiry", 0)
    users_db[uid].setdefault("total_spent", 0)
    users_db[uid].setdefault("purchases", [])
    users_db[uid].setdefault("fullname", "Thành viên")
    users_db[uid].setdefault("username", "")
    users_db[uid].setdefault("joined", get_vn_time())
    return users_db[uid]

def update_balance(user_id, amount):
    user = get_user(user_id)
    user["balance"] += amount
    save_data()

# ==============================
# HÀM LẤY THỜI GIAN VIỆT NAM
# ==============================

def get_vn_time():
    try:
        tz = ZoneInfo("Asia/Ho_Chi_Minh")
    except Exception:
        from datetime import timezone, timedelta
        tz = timezone(timedelta(hours=7))
    return datetime.now(tz).strftime("%H:%M:%S - %d/%m/%Y")

def get_full_name(user):
    """Lấy fullname từ telegram user object."""
    if user.last_name:
        return f"{user.first_name} {user.last_name}"
    return user.first_name or "Thành viên"

# ==============================
# HÀM XỬ LÝ VIP
# ==============================

def is_vip_active(user_id):
    user = get_user(user_id)
    expiry = user.get("vip_expiry", 0)
    if expiry == -1:
        return True
    return expiry > time.time()

def get_vip_status_text(user_id):
    user = get_user(user_id)
    expiry = user.get("vip_expiry", 0)
    if expiry == -1:
        return "💎 VIP Vĩnh Viễn ♾️"
    if expiry <= time.time():
        return "❌ Chưa kích hoạt VIP"
    remaining = expiry - time.time()
    days = int(remaining // 86400)
    hours = int((remaining % 86400) // 3600)
    minutes = int((remaining % 3600) // 60)
    return f"✅ Còn {days} ngày {hours} giờ {minutes} phút"

def add_vip(user_id, duration_days):
    user = get_user(user_id)
    now = time.time()
    current = user.get("vip_expiry", 0)
    if duration_days == -1:
        user["vip_expiry"] = -1
    elif current == -1:
        pass
    elif current > now:
        user["vip_expiry"] = current + duration_days * 86400
    else:
        user["vip_expiry"] = now + duration_days * 86400
    save_data()

# ==============================
# FLASK WEB SERVER
# ==============================

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Hệ Thống Tài Xỉu</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #fff;
            padding: 30px 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        .header .logo { font-size: 64px; margin-bottom: 8px; }
        .header h1 {
            font-size: 32px;
            font-weight: 800;
            margin-bottom: 6px;
            background: linear-gradient(90deg, #f7971e, #ffd200);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header .subtitle { color: #a0a0b0; font-size: 14px; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 18px;
            margin-bottom: 30px;
        }
        .stat-box {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 18px;
            padding: 24px;
            text-align: center;
            transition: transform 0.3s;
        }
        .stat-box:hover { transform: translateY(-3px); }
        .stat-box .icon { font-size: 30px; margin-bottom: 10px; }
        .stat-box .number {
            font-size: 28px;
            font-weight: 800;
            color: #ffd200;
        }
        .stat-box .label {
            font-size: 13px;
            color: #a0a0b0;
            margin-top: 6px;
        }
        .buttons {
            display: flex;
            gap: 14px;
            justify-content: center;
            flex-wrap: wrap;
            margin-bottom: 35px;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(90deg, #f7971e, #ffd200);
            color: #1a1a2e;
            font-weight: 700;
            font-size: 15px;
            padding: 13px 30px;
            border-radius: 50px;
            text-decoration: none;
            transition: all 0.3s ease;
            box-shadow: 0 8px 25px rgba(247, 151, 30, 0.35);
        }
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 35px rgba(247, 151, 30, 0.5);
        }
        .btn.secondary {
            background: rgba(255, 255, 255, 0.08);
            color: #fff;
            border: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: none;
        }
        .btn.secondary:hover {
            background: rgba(255, 255, 255, 0.15);
        }
        .section-title {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .activity-panel {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 18px;
            padding: 24px;
        }
        .activity-list {
            max-height: 500px;
            overflow-y: auto;
        }
        .activity-item {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 14px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.03);
            margin-bottom: 10px;
            border-left: 4px solid #ffd200;
            transition: background 0.2s;
        }
        .activity-item:hover { background: rgba(255, 255, 255, 0.08); }
        .activity-item.deposit { border-left-color: #00d97e; }
        .activity-item.purchase { border-left-color: #ffd200; }
        .activity-item.reject { border-left-color: #ff4757; }
        .activity-item.start { border-left-color: #3498db; }
        .activity-icon { font-size: 24px; flex-shrink: 0; }
        .activity-content { flex: 1; }
        .activity-title { font-size: 14px; font-weight: 700; margin-bottom: 4px; }
        .activity-meta { font-size: 12px; color: #a0a0b0; }
        .activity-amount {
            font-size: 14px;
            font-weight: 800;
            color: #ffd200;
            flex-shrink: 0;
        }
        .empty {
            text-align: center;
            color: #606070;
            padding: 40px;
            font-style: italic;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            font-size: 12px;
            color: #606070;
        }
        .footer a { color: #ffd200; text-decoration: none; }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); border-radius: 4px; }
        ::-webkit-scrollbar-thumb { background: rgba(255, 210, 0, 0.4); border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🎰</div>
            <h1>HỆ THỐNG DỰ ĐOÁN TÀI XỈU</h1>
            <p class="subtitle">Dashboard quản lý & lịch sử hoạt động</p>
        </div>

        <div class="stats">
            <div class="stat-box">
                <div class="icon">👥</div>
                <div class="number">{{ total_users }}</div>
                <div class="label">Người dùng</div>
            </div>
            <div class="stat-box">
                <div class="icon">💎</div>
                <div class="number">{{ total_vip }}</div>
                <div class="label">Thành viên VIP</div>
            </div>
            <div class="stat-box">
                <div class="icon">💰</div>
                <div class="number">{{ "{:,}".format(total_balance) }}</div>
                <div class="label">Tổng số dư (VND)</div>
            </div>
            <div class="stat-box">
                <div class="icon">📈</div>
                <div class="number">{{ "{:,}".format(total_revenue) }}</div>
                <div class="label">Doanh thu VIP (VND)</div>
            </div>
        </div>

        <div class="buttons">
            <a href="/download-json" class="btn">⬇️ Tải users.json</a>
            <a href="/download-activities" class="btn secondary">📋 Tải activities.json</a>
        </div>

        <div class="activity-panel">
            <div class="section-title">📜 Lịch Sử Hoạt Động ({{ activities|length }} gần nhất)</div>
            <div class="activity-list">
                {% if activities %}
                    {% for a in activities %}
                        <div class="activity-item {{ a.css_class }}">
                            <div class="activity-icon">{{ a.icon }}</div>
                            <div class="activity-content">
                                <div class="activity-title">{{ a.title }}</div>
                                <div class="activity-meta">👤 {{ a.fullname }} • 🆔 {{ a.user_id }} • ⏰ {{ a.time }}</div>
                            </div>
                            {% if a.amount %}
                                <div class="activity-amount">{{ "{:,}".format(a.amount) }}đ</div>
                            {% endif %}
                        </div>
                    {% endfor %}
                {% else %}
                    <div class="empty">Chưa có hoạt động nào</div>
                {% endif %}
            </div>
        </div>

        <div class="footer">
            Bot: <a href="https://t.me/CNDDTX_BOT">@CNDDTX_BOT</a> | 
            Group: <a href="https://t.me/HTDDTX">@HTDDTX</a>
        </div>
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "HEAD"])
def home():
    try:
        total_users = len(users_db)
        total_balance = sum(u.get("balance", 0) for u in users_db.values())
        total_vip = sum(1 for u in users_db.values()
                        if u.get("vip_expiry", 0) == -1 or u.get("vip_expiry", 0) > time.time())
        total_revenue = sum(u.get("total_spent", 0) for u in users_db.values())

        # Chuẩn bị danh sách hoạt động (mới nhất lên đầu)
        activities = []
        for a in reversed(activity_log[-100:]):
            action = a.get("action", "")
            if action == "deposit":
                icon, css, title = "💰", "deposit", "Nạp tiền thành công"
            elif action == "purchase":
                icon, css, title = "🛒", "purchase", f"Mua VIP: {a.get('detail', '')}"
            elif action == "reject":
                icon, css, title = "❌", "reject", "Đơn nạp bị từ chối"
            elif action == "start":
                icon, css, title = "🚀", "start", "Bắt đầu sử dụng bot"
            else:
                icon, css, title = "📌", "", action

            activities.append({
                "icon": icon,
                "css_class": css,
                "title": title,
                "fullname": a.get("fullname", "N/A"),
                "user_id": a.get("user_id", "N/A"),
                "time": a.get("time", ""),
                "amount": a.get("amount", 0)
            })

        return render_template_string(
            DASHBOARD_HTML,
            total_users=total_users,
            total_vip=total_vip,
            total_balance=total_balance,
            total_revenue=total_revenue,
            activities=activities
        )
    except Exception as e:
        print(f"❌ Lỗi dashboard: {e}")
        import traceback
        traceback.print_exc()
        return f"<h1>Lỗi</h1><pre>{e}</pre>", 500

@app.route("/download-json", methods=["GET", "HEAD"])
def download_json():
    if not os.path.exists(DATA_FILE):
        save_data()
    return send_file(DATA_FILE, mimetype="application/json",
                     as_attachment=True, download_name="users.json")

@app.route("/download-activities", methods=["GET", "HEAD"])
def download_activities():
    if not os.path.exists(ACTIVITY_FILE):
        save_activities()
    return send_file(ACTIVITY_FILE, mimetype="application/json",
                     as_attachment=True, download_name="activities.json")

@app.route("/health", methods=["GET", "HEAD"])
def health():
    return "OK", 200

# ==============================
# ĐĂNG KÝ MENU LỆNH (CHỈ /start)
# ==============================

def register_commands():
    try:
        bot.set_my_commands([
            BotCommand("start", "🚀 Khởi động bot")
        ])
        print("✅ Đã đăng ký menu lệnh")
    except Exception as e:
        print(f"⚠️ Không thể đăng ký menu lệnh: {e}")

# ==============================
# HÀM TẠO MENU CHÍNH
# ==============================

def build_main_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("💳 Nạp Tiền", callback_data="deposit"),
        types.InlineKeyboardButton("🔑 Mua Key", callback_data="buy_key")
    )
    keyboard.add(
        types.InlineKeyboardButton("🎮 Chơi Game", callback_data="play_game"),
        types.InlineKeyboardButton("👤 Tài Khoản", callback_data="account")
    )
    keyboard.add(
        types.InlineKeyboardButton("📋 Menu Lệnh", callback_data="show_menu"),
        types.InlineKeyboardButton("📞 Liên Hệ ADMIN",
                                   url=f"https://t.me/{ADMIN_USERNAME.lstrip('@')}")
    )
    keyboard.add(types.InlineKeyboardButton("💬 Cộng Đồng", url=GROUP_LINK))
    return keyboard

# ==============================
# LỆNH START
# ==============================

@bot.message_handler(commands=["start"])
def start_command(message):
    user = message.from_user
    user_id = user.id
    fullname = get_full_name(user)
    username = f"@{user.username}" if user.username else ""

    user_data = get_user(user_id)
    user_data["fullname"] = fullname
    user_data["username"] = username
    save_data()

    log_activity("start", user_id, fullname, "Bắt đầu sử dụng bot")

    vip_text = get_vip_status_text(user_id)

    text = (
        "🎰 <b>HỆ THỐNG DỰ ĐOÁN TÀI XỈU</b> 🎰\n"
        "🔥 <b>UY TÍN - CHÍNH XÁC - TỐC ĐỘ</b> 🔥\n\n"
        "✨ <b>CHÀO MỪNG BẠN ĐẾN VỚI SÂN CHƠI</b> ✨\n"
        "🎯 <i>Dự đoán chuẩn - Trúng lớn mỗi ngày</i>\n\n"
        "👤 <b>THÔNG TIN TÀI KHOẢN</b>\n"
        "<blockquote>"
        f"👤 <b>Họ tên:</b> {fullname}\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"💎 <b>Số dư:</b> <b>{user_data['balance']:,} VND</b>\n"
        f"🎖️ <b>Trạng thái:</b> {vip_text}\n"
        "</blockquote>\n"
        "💡 <i>Chọn chức năng bên dưới để bắt đầu 👇</i>"
    )

    bot.send_message(message.chat.id, text, parse_mode="HTML",
                     reply_markup=build_main_keyboard())

# ==============================
# MENU LỆNH (HIỆN TẤT CẢ CHỨC NĂNG)
# ==============================

@bot.callback_query_handler(func=lambda call: call.data == "show_menu")
def show_menu_callback(call):
    bot.answer_callback_query(call.id)

    text = (
        "📋 <b>DANH SÁCH LỆNH & CHỨC NĂNG</b> 📋\n\n"

        "🚀 <b>/start</b>\n"
        "<blockquote>Khởi động bot & xem thông tin tài khoản</blockquote>\n"

        "💳 <b>Nạp Tiền</b>\n"
        "<blockquote>Nạp tiền vào tài khoản qua QR MB Bank</blockquote>\n"

        "🔑 <b>Mua Key VIP</b>\n"
        "<blockquote>Mua gói VIP để mở khóa chơi game</blockquote>\n"

        "🎮 <b>Chơi Game</b>\n"
        "<blockquote>Truy cập các game (yêu cầu VIP)</blockquote>\n"

        "👤 <b>Tài Khoản</b>\n"
        "<blockquote>Xem thông tin & số dư tài khoản</blockquote>\n"

        "📞 <b>Liên Hệ ADMIN</b>\n"
        "<blockquote>Hỗ trợ trực tiếp từ ADMIN</blockquote>\n"

        "💬 <b>Cộng Đồng</b>\n"
        "<blockquote>Tham gia group thông báo</blockquote>\n\n"

        "━━━━━━━━━━━━━━━━━━━━━\n"
        "💎 <b>CÁC GÓI VIP HIỆN CÓ:</b>\n"
        "<blockquote>"
        "🥉 Key 1 Ngày — 25.000 VND\n"
        "🥈 Key 3 Ngày — 50.000 VND\n"
        "🥇 Key 1 Tuần — 70.000 VND\n"
        "🏆 Key 1 Tháng — 150.000 VND\n"
        "👑 Key 1 Năm — 200.000 VND\n"
        "💎 Key Vĩnh Viễn — 350.000 VND\n"
        "</blockquote>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"

        "🔥 <i>Chọn chức năng để tiếp tục trải nghiệm!</i>"
    )

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("💳 Nạp Tiền", callback_data="deposit"),
        types.InlineKeyboardButton("🔑 Mua Key", callback_data="buy_key")
    )
    keyboard.add(
        types.InlineKeyboardButton("🎮 Chơi Game", callback_data="play_game"),
        types.InlineKeyboardButton("👤 Tài Khoản", callback_data="account")
    )
    keyboard.add(types.InlineKeyboardButton("🔙 Quay Lại", callback_data="back_to_menu"))

    bot.send_message(call.message.chat.id, text, parse_mode="HTML",
                     reply_markup=keyboard)

# ==============================
# NÚT NẠP TIỀN
# ==============================

@bot.callback_query_handler(func=lambda call: call.data == "deposit")
def deposit_callback(call):
    bot.answer_callback_query(call.id)
    text = (
        "💳 <b>NẠP TIỀN VÀO HỆ THỐNG</b>\n\n"
        "📝 <b>Vui Lòng Nhập Số Tiền Cần Nạp:</b>\n\n"
        "💰 <i>Ví dụ: 100000 (tương đương 100.000 VND)</i>\n"
        "⚠️ <i>Số tiền tối thiểu: 10.000 VND</i>\n\n"
        "👉 <i>Hãy gửi số tiền bạn muốn nạp ngay bây giờ:</i>"
    )
    msg = bot.send_message(call.message.chat.id, text, parse_mode="HTML")
    bot.register_next_step_handler(msg, process_amount)

def process_amount(message):
    user = message.from_user
    raw = message.text.strip().replace(".", "").replace(",", "").replace(" ", "")

    if not raw.isdigit():
        msg = bot.send_message(message.chat.id,
            "❌ <b>Số tiền không hợp lệ!</b>\n"
            "👉 Vui lòng nhập lại <b>chỉ với chữ số</b> (Ví dụ: 100000):",
            parse_mode="HTML")
        bot.register_next_step_handler(msg, process_amount)
        return

    amount = int(raw)

    if amount < 10000:
        msg = bot.send_message(message.chat.id,
            "⚠️ <b>Số tiền quá nhỏ!</b>\n"
            "👉 Số tiền nạp tối thiểu là <b>10.000 VND</b>.\n"
            "Vui lòng nhập lại:", parse_mode="HTML")
        bot.register_next_step_handler(msg, process_amount)
        return

    if amount > 100_000_000:
        msg = bot.send_message(message.chat.id,
            "⚠️ <b>Số tiền quá lớn!</b>\n"
            "👉 Vui lòng liên hệ ADMIN để nạp số tiền lớn.\n"
            "Nhập lại số tiền hợp lệ:", parse_mode="HTML")
        bot.register_next_step_handler(msg, process_amount)
        return

    add_info = f"NAP {user.id}"
    qr_url = (f"https://img.vietqr.io/image/"
              f"{BANK_BIN}-{ACCOUNT_NO}-compact2.png"
              f"?amount={amount}"
              f"&addInfo={quote(add_info)}"
              f"&accountName={quote(ACCOUNT_NAME)}")

    caption = (
        "💳 <b>THÔNG TIN CHUYỂN KHOẢN</b>\n\n"
        f"💰 <b>Số tiền:</b> <b>{amount:,} VND</b>\n\n"
        "<blockquote>"
        f"🏦 <b>Ngân hàng:</b> {BANK_NAME}\n"
        f"💳 <b>Số tài khoản:</b> <code>{ACCOUNT_NO}</code>\n"
        f"👤 <b>Chủ tài khoản:</b> {ACCOUNT_NAME}\n"
        f"💵 <b>Số tiền:</b> <b>{amount:,} VND</b>\n"
        f"📝 <b>Nội dung CK:</b> <code>{add_info}</code>\n"
        "</blockquote>\n"
        "⚠️ <b>LƯU Ý QUAN TRỌNG:</b>\n"
        "🔹 Quét mã QR hoặc chuyển khoản thủ công theo thông tin trên.\n"
        "🔹 Ghi <b>ĐÚNG nội dung</b> chuyển khoản để hệ thống xử lý tự động.\n"
        "🔹 Sau khi chuyển khoản thành công, bấm nút "
        "<b>✅ Tôi Đã Chuyển Khoản</b> bên dưới.\n"
        "🔹 Tiền sẽ được cộng vào tài khoản trong vòng <b>1 - 5 phút</b>.\n\n"
        "💬 <i>Nếu sau 5 phút chưa nhận được tiền, vui lòng liên hệ ADMIN "
        "để được hỗ trợ.</i>"
    )

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(
        "✅ Tôi Đã Chuyển Khoản",
        callback_data=f"confirm_deposit_{amount}"))
    keyboard.add(types.InlineKeyboardButton(
        "📞 Liên Hệ ADMIN",
        url=f"https://t.me/{ADMIN_USERNAME.lstrip('@')}"))

    bot.send_photo(message.chat.id, photo=qr_url, caption=caption,
                   parse_mode="HTML", reply_markup=keyboard)

# ==============================
# NÚT "TÔI ĐÃ CHUYỂN KHOẢN"
# ==============================

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_deposit_"))
def confirm_deposit_callback(call):
    amount = int(call.data.split("_")[-1])
    user = call.from_user
    fullname = get_full_name(user)
    time_vn = get_vn_time()

    pending_deposits[user.id] = {
        "amount": amount, "fullname": fullname, "time": time_vn
    }

    bot.answer_callback_query(call.id, "✅ Đã gửi đơn nạp tiền đến ADMIN!")

    bot.send_message(call.message.chat.id,
        "📩 <b>ĐÃ GỬI ĐƠN NẠP TIỀN</b>\n\n"
        "<blockquote>"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"👤 <b>Họ tên:</b> {fullname}\n"
        f"💰 <b>Số tiền:</b> <b>{amount:,} VND</b>\n"
        f"⏰ <b>Thời gian:</b> {time_vn}\n"
        f"⏳ <b>Trạng thái:</b> Đang chờ ADMIN duyệt...\n"
        "</blockquote>\n\n"
        "⚠️ <i>Vui lòng chờ ADMIN xác nhận. Tiền sẽ được cộng trong vòng "
        "1-5 phút!</i>", parse_mode="HTML")

    admin_text = (
        "🔔 <b>ĐƠN NẠP TIỀN MỚI</b> 🔔\n\n"
        "<blockquote>"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"👤 <b>Họ tên:</b> {fullname}\n"
        f"💰 <b>Số tiền:</b> <b>{amount:,} VND</b>\n"
        f"⏰ <b>Thời gian:</b> {time_vn}\n"
        "</blockquote>\n\n"
        "👉 <b>Xác nhận duyệt đơn nạp tiền này?</b>"
    )

    admin_keyboard = types.InlineKeyboardMarkup(row_width=2)
    admin_keyboard.add(
        types.InlineKeyboardButton("✅ Duyệt",
                                   callback_data=f"approve_{user.id}_{amount}"),
        types.InlineKeyboardButton("❌ Từ Chối",
                                   callback_data=f"reject_{user.id}_{amount}")
    )

    bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML",
                     reply_markup=admin_keyboard)

# ==============================
# ADMIN DUYỆT / TỪ CHỐI
# ==============================

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def admin_approve_callback(call):
    data = call.data.split("_")
    user_id = int(data[1])
    amount = int(data[2])

    pending = pending_deposits.get(user_id, {})
    fullname = pending.get("fullname", "Thành viên")

    update_balance(user_id, amount)
    new_balance = get_user(user_id)["balance"]

    if user_id in pending_deposits:
        del pending_deposits[user_id]

    bot.answer_callback_query(call.id, "✅ Đã duyệt đơn nạp!")
    time_vn = get_vn_time()

    log_activity("deposit", user_id, fullname, "Nạp tiền thành công", amount)

    try:
        bot.send_message(user_id,
            "✅ <b>NẠP TIỀN THÀNH CÔNG</b> ✅\n\n"
            "<blockquote>"
            f"💰 <b>Số tiền nạp:</b> <b>{amount:,} VND</b>\n"
            f"💎 <b>Số dư mới:</b> <b>{new_balance:,} VND</b>\n"
            f"⏰ <b>Thời gian:</b> {time_vn}\n"
            "</blockquote>\n\n"
            "🎉 <i>Cảm ơn bạn đã nạp tiền! Chúc bạn chơi game vui vẻ!</i>",
            parse_mode="HTML")
    except Exception as e:
        print(f"Không thể gửi tin nhắn cho user {user_id}: {e}")

    group_text = (
        "🎉 <b>THÔNG BÁO NẠP TIỀN THÀNH CÔNG</b> 🎉\n\n"
        f"👤 <b>Họ tên:</b> {fullname}\n"
        f"💰 <b>Số tiền:</b> <b>{amount:,} VND</b>\n"
        f"⏰ <b>Thời gian:</b> {time_vn}\n\n"
        "💎 <i>Chúc mừng thành viên đã nạp tiền thành công!</i>\n"
        "🔥 <i>Tham gia chơi ngay để nhận thưởng lớn!</i>"
    )

    group_keyboard = types.InlineKeyboardMarkup(row_width=2)
    group_keyboard.add(
        types.InlineKeyboardButton("🤖 Vào Bot", url=BOT_LINK),
        types.InlineKeyboardButton("📢 Group Thông Báo", url=GROUP_LINK)
    )

    try:
        bot.send_message(GROUP_CHAT_ID, group_text, parse_mode="HTML",
                         reply_markup=group_keyboard)
    except Exception as e:
        print(f"Không thể gửi tin nhắn lên group: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_"))
def admin_reject_callback(call):
    data = call.data.split("_")
    user_id = int(data[1])
    amount = int(data[2])

    pending = pending_deposits.get(user_id, {})
    fullname = pending.get("fullname", "Thành viên")

    if user_id in pending_deposits:
        del pending_deposits[user_id]

    bot.answer_callback_query(call.id, "❌ Đã từ chối đơn nạp!")

    log_activity("reject", user_id, fullname, "Đơn nạp bị từ chối", amount)

    try:
        bot.send_message(user_id,
            "❌ <b>ĐƠN NẠP TIỀN BỊ TỪ CHỐI</b>\n\n"
            f"💰 <b>Số tiền:</b> {amount:,} VND\n\n"
            f"📞 <i>Vui lòng liên hệ ADMIN {ADMIN_USERNAME} "
            "để được hỗ trợ!</i>", parse_mode="HTML")
    except Exception as e:
        print(f"Không thể gửi tin nhắn cho user {user_id}: {e}")

# ==============================
# NÚT TÀI KHOẢN
# ==============================

@bot.callback_query_handler(func=lambda call: call.data == "account")
def account_callback(call):
    user = call.from_user
    fullname = get_full_name(user)
    user_data = get_user(user.id)
    vip_text = get_vip_status_text(user.id)

    text = (
        "👤 <b>THÔNG TIN TÀI KHOẢN</b> 👤\n\n"
        "<blockquote>"
        f"👤 <b>Họ tên:</b> {fullname}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"💎 <b>Số dư:</b> <b>{user_data['balance']:,} VND</b>\n"
        f"🎖️ <b>Trạng thái:</b> {vip_text}\n"
        f"💵 <b>Tổng chi tiêu:</b> <b>{user_data.get('total_spent', 0):,} VND</b>\n"
        f"📅 <b>Tham gia:</b> {user_data.get('joined', 'N/A')}\n"
        "</blockquote>\n\n"
        "💡 <i>Nạp tiền để tham gia đặt cược ngay!</i>"
    )
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, text, parse_mode="HTML")

# ==============================
# NÚT MUA KEY
# ==============================

@bot.callback_query_handler(func=lambda call: call.data == "buy_key")
def buy_key_callback(call):
    bot.answer_callback_query(call.id)

    text = (
        "🔑 <b>MUA KEY VIP</b> 🔑\n\n"
        "💎 <b>Chọn gói VIP phù hợp với bạn:</b>\n\n"
        "<blockquote>"
        "🥉 <b>Key 1 Ngày</b> — 25.000 VND\n"
        "🥈 <b>Key 3 Ngày</b> — 50.000 VND\n"
        "🥇 <b>Key 1 Tuần</b> — 70.000 VND\n"
        "🏆 <b>Key 1 Tháng</b> — 150.000 VND\n"
        "👑 <b>Key 1 Năm</b> — 200.000 VND\n"
        "💎 <b>Key Vĩnh Viễn</b> — 350.000 VND\n"
        "</blockquote>\n\n"
        "⚠️ <i>Số tiền sẽ được trừ trực tiếp từ số dư của bạn.</i>\n"
        "💡 <i>Nếu chưa đủ tiền, hãy nạp thêm trước khi mua!</i>"
    )

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for pkg_key, pkg in VIP_PACKAGES.items():
        keyboard.add(types.InlineKeyboardButton(
            f"{pkg['emoji']} {pkg['name']} — {pkg['price']:,}đ",
            callback_data=f"buy_package_{pkg_key}"
        ))
    keyboard.add(types.InlineKeyboardButton(
        "💳 Nạp Tiền Ngay", callback_data="deposit"))
    keyboard.add(types.InlineKeyboardButton(
        "📞 Liên Hệ ADMIN",
        url=f"https://t.me/{ADMIN_USERNAME.lstrip('@')}"))

    bot.send_message(call.message.chat.id, text, parse_mode="HTML",
                     reply_markup=keyboard)

# ==============================
# XỬ LÝ MUA GÓI VIP
# ==============================

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_package_"))
def buy_package_callback(call):
    pkg_key = call.data.replace("buy_package_", "")
    if pkg_key not in VIP_PACKAGES:
        bot.answer_callback_query(call.id, "❌ Gói không tồn tại!", show_alert=True)
        return

    pkg = VIP_PACKAGES[pkg_key]
    user = call.from_user
    fullname = get_full_name(user)
    user_data = get_user(user.id)

    if user_data["balance"] < pkg["price"]:
        missing = pkg["price"] - user_data["balance"]
        bot.answer_callback_query(call.id, "❌ Số dư không đủ!", show_alert=True)

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(
            "💳 Nạp Tiền Ngay", callback_data="deposit"))
        keyboard.add(types.InlineKeyboardButton(
            "📞 Liên Hệ ADMIN",
            url=f"https://t.me/{ADMIN_USERNAME.lstrip('@')}"))

        bot.send_message(call.message.chat.id,
            f"❌ <b>KHÔNG ĐỦ SỐ DƯ</b>\n\n"
            "<blockquote>"
            f"🎁 <b>Gói:</b> {pkg['emoji']} {pkg['name']}\n"
            f"💰 <b>Giá:</b> <b>{pkg['price']:,} VND</b>\n"
            f"💎 <b>Số dư hiện tại:</b> <b>{user_data['balance']:,} VND</b>\n"
            f"⚠️ <b>Cần thêm:</b> <b>{missing:,} VND</b>\n"
            "</blockquote>\n\n"
            "👉 <i>Vui lòng nạp thêm tiền để tiếp tục mua gói này!</i>",
            parse_mode="HTML", reply_markup=keyboard)
        return

    user_data["balance"] -= pkg["price"]
    user_data["total_spent"] = user_data.get("total_spent", 0) + pkg["price"]
    add_vip(user.id, pkg["days"])

    time_vn = get_vn_time()
    user_data["purchases"].append({
        "package": pkg_key,
        "name": pkg["name"],
        "price": pkg["price"],
        "time": time_vn
    })
    save_data()

    log_activity("purchase", user.id, fullname, pkg["name"], pkg["price"])

    bot.answer_callback_query(call.id, f"✅ Mua thành công {pkg['name']}!")

    vip_status = get_vip_status_text(user.id)

    bot.send_message(call.message.chat.id,
        "✅ <b>MUA GÓI VIP THÀNH CÔNG</b> ✅\n\n"
        "<blockquote>"
        f"🎁 <b>Gói đã mua:</b> {pkg['emoji']} {pkg['name']}\n"
        f"💰 <b>Giá:</b> <b>{pkg['price']:,} VND</b>\n"
        f"💎 <b>Số dư còn lại:</b> <b>{user_data['balance']:,} VND</b>\n"
        f"🎖️ <b>Trạng thái:</b> {vip_status}\n"
        f"⏰ <b>Thời gian:</b> {time_vn}\n"
        "</blockquote>\n\n"
        "🎉 <i>Cảm ơn bạn đã mua gói VIP! "
        "Chúc bạn chơi game vui vẻ và thắng lớn!</i>",
        parse_mode="HTML")

    try:
        bot.send_message(ADMIN_ID,
            "🛒 <b>ĐƠN MUA VIP MỚI</b> 🛒\n\n"
            "<blockquote>"
            f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
            f"👤 <b>Họ tên:</b> {fullname}\n"
            f"🎁 <b>Gói:</b> {pkg['emoji']} {pkg['name']}\n"
            f"💰 <b>Giá:</b> <b>{pkg['price']:,} VND</b>\n"
            f"⏰ <b>Thời gian:</b> {time_vn}\n"
            "</blockquote>", parse_mode="HTML")
    except Exception as e:
        print(f"Không thể gửi thông báo cho admin: {e}")

    group_text = (
        "🎉 <b>THÔNG BÁO MUA VIP THÀNH CÔNG</b> 🎉\n\n"
        f"👤 <b>Họ tên:</b> {fullname}\n"
        f"🎁 <b>Gói VIP:</b> {pkg['emoji']} <b>{pkg['name']}</b>\n"
        f"💰 <b>Giá trị:</b> <b>{pkg['price']:,} VND</b>\n"
        f"⏰ <b>Thời gian:</b> {time_vn}\n\n"
        "💎 <i>Chúc mừng thành viên đã nâng cấp VIP thành công!</i>\n"
        "🔥 <i>Tham gia chơi ngay để nhận thưởng lớn!</i>"
    )

    group_keyboard = types.InlineKeyboardMarkup(row_width=2)
    group_keyboard.add(
        types.InlineKeyboardButton("🤖 Vào Bot", url=BOT_LINK),
        types.InlineKeyboardButton("📢 Group Thông Báo", url=GROUP_LINK)
    )

    try:
        bot.send_message(GROUP_CHAT_ID, group_text, parse_mode="HTML",
                         reply_markup=group_keyboard)
    except Exception as e:
        print(f"Không thể gửi tin nhắn lên group: {e}")

# ==============================
# NÚT CHƠI GAME
# ==============================

@bot.callback_query_handler(func=lambda call: call.data == "play_game")
def play_game_callback(call):
    user = call.from_user

    if not is_vip_active(user.id):
        bot.answer_callback_query(call.id, "❌ Bạn chưa có VIP!", show_alert=True)

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton(
            "🔑 Mua Key VIP Ngay", callback_data="buy_key"))
        keyboard.add(types.InlineKeyboardButton(
            "📞 Liên Hệ ADMIN",
            url=f"https://t.me/{ADMIN_USERNAME.lstrip('@')}"))

        bot.send_message(call.message.chat.id,
            "🔒 <b>YÊU CẦU VIP</b>\n\n"
            "<blockquote>"
            "❌ Bạn chưa có gói VIP để chơi game!\n"
            "💎 Vui lòng mua VIP để truy cập vào hệ thống game.\n"
            "</blockquote>\n\n"
            "🎁 <b>Các gói VIP hiện có:</b>\n"
            "<blockquote>"
            "🥉 Key 1 Ngày — 25.000 VND\n"
            "🥈 Key 3 Ngày — 50.000 VND\n"
            "🥇 Key 1 Tuần — 70.000 VND\n"
            "🏆 Key 1 Tháng — 150.000 VND\n"
            "👑 Key 1 Năm — 200.000 VND\n"
            "💎 Key Vĩnh Viễn — 350.000 VND\n"
            "</blockquote>\n\n"
            "👉 <i>Nhấn nút bên dưới để mua VIP ngay!</i>",
            parse_mode="HTML", reply_markup=keyboard)
        return

    bot.answer_callback_query(call.id, "🎮 Đang mở danh sách game...")

    vip_text = get_vip_status_text(user.id)

    text = (
        "🎮 <b>DANH SÁCH GAME</b> 🎮\n\n"
        f"🎖️ <b>Trạng thái:</b> {vip_text}\n\n"
        "🎯 <b>Chọn game bạn muốn chơi:</b>\n"
        "<blockquote>"
        "☀️ <b>Sunwin</b> — Game bài đổi thưởng\n"
        "🎯 <b>B52 Club</b> — Sân chơi đỉnh cao\n"
        "🎰 <b>Go88</b> — Cổng game quốc tế\n"
        "🎲 <b>Rikvip</b> — Game bài uy tín\n"
        "🃏 <b>Manclub</b> — Đẳng cấp số 1\n"
        "🎴 <b>789 Club</b> — Kho game khổng lồ\n"
        "</blockquote>\n\n"
        "🔥 <i>Chọn game bên dưới để bắt đầu trải nghiệm!</i>"
    )

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for game_key, game in GAMES.items():
        keyboard.add(types.InlineKeyboardButton(
            f"{game['emoji']} {game['name']}",
            callback_data=f"game_{game_key}"
        ))
    keyboard.add(types.InlineKeyboardButton(
        "🔙 Quay Lại", callback_data="back_to_menu"))

    bot.send_message(call.message.chat.id, text, parse_mode="HTML",
                     reply_markup=keyboard)

# ==============================
# XỬ LÝ CHỌN GAME
# ==============================

@bot.callback_query_handler(func=lambda call: call.data.startswith("game_"))
def game_callback(call):
    game_key = call.data.replace("game_", "")
    if game_key not in GAMES:
        bot.answer_callback_query(call.id, "❌ Game không tồn tại!", show_alert=True)
        return

    game = GAMES[game_key]
    user = call.from_user

    if not is_vip_active(user.id):
        bot.answer_callback_query(call.id, "❌ VIP đã hết hạn!", show_alert=True)
        return

    bot.answer_callback_query(call.id, f"🎮 Đang mở {game['name']}...")

    text = (
        f"{game['emoji']} <b>{game['name'].upper()}</b> {game['emoji']}\n\n"
        "<blockquote>"
        f"🎮 <b>Game:</b> {game['name']}\n"
        f"🔗 <b>Link:</b> <a href=\"{game['link']}\">Nhấn vào đây để chơi</a>\n"
        "</blockquote>\n\n"
        "⚠️ <i>Vui lòng đăng nhập và chơi có trách nhiệm!</i>\n"
        "💎 <i>Chúc bạn may mắn và thắng lớn!</i>"
    )

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(types.InlineKeyboardButton(
        f"🎮 Chơi {game['name']}", url=game["link"]))
    keyboard.add(types.InlineKeyboardButton(
        "🔙 Danh Sách Game", callback_data="play_game"))

    bot.send_message(call.message.chat.id, text, parse_mode="HTML",
                     reply_markup=keyboard)

# ==============================
# NÚT QUAY LẠI MENU
# ==============================

@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu_callback(call):
    bot.answer_callback_query(call.id)

    user = call.from_user
    fullname = get_full_name(user)
    user_data = get_user(user.id)
    vip_text = get_vip_status_text(user.id)

    text = (
        "🎰 <b>HỆ THỐNG DỰ ĐOÁN TÀI XỈU</b> 🎰\n"
        "🔥 <b>UY TÍN - CHÍNH XÁC - TỐC ĐỘ</b> 🔥\n\n"
        "👤 <b>THÔNG TIN TÀI KHOẢN</b>\n"
        "<blockquote>"
        f"👤 <b>Họ tên:</b> {fullname}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"💎 <b>Số dư:</b> <b>{user_data['balance']:,} VND</b>\n"
        f"🎖️ <b>Trạng thái:</b> {vip_text}\n"
        "</blockquote>\n"
        "💡 <i>Chọn chức năng bên dưới để bắt đầu 👇</i>"
    )

    bot.send_message(call.message.chat.id, text, parse_mode="HTML",
                     reply_markup=build_main_keyboard())

# ==============================
# CHẠY SONG SONG FLASK + BOT
# ==============================

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    try:
        bot.remove_webhook()
        print("✅ Đã xóa webhook cũ")
    except Exception as e:
        print(f"⚠️ Không thể xóa webhook: {e}")

    register_commands()

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"🌐 Flask đang chạy tại http://0.0.0.0:{os.environ.get('PORT', 5000)}")

    print("🤖 Bot Telegram đang chạy...")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)