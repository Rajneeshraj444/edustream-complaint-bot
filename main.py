#!/usr/bin/env python3
"""
Telegram Bot for Complaint Submission
A multi-step workflow bot for submitting and tracking complaints
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from telegram.error import BadRequest

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "8099043757:AAENjgM164FuPLbE10GJH0AFWTOir2RLgoY")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "5915871770"))

# Conversation states
(
    BATCH_SELECTION,
    SUBJECT_SELECTION,
    LECTURE_NAME_INPUT,
    SCREENSHOT_UPLOAD,
    ADMIN_STATUS_UPDATE
) = range(5)

# Available batches and subjects
BATCHES = ["Master quest 2.0 2025", "master quest 2026", "Ace ipm crash course"]
SUBJECTS = ["Quant", "DILR", "VARC", "Current Affairs" ]

# Status options for admin
STATUS_OPTIONS = ["Send", "Seen", "Approved", "Resolved"]

# Global storage for user data and complaints
user_data_store = {}
complaint_store = {}
complaint_counter = 0

# Utility functions
def store_user_data(user_id, key, value):
    """Store user data in the global dictionary"""
    if user_id not in user_data_store:
        user_data_store[user_id] = {}
    user_data_store[user_id][key] = value
    logger.info(f"Stored {key} for user {user_id}: {value}")

def get_user_data(user_id, key=None):
    """Get user data from the global dictionary"""
    if user_id not in user_data_store:
        return None if key else {}

    if key:
        return user_data_store[user_id].get(key)
    return user_data_store[user_id]

def clear_user_data(user_id):
    """Clear user data for a specific user"""
    if user_id in user_data_store:
        del user_data_store[user_id]
        logger.info(f"Cleared data for user {user_id}")

def create_complaint(user_id, username, batch, subject, lecture_name, photo_file_id):
    """Create a new complaint and store it"""
    global complaint_counter
    complaint_counter += 1

    complaint_id = f"complaint_{complaint_counter}"
    complaint_data = {
        'id': complaint_id,
        'user_id': user_id,
        'username': username,
        'batch': batch,
        'subject': subject,
        'lecture_name': lecture_name,
        'photo_file_id': photo_file_id,
        'status': 'submitted',
        'created_at': None
    }

    complaint_store[complaint_id] = complaint_data
    logger.info(f"Created complaint {complaint_id} for user {user_id}")
    return complaint_id

def update_complaint_status(complaint_id, new_status):
    """Update complaint status"""
    if complaint_id in complaint_store:
        complaint_store[complaint_id]['status'] = new_status
        logger.info(f"Updated complaint {complaint_id} status to {new_status}")
        return True
    return False

def get_complaint(complaint_id):
    """Get complaint data"""
    return complaint_store.get(complaint_id)

def format_complaint_message(complaint_data):
    """Format complaint message for admin"""
    username = complaint_data['username'] or "No username"
    message = f"""
🆘 **New Complaint Submitted**

👤 **User Details:**
• User ID: `{complaint_data['user_id']}`
• Username: @{username}

📚 **Complaint Details:**
• Batch: {complaint_data['batch']}
• Subject: {complaint_data['subject']}
• Lecture Name: {complaint_data['lecture_name']}

📊 **Status:** {complaint_data['status'].title()}
🆔 **Complaint ID:** `{complaint_data['id']}`

Please review and update the status accordingly.
"""
    return message

def is_admin(user_id):
    """Check if user is admin"""
    return user_id == ADMIN_CHAT_ID

# Keyboard functions
def get_batch_keyboard():
    """Create inline keyboard for batch selection"""
    keyboard = []
    for batch in BATCHES:
        keyboard.append([InlineKeyboardButton(batch, callback_data=f"batch_{batch.replace(' ', '_')}")])
    return InlineKeyboardMarkup(keyboard)

def get_subject_keyboard():
    """Create inline keyboard for subject selection"""
    keyboard = []
    for subject in SUBJECTS:
        keyboard.append([InlineKeyboardButton(subject, callback_data=f"subject_{subject.replace(' ', '_')}")])
    return InlineKeyboardMarkup(keyboard)

def get_status_keyboard(complaint_id):
    """Create inline keyboard for admin status updates"""
    keyboard = []
    row = []
    for i, status in enumerate(STATUS_OPTIONS):
        row.append(InlineKeyboardButton(status, callback_data=f"status_{complaint_id}_{status.lower()}"))
        # Create new row after every 2 buttons
        if (i + 1) % 2 == 0:
            keyboard.append(row)
            row = []
    # Add remaining buttons if any
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def get_back_to_batch_keyboard():
    """Create back button to restart batch selection"""
    keyboard = [[InlineKeyboardButton("🔄 Start Over", callback_data="restart")]]
    return InlineKeyboardMarkup(keyboard)

# Handler functions
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command"""
    user = update.effective_user

    # Clear any existing user data
    clear_user_data(user.id)

    welcome_message = f"""
👋 Welcome {user.first_name}!

I'm here to help you submit complaints about lectures.

Please follow these steps:
1️⃣ Select your batch
2️⃣ Choose the subject
3️⃣ Enter the lecture name
4️⃣ Upload a screenshot

Let's start by selecting your batch:
"""

    await update.message.reply_text(
        welcome_message,
        reply_markup=get_batch_keyboard()
    )

    return BATCH_SELECTION

async def batch_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle batch selection"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user

    if query.data == "restart":
        await query.message.reply_text(
            "🔄 Starting over. Please select your batch:",
            reply_markup=get_batch_keyboard()
        )
        return BATCH_SELECTION

    if query.data.startswith("batch_"):
        batch = query.data.replace("batch_", "").replace("_", " ")
        store_user_data(user.id, 'batch', batch)

        await query.message.reply_text(
            f"✅ Batch selected: **{batch}**\n\nNow please select the subject:",
            reply_markup=get_subject_keyboard(),
            parse_mode='Markdown'
        )

        return SUBJECT_SELECTION

    return BATCH_SELECTION

async def subject_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle subject selection"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user

    if query.data.startswith("subject_"):
        subject = query.data.replace("subject_", "").replace("_", " ")
        store_user_data(user.id, 'subject', subject)

        user_data = get_user_data(user.id)

        await query.message.reply_text(
            f"✅ Subject selected: **{subject}**\n"
            f"📚 Batch: {user_data.get('batch')}\n\n"
            f"Now please type the **lecture name** in the chat:",
            parse_mode='Markdown'
        )

        return LECTURE_NAME_INPUT

    return SUBJECT_SELECTION

async def lecture_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle lecture name input"""
    user = update.effective_user
    lecture_name = update.message.text.strip()

    if not lecture_name:
        await update.message.reply_text(
            "❌ Please enter a valid lecture name:"
        )
        return LECTURE_NAME_INPUT

    store_user_data(user.id, 'lecture_name', lecture_name)
    user_data = get_user_data(user.id)

    summary_message = f"""
✅ **Lecture name saved:** {lecture_name}

📋 **Summary so far:**
• Batch: {user_data.get('batch')}
• Subject: {user_data.get('subject')}
• Lecture: {lecture_name}

📸 Now please send a **screenshot** (image file) related to your complaint:
"""

    await update.message.reply_text(
        summary_message,
        parse_mode='Markdown'
    )

    return SCREENSHOT_UPLOAD

async def screenshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle screenshot upload"""
    user = update.effective_user

    if not update.message.photo:
        await update.message.reply_text(
            "❌ Please send an image file (screenshot). Other file types are not accepted."
        )
        return SCREENSHOT_UPLOAD

    # Get the largest photo size
    photo = update.message.photo[-1]
    photo_file_id = photo.file_id

    # Get user data
    user_data = get_user_data(user.id)

    # Create complaint
    complaint_id = create_complaint(
        user_id=user.id,
        username=user.username,
        batch=user_data.get('batch'),
        subject=user_data.get('subject'),
        lecture_name=user_data.get('lecture_name'),
        photo_file_id=photo_file_id
    )

    # Store complaint ID for user
    store_user_data(user.id, 'complaint_id', complaint_id)

    # Send confirmation to user
    await update.message.reply_text(
        f"✅ **Complaint submitted successfully!**\n\n"
        f"🆔 **Complaint ID:** `{complaint_id}`\n"
        f"📊 **Status:** Submitted\n\n"
        f"Your complaint has been forwarded to the admin team. "
        f"You will be notified when the status changes.\n\n"
        f"Thank you for your feedback! 🙏",
        parse_mode='Markdown'
    )

    # Forward complaint to admin
    await send_complaint_to_admin(context, complaint_id)

    # Clear user data
    clear_user_data(user.id)

    return ConversationHandler.END

async def send_complaint_to_admin(context: ContextTypes.DEFAULT_TYPE, complaint_id: str):
    """Send complaint to admin chat"""
    complaint_data = get_complaint(complaint_id)

    if not complaint_data:
        logger.error(f"Complaint {complaint_id} not found")
        return

    try:
        # Send photo to admin
        await context.bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=complaint_data['photo_file_id']
        )

        # Send complaint details with status buttons
        message = format_complaint_message(complaint_data)

        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=message,
            reply_markup=get_status_keyboard(complaint_id),
            parse_mode='Markdown'
        )

        logger.info(f"Complaint {complaint_id} sent to admin")

    except Exception as e:
        logger.error(f"Error sending complaint to admin: {e}")

async def admin_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin status updates"""
    query = update.callback_query
    user = update.effective_user

    # Check if user is admin
    if not is_admin(user.id):
        await query.answer("❌ You are not authorized to perform this action.", show_alert=True)
        return

    await query.answer()

    if query.data.startswith("status_"):
        parts = query.data.split("_")
        if len(parts) >= 3:
            complaint_id = "_".join(parts[1:-1])  # Handle complaint IDs with underscores
            new_status = parts[-1]

            complaint_data = get_complaint(complaint_id)

            if not complaint_data:
                await query.message.reply_text("❌ Complaint not found.")
                return

            # Update complaint status
            update_complaint_status(complaint_id, new_status)

            # Notify user about status change
            try:
                status_message = f"""
📊 **Complaint Status Updated**

🆔 **Complaint ID:** `{complaint_id}`
📊 **New Status:** {new_status.title()}

Your complaint about:
• Subject: {complaint_data['subject']}
• Lecture: {complaint_data['lecture_name']}

Thank you for your patience! 🙏
"""

                await context.bot.send_message(
                    chat_id=complaint_data['user_id'],
                    text=status_message,
                    parse_mode='Markdown'
                )

                # Update admin message
                try:
                    updated_complaint = get_complaint(complaint_id)
                    updated_message = format_complaint_message(updated_complaint)

                    await query.edit_message_text(
                        text=updated_message,
                        reply_markup=get_status_keyboard(complaint_id),
                        parse_mode='Markdown'
                    )
                except BadRequest as e:
                    if "Message is not modified" not in str(e):
                        # If it's not the "not modified" error, send a new message
                        await query.message.reply_text(
                            f"✅ Status updated to: {new_status.title()}\n"
                            f"User has been notified."
                        )

                logger.info(f"Admin updated complaint {complaint_id} status to {new_status}")

            except Exception as e:
                logger.error(f"Error notifying user about status change: {e}")
                await query.message.reply_text(
                    f"✅ Status updated to: {new_status.title()}\n"
                    f"⚠️ Could not notify user (user may have blocked the bot)."
                )

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversation cancellation"""
    user = update.effective_user
    clear_user_data(user.id)

    await update.message.reply_text(
        "❌ **Complaint submission cancelled.**\n\n"
        "You can start again anytime by using /start command.\n\n"
        "Thank you! 🙏",
        parse_mode='Markdown'
    )

    return ConversationHandler.END

async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown commands"""
    await update.message.reply_text(
        "❓ I don't understand that command.\n\n"
        "Use /start to begin submitting a complaint."
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    """Main function to start the bot"""

    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Create conversation handler for complaint submission
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            BATCH_SELECTION: [
                CallbackQueryHandler(batch_selection_handler, pattern="^(batch_|restart)")
            ],
            SUBJECT_SELECTION: [
                CallbackQueryHandler(subject_selection_handler, pattern="^subject_")
            ],
            LECTURE_NAME_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lecture_name_handler)
            ],
            SCREENSHOT_UPLOAD: [
                MessageHandler(filters.PHOTO, screenshot_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, screenshot_handler)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_handler),
            CommandHandler("start", start_command)  # Allow restart at any time
        ],
        allow_reentry=True
    )

    # Add handlers
    application.add_handler(conversation_handler)
    application.add_handler(CallbackQueryHandler(admin_status_handler, pattern="^status_"))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_handler))

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    logger.info("Starting Complaint Submission Bot...")
    print("🤖 Complaint Submission Bot is starting...")
    print(f"📱 Bot Token: {BOT_TOKEN[:10]}...")
    print("🚀 Bot is running! Press Ctrl+C to stop.")

    application.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n👋 Bot stopped gracefully!")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        print(f"\n❌ Bot crashed: {e}")
