import telebot
from telebot import types
from urllib.parse import quote
from collections import defaultdict
from datetime import datetime
import pytz
import json
import os
import threading
from flask import Flask, render_template, send_file

# ==============================
# CẤU HÌNH BOT
# ==============================

BOT_TOKEN = "8638972575:AAGMXJqG2U3Ukg9aH6T0ngcNoDGR-tibZYI"
bot = telebot.TeleBot(BOT_TOKEN)

# ==============================
# CẤU HÌNH ADMIN & GROUP
# ==============================

ADMIN_ID       = 8771034410
ADMIN_USERNAME = "@NguyenVanGiaHuyy"
GROUP_CHAT_ID  = -1004442084088
BOT_LINK       = "https://t.me/CNDDTX_BOT"
GROUP_LINK     = "https://t.me/HTDDTX"

# ==============================
# CẤU HÌNH NGÂN HÀNG (VIETQR)
# ==============================

BANK_BIN     = "970422"
BANK_NAME    = "MB Bank"
ACCOUNT_NO   = "101072011"
ACCOUNT_NAME = "NGUYEN VAN GIA HUY"

# ==============================
# FILE LƯU TRỮ JSON
# ==============================

DATA_FILE = "users.json"

# ==============================
# HÀM ĐỌC / GHI JSON
# ==============================

def load_data():
    """Đọc dữ liệu từ file JSON."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data():
    """Ghi dữ liệu vào file JSON."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users_db, f, ensure_ascii=False, indent=4)

# ==============================
# KHỞI TẠO DỮ LIỆU
# ==============================

users_db = load_data()   # { "user_id": { "username": str, "balance": int } }
pending_deposits = {}

def get_user(user_id):
    """Lấy hoặc tạo mới thông tin người dùng."""
    uid = str(user_id)
    if uid not in users_db:
        users_db[uid] = {"username": "Thành viên", "balance": 0}
        save_data()
    return users_db[uid]

def update_balance(user_id, amount):
    """Cập nhật số dư người dùng."""
    user = get_user(user_id)
    user["balance"] += amount
    save_data()

# ==============================
# HÀM LẤY THỜI GIAN VIỆT NAM
# ==============================

def get_vn_time():
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    return datetime.now(tz).strftime("%H:%M:%S - %d/%m/%Y")

# ==============================
# FLASK WEB SERVER
# ==============================

app = Flask(__name__)

@app.route("/")
def home():
    """Trang chủ hiển thị số người dùng và nút tải JSON."""
    total_users = len(users_db)
    total_balance = sum(u["balance"] for u in users_db.values())
    return render_template("index.html",
                           total_users=total_users,
                           total_balance=total_balance)

@app.route("/download-json")
def download_json():
    """Tải file JSON chứa toàn bộ dữ liệu người dùng."""
    return send_file(DATA_FILE, mimetype="application/json",
                     as_attachment=True, download_name="users.json")

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
# ADMIN DUYỆT ĐƠN
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

# ==============================
# ADMIN TỪ CHỐI ĐƠN
# ==============================

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
    username = (f"@{user.username}" if user.username else user.first_name)

    text = (
        "👤 <b>THÔNG TIN TÀI KHOẢN</b> 👤\n\n"
        "<blockquote>"
        f"👤 <b>Tên:</b> {username}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"💎 <b>Số dư:</b> <b>{user_data['balance']:,} VND</b>\n"
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
        "🔑 <b>MUA KEY</b>\n\n"
        "🗝️ <b>Các loại Key hiện có:</b>\n"
        "<blockquote>"
        "🥉 Key Ngày — 50.000 VND\n"
        "🥈 Key Tuần — 200.000 VND\n"
        "🥇 Key Tháng — 500.000 VND\n"
        "💎 Key Vĩnh Viễn — 1.500.000 VND\n"
        "</blockquote>\n"
        "📩 <i>Liên hệ ADMIN để mua Key và kích hoạt ngay!</i>"
    )
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        f"📞 Liên Hệ ADMIN {ADMIN_USERNAME}",
        url=f"https://t.me/{ADMIN_USERNAME.lstrip('@')}"))
    bot.send_message(call.message.chat.id, text, parse_mode="HTML",
                     reply_markup=keyboard)

# ==============================
# NÚT CHƠI GAME
# ==============================

@bot.callback_query_handler(func=lambda call: call.data == "play_game")
def play_game_callback(call):
    bot.answer_callback_query(call.id,
        "🎮 Hãy nhập Key để bắt đầu chơi!", show_alert=True)

# ==============================
# CHẠY SONG SONG FLASK + BOT
# ==============================

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Chạy Flask server trên một luồng riêng
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("🌐 Flask server đang chạy tại http://localhost:5000")

    # Chạy bot Telegram
    print("🤖 Bot Telegram đang chạy...")
    bot.infinity_polling(skip_pending=True)