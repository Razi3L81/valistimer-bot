import os
import json
import time
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Charger .env en local (Railway ignore ce fichier)
load_dotenv()

TOKEN = os.getenv("TOKEN")
STATE_FILE = "users.json"


# ---------------------------------------------------------
#  UTILITAIRES
# ---------------------------------------------------------

def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def clear_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)


def format_time(seconds):
    minutes = int(seconds // 60)
    sec = int(seconds % 60)
    return f"{minutes:02d}:{sec:02d}"


# ---------------------------------------------------------
#  INTERFACE : CLAVIER INLINE
# ---------------------------------------------------------

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧳 Ouvrir la valise", callback_data="start_timer")],
        [InlineKeyboardButton("🟢 Status", callback_data="status")],
        [InlineKeyboardButton("🔄 Reset", callback_data="reset_timer")]
    ])


# ---------------------------------------------------------
#  COMMANDES
# ---------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bienvenue dans ValisTimer !\nChoisis une action :",
        reply_markup=main_keyboard()
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commandes disponibles :\n"
        "/start – Afficher le menu\n"
        "/status – Voir le temps restant\n"
        "/reset – Réinitialiser le timer"
    )


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()

    if not state:
        await update.message.reply_text("Aucun timer en cours.")
        return

    remaining = state["timer_end"] - time.time()
    if remaining <= 0:
        await update.message.reply_text("🧳 La valise est disponible !")
        return

    await update.message.reply_text(f"⏳ Temps restant : {format_time(remaining)}")


async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_state()
    await update.message.reply_text("🔄 Timer réinitialisé.")


# ---------------------------------------------------------
#  GESTION DES BOUTONS
# ---------------------------------------------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # --------------------------
    # 1. Démarrer le timer
    # --------------------------
    if data == "start_timer":
        duration = 20 * 60  # 20 minutes
        end_time = time.time() + duration

        state = {
            "timer_end": end_time,
            "message_id": query.message.message_id,
            "chat_id": query.message.chat_id
        }
        save_state(state)

        await query.message.reply_text(
            f"🧳 Valise ouverte !\n⏳ Temps restant : {format_time(duration)}",
            reply_markup=main_keyboard()
        )
        return

    # --------------------------
    # 2. Status
    # --------------------------
    if data == "status":
        state = load_state()

        if not state:
            await query.message.reply_text("Aucun timer en cours.")
            return

        remaining = state["timer_end"] - time.time()

        if remaining <= 0:
            await query.message.reply_text("🧳 La valise est disponible !")
            return

        await query.message.reply_text(
            f"⏳ Temps restant : {format_time(remaining)}"
        )
        return

    # --------------------------
    # 3. Reset
    # --------------------------
    if data == "reset_timer":
        clear_state()
        await query.message.reply_text("🔄 Timer réinitialisé.")
        return


# ---------------------------------------------------------
#  MAIN
# ---------------------------------------------------------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Commandes
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))

    # Boutons
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot lancé...")
    app.run_polling()


if __name__ == "__main__":
    main()
