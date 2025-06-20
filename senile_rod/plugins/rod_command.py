import logging
from discord import TextChannel, User, Webhook
from discord.ext.commands import Cog, HybridCommand, Context, Bot

from senile_rod.constants.constants import Constants


LOGGER = logging.getLogger(__name__)


class RodCommandPlugin(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        LOGGER.info(f"{self.__class__.__name__} is locked and loaded!")

    @HybridCommand
    async def send_rod_message(self, ctx: Context, *, message: str):
        """Send a message as if it was sent by Rod"""
        assert isinstance(ctx.channel, TextChannel)
        user = await self.get_user_by_id(int(Constants.ROD_USER_ID.value))
        avatar_url = user.avatar.url if user.avatar else None
        webhook = await self.create_or_get_rod_webhook(ctx.channel, user)

        await webhook.send(
            message,
            username=user.display_name,
            avatar_url=avatar_url,
        )
        await ctx.reply("Message sent!", ephemeral=True)

    async def create_or_get_rod_webhook(
        self, channel: TextChannel, user: User
    ) -> Webhook:
        """Create or get a webhook for Rod Messages"""
        webhooks = await channel.webhooks()
        for webhook in webhooks:
            if webhook.name == "Rod Message":
                return webhook

        avatar_bytes = None
        if user.avatar:
            avatar_bytes = await user.avatar.read()
        return await channel.create_webhook(name="Rod Messages", avatar=avatar_bytes)

    async def get_user_by_id(self, user_id: int) -> User:
        """Get a user by their ID across servers"""
        user = self.bot.get_user(user_id)
        if user is None:
            user = await self.bot.fetch_user(user_id)
        return user


async def setup(bot: Bot):
    await bot.add_cog(RodCommandPlugin(bot))
