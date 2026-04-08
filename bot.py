"""
bot.py — Main Telegram Bot for Gmail OTP via 5sim.net

Usage:
  python bot.py

Requirements: python-telegram-bot>=20.0, requests, python-dotenv
"""

import asyncio
import logging
import time
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

import config
from fivesim_api import FiveSimAPI
from utils import extract_otp_code, format_phone_number, country_flag, humanize_country

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Shared API instance
# ─────────────────────────────────────────────────────────────────────────────
api = FiveSimAPI()

# ─────────────────────────────────────────────────────────────────────────────
# Keyboard layouts
# ─────────────────────────────────────────────────────────────────────────────

MAIN_MENU_KEYBOARD = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("💰 Check Balance", callback_data="balance")],
        [InlineKeyboardButton("📱 Buy Gmail OTP Number", callback_data="buy")],
        [InlineKeyboardButton("❌ Cancel Number", callback_data="cancel_menu")],
        [InlineKeyboardButton("✅ Finish Order", callback_data="finish_menu")],
        [InlineKeyboardButton("📋 My Active Orders", callback_data="orders")],
    ]
)


def otp_action_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Keyboard shown after an OTP arrives."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔄 Check OTP Again", callback_data=f"check_otp:{order_id}")],
            [
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{order_id}"),
                InlineKeyboardButton("✅ Finish", callback_data=f"finish:{order_id}"),
            ],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ]
    )


def waiting_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Keyboard shown while waiting for OTP."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔄 Check OTP Now", callback_data=f"check_otp:{order_id}")],
            [InlineKeyboardButton("❌ Cancel Order", callback_data=f"cancel:{order_id}")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ]
    )


# ─────────────────────────────────────────────────────────────────────────────
# Access control helper
# ─────────────────────────────────────────────────────────────────────────────

def is_allowed(user_id: int) -> bool:
    """Return True if the user is allowed to use the bot."""
    if not config.ADMIN_USER_IDS:
        return True  # open to everyone
    return user_id in config.ADMIN_USER_IDS


# ─────────────────────────────────────────────────────────────────────────────
# /start command handler
# ─────────────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the main menu."""
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text("❌ Aapko is bot ka access nahi hai.")
        return

    await update.message.reply_text(
        f"🤖 *Namaste {user.first_name}!*\n\n"
        "Main aapko Gmail ke liye *fresh virtual number* aur *OTP* dunga.\n\n"
        "👇 Niche se option choose karo:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=MAIN_MENU_KEYBOARD,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Callback query dispatcher
# ─────────────────────────────────────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route inline button presses to the right handler."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not is_allowed(user_id):
        await query.edit_message_text("❌ Access denied.")
        return

    data: str = query.data

    if data == "main_menu":
        await query.edit_message_text(
            "🏠 *Main Menu* — Option choose karo:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MAIN_MENU_KEYBOARD,
        )

    elif data == "balance":
        await handle_balance(query, context)

    elif data == "buy":
        await handle_buy(query, context)

    elif data == "cancel_menu":
        await handle_cancel_menu(query, context)

    elif data == "finish_menu":
        await handle_finish_menu(query, context)

    elif data == "orders":
        await handle_orders(query, context)

    elif data.startswith("check_otp:"):
        order_id = int(data.split(":")[1])
        await handle_check_otp(query, context, order_id)

    elif data.startswith("cancel:"):
        order_id = int(data.split(":")[1])
        await handle_cancel_order(query, context, order_id)

    elif data.startswith("finish:"):
        order_id = int(data.split(":")[1])
        await handle_finish_order(query, context, order_id)

    elif data.startswith("cancel_select:"):
        order_id = int(data.split(":")[1])
        await handle_cancel_order(query, context, order_id)

    elif data.startswith("finish_select:"):
        order_id = int(data.split(":")[1])
        await handle_finish_order(query, context, order_id)

    elif data.startswith("confirm_buy:"):
        parts = data.split(":")
        country = parts[1]
        operator = parts[2]
        await handle_confirmed_buy(query, context, country, operator)

    else:
        await query.edit_message_text("❓ Unknown action. /start se dobara shuru karo.")


# ─────────────────────────────────────────────────────────────────────────────
# Individual action handlers
# ─────────────────────────────────────────────────────────────────────────────

async def handle_balance(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    await query.edit_message_text("⏳ Balance check ho raha hai...")
    try:
        balance = api.get_balance()
        await query.edit_message_text(
            f"💰 *Aapka 5sim.net Balance:*\n\n`${balance:.4f}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            ),
        )
    except Exception as exc:
        logger.error("Balance error: %s", exc)
        await query.edit_message_text(
            "❌ Balance nahi mila. API key sahi hai? Dobara try karo.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            ),
        )


async def handle_buy(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Buy a fresh number and start OTP polling (with auto price escalation)."""
    await query.edit_message_text(
        f"🔍 *${config.MAX_PRICE/100:.2f} mein dhoond raha hu...*",
        parse_mode=ParseMode.MARKDOWN,
    )

    # 1. Check balance first
    try:
        balance = api.get_balance()
        if balance < config.MAX_PRICE / 100:
            await query.edit_message_text(
                f"❌ *Balance kam hai!*\n\n"
                f"Aapka balance: `${balance:.4f}`\n"
                f"Minimum chahiye: `${config.MAX_PRICE/100:.2f}`\n\n"
                "Please 5sim.net account recharge karo.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
                ),
            )
            return
    except Exception as exc:
        logger.warning("Could not check balance before buy: %s", exc)
        # Non-fatal — continue anyway

    # 2. Find cheapest options with auto price escalation
    try:
        options, price_tier_used = api.find_cheapest_with_escalation()
    except Exception as exc:
        logger.error("Price fetch error: %s", exc)
        await query.edit_message_text(
            "❌ Prices fetch nahi ho sake. Network error? Thodi der baad try karo.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            ),
        )
        return

    if not options:
        await query.edit_message_text(
            "❌ *Koi number available nahi hai!*\n\n"
            "Thodi der baad try karo.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            ),
        )
        return

    # 3. If price is above user's original MAX_PRICE, ask for confirmation first
    if price_tier_used > config.MAX_PRICE:
        best = options[0]
        country = best["country"]
        operator = best["operator"]
        cost_usd = best["cost"]
        await query.edit_message_text(
            f"⚠️ *${config.MAX_PRICE/100:.2f} mein koi number nahi mila.*\n\n"
            f"💰 Sabse sasta mila:\n"
            f"{country_flag(country)} *{humanize_country(country)}* — `${cost_usd:.4f}`\n\n"
            f"⚠️ Ye aapke budget `${config.MAX_PRICE/100:.2f}` se zyada hai.\n\n"
            "Kya buy karna hai?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Haan, Buy Karo",
                            callback_data=f"confirm_buy:{country}:{operator}",
                        ),
                        InlineKeyboardButton("❌ Nahi, Cancel", callback_data="main_menu"),
                    ]
                ]
            ),
        )
        return

    # 4. Within budget — buy directly
    await _do_buy(query, context, options)


async def _do_buy(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    options: list[dict],
) -> None:
    """Internal helper: try buying from the given options list (cheapest first)."""
    order: Optional[dict] = None
    tried_countries: list[str] = []

    for opt in options[: config.MAX_RETRIES]:
        country = opt["country"]
        operator = opt["operator"]
        tried_countries.append(humanize_country(country))
        try:
            await query.edit_message_text(
                f"⏳ Try kar raha hu: {country_flag(country)} *{humanize_country(country)}* "
                f"({operator}) — `${opt['cost']:.4f}`",
                parse_mode=ParseMode.MARKDOWN,
            )
            order = api.buy_number(country=country, operator=operator)
            if order.get("id"):
                order["_country"] = country
                order["_operator"] = operator
                order["_cost"] = opt["cost"]
                break
            order = None
        except Exception as exc:
            logger.warning("Buy failed %s/%s: %s", country, operator, exc)
            order = None

    if not order or not order.get("id"):
        await query.edit_message_text(
            "❌ *Number nahi mila* in sab countries try karne ke baad:\n"
            + ", ".join(tried_countries)
            + "\n\nThodi der baad dobara try karo.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            ),
        )
        return

    # Store active order in user context
    order_id: int = order["id"]
    phone_raw: str = order.get("phone", "")
    phone_formatted = format_phone_number(phone_raw)
    country_name = humanize_country(order.get("_country", order.get("country", "")))
    cost = order.get("_cost", 0.0)

    active_orders: dict = context.user_data.get("active_orders", {})
    active_orders[order_id] = {
        "phone": phone_formatted,
        "country": country_name,
        "cost": cost,
        "sms_seen": [],
        "bought_at": time.time(),
    }
    context.user_data["active_orders"] = active_orders

    await query.edit_message_text(
        f"✅ *Number mil gaya!*\n\n"
        f"📱 Number: `{phone_formatted}`\n"
        f"{country_flag(order.get('_country',''))} Country: *{country_name}*\n"
        f"💰 Price: `${cost:.4f}`\n\n"
        f"⏳ OTP ka wait kar raha hu... (max {config.OTP_TIMEOUT}s)",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=waiting_keyboard(order_id),
    )

    context.application.create_task(
        poll_for_otp(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            order_id=order_id,
            phone=phone_formatted,
            context=context,
        )
    )


async def handle_confirmed_buy(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    country: str,
    operator: str,
) -> None:
    """
    User confirmed buying a number that was above the original MAX_PRICE.
    Skip price search — directly buy the specific country/operator.
    """
    await query.edit_message_text(
        f"⏳ Try kar raha hu: {country_flag(country)} *{humanize_country(country)}* "
        f"({operator})...",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        order = api.buy_number(country=country, operator=operator)
    except Exception as exc:
        logger.error("Confirmed buy failed %s/%s: %s", country, operator, exc)
        await query.edit_message_text(
            f"❌ Number kharidne mein error aaya: {exc}\n\nDobara try karo.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            ),
        )
        return

    if not order or not order.get("id"):
        await query.edit_message_text(
            "❌ Number nahi mila. Dobara try karo.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            ),
        )
        return

    order["_country"] = country
    order["_operator"] = operator
    # cost may not be in the order response directly; "price" is the 5sim field name,
    # "cost" is used elsewhere in this codebase — fall back to 0 if neither present.
    raw_cost = order.get("price") or order.get("cost") or 0.0
    order["_cost"] = float(raw_cost)

    order_id: int = order["id"]
    phone_raw: str = order.get("phone", "")
    phone_formatted = format_phone_number(phone_raw)
    country_name = humanize_country(country)
    cost = order["_cost"]

    active_orders: dict = context.user_data.get("active_orders", {})
    active_orders[order_id] = {
        "phone": phone_formatted,
        "country": country_name,
        "cost": cost,
        "sms_seen": [],
        "bought_at": time.time(),
    }
    context.user_data["active_orders"] = active_orders

    await query.edit_message_text(
        f"✅ *Number mil gaya!*\n\n"
        f"📱 Number: `{phone_formatted}`\n"
        f"{country_flag(country)} Country: *{country_name}*\n"
        f"💰 Price: `${cost:.4f}`\n\n"
        f"⏳ OTP ka wait kar raha hu... (max {config.OTP_TIMEOUT}s)",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=waiting_keyboard(order_id),
    )

    context.application.create_task(
        poll_for_otp(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
            order_id=order_id,
            phone=phone_formatted,
            context=context,
        )
    )


async def poll_for_otp(
    chat_id: int,
    message_id: int,
    order_id: int,
    phone: str,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Background coroutine: poll 5sim.net every POLL_INTERVAL seconds.
    Sends OTP to user when received. Stops after OTP_TIMEOUT seconds.
    """
    start_ts = time.time()
    seen_codes: list[str] = []

    while True:
        elapsed = time.time() - start_ts

        # Timeout?
        if elapsed > config.OTP_TIMEOUT:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"⏰ *{config.OTP_TIMEOUT} second ho gaye, OTP nahi aaya.*\n\n"
                        f"📱 Number: `{phone}`\n\n"
                        "Kya karna chahte ho?"
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=waiting_keyboard(order_id),
                )
            except Exception as exc:
                logger.warning("Could not send timeout message: %s", exc)
            return

        await asyncio.sleep(config.POLL_INTERVAL)

        try:
            sms_list = api.get_sms(order_id)
        except Exception as exc:
            logger.warning("OTP poll error for order %d: %s", order_id, exc)
            continue

        for sms in sms_list:
            code = sms.get("code") or extract_otp_code(sms.get("text", ""))
            text = sms.get("text", "")

            if code and code not in seen_codes:
                seen_codes.append(code)
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"📩 *OTP Aa Gaya!*\n\n"
                            f"🔢 Code: `{code}`\n"
                            f"📱 Number: `{phone}`\n"
                            f"💬 Full SMS: _{text}_\n\n"
                            "🔄 Aur OTP chahiye? *Check OTP Again* dabao\n"
                            "✅ Kaam ho gaya? *Finish Order* dabao"
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=otp_action_keyboard(order_id),
                    )
                except Exception as exc:
                    logger.warning("Could not send OTP message: %s", exc)

                # After first OTP, keep polling for more but slow down
                # (number stays active until user clicks Finish)


async def handle_check_otp(query, context: ContextTypes.DEFAULT_TYPE, order_id: int) -> None:
    """Manually check for a new OTP on an active order."""
    await query.edit_message_text(
        f"🔍 Order #{order_id} ke liye OTP check ho raha hai..."
    )
    try:
        sms_list = api.get_sms(order_id)
    except Exception as exc:
        logger.error("Check OTP error: %s", exc)
        await query.edit_message_text(
            "❌ OTP check nahi ho saka. Order cancel ya finish ho gaya hoga.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            ),
        )
        return

    if not sms_list:
        await query.edit_message_text(
            f"📭 *Order #{order_id}* — Abhi tak koi OTP nahi aaya.\n\n"
            "Gmail signup pe number daal ke wait karo phir dobara check karo.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=waiting_keyboard(order_id),
        )
        return

    # Show all received SMSs
    lines = [f"📩 *Order #{order_id} — Received SMS:*\n"]
    for i, sms in enumerate(sms_list, 1):
        code = sms.get("code") or extract_otp_code(sms.get("text", ""))
        text = sms.get("text", "—")
        lines.append(f"*SMS {i}:*\n🔢 Code: `{code}`\n💬 _{text}_\n")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=otp_action_keyboard(order_id),
    )


async def handle_cancel_order(query, context: ContextTypes.DEFAULT_TYPE, order_id: int) -> None:
    """Cancel an active order."""
    await query.edit_message_text(f"⏳ Order #{order_id} cancel ho raha hai...")
    try:
        api.cancel_order(order_id)
        # Remove from local cache
        active_orders: dict = context.user_data.get("active_orders", {})
        active_orders.pop(order_id, None)
        context.user_data["active_orders"] = active_orders

        await query.edit_message_text(
            f"❌ *Order #{order_id} cancel ho gaya!*\n\nRefund process ho raha hai.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            ),
        )
    except Exception as exc:
        logger.error("Cancel error: %s", exc)
        await query.edit_message_text(
            f"❌ Order cancel nahi ho saka: {exc}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            ),
        )


async def handle_finish_order(query, context: ContextTypes.DEFAULT_TYPE, order_id: int) -> None:
    """Finish / close an active order."""
    await query.edit_message_text(f"⏳ Order #{order_id} finish ho raha hai...")
    try:
        api.finish_order(order_id)
        active_orders: dict = context.user_data.get("active_orders", {})
        active_orders.pop(order_id, None)
        context.user_data["active_orders"] = active_orders

        await query.edit_message_text(
            f"✅ *Order #{order_id} finish ho gaya!*\n\nAb naya number le sakte ho.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            ),
        )
    except Exception as exc:
        logger.error("Finish error: %s", exc)
        await query.edit_message_text(
            f"❌ Order finish nahi ho saka: {exc}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            ),
        )


async def handle_cancel_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show list of active orders for cancellation."""
    active_orders: dict = context.user_data.get("active_orders", {})
    if not active_orders:
        await query.edit_message_text(
            "📋 Koi active order nahi hai.\n\nPehle ek number kharido.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            ),
        )
        return

    buttons = [
        [
            InlineKeyboardButton(
                f"❌ #{oid} — {info['phone']}",
                callback_data=f"cancel_select:{oid}",
            )
        ]
        for oid, info in active_orders.items()
    ]
    buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])

    await query.edit_message_text(
        "❌ *Kaun sa order cancel karna hai?*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_finish_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show list of active orders for finishing."""
    active_orders: dict = context.user_data.get("active_orders", {})
    if not active_orders:
        await query.edit_message_text(
            "📋 Koi active order nahi hai.\n\nPehle ek number kharido.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            ),
        )
        return

    buttons = [
        [
            InlineKeyboardButton(
                f"✅ #{oid} — {info['phone']}",
                callback_data=f"finish_select:{oid}",
            )
        ]
        for oid, info in active_orders.items()
    ]
    buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])

    await query.edit_message_text(
        "✅ *Kaun sa order finish karna hai?*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_orders(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all active orders."""
    active_orders: dict = context.user_data.get("active_orders", {})
    if not active_orders:
        await query.edit_message_text(
            "📋 *Aapke paas koi active order nahi hai.*\n\n"
            "Naya number kharidne ke liye *Buy Gmail OTP Number* dabao.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            ),
        )
        return

    lines = ["📋 *Aapke Active Orders:*\n"]
    for oid, info in active_orders.items():
        elapsed = int(time.time() - info.get("bought_at", time.time()))
        lines.append(
            f"🔹 Order `#{oid}`\n"
            f"   📱 {info['phone']}\n"
            f"   🌍 {info['country']} | 💰 ${info['cost']:.4f}\n"
            f"   ⏱ {elapsed}s ago\n"
        )

    buttons = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ─────────────────────────────────────────────────────────────────────────────
# /help command
# ─────────────────────────────────────────────────────────────────────────────

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "ℹ️ *OTP Bot — Help*\n\n"
        "Commands:\n"
        "• /start — Main menu\n"
        "• /help  — Yeh message\n\n"
        "Buttons:\n"
        "• 💰 Check Balance — 5sim.net balance dekho\n"
        "• 📱 Buy Gmail OTP Number — Fresh number kharido\n"
        "• ❌ Cancel Number — Order cancel karo (refund milega)\n"
        "• ✅ Finish Order — Order finish karo\n"
        "• 📋 My Active Orders — Active orders dekho\n\n"
        "📌 Bot automatically sabse sasta fresh number choose karta hai "
        f"(max ${config.MAX_PRICE/100:.2f})\n"
        "📌 Ek number pe 2-3 OTP le sakte ho — Finish dabane se pehle!\n",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=MAIN_MENU_KEYBOARD,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main entry-point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Start the bot."""
    token = config.TELEGRAM_BOT_TOKEN
    if not token or token == "your-telegram-bot-token":
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN set nahi hai! "
            ".env file mein apna Telegram bot token daalo."
        )

    api_key = config.FIVESIM_API_KEY
    if not api_key or api_key == "your-5sim-api-key":
        raise RuntimeError(
            "FIVESIM_API_KEY set nahi hai! "
            ".env file mein apna 5sim.net API key daalo."
        )

    logger.info("Bot shuru ho raha hai...")

    app = Application.builder().token(token).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot chal raha hai. Ctrl+C se band karo.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
