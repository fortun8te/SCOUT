"""Discord bot status management"""

import asyncio
import logging
from discord import Client, Intents, Status

logger = logging.getLogger(__name__)


class BotStatusManager:
    """Manages Discord bot presence and status"""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.client = None
        self.ready = False

    async def set_dnd_status_background(self):
        """Connect bot and keep DND status during execution"""
        try:
            intents = Intents.default()
            self.client = Client(intents=intents)

            @self.client.event
            async def on_ready():
                await self.client.change_presence(status=Status.dnd)
                logger.info("[BOT] Connected - Status: DND")
                self.ready = True

            # Start the bot in background
            await self.client.start(self.bot_token)

        except Exception as e:
            logger.error(f"Bot status error: {e}")

    def connect_background(self):
        """Start bot connection in background task"""
        try:
            # Create task that runs in background
            asyncio.create_task(self.set_dnd_status_background())
            logger.info("[BOT] Starting background connection...")
        except Exception as e:
            logger.error(f"Failed to start bot background: {e}")

    async def disconnect(self):
        """Disconnect bot cleanly"""
        try:
            if self.client:
                await self.client.close()
                logger.info("[BOT] Disconnected")
        except Exception as e:
            logger.error(f"Failed to disconnect bot: {e}")
