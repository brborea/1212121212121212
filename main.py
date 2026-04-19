import os
import time
import requests
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import threading

# جلب البيانات من إعدادات ريلوي (Variables)
TOKEN = "8246397533:AAHNbVpRh2NcCViZXBjlPyJMkTHk6iijFJI"
ADMIN_ID = "6712633269"
API_KEY = "MnbbxvIVH7c3sCjoFkvcsPjucFq6L19n_10sKWodpNV6Y9YWk2DbO8vC1oxE4NOL"
CHANNEL_LINK = "https://t.me/+rFgu03v83t1mNTdk"

app = Flask(__name__)
bot = Bot(token=TOKEN)

def create_plisio_invoice(amount, network, user_id):
    ps_network = "USDT_BSC" if network == "BEP20" else "USDT_TRX"
    url = "https://api.plisio.net/api/v1/invoices/new"
    params = {
        'api_key': API_KEY,
        'currency': 'USDT',
        'network': ps_network,
        'order_number': f"{user_id}_{int(time.time())}",
        'order_name': 'VIP_Sub',
        'amount': str(amount),
        'callback_url': f"https://{os.getenv('RAILWAY_STATIC_URL')}/webhook",
        'expire_time': 900
    }
    try:
        response = requests.get(url, params=params)
        return response.json()['data']['invoice_url']
    except:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("شام كاش (يدوي)", callback_data="pay_sham")],
                [InlineKeyboardButton("USDT (BEP20) - آلي", callback_data="pay_BEP20")],
                [InlineKeyboardButton("USDT (TRC20) - آلي", callback_data="pay_TRC20")]]
    await update.message.reply_text("أهلاً بك! اختر وسيلة الدفع:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "pay_sham":
        await query.edit_message_text("حول لشام كاش (رقمك هنا) وأرسل صورة الإيصال:")
        context.user_data['waiting_receipt'] = True
    elif "pay_" in query.data:
        net = query.data.split("_")[1]
        keyboard = [[InlineKeyboardButton("تأكيد وتوليد الرابط", callback_data=f"conf_{net}")]]
        await query.edit_message_text(f"سيولد البوت رابط دفع {net} لـ 15 دقيقة. للتأكيد:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif "conf_" in query.data:
        net = query.data.split("_")[1]
        url = create_plisio_invoice(10, net, query.from_user.id) # السعر 10
        await query.edit_message_text(f"رابط الدفع الخاص بك:\n{url}" if url else "خطأ في الاتصال.")

@app.route('/webhook', methods=['POST', 'GET'])
def plisio_webhook():
    data = request.form if request.form else request.json
    if data.get('status') == 'completed':
        u_id = int(data.get('order_number').split('_')[0])
        requests.get(f"https://telegram.org{TOKEN}/sendMessage?chat_id={u_id}&text=تم الدفع! رابط القناة: {CHANNEL_LINK}")
    return "OK", 200

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))).start()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()
