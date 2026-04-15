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

    async def connect_and_wait(self):
        """Start bot connection and wait for ready"""
        try:
            # Start connection - this runs concurrently
            task = asyncio.create_task(self.set_dnd_status_background())

            # Wait a bit for connection to establish
            for _ in range(30):  # Try for 3 seconds
                if self.ready:
                    logger.info("[BOT] Connected and ready")
                    return task
                await asyncio.sleep(0.1)

            logger.warning("[BOT] Timeout waiting for connection (but continuing anyway)")
            return task
        except Exception as e:
            logger.error(f"Failed to connect bot: {e}")
            return None

    async def disconnect(self):
        """Disconnect bot cleanly"""
        try:
            if self.client:
                await self.client.close()
                logger.info("[BOT] Disconnected")
        except Exception as e:
            logger.error(f"Failed to disconnect bot: {e}")
