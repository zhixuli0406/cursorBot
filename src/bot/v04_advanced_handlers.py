"""
v0.4 Advanced Feature Handlers for CursorBot

Telegram command handlers for v0.4 advanced features:
- Multi-Gateway (High Availability)
- DM Pairing (Device Pairing)
- Live Canvas (A2UI Visual Workspace)
- i18n (Internationalization)
- Email Classifier
"""

import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from ..utils.logger import logger
from ..utils.auth import is_authorized


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ============================================
# Multi-Gateway Handlers
# ============================================

async def gateway_cluster_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /gateways command - Multi-Gateway management.
    
    Usage:
        /gateways - Show gateway status
        /gateways list - List all gateways
        /gateways add <id> <host> <port> - Add gateway
        /gateways remove <id> - Remove gateway
        /gateways strategy <strategy> - Set load balance strategy
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    
    try:
        from ..core.multi_gateway import get_multi_gateway_manager, LoadBalanceStrategy
        manager = get_multi_gateway_manager()
        
        if not args:
            # Show status
            stats = manager.get_cluster_stats()
            gateways = manager.get_all_gateways()
            
            text = (
                "🌐 <b>Multi-Gateway Cluster</b>\n\n"
                f"Cluster: <code>{_escape_html(stats['cluster_name'])}</code>\n"
                f"Strategy: {_escape_html(stats['strategy'])}\n"
                f"Gateways: {stats['available_gateways']}/{stats['total_gateways']}\n"
                f"Connections: {stats['total_connections']}\n"
                f"Active Sessions: {stats['active_sessions']}\n"
                f"Error Rate: {stats['error_rate']}%\n"
            )
            
            if gateways:
                text += "\n<b>Gateways:</b>\n"
                for gw in gateways[:10]:
                    state_icon = {
                        "healthy": "🟢",
                        "degraded": "🟡",
                        "unhealthy": "🔴",
                        "starting": "⚪",
                        "draining": "🟠",
                        "stopped": "⚫",
                    }.get(gw.state.value, "⚪")
                    text += f"{state_icon} <code>{_escape_html(gw.id)}</code>: {_escape_html(gw.host)}:{gw.port}\n"
            
            text += (
                "\n<b>Commands:</b>\n"
                "<code>/gateways list</code> - List gateways\n"
                "<code>/gateways add &lt;id&gt; &lt;host&gt; &lt;port&gt;</code>\n"
                "<code>/gateways remove &lt;id&gt;</code>\n"
                "<code>/gateways strategy &lt;type&gt;</code>\n"
            )
            
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "list":
            gateways = manager.get_all_gateways()
            
            if not gateways:
                await update.message.reply_text("No gateways registered.")
                return
            
            text = "🌐 <b>All Gateways</b>\n\n"
            for gw in gateways:
                state_icon = {
                    "healthy": "🟢",
                    "degraded": "🟡",
                    "unhealthy": "🔴",
                    "starting": "⚪",
                }.get(gw.state.value, "⚪")
                
                text += (
                    f"{state_icon} <b>{_escape_html(gw.name)}</b>\n"
                    f"   ID: <code>{_escape_html(gw.id)}</code>\n"
                    f"   URL: {_escape_html(gw.url)}\n"
                    f"   Conn: {gw.current_connections}/{gw.max_connections}\n"
                    f"   Requests: {gw.total_requests} (err: {gw.failed_requests})\n\n"
                )
            
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "add" and len(args) >= 4:
            gw_id = args[1]
            host = args[2]
            port = int(args[3])
            
            gateway = manager.register_gateway(gw_id, host, port)
            
            await update.message.reply_text(
                f"✅ Gateway registered\n\n"
                f"ID: <code>{_escape_html(gw_id)}</code>\n"
                f"URL: <code>{_escape_html(gateway.url)}</code>",
                parse_mode="HTML"
            )
        
        elif args[0] == "remove" and len(args) >= 2:
            gw_id = args[1]
            
            success = manager.unregister_gateway(gw_id)
            
            if success:
                await update.message.reply_text(f"✅ Gateway <code>{_escape_html(gw_id)}</code> removed", parse_mode="HTML")
            else:
                await update.message.reply_text(f"❌ Gateway <code>{_escape_html(gw_id)}</code> not found", parse_mode="HTML")
        
        elif args[0] == "strategy" and len(args) >= 2:
            strategy_name = args[1].upper()
            
            strategy_map = {
                "ROUND_ROBIN": LoadBalanceStrategy.ROUND_ROBIN,
                "LEAST_CONNECTIONS": LoadBalanceStrategy.LEAST_CONNECTIONS,
                "RANDOM": LoadBalanceStrategy.RANDOM,
                "IP_HASH": LoadBalanceStrategy.IP_HASH,
                "WEIGHTED": LoadBalanceStrategy.WEIGHTED,
            }
            
            if strategy_name not in strategy_map:
                strategies = ", ".join(strategy_map.keys())
                await update.message.reply_text(f"Invalid strategy. Available: {strategies}")
                return
            
            manager.configure_cluster(strategy=strategy_map[strategy_name])
            await update.message.reply_text(f"✅ Load balance strategy set to <code>{_escape_html(strategy_name)}</code>", parse_mode="HTML")
        
        else:
            await update.message.reply_text(
                "Usage:\n"
                "<code>/gateways</code> - Status\n"
                "<code>/gateways list</code> - List all\n"
                "<code>/gateways add &lt;id&gt; &lt;host&gt; &lt;port&gt;</code>\n"
                "<code>/gateways remove &lt;id&gt;</code>\n"
                "<code>/gateways strategy &lt;type&gt;</code>\n\n"
                "Strategies: ROUND_ROBIN, LEAST_CONNECTIONS, RANDOM, IP_HASH, WEIGHTED",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Gateway command error: {e}")
        await update.message.reply_text(f"Error: {str(e)[:200]}")


# ============================================
# DM Pairing Handlers
# ============================================

async def pair_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /pair command - Device pairing.
    
    Usage:
        /pair - Generate pairing code
        /pair qr - Generate QR code
        /pair <code> - Complete pairing with code
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    
    try:
        from ..core.dm_pairing import get_dm_pairing_manager, DeviceType
        manager = get_dm_pairing_manager()
        
        if not args:
            # Generate new pairing code
            code = manager.generate_code(
                user_id=user_id,
                device_name=f"Device_{datetime.now().strftime('%H%M%S')}",
                device_type=DeviceType.MOBILE,
            )
            
            text = (
                "📱 <b>Device Pairing</b>\n\n"
                f"Pairing Code: <code>{code.code}</code>\n\n"
                f"⏱️ Expires in {code.remaining_seconds} seconds\n\n"
                "Enter this code on your other device to pair.\n\n"
                "Or use <code>/pair qr</code> to generate QR code."
            )
            
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "qr":
            # Generate QR code
            code = manager.generate_code(
                user_id=user_id,
                device_name=f"Device_{datetime.now().strftime('%H%M%S')}",
                device_type=DeviceType.MOBILE,
            )
            
            qr_data = manager.generate_qr_data(code)
            
            text = (
                "📱 <b>QR Code Pairing</b>\n\n"
                f"Pairing Code: <code>{code.code}</code>\n"
                f"⏱️ Expires in {code.remaining_seconds} seconds\n\n"
                f"QR Data:\n<code>{_escape_html(qr_data)}</code>\n\n"
                "Scan this QR code with the CursorBot app."
            )
            
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif len(args[0]) == 6 and args[0].isdigit():
            # Complete pairing with code
            code_str = args[0]
            
            device = manager.complete_pairing(
                code_str=code_str,
                ip_address=None,
                user_agent="Telegram Bot",
            )
            
            if device:
                await update.message.reply_text(
                    f"✅ <b>Device Paired!</b>\n\n"
                    f"Device: {_escape_html(device.device_name)}\n"
                    f"ID: <code>{_escape_html(device.device_id)}</code>",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text("❌ Invalid or expired pairing code.")
        
        else:
            await update.message.reply_text(
                "Usage:\n"
                "<code>/pair</code> - Generate pairing code\n"
                "<code>/pair qr</code> - Generate QR code\n"
                "<code>/pair &lt;code&gt;</code> - Complete pairing",
                parse_mode="HTML"
            )
            
    except ValueError as e:
        await update.message.reply_text(f"❌ {str(e)}")
    except Exception as e:
        logger.error(f"Pair command error: {e}")
        await update.message.reply_text(f"Error: {str(e)[:200]}")


async def devices_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /devices command - List paired devices.
    
    Usage:
        /devices - List all devices
        /devices remove <device_id> - Remove device
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    
    try:
        from ..core.dm_pairing import get_dm_pairing_manager
        manager = get_dm_pairing_manager()
        
        if not args:
            devices = manager.get_user_devices(user_id)
            
            if not devices:
                await update.message.reply_text(
                    "📱 <b>No Paired Devices</b>\n\n"
                    "Use <code>/pair</code> to pair a new device.",
                    parse_mode="HTML"
                )
                return
            
            text = f"📱 <b>Your Devices</b> ({len(devices)})\n\n"
            
            for device in devices:
                type_icon = {
                    "desktop": "🖥️",
                    "mobile": "📱",
                    "tablet": "📱",
                    "web": "🌐",
                    "cli": "💻",
                    "iot": "🔌",
                }.get(device.device_type.value, "📱")
                
                last_seen = device.last_seen.strftime("%Y-%m-%d %H:%M") if device.last_seen else "Never"
                
                text += (
                    f"{type_icon} <b>{_escape_html(device.device_name)}</b>\n"
                    f"   ID: <code>{_escape_html(device.device_id[:12])}...</code>\n"
                    f"   Last seen: {last_seen}\n\n"
                )
            
            text += "\nUse <code>/devices remove &lt;id&gt;</code> to unpair."
            
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "remove" and len(args) >= 2:
            device_id = args[1]
            
            # Find device by partial ID
            devices = manager.get_user_devices(user_id)
            target = None
            for d in devices:
                if d.device_id.startswith(device_id):
                    target = d
                    break
            
            if target:
                success = manager.unpair_device(target.device_id, user_id)
                if success:
                    await update.message.reply_text(
                        f"✅ Device <code>{_escape_html(target.device_name)}</code> unpaired.",
                        parse_mode="HTML"
                    )
                else:
                    await update.message.reply_text("❌ Failed to unpair device.")
            else:
                await update.message.reply_text("❌ Device not found.")
        
        else:
            await update.message.reply_text(
                "Usage:\n"
                "<code>/devices</code> - List devices\n"
                "<code>/devices remove &lt;id&gt;</code> - Unpair device",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Devices command error: {e}")
        await update.message.reply_text(f"Error: {str(e)[:200]}")


# ============================================
# Live Canvas Handlers
# ============================================

async def canvas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /canvas command - Live Canvas management.
    
    Usage:
        /canvas - Show status
        /canvas new [name] - Create new canvas
        /canvas list - List canvases
        /canvas open <id> - Open canvas
        /canvas add <type> <content> - Add component
        /canvas clear - Clear current canvas
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    
    try:
        from ..core.live_canvas import get_live_canvas_manager, ComponentType
        canvas = get_live_canvas_manager()
        
        # Get or create user's current session
        user_sessions = canvas.get_user_sessions(user_id)
        current_session = user_sessions[0] if user_sessions else None
        
        if not args:
            # Show status
            text = (
                "🎨 <b>Live Canvas</b>\n\n"
                f"Your Canvases: {len(user_sessions)}\n"
            )
            
            if current_session:
                text += (
                    f"\n<b>Current Canvas:</b>\n"
                    f"Name: {_escape_html(current_session.name)}\n"
                    f"Components: {len(current_session.components)}\n"
                    f"ID: <code>{_escape_html(current_session.session_id)}</code>\n"
                )
            
            text += (
                "\n<b>Commands:</b>\n"
                "<code>/canvas new [name]</code> - Create canvas\n"
                "<code>/canvas list</code> - List canvases\n"
                "<code>/canvas add text &lt;text&gt;</code>\n"
                "<code>/canvas add code &lt;code&gt;</code>\n"
                "<code>/canvas clear</code> - Clear canvas\n"
            )
            
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "new":
            name = " ".join(args[1:]) if len(args) > 1 else f"Canvas_{datetime.now().strftime('%H%M%S')}"
            
            session = canvas.create_session(user_id, name)
            
            await update.message.reply_text(
                f"✅ <b>Canvas Created</b>\n\n"
                f"Name: {_escape_html(name)}\n"
                f"ID: <code>{_escape_html(session.session_id)}</code>",
                parse_mode="HTML"
            )
        
        elif args[0] == "list":
            sessions = canvas.get_user_sessions(user_id)
            
            if not sessions:
                await update.message.reply_text(
                    "No canvases yet.\nUse <code>/canvas new</code> to create one.",
                    parse_mode="HTML"
                )
                return
            
            text = "🎨 <b>Your Canvases</b>\n\n"
            for session in sessions[:10]:
                text += (
                    f"• <b>{_escape_html(session.name)}</b>\n"
                    f"  ID: <code>{_escape_html(session.session_id[:12])}...</code>\n"
                    f"  Components: {len(session.components)}\n\n"
                )
            
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "add" and len(args) >= 3:
            if not current_session:
                current_session = canvas.create_session(user_id, "Default Canvas")
            
            comp_type = args[1].lower()
            content = " ".join(args[2:])
            
            type_map = {
                "text": ComponentType.TEXT,
                "markdown": ComponentType.MARKDOWN,
                "md": ComponentType.MARKDOWN,
                "code": ComponentType.CODE,
                "json": ComponentType.JSON,
                "alert": ComponentType.ALERT,
            }
            
            if comp_type not in type_map:
                types = ", ".join(type_map.keys())
                await update.message.reply_text(f"Invalid type. Available: {types}")
                return
            
            component = canvas.add_component(
                current_session.session_id,
                type_map[comp_type],
                content,
            )
            
            if component:
                await update.message.reply_text(
                    f"✅ Added {comp_type} component\n"
                    f"ID: <code>{_escape_html(component.id)}</code>",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text("❌ Failed to add component.")
        
        elif args[0] == "clear":
            if current_session:
                canvas.clear_canvas(current_session.session_id)
                await update.message.reply_text("✅ Canvas cleared")
            else:
                await update.message.reply_text("No active canvas.")
        
        elif args[0] == "render":
            if current_session:
                render_data = canvas.render(current_session.session_id)
                
                if render_data:
                    import json
                    json_str = json.dumps(render_data, indent=2, default=str)
                    
                    if len(json_str) > 4000:
                        json_str = json_str[:3900] + "\n... (truncated)"
                    
                    await update.message.reply_text(
                        f"🎨 <b>Canvas Render</b>\n\n<pre>{_escape_html(json_str)}</pre>",
                        parse_mode="HTML"
                    )
                else:
                    await update.message.reply_text("Failed to render canvas.")
            else:
                await update.message.reply_text("No active canvas.")
        
        else:
            await update.message.reply_text(
                "Usage:\n"
                "<code>/canvas new [name]</code> - Create\n"
                "<code>/canvas list</code> - List all\n"
                "<code>/canvas add &lt;type&gt; &lt;content&gt;</code>\n"
                "<code>/canvas clear</code> - Clear\n"
                "<code>/canvas render</code> - Show JSON",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Canvas command error: {e}")
        await update.message.reply_text(f"Error: {str(e)[:200]}")


# ============================================
# i18n (Internationalization) Handlers
# ============================================

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /lang command - Language settings.
    
    Usage:
        /lang - Show current language
        /lang list - List available languages
        /lang set <code> - Set language
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    
    try:
        from ..core.i18n import get_i18n_manager
        i18n = get_i18n_manager()
        
        if not args:
            current = i18n.get_user_language(user_id) if hasattr(i18n, 'get_user_language') else "zh-TW"
            
            text = (
                "🌐 <b>Language Settings</b>\n\n"
                f"Current: <code>{_escape_html(current)}</code>\n\n"
                "<b>Commands:</b>\n"
                "<code>/lang list</code> - Available languages\n"
                "<code>/lang set &lt;code&gt;</code> - Change language"
            )
            
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "list":
            from ..core.i18n import Language
            
            current = i18n.get_user_language(user_id)
            
            text = "🌐 <b>Available Languages</b>\n\n"
            for lang in Language:
                marker = "✓" if lang == current else " "
                name = i18n.get_language_name(lang)
                text += f"{marker} <code>{lang.value}</code> - {name}\n"
            
            text += "\nUse <code>/lang set &lt;code&gt;</code> to change."
            
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "set" and len(args) >= 2:
            lang_code = args[1].lower()
            
            # Map language code to Language enum
            from ..core.i18n import Language
            lang_map = {
                "zh-tw": Language.ZH_TW,
                "zhtw": Language.ZH_TW,
                "tw": Language.ZH_TW,
                "zh-cn": Language.ZH_CN,
                "zhcn": Language.ZH_CN,
                "cn": Language.ZH_CN,
                "en": Language.EN,
                "english": Language.EN,
                "ja": Language.JA,
                "jp": Language.JA,
                "japanese": Language.JA,
            }
            
            language = lang_map.get(lang_code)
            
            if language:
                i18n.set_user_language(user_id, language)
                lang_name = i18n.get_language_name(language)
                await update.message.reply_text(
                    f"✅ Language set to <b>{_escape_html(lang_name)}</b> ({language.value})",
                    parse_mode="HTML"
                )
            else:
                valid_codes = "zh-TW, zh-CN, en, ja"
                await update.message.reply_text(
                    f"❌ Invalid language code: {_escape_html(args[1])}\n\n"
                    f"Valid codes: {valid_codes}",
                    parse_mode="HTML"
                )
        
        else:
            await update.message.reply_text(
                "Usage:\n"
                "<code>/lang</code> - Current language\n"
                "<code>/lang list</code> - List languages\n"
                "<code>/lang set &lt;code&gt;</code> - Set language",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Lang command error: {e}")
        await update.message.reply_text(f"Error: {str(e)[:200]}")


# ============================================
# Email Classifier Handlers
# ============================================

async def email_classify_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /classify command - Email classification.
    
    Usage:
        /classify - Show classification status
        /classify <email_content> - Classify email
        /classify rules - Show classification rules
    """
    user_id = str(update.effective_user.id)
    
    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized")
        return
    
    args = context.args or []
    
    try:
        from ..core.email_classifier import get_email_classifier
        classifier = get_email_classifier()
        
        if not args:
            stats = classifier.get_stats() if hasattr(classifier, 'get_stats') else {}
            
            text = (
                "📧 <b>Email Classifier</b>\n\n"
                f"Total Classified: {stats.get('total_classified', 0)}\n"
                f"Categories: {stats.get('categories', 8)}\n\n"
                "<b>Categories:</b>\n"
                "• Primary - 重要郵件\n"
                "• Social - 社交網絡\n"
                "• Promotions - 促銷廣告\n"
                "• Updates - 系統更新\n"
                "• Forums - 論壇討論\n"
                "• Notifications - 通知提醒\n"
                "• Spam - 垃圾郵件\n"
                "• Other - 其他\n\n"
                "<b>Commands:</b>\n"
                "<code>/classify &lt;content&gt;</code> - Classify\n"
                "<code>/classify rules</code> - Show rules"
            )
            
            await update.message.reply_text(text, parse_mode="HTML")
        
        elif args[0] == "rules":
            rules = classifier.get_rules() if hasattr(classifier, 'get_rules') else []
            
            text = "📧 <b>Classification Rules</b>\n\n"
            
            if rules:
                for rule in rules[:15]:
                    text += f"• {_escape_html(str(rule))}\n"
            else:
                text += "Using default AI-based classification.\n"
            
            await update.message.reply_text(text, parse_mode="HTML")
        
        else:
            # Classify the provided content
            content = " ".join(args)
            
            result = await classifier.classify(content)
            
            if result:
                category = result.category if hasattr(result, 'category') else str(result)
                confidence = result.confidence if hasattr(result, 'confidence') else 0.0
                priority = result.priority if hasattr(result, 'priority') else "normal"
                
                category_icon = {
                    "primary": "⭐",
                    "social": "👥",
                    "promotions": "🏷️",
                    "updates": "🔄",
                    "forums": "💬",
                    "notifications": "🔔",
                    "spam": "🚫",
                    "other": "📄",
                }.get(category.lower(), "📧")
                
                text = (
                    f"📧 <b>Classification Result</b>\n\n"
                    f"{category_icon} Category: <b>{_escape_html(category)}</b>\n"
                    f"Confidence: {confidence*100:.1f}%\n"
                    f"Priority: {_escape_html(priority)}\n"
                )
                
                await update.message.reply_text(text, parse_mode="HTML")
            else:
                await update.message.reply_text("❌ Failed to classify email content.")
            
    except Exception as e:
        logger.error(f"Classify command error: {e}")
        await update.message.reply_text(f"Error: {str(e)[:200]}")


# ============================================
# Handler Registration
# ============================================

def register_v04_advanced_handlers(application) -> None:
    """Register v0.4 advanced feature handlers with the application."""
    # Multi-Gateway
    application.add_handler(CommandHandler("gateways", gateway_cluster_command))
    application.add_handler(CommandHandler("gateway", gateway_cluster_command))
    
    # DM Pairing
    application.add_handler(CommandHandler("pair", pair_command))
    application.add_handler(CommandHandler("devices", devices_command))
    application.add_handler(CommandHandler("unpair", devices_command))
    
    # Live Canvas
    application.add_handler(CommandHandler("canvas", canvas_command))
    
    # i18n
    application.add_handler(CommandHandler("lang", lang_command))
    application.add_handler(CommandHandler("language", lang_command))
    
    # Email Classifier
    application.add_handler(CommandHandler("classify", email_classify_command))
    
    logger.info("v0.4 advanced feature handlers registered")


__all__ = [
    "gateway_cluster_command",
    "pair_command",
    "devices_command",
    "canvas_command",
    "lang_command",
    "email_classify_command",
    "register_v04_advanced_handlers",
]
