#!/usr/bin/env python3
"""
Teen Bot — Bot profesional de Discord
Punto de entrada principal.
"""

import asyncio
import logging
import config
from core.bot import Bot
from utils.logger import setup_logger

logger = setup_logger("Main")
setup_logger("TeenBot")


async def main():
    logger.info("=" * 50)
    logger.info("🤖 Iniciando Teen Bot...")
    logger.info("=" * 50)

    if not config.TOKEN:
        logger.error("❌ DISCORD_TOKEN no configurado. Edita el archivo .env")
        return

    bot = Bot()

    try:
        await bot.start(config.TOKEN)
    except discord.LoginFailure:
        logger.error("❌ Token inválido. Verifica tu .env")
    except discord.PrivilegedIntentsRequired:
        logger.error("❌ Activa los 3 intents en discord.com/developers")
    except KeyboardInterrupt:
        logger.info("👋 Deteniendo bot...")
        await bot.close()
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
    finally:
        await bot.db.close()
        logger.info("👋 Bot desconectado.")


if __name__ == "__main__":
    import discord
    asyncio.run(main())
