import threading
import telebot
from telebot import types
import django
import os
import decimal

TOKEN = '8591871334:AAEmZz8nqaXzlABSq35oRE3wxK2i-5ccYiQ'

bot = telebot.TeleBot(TOKEN)

# Dictionary to store temporary state during login
# Format: {chat_id: {'step': 'phone_number', 'phone': '...'} }
login_sessions = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Assalomu alaykum! X-Store botiga xush kelibsiz.\n\nIltimos, tizimga kirish uchun telefon raqamingizni kiriting (masalan: +998901234567 yoki 998901234567):")
    login_sessions[message.chat.id] = {'step': 'phone_number'}

@bot.message_handler(func=lambda message: message.chat.id in login_sessions)
def handle_login(message):
    chat_id = message.chat.id
    session = login_sessions[chat_id]
    
    if session['step'] == 'phone_number':
        phone = message.text.strip()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Check if user exists
        if not User.objects.filter(phone_number=phone).exists():
            bot.reply_to(message, "Bunday telefon raqamli foydalanuvchi topilmadi. Qaytadan kiriting:")
            return
            
        session['phone'] = phone
        session['step'] = 'password'
        bot.reply_to(message, "Endi parolingizni kiriting:")
        
    elif session['step'] == 'password':
        password = message.text.strip()
        phone = session['phone']
        
        from django.contrib.auth import authenticate
        user = authenticate(phone_number=phone, password=password)
        
        if user is not None:
            user.telegram_chat_id = str(chat_id)
            user.save()
            del login_sessions[chat_id]
            bot.reply_to(message, f"Muvaffaqiyatli kirdingiz, {user.name}! Endi sizga yangi savdolar haqida xabarlar keladi.")
        else:
            bot.reply_to(message, "Parol noto'g'ri. Qaytadan parolingizni kiriting:")

def run_bot_polling():
    # Only run if Django is setup
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Telegram Bot error: {e}")

def start_telegram_bot_thread():
    thread = threading.Thread(target=run_bot_polling, daemon=True)
    thread.start()

def format_currency(value):
    try:
        return f"{int(float(value)):,} UZS".replace(',', ' ')
    except:
        return f"{value} UZS"

def send_sale_notification(sale):
    """
    Called from sale views after a sale is completed.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Get all users who have registered a chat ID
    users_with_tg = User.objects.exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id__exact='')
    
    if not users_with_tg.exists():
        return
        
    items = sale.items.all()
    
    total_cost_price = sum(item.quantity * item.variant.cost_price for item in items)
    total_sticker_price = sum(item.quantity * item.variant.sticker_price for item in items)
    tax_applied = sum(item.applied_tax_amount * item.quantity for item in items)
    
    net_sales = sale.total_price - tax_applied
    profit = net_sales - total_cost_price
    
    pm_name = sale.payment_method.name if sale.payment_method else "Noma'lum"
    client_name = sale.client.first().name if sale.client.exists() else "Umumiy Mijoz"
    
    items_text = ""
    for item in items:
        items_text += f"- {item.variant.product.name} ({item.variant.size.name if item.variant.size else ''}): {item.quantity} dona x {format_currency(item.price)}\n"
        
    message_text = f"""
🛒 *YANGI SAVDO: #{sale.id}*

👤 *Sotuvchi:* {sale.seller.name if sale.seller else 'Noma\'lum'}
👥 *Mijoz:* {client_name}
💳 *To'lov usuli:* {pm_name}

💰 *Umumiy summa:* {format_currency(sale.total_price)}
💵 *To'langan:* {format_currency(sale.total_price - sale.debt)}
📉 *Qarz:* {format_currency(sale.debt)}

📊 *Moliyaviy ma'lumotlar:*
- Soliq (QQS/Tax): {format_currency(tax_applied)}
- Tan narxi (Cost): {format_currency(total_cost_price)}
- Sof foyda: {format_currency(profit)}

🛍 *Sotilgan tovarlar:*
{items_text}
"""
    
    for user in users_with_tg:
        try:
            bot.send_message(user.telegram_chat_id, message_text, parse_mode="Markdown")
        except Exception as e:
            print(f"Failed to send TG message to {user.name}: {e}")
