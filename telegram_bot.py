# telegram_bot.py - FULLY FIXED
from dotenv import load_dotenv
import os
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters, CallbackQueryHandler
)
from database import (load_profiles, get_person, add_person, delete_person,
                      update_person, get_memory_summary, save_chat, clear_memory)
from memory_manager import detect_phase
from prompt_engine import generate_message
from datetime import datetime

load_dotenv()
TOKEN = os.environ.get("TELEGRAM_TOKEN")

# ── States ─────────────────────────────────────────────────
(SELECT_PERSON, GET_MESSAGE, GET_CONTEXT, SAVE_REPLY,
 NEW_NAME, NEW_RELATION, NEW_AGE, NEW_GENDER,
 NEW_LANGUAGE, NEW_TONE, NEW_HABITS, NEW_DAYS,
 DELETE_CONFIRM, UPDATE_SELECT, UPDATE_FIELD, UPDATE_VALUE,
 WHAT_NEXT) = range(17)

# ── Special day checker ────────────────────────────────────
def check_special_days(user_id):
    profiles = load_profiles(user_id)
    today = datetime.now().strftime("%d %B").lstrip("0")
    day_part, month_part = today.split()[0], today.split()[1]
    alerts = []
    for name, data in profiles.items():
        special = data.get("special_days", "")
        if special and day_part in special and month_part.lower() in special.lower():
            alerts.append((name, special))
    return alerts

# ── Send options as separate messages ──────────────────────
async def send_options(update, result, name):
    lines = result.strip().split("\n")
    current_block = []
    blocks = []

    for line in lines:
        if line.startswith("Option") and current_block:
            blocks.append("\n".join(current_block))
            current_block = [line]
        elif line.startswith("💡 Tips:") and current_block:
            blocks.append("\n".join(current_block))
            current_block = [line]
        else:
            current_block.append(line)
    if current_block:
        blocks.append("\n".join(current_block))

    emojis = ["1️⃣", "2️⃣", "3️⃣"]
    count = 0
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block.startswith("Option"):
            lines_in_block = block.split("\n")
            message_only = "\n".join(lines_in_block[1:]).strip()
            if message_only:
                await update.message.reply_text(f"{emojis[count]} {message_only}")
                count += 1
        elif block.startswith("💡"):
            await update.message.reply_text(block)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate")],
        [InlineKeyboardButton("💾 Save & record reply", callback_data="save")]
    ])
    await update.message.reply_text("Copy the message you like 👆 then:", reply_markup=keyboard)

# ── /help ──────────────────────────────────────────────────
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Commands:*\n\n"
        "/start → Begin chat, select person\n"
        "/new → Add a new person\n"
        "/update → Edit a person's details\n"
        "/delete → Remove a person\n"
        "/memory → View past chat memory\n"
        "/cancel → End current session\n"
        "/help → Show this menu\n\n"
        "💡 *How it works:*\n"
        "1. Select who you want to message\n"
        "2. Tell the bot what you want to say\n"
        "3. Get 3 polished message options\n"
        "4. Copy the one you like to the real chat\n"
        "5. Paste their reply back to save memory",
        parse_mode="Markdown"
    )

# ── /start ─────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data["user_id"] = user_id
    profiles = load_profiles(user_id)
    people = list(profiles.keys())

    alerts = check_special_days(user_id)
    for name, event in alerts:
        await update.message.reply_text(
            f"🎉 Today is special for *{name}* → {event}",
            parse_mode="Markdown"
        )

    if not people:
        await update.message.reply_text(
            "👋 Welcome to *Chat Assistant!*\n\n"
            "No profiles yet. Use /new to add your first person!",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    keyboard = [[p] for p in people]
    await update.message.reply_text(
        "👋 *Welcome!*\n\nWho do you want to message?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
        parse_mode="Markdown"
    )
    return SELECT_PERSON

# ── Person selected ────────────────────────────────────────
async def person_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data["user_id"]
    name = update.message.text
    person = get_person(user_id, name)

    if not person:
        await update.message.reply_text("❌ Profile not found. Try /start again.")
        return ConversationHandler.END

    context.user_data["selected_person"] = name
    await update.message.reply_text(
        f"✅ *{name}* selected\n"
        f"Relation: {person['relation']} | Language: {person['language']} | Tone: {person['default_tone']}\n\n"
        f"What do you want to say to {name}?\n"
        f"_(any language, any tone)_",
        parse_mode="Markdown"
    )
    return GET_MESSAGE

# ── Get message ────────────────────────────────────────────
async def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["user_input"] = update.message.text
    keyboard = ReplyKeyboardMarkup([["skip"]], one_time_keyboard=True)
    await update.message.reply_text(
        "📎 Any extra context?\n"
        "_(e.g. 'we had a fight', 'its urgent')_\n\nOr tap *skip*",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    return GET_CONTEXT

# ── Generate ───────────────────────────────────────────────
async def get_context_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    extra = "" if update.message.text.lower() == "skip" else update.message.text
    user_id = context.user_data["user_id"]
    name = context.user_data["selected_person"]
    user_input = context.user_data["user_input"]

    context.user_data["extra"] = extra
    context.user_data["last_input"] = user_input

    await update.message.reply_text("⚙️ Generating message options...")

    result = generate_message(
        user_id=user_id,
        name=name,
        user_input=user_input,
        extra_context=extra
    )
    context.user_data["last_result"] = result
    await send_options(update, result, name)
    return SAVE_REPLY

# ── Regenerate button ──────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "regenerate":
        user_id = context.user_data.get("user_id")
        name = context.user_data.get("selected_person")
        user_input = context.user_data.get("last_input")
        extra = context.user_data.get("extra", "")

        await query.message.reply_text("🔄 Regenerating...")
        result = generate_message(
            user_id=user_id,
            name=name,
            user_input=user_input + " (give different options than before)",
            extra_context=extra
        )
        context.user_data["last_result"] = result
        await send_options(query, result, name)

    elif query.data == "save":
        await query.message.reply_text(
            "📥 Paste their reply here.\n_(Or type 'skip')_",
            parse_mode="Markdown"
        )

# ── Save reply ─────────────────────────────────────────────
async def save_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    their_reply = update.message.text
    user_id = context.user_data["user_id"]
    name = context.user_data["selected_person"]
    user_input = context.user_data["last_input"]
    last_result = context.user_data["last_result"]

    save_chat(
        user_id=user_id,
        name=name,
        user_input=user_input,
        generated_options=last_result,
        chosen_option=context.user_data.get("chosen_option", "not recorded"),
        they_said="" if their_reply.lower() == "skip" else their_reply,
        phase=detect_phase(user_input)
    )

    keyboard = ReplyKeyboardMarkup([
        ["💬 Send another message"],
        ["👤 Change person"],
        ["🏠 End session"]
    ], one_time_keyboard=True)

    await update.message.reply_text(
        "💾 Saved!\n\nWhat do you want to do next?",
        reply_markup=keyboard
    )
    return WHAT_NEXT

# ── What next ──────────────────────────────────────────────
async def what_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    user_id = context.user_data["user_id"]

    if choice == "💬 Send another message":
        name = context.user_data["selected_person"]
        await update.message.reply_text(
            f"What do you want to say to {name} now?",
        )
        return GET_MESSAGE

    elif choice == "👤 Change person":
        profiles = load_profiles(user_id)
        people = list(profiles.keys())
        keyboard = [[p] for p in people]
        await update.message.reply_text(
            "Who do you want to chat with?",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return SELECT_PERSON

    else:
        await update.message.reply_text("👋 Session ended. Send /start anytime!")
        return ConversationHandler.END

# ── /new person flow ───────────────────────────────────────
async def new_person(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data["user_id"] = user_id
    await update.message.reply_text("➕ *Adding new person*\n\nWhat is their name?", parse_mode="Markdown")
    return NEW_NAME

async def new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_name"] = update.message.text
    keyboard = ReplyKeyboardMarkup(
        [["friend", "close friend"], ["boss", "parent"],
         ["sibling", "crush"], ["client", "colleague"]],
        one_time_keyboard=True
    )
    await update.message.reply_text("What is your relation?", reply_markup=keyboard)
    return NEW_RELATION

async def new_relation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_relation"] = update.message.text
    await update.message.reply_text("How old are they? (just the number)")
    return NEW_AGE

async def new_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_age"] = update.message.text
    keyboard = ReplyKeyboardMarkup([["male", "female", "other"]], one_time_keyboard=True)
    await update.message.reply_text("Gender?", reply_markup=keyboard)
    return NEW_GENDER

async def new_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_gender"] = update.message.text
    keyboard = ReplyKeyboardMarkup([["Hindi", "English", "Hinglish"]], one_time_keyboard=True)
    await update.message.reply_text("Preferred language?", reply_markup=keyboard)
    return NEW_LANGUAGE

async def new_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_language"] = update.message.text
    keyboard = ReplyKeyboardMarkup(
        [["casual", "formal"], ["emotional", "humorous"]],
        one_time_keyboard=True
    )
    await update.message.reply_text("Default tone?", reply_markup=keyboard)
    return NEW_TONE

async def new_tone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_tone"] = update.message.text
    await update.message.reply_text(
        "Any special habits?\n_(or type 'skip')_",
        parse_mode="Markdown"
    )
    return NEW_HABITS

async def new_habits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_habits"] = "" if update.message.text.lower() == "skip" else update.message.text
    await update.message.reply_text(
        "Any special days?\n_(e.g. 'Birthday: 15 August' or 'skip')_",
        parse_mode="Markdown"
    )
    return NEW_DAYS

async def new_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    special_days = "" if update.message.text.lower() == "skip" else update.message.text
    d = context.user_data
    user_id = d["user_id"]
    add_person(
        user_id, d["new_name"], d["new_relation"], int(d["new_age"]),
        d["new_gender"], d["new_language"], d["new_tone"],
        d["new_habits"], special_days
    )
    await update.message.reply_text(
        f"✅ Profile for *{d['new_name']}* saved!\n\nSend /start to begin chatting.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ── /delete flow ───────────────────────────────────────────
async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data["user_id"] = user_id
    profiles = load_profiles(user_id)
    people = list(profiles.keys())
    if not people:
        await update.message.reply_text("No profiles found.")
        return ConversationHandler.END

    keyboard = [[p] for p in people]
    await update.message.reply_text(
        "🗑️ *Which person to delete?*",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
        parse_mode="Markdown"
    )
    return DELETE_CONFIRM

async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    context.user_data["delete_name"] = name
    keyboard = ReplyKeyboardMarkup([["✅ Yes, delete", "❌ Cancel"]], one_time_keyboard=True)
    await update.message.reply_text(
        f"Sure you want to delete *{name}*?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    return DELETE_CONFIRM + 1

async def delete_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data["user_id"]
    if "Yes" in update.message.text:
        name = context.user_data["delete_name"]
        delete_person(user_id, name)
        await update.message.reply_text(f"🗑️ *{name}* deleted.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

# ── /update flow ───────────────────────────────────────────
async def update_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data["user_id"] = user_id
    profiles = load_profiles(user_id)
    people = list(profiles.keys())
    if not people:
        await update.message.reply_text("No profiles found.")
        return ConversationHandler.END

    keyboard = [[p] for p in people]
    await update.message.reply_text(
        "✏️ *Which person to update?*",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
        parse_mode="Markdown"
    )
    return UPDATE_SELECT

async def update_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data["user_id"]
    name = update.message.text
    person = get_person(user_id, name)

    if not person:
        await update.message.reply_text("❌ Profile not found.")
        return ConversationHandler.END

    context.user_data["update_name"] = name
    await update.message.reply_text(
        f"📋 *Current details for {name}:*\n"
        f"• Relation: {person['relation']}\n"
        f"• Age: {person['age']}\n"
        f"• Gender: {person['gender']}\n"
        f"• Language: {person['language']}\n"
        f"• Tone: {person['default_tone']}\n"
        f"• Habits: {person['special_habits']}\n"
        f"• Special Days: {person['special_days']}",
        parse_mode="Markdown"
    )
    keyboard = ReplyKeyboardMarkup([
        ["relation", "age"],
        ["gender", "language"],
        ["default_tone", "special_habits"],
        ["special_days"]
    ], one_time_keyboard=True)
    await update.message.reply_text("Which field to update?", reply_markup=keyboard)
    return UPDATE_FIELD

async def update_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["update_field"] = update.message.text
    field = update.message.text

    if field == "language":
        keyboard = ReplyKeyboardMarkup([["Hindi", "English", "Hinglish"]], one_time_keyboard=True)
        await update.message.reply_text("Choose new language:", reply_markup=keyboard)
    elif field == "default_tone":
        keyboard = ReplyKeyboardMarkup([["casual", "formal"], ["emotional", "humorous"]], one_time_keyboard=True)
        await update.message.reply_text("Choose new tone:", reply_markup=keyboard)
    elif field == "gender":
        keyboard = ReplyKeyboardMarkup([["male", "female", "other"]], one_time_keyboard=True)
        await update.message.reply_text("Choose gender:", reply_markup=keyboard)
    elif field == "relation":
        keyboard = ReplyKeyboardMarkup(
            [["friend", "close friend"], ["boss", "parent"], ["sibling", "crush"]],
            one_time_keyboard=True
        )
        await update.message.reply_text("Choose relation:", reply_markup=keyboard)
    else:
        await update.message.reply_text(f"Enter new value for *{field}*:", parse_mode="Markdown")
    return UPDATE_VALUE

async def update_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data["user_id"]
    name = context.user_data["update_name"]
    field = context.user_data["update_field"]
    value = update.message.text
    update_person(user_id, name, field, value)
    await update.message.reply_text(
        f"✅ *{name}'s* {field} updated!\n\nSend /start to continue.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ── /memory ────────────────────────────────────────────────
async def memory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profiles = load_profiles(user_id)
    if not profiles:
        await update.message.reply_text("No profiles found.")
        return
    for name in profiles:
        summary = get_memory_summary(user_id, name, last_n=3)
        await update.message.reply_text(f"🧠 *{name}:*\n{summary}", parse_mode="Markdown")

# ── /cancel ────────────────────────────────────────────────
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Session ended. Send /start to begin again.")
    return ConversationHandler.END

# ── Main ───────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()

    chat_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_PERSON: [MessageHandler(filters.TEXT & ~filters.COMMAND, person_selected)],
            GET_MESSAGE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_message)],
            GET_CONTEXT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_context_and_generate)],
            SAVE_REPLY:    [MessageHandler(filters.TEXT & ~filters.COMMAND, save_reply)],
            WHAT_NEXT:     [MessageHandler(filters.TEXT & ~filters.COMMAND, what_next)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    new_conv = ConversationHandler(
        entry_points=[CommandHandler("new", new_person)],
        states={
            NEW_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, new_name)],
            NEW_RELATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_relation)],
            NEW_AGE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, new_age)],
            NEW_GENDER:   [MessageHandler(filters.TEXT & ~filters.COMMAND, new_gender)],
            NEW_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_language)],
            NEW_TONE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, new_tone)],
            NEW_HABITS:   [MessageHandler(filters.TEXT & ~filters.COMMAND, new_habits)],
            NEW_DAYS:     [MessageHandler(filters.TEXT & ~filters.COMMAND, new_days)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    delete_conv = ConversationHandler(
        entry_points=[CommandHandler("delete", delete_cmd)],
        states={
            DELETE_CONFIRM:     [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_confirm)],
            DELETE_CONFIRM + 1: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_final)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    update_conv = ConversationHandler(
        entry_points=[CommandHandler("update", update_cmd)],
        states={
            UPDATE_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_select)],
            UPDATE_FIELD:  [MessageHandler(filters.TEXT & ~filters.COMMAND, update_field)],
            UPDATE_VALUE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, update_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(chat_conv)
    app.add_handler(new_conv)
    app.add_handler(delete_conv)
    app.add_handler(update_conv)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("memory", memory))
    app.add_handler(CommandHandler("help", help_cmd))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()