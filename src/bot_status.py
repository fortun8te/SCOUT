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

    async def set_dnd_status(self):
        """Set bot to DND (Do Not Disturb) status"""
        try:
            intents = Intents.default()
            self.client = Client(intents=intents)

            @self.client.event
            async def on_ready():
                # Set status to DND with "Monitoring news"
                await self.client.change_presence(
                    status=Status.dnd,
                    activity=None
                )
                logger.info("Bot status set to DND")
                # Keep the connection alive briefly then close
                await asyncio.sleep(2)
                await self.client.close()

            # Connect and maintain for a moment
            await asyncio.wait_for(self.client.start(self.bot_token), timeout=10)

        except asyncio.TimeoutError:
            logger.info("Status update completed (timeout as expected)")
            if self.client:
                await self.client.close()
        except Exception as e:
            logger.error(f"Failed to set DND status: {e}")
            if self.client:
                try:
                    await self.client.close()
                except:
                    pass

    def run_status_update(self):
        """Synchronous wrapper to set status"""
        try:
            asyncio.run(self.set_dnd_status())
        except Exception as e:
            logger.error(f"Status update error: {e}")
