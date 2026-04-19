import os
import time
import requests
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import threading

# --- الإعدادات من Railway ---
TOKEN = 8246397533:AAHNbVpRh2NcCViZXBjlPyJMkTHk6iijFJI
ADMIN_ID = 6712633269
API_KEY = MnbbxvIVH7c3sCjoFkvcsPjucFq6L19n_10sKWodpNV6Y9YWk2DbO8vC1oxE4NOL # مفتاح بليسيو السري
CHANNEL_LINK = https://t.me/+rFgu03v83t1mNTdk

app = Flask(__name__)
bot = Bot(token=TOKEN)

# --- وظيفة توليد رابط دفع Plisio ---
def create_plisio_invoice(amount, network, user_id):
    url = "https://plisio.net"
    params = {
        'api_key': API_KEY,
        'currency': 'USDT',
        'network': network, # BEP20 أو TRC20
        'order_number': f"{user_id}_{int(time.time())}",
        'order_name': 'Subscription',
        'amount': str(amount),
        'callback_url': os.getenv("WEBHOOK_URL"), # رابط ريلوي + /webhook
        'expire_time': 900 # 15 دقيقة
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data['status'] == 'success':
            return data['data']['invoice_url']
    except Exception as e:
        print(f"Error: {e}")
    return None

# --- معالجات البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("دفع شام كاش (يدوي)", callback_data="pay_sham")],
        [InlineKeyboardButton("USDT (BEP20) - آلي", callback_data="pay_BEP20")],
        [InlineKeyboardButton("USDT (TRC20) - آلي", callback_data="pay_TRC20")]
    ]
    await update.message.reply_text("أهلاً بك! اختر وسيلة الدفع:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "pay_sham":
        await query.edit_message_text("حول لشام كاش [رقمك هنا] وأرسل صورة الإيصال.")
        context.user_data['waiting_for_receipt'] = True
        
    elif "pay_" in query.data:
        net = query.data.split("_")[1]
        keyboard = [[InlineKeyboardButton("تأكيد وتوليد الرابط", callback_data=f"conf_{net}")]]
        await query.edit_message_text(f"سيتم توليد رابط دفع {net} مدته 15 دقيقة.\nللتأكيد اضغط:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif "conf_" in query.data:
        net = query.data.split("_")[1]
        invoice_url = create_plisio_invoice("10", net, query.from_user.id)
        if invoice_url:
            await query.edit_message_text(f"رابط الدفع (15 دقيقة):\n{invoice_url}")
        else:
            await query.edit_message_text("خطأ في الاتصال ببليسيو.")

# --- استقبال تأكيد الدفع (Webhook) ---
@app.route('/webhook', methods=['POST', 'GET'])
def plisio_webhook():
    # بليسيو يرسل بيانات الدفع هنا
    data = request.form if request.form else request.json
    if data.get('status') == 'completed':
        user_id = int(data.get('order_number').split('_')[0])
        requests.get(f"https://telegram.org{TOKEN}/sendMessage?chat_id={user_id}&text=تم الدفع بنجاح! تفضل رابط القناة:\n{CHANNEL_LINK}")
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()
