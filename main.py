import telebot
from telebot import types
from urllib.parse import quote
from datetime import datetime
import pytz
import json
import os
import time
import threading
from flask import Flask, render_template, send_file

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
    "1day":    {"name": "Key 1 Ngày",      "price": 25000,  "days": 1,    "emoji": "🥉"},
    "3day":    {"name": "Key 3 Ngày",      "price": 50000,  "days": 3,    "emoji": "🥈"},
    "1week":   {"name": "Key 1 Tuần",      "price": 70000,  "days": 7,    "emoji": "🥇"},
    "1month":  {"name": "Key 1 Tháng",     "price": 150000, "days": 30,   "emoji": "🏆"},
    "1year":   {"name": "Key 1 Năm",       "price": 200000, "days": 365,  "emoji": "👑"},
    "forever": {"name": "Key Vĩnh Viễn",   "price": 350000, "days": -1,   "emoji": "💎"},
}

# ==============================
# DANH SÁCH GAME
# ==============================

GAMES = {
    "sunwin":   {"name": "Sunwin",    "emoji": "☀️", "link": "https://sunwin.com"},
    "b52":      {"name": "B52 Club",  "emoji": "🎯", "link": "https://b52.club"},
    "go88":     {"name": "Go88",      "emoji": "🎰", "link": "https://go88.com"},
    "rikvip":   {"name": "Rikvip",    "emoji": "🎲", "link": "https://rikvip.com"},
    "manclub":  {"name": "Manclub",   "emoji": "🃏", "link": "https://manclub.com"},
    "789club":  {"name": "789 Club",  "emoji": "🎴", "link": "https://789club.com"},
}

# ==============================
# FILE JSON
# ==============================

DATA_FILE = "users.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users_db, f, ensure_ascii=False, indent=4)

users_db = load_data()
pending_deposits = {}

def get_user(user_id):
    uid = str(user_id)
    if uid not in users_db:
        users_db[uid] = {
            "username": "Thành viên",
            "balance": 0,
            "vip_expiry": 0,
            "total_spent": 0,
            "purchases": []
        }
        save_data()
    # Đảm bảo các key tồn tại (cho data cũ)
    users_db[uid].setdefault("vip_expiry", 0)
    users_db[uid].setdefault("total_spent", 0)
    users_db[uid].setdefault("purchases", [])
    return users_db[uid]

def update_balance(user_id, amount):
    user = get_user(user_id)
    user["balance"] += amount
    save_data()

def get_vn_time():
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    return datetime.now(tz).strftime("%H:%M:%S - %d/%m/%Y")

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
        return "💎 VIP: Vĩnh viễn ♾️"
    if expiry <= time.time():
        return "❌ VIP: Chưa kích hoạt"
    remaining = expiry - time.time()
    days = int(remaining // 86400)
    hours = int((remaining % 86400) // 3600)
    minutes = int((remaining % 3600) // 60)
    return f"✅ VIP: Còn {days} ngày {hours} giờ {minutes} phút"

def add_vip(user_id, duration_days):
    user = get_user(user_id)
    now = time.time()
    current = user.get("vip_expiry", 0)

    if duration_days == -1:
        user["vip_expiry"] = -1
    elif current == -1:
        pass  # Đã vĩnh viễn
    elif current > now:
        user["vip_expiry"] = current + duration_days * 86400
    else:
        user["vip_expiry"] = now + duration_days * 86400
    save_data()

# ==============================
# FLASK WEB SERVER
# ==============================

app = Flask(__name__)

@app.route("/", methods=["GET", "HEAD"])
def home():
    try:
        total_users = len(users_db)
        total_balance = sum(u.get("balance", 0) for u in users_db.values())
        total_vip = sum(1 for u in users_db.values() if u.get("vip_expiry", 0) == -1 or u.get("vip_expiry", 0) > time.time())
        total_revenue = sum(u.get("total_spent", 0) for u in users_db.values())
    except Exception:
        total_users = total_balance = total_vip = total_revenue = 0
    return render_template("index.html",
                           total_users=total_users,
                           total_balance=total_balance,
                           total_vip=total_vip,
                           total_revenue=total_revenue)

@app.route("/download-json", methods=["GET", "HEAD"])
def download_json():
    if not os.path.exists(DATA_FILE):
        save_data()
    return send_file(DATA_FILE,
                     mimetype="application/json",
                     as_attachment=True,
                     download_name="users.json")

@app.route("/health", methods=["GET", "HEAD"])
def health():
    return "OK", 200

# ==============================
# LỆNH START
# ==============================

@bot.message_handler(commands=["start"])
def start_command(message):
    user = message.from_user
    user_id = user.id
    user_data = get_user(user_id)
    user_data["username"] = f"@{user.username}" if user.username else user.first_name
    save_data()

    vip_text = get_vip_status_text(user_id)

    text = (
        "🎰 <b>HỆ THỐNG DỰ ĐOÁN TÀI XỈU</b> 🎰\n"
        "🔥 <b>UY TÍN - CHÍNH XÁC - TỐC ĐỘ</b> 🔥\n\n"
        "✨ <b>CHÀO MỪNG BẠN ĐẾN VỚI SÂN CHƠI</b> ✨\n"
        "🎯 <i>Dự đoán chuẩn - Trúng lớn mỗi ngày</i>\n\n"
        "👤 <b>THÔNG TIN TÀI KHOẢN</b>\n"
        "<blockquote>"
        f"👤 <b>Tên:</b> {user_data['username']}\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"💎 <b>Số dư:</b> <b>{user_data['balance']:,} VND</b>\n"
        f"🎖️ <b>Trạng thái:</b> {vip_text}\n"
        "</blockquote>\n"
        "💡 <i>Chọn chức năng bên dưới để bắt đầu 👇</i>"
    )

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("💳 Nạp Tiền", callback_data="deposit"),
        types.InlineKeyboardButton("🔑 Mua Key", callback_data="buy_key")
    )
    keyboard.add(
        types.InlineKeyboardButton("🎮 Chơi Game", callback_data="play_game"),
        types.InlineKeyboardButton("📞 Liên Hệ ADMIN",
                                   url=f"https://t.me/{ADMIN_USERNAME.lstrip('@')}")
    )
    keyboard.add(types.InlineKeyboardButton("💬 Cộng Đồng", url=GROUP_LINK))

    bot.send_message(message.chat.id, text, parse_mode="HTML",
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
    username = f"@{user.username}" if user.username else user.first_name
    time_vn = get_vn_time()

    pending_deposits[user.id] = {
        "amount": amount, "username": username, "time": time_vn
    }

    bot.answer_callback_query(call.id, "✅ Đã gửi đơn nạp tiền đến ADMIN!")

    bot.send_message(call.message.chat.id,
        "📩 <b>ĐÃ GỬI ĐƠN NẠP TIỀN</b>\n\n"
        "<blockquote>"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"👤 <b>Tên:</b> {username}\n"
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
        f"👤 <b>Username:</b> {username}\n"
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
# ADMIN DUYỆT / TỪ CHỐI NẠP
# ==============================

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def admin_approve_callback(call):
    data = call.data.split("_")
    user_id = int(data[1])
    amount = int(data[2])

    pending = pending_deposits.get(user_id, {})
    username = pending.get("username", "Thành viên")

    update_balance(user_id, amount)
    new_balance = get_user(user_id)["balance"]

    if user_id in pending_deposits:
        del pending_deposits[user_id]

    bot.answer_callback_query(call.id, "✅ Đã duyệt đơn nạp!")
    time_vn = get_vn_time()

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
        f"👤 <b>Username:</b> {username}\n"
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

    if user_id in pending_deposits:
        del pending_deposits[user_id]

    bot.answer_callback_query(call.id, "❌ Đã từ chối đơn nạp!")

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
    user_data = get_user(user.id)
    username = f"@{user.username}" if user.username else user.first_name
    vip_text = get_vip_status_text(user.id)

    text = (
        "👤 <b>THÔNG TIN TÀI KHOẢN</b> 👤\n\n"
        "<blockquote>"
        f"👤 <b>Tên:</b> {username}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"💎 <b>Số dư:</b> <b>{user_data['balance']:,} VND</b>\n"
        f"🎖️ <b>Trạng thái:</b> {vip_text}\n"
        f"💵 <b>Tổng chi tiêu:</b> <b>{user_data.get('total_spent', 0):,} VND</b>\n"
        "</blockquote>\n\n"
        "💡 <i>Nạp tiền để tham gia đặt cược ngay!</i>"
    )
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, text, parse_mode="HTML")

# ==============================
# NÚT MUA KEY (MENU GÓI)
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
    user_data = get_user(user.id)

    # Kiểm tra số dư
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

    # Trừ tiền
    user_data["balance"] -= pkg["price"]
    user_data["total_spent"] = user_data.get("total_spent", 0) + pkg["price"]

    # Thêm VIP
    add_vip(user.id, pkg["days"])

    # Lưu lịch sử
    time_vn = get_vn_time()
    user_data["purchases"].append({
        "package": pkg_key,
        "name": pkg["name"],
        "price": pkg["price"],
        "time": time_vn
    })
    save_data()

    bot.answer_callback_query(call.id, f"✅ Mua thành công {pkg['name']}!")

    vip_status = get_vip_status_text(user.id)

    # Thông báo cho user
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

    # Thông báo cho ADMIN
    username = f"@{user.username}" if user.username else user.first_name
    try:
        bot.send_message(ADMIN_ID,
            "🛒 <b>ĐƠN MUA VIP MỚI</b> 🛒\n\n"
            "<blockquote>"
            f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
            f"👤 <b>Username:</b> {username}\n"
            f"🎁 <b>Gói:</b> {pkg['emoji']} {pkg['name']}\n"
            f"💰 <b>Giá:</b> <b>{pkg['price']:,} VND</b>\n"
            f"⏰ <b>Thời gian:</b> {time_vn}\n"
            "</blockquote>", parse_mode="HTML")
    except Exception as e:
        print(f"Không thể gửi thông báo cho admin: {e}")

    # Thông báo lên GROUP
    group_text = (
        "🎉 <b>THÔNG BÁO MUA VIP THÀNH CÔNG</b> 🎉\n\n"

        f"👤 <b>Username:</b> {username}\n"
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

    # Kiểm tra VIP
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
    user_data = get_user(user.id)
    username = f"@{user.username}" if user.username else user.first_name
    vip_text = get_vip_status_text(user.id)

    text = (
        "🎰 <b>HỆ THỐNG DỰ ĐOÁN TÀI XỈU</b> 🎰\n"
        "🔥 <b>UY TÍN - CHÍNH XÁC - TỐC ĐỘ</b> 🔥\n\n"
        "👤 <b>THÔNG TIN TÀI KHOẢN</b>\n"
        "<blockquote>"
        f"👤 <b>Tên:</b> {username}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"💎 <b>Số dư:</b> <b>{user_data['balance']:,} VND</b>\n"
        f"🎖️ <b>Trạng thái:</b> {vip_text}\n"
        "</blockquote>\n"
        "💡 <i>Chọn chức năng bên dưới để bắt đầu 👇</i>"
    )

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("💳 Nạp Tiền", callback_data="deposit"),
        types.InlineKeyboardButton("🔑 Mua Key", callback_data="buy_key")
    )
    keyboard.add(
        types.InlineKeyboardButton("🎮 Chơi Game", callback_data="play_game"),
        types.InlineKeyboardButton("📞 Liên Hệ ADMIN",
                                   url=f"https://t.me/{ADMIN_USERNAME.lstrip('@')}")
    )
    keyboard.add(types.InlineKeyboardButton("💬 Cộng Đồng", url=GROUP_LINK))

    bot.send_message(call.message.chat.id, text, parse_mode="HTML",
                     reply_markup=keyboard)

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

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"🌐 Flask đang chạy tại http://0.0.0.0:{os.environ.get('PORT', 5000)}")

    print("🤖 Bot Telegram đang chạy...")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)