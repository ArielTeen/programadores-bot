#!/usr/bin/env python3
"""
Punto de entrada combinado para Discloud.
Ejecuta el bot de Discord y el dashboard web en un mismo proceso.
"""
import asyncio
import logging
import threading
import os
import config
from core.bot import Bot
from utils.logger import setup_logger

logger = setup_logger("Main")
setup_logger("TeenBot")

# ─── Dashboard thread ────────────────────────────────────────────────────

def run_dashboard():
    from dashboard.app import app
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ─── Bot ─────────────────────────────────────────────────────────────────

async def run_bot():
    bot = Bot()
    try:
        await bot.start(config.TOKEN)
    except KeyboardInterrupt:
        logger.info("Deteniendo bot...")
        await bot.close()
    except Exception as e:
        logger.error(f"Error fatal: {e}")
    finally:
        await bot.db.close()

# ─── Entry point ─────────────────────────────────────────────────────────

def main():
    logger.info("=" * 50)
    logger.info("Iniciando Teen Bot + Dashboard")
    logger.info("=" * 50)

    if not config.TOKEN:
        logger.error("DISCORD_TOKEN no configurado. Edita el archivo .env")
        return

    t = threading.Thread(target=run_dashboard, daemon=True)
    t.start()
    logger.info(f"Dashboard iniciado en puerto {os.getenv('PORT', 5000)}")

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
