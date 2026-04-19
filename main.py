import os
import time
import hashlib
import json
import requests
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import threading

# --- الإعدادات (سيتم جلبها من Railway Variables) ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
MERCHANT_ID = os.getenv("MERCHANT_ID")
SECRET_KEY = os.getenv("SECRET_KEY")
CHANNEL_LINK = os.getenv("CHANNEL_LINK") # رابط القناة الخاصة

app = Flask(__name__)
bot = Bot(token=TOKEN)

# --- وظيفة توليد رابط الدفع من Cryptomus ---
def create_cryptomus_invoice(amount, network, user_id):
    url = "https://cryptomus.com"
    payload = {
        "amount": str(amount),
        "currency": "USDT",
        "network": network,
        "order_id": f"{user_id}_{int(time.time())}",
        "url_callback": os.getenv("WEBHOOK_URL"), # سيتم ضبطه بعد رفع المشروع
        "lifetime": 900 # 15 دقيقة
    }
    
    # التوقيع الرقمي (Signature)
    data_json = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    sign = hashlib.md5(data_json + SECRET_KEY.encode('utf-8')).hexdigest()
    
    headers = {
        "merchant": MERCHANT_ID,
        "sign": sign,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()['result']['url']
    except Exception as e:
        print(f"Error creating invoice: {e}")
        return None

# --- معالجات بوت تلغرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("دفع شام كاش (يدوي)", callback_data="pay_sham")],
        [InlineKeyboardButton("USDT (BEP20) - آلي", callback_data="pay_BEP20")],
        [InlineKeyboardButton("USDT (TRC20) - آلي", callback_data="pay_TRC20")]
    ]
    await update.message.reply_text("أهلاً بك! اختر وسيلة الدفع للاشتراك في القناة الخاصة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "pay_sham":
        await query.edit_message_text("حول المبلغ لحساب شام كاش [ضع رقمك هنا] ثم أرسل صورة الإيصال هنا.")
        context.user_data['waiting_for_receipt'] = True

    elif "pay_" in query.data:
        network = query.data.split("_")[1]
        keyboard = [[InlineKeyboardButton("تأكيد وتوليد رابط الدفع", callback_data=f"confirm_{network}")]]
        await query.edit_message_text(f"سيتم توليد رابط دفع {network} مدته 15 دقيقة.\nللتأكيد اضغط الزر أدناه:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif "confirm_" in query.data:
        network = query.data.split("_")[1]
        invoice_url = create_cryptomus_invoice("10", network, user_id) # السعر هنا 10
        if invoice_url:
            await query.edit_message_text(f"تفضل رابط الدفع الخاص بك (صالح لـ 15 دقيقة):\n{invoice_url}\n\nسيتم تفعيل اشتراكك آلياً فور التحويل.")
        else:
            await query.edit_message_text("عذراً، حدث خطأ في الاتصال ببوابة الدفع. حاول لاحقاً.")

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_receipt') and update.message.photo:
        await bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, 
                             caption=f"إيصال جديد من: @{update.message.from_user.username}\nID: {update.message.from_user.id}")
        await update.message.reply_text("تم استلام الإيصال، جاري التدقيق من قبل الإدارة.")

# --- مسار الـ Webhook لاستقبال تأكيد الدفع من Cryptomus ---
@app.route('/webhook', methods=['POST'])
def cryptomus_webhook():
    data = request.json
    if data.get('status') in ['paid', 'completed']:
        user_id = int(data.get('order_id').split('_')[0])
        # إرسال رابط القناة للمشترك
        requests.get(f"https://telegram.org{TOKEN}/sendMessage?chat_id={user_id}&text=تم تأكيد دفعك! رابط القناة: {CHANNEL_LINK}")
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    application.run_polling()
