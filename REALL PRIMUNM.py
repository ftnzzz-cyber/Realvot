
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Bot configuration
TOKEN = '9078253986:AAHhOaLw-Hf8JQdK_BnXkWEPbNH7K5TbYCg'
ADMIN_ID = 123456789
QR_FILE = 'payment.png'

# Replace these with invite links for groups you manage.
GROUPS = {
    'son and mom😜': ('Son and mom 😜', 68, 'GROUP_SM_LINK'),
    'c*p👀': ('C*P👀', 59, 'GROUP_CP_LINK'),
    'sister and brother😈': ('sister and brother 😈', 68, 'GROUP_SB_LINK'),
    'mallu🥵': ('mallu🥵', 80, 'GROUP_MA_LINK'),
    'tamil🫠': ('Tamil🫠', 80, 'GROUP_TA_LINK'),
    'leak viral🔥': ('leak viral🔥', 90, 'GROUP_LE_LINK'),
    'boy friend leaked call 🤫': ('call😇', 99, 'GROUP_call_LINK'),
    'bundle🗿': ('Bundle🗿', 199, 'BUNDLE_LINK'),
    'real rpe😳': ('rpe😳', 99, 'real rpe_LINK'),
    '': ('hidden cam😏', 79, 'cam_LINK'),
    'river side😱 ': ('river side💖 ', 99, 'river side_LINK'),
    'all demo one video each ': ('all demo 😋', 99, 'demo_LINK'),
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Demo storage only. Use a database for production.
paid_users = {}
pending_payments = {}


def main_menu():
    rows = []
    items = list(GROUPS.items())

    for i in range(0, len(items), 2):
        row = []
        for key, (name, price, link) in items[i:i + 2]:
            row.append(
                InlineKeyboardButton(
                    f'{name} - ₹{price}',
                    callback_data=f'item:{key}',
                )
            )
        rows.append(row)

    rows.append([
        InlineKeyboardButton('❌ Cancel', callback_data='cancel')
    ])
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        '🌽💦Welcome to Corn find your group !\n\nChoose a group🫦:',
        reply_markup=main_menu(),
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith('item:'):
        key = data.split(':', 1)[1]
        if key not in GROUPS:
            return

        name, price, link = GROUPS[key]
        context.user_data['selected_item'] = key

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton('✅ I Paid', callback_data='i_paid')],
            [InlineKeyboardButton('⬅️ Back', callback_data='back')],
            [InlineKeyboardButton('❌ Cancel', callback_data='cancel')],
        ])

        try:
            with open(QR_FILE, 'rb') as qr:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=qr,
                    caption=(
                        f'🛒 Selected: {name}\n'
                        f'💰 Price: ₹{price}\n\n'
                        'Scan the QR to pay. After payment, '
                        'tap I Paid and submit your UTR or screenshot.'
                    ),
                    reply_markup=keyboard,
                )
        except FileNotFoundError:
            await context.bot.send_message(
                chat_id=user_id,
                text='Payment QR is not configured. Contact admin.',
            )

    elif data == 'i_paid':
        if not context.user_data.get('selected_item'):
            await context.bot.send_message(
                chat_id=user_id,
                text='Choose a group first.',
                reply_markup=main_menu(),
            )
            return

        context.user_data['awaiting_proof'] = True
        await context.bot.send_message(
            chat_id=user_id,
            text='Send your UTR/reference number or payment screenshot.',
        )

    elif data == 'back':
        await context.bot.send_message(
            chat_id=user_id,
            text='Choose a group:',
            reply_markup=main_menu(),
        )

    elif data == 'cancel':
        context.user_data['awaiting_proof'] = False
        context.user_data.pop('selected_item', None)
        await context.bot.send_message(
            chat_id=user_id,
            text='Cancelled. Choose an option whenever you are ready.',
            reply_markup=main_menu(),
        )


async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return
    if not context.user_data.get('awaiting_proof'):
        return

    if not message.photo and not message.text:
        await message.reply_text('Please send a UTR or screenshot.')
        return

    key = context.user_data.get('selected_item')
    if key not in GROUPS:
        await message.reply_text('Please select a group again.')
        return

    name, price, link = GROUPS[key]
    pending_payments[user.id] = {
        'item': key,
        'name': name,
        'price': price,
    }
    context.user_data['awaiting_proof'] = False

    await message.reply_text(
        '📩 Proof submitted. The admin will verify your payment,don t worry your group on the way 🫟.'
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            '✅ Approve',
            callback_data=f'approve:{user.id}',
        ),
        InlineKeyboardButton(
            '❌ Reject',
            callback_data=f'reject:{user.id}',
        ),
    ]])

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            '💳 Payment review\n'
            f'User: {user.full_name}\n'
            f'User ID: {user.id}\n'
            f'Item: {name}\n'
            f'Amount: ₹{price}\n'
            'Review the proof message below.'
        ),
        reply_markup=keyboard,
    )

    await context.bot.forward_message(
        chat_id=ADMIN_ID,
        from_chat_id=message.chat_id,
        message_id=message.message_id,
    )


async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer('Not authorized.', show_alert=True)
        return

    await query.answer()
    action, user_text = query.data.split(':', 1)
    user_id = int(user_text)
    payment = pending_payments.get(user_id)

    if not payment:
        await query.edit_message_text('No pending payment found.')
        return

    if action == 'approve':
        key = payment['item']
        name, price, link = GROUPS[key]

        paid_users.setdefault(user_id, set()).add(key)
        pending_payments.pop(user_id, None)

        if link.startswith('https://t.me/'):
            await context.bot.send_message(
                chat_id=user_id,
                text=f'✅ Payment approved for {name}!\nGroup link: {link}',
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f'✅ Payment approved for {name}!\n'
                    'The group link has not been configured yet. '
                    'Contact admin.'
                ),
            )

        await query.edit_message_text(
            f'Approved: {name}, ₹{price}, user {user_id}.'
        )

    elif action == 'reject':
        pending_payments.pop(user_id, None)
        await context.bot.send_message(
            chat_id=user_id,
            text='❌ Payment not approved. Please contact admin.',
        )
        await query.edit_message_text(
            f'Rejected payment for user {user_id}.'
        )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(
        admin_decision, pattern=r'^(approve|reject):\d+$'
    ))
    app.add_handler(CallbackQueryHandler(
        buttons, pattern=r'^(item:|i_paid$|back$|cancel$)'
    ))
    app.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO, handle_proof
    ))

    logger.info('Corn Bot started.')
    app.run_polling()


if __name__ == '__main__':
    main()
