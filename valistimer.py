import asyncio
import json
import os
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TIMER_DURATION = 22 * 60  # 22 minutes
STATE_FILE = "timer_state.json"
USERS_FILE = "users.json"
current_task = None


# ------------------------------
#  GESTION ÉTAT TIMER
# ------------------------------

def save_state(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)

def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def clear_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)


# ------------------------------
#  GESTION UTILISATEURS
# ------------------------------

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def register_user(user_id: int):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_users(users)


# ------------------------------
#  BOUCLE TIMER + MESSAGE ÉPINGLÉ
# ------------------------------

async def timer_loop(app: Application, state):
    end = state["timer_end"]
    chat_id = state["message_chat_id"]
    msg_id = state["message_id"]
    starter_id = state["starter_id"]

    # Ré‑épingler si redémarrage
    try:
        await app.bot.pin_chat_message(chat_id, msg_id, disable_notification=True)
    except:
        pass

    while True:
        remaining = end - time.time()

        if remaining <= 0:
            # Message final
            await app.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text="🧳 La valise est dispo !"
            )

            # DM aux autres utilisateurs
            users = load_users()
            for uid in users:
                if uid != starter_id:
                    try:
                        await app.bot.send_message(
                            uid,
                            "🧳 La valise est maintenant disponible !"
                        )
                    except:
                        pass

            clear_state()
            return

        minutes = int(remaining // 60)
        seconds = int(remaining % 60)

        # Mise à jour du message épinglé
        try:
            await app.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=f"⏳ Temps restant : {minutes:02d}:{seconds:02d}"
            )
        except:
            pass

        await asyncio.sleep(30)


# ------------------------------
#  COMMANDES
# ------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user:
        register_user(update.effective_user.id)

    keyboard = [
        [InlineKeyboardButton("🧳 Ouvrir la valise", callback_data="start_timer")],
        [InlineKeyboardButton("🔄 Reset", callback_data="reset_timer")]
    ]
    await update.message.reply_text(
        "ValisTimer est prêt.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()

    if not state:
        await update.message.reply_text("Aucun timer en cours.")
        return

    remaining = state["timer_end"] - time.time()
    if remaining <= 0:
        await update.message.reply_text("🧳 La valise est dispo !")
        return

    minutes = int(remaining // 60)
    seconds = int(remaining % 60)

    await update.message.reply_text(
        f"⏳ Temps restant : {minutes:02d}:{seconds:02d}"
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_task
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id
    user_name = user.first_name

    register_user(user_id)

    state = load_state()

    # ------------------------------
    #  DÉMARRER LE TIMER
    # ------------------------------
    if query.data == "start_timer":
        if state:
            await query.message.reply_text("⏳ Un timer est déjà en cours.")
            return

        end_time = time.time() + TIMER_DURATION

        # Message du timer
        msg = await query.message.reply_text("⏳ Timer lancé...")

        # Épingler le message
        try:
            await msg.pin(disable_notification=True)
        except:
            pass

        state = {
            "timer_end": end_time,
            "starter_id": user_id,
            "starter_name": user_name,
            "message_chat_id": msg.chat_id,
            "message_id": msg.message_id
        }
        save_state(state)

        # Lancer la boucle
        current_task = asyncio.create_task(timer_loop(context.application, state))

        # Message groupe
        await query.message.reply_text(
            f"La valise a été ouverte par {user_name}, veuillez patienter."
        )

        # DM aux autres
        users = load_users()
        for uid in users:
            if uid != user_id:
                try:
                    await context.bot.send_message(
                        uid,
                        f"🧳 {user_name} vient d’ouvrir la valise. Elle sera dispo dans 22 minutes."
                    )
                except:
                    pass

    # ------------------------------
    #  RESET
    # ------------------------------
    elif query.data == "reset_timer":
        if not state:
            await query.message.reply_text("Aucun timer en cours.")
            return

        if user_id != state["starter_id"]:
            await query.message.reply_text(
                "❌ Seul l'utilisateur qui a lancé le timer peut le réinitialiser."
            )
            return

        if current_task:
            current_task.cancel()
            current_task = None

        clear_state()

        await query.message.reply_text("🔄 Timer réinitialisé.")


# ------------------------------
#  STARTUP (REPRISE TIMER)
# ------------------------------

async def on_startup(app: Application):
    global current_task
    state = load_state()
    if state:
        current_task = asyncio.create_task(timer_loop(app, state))


# ------------------------------
#  MAIN
# ------------------------------

def main():
    TOKEN = os.getenv("TOKEN")

    app = Application.builder().token(TOKEN).post_init(on_startup).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
