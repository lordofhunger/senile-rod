import logging
from pathlib import Path

from discord import LoginFailure, Intents
from discord.ext.commands import Bot
from discord.utils import setup_logging

from typing import Generator

from senile_rod.constants.constants import Constants


class SenileBot(Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def on_ready(self) -> None:
        await self.tree.sync()

    async def setup_hook(self) -> None:
        for plugin in self._get_plugins():
            await self.load_extension(plugin[0])

    def _get_plugins(self) -> Generator[list[str], None]:
        """Get a list of loadable plugin modules

        Yields:
            Generator[list[str], None]: Yields found plugin module name e.g. senile_rod.plugins.whatever
        """
        plugin_path = Path(Path.cwd(), "senile_rod", "plugins")
        yield [
            f"senile_rod.plugins.{filename.stem}"
            for filename in plugin_path.iterdir()
            if filename.is_file()
            and filename.suffix == ".py"
            and not filename.name.startswith("_")
        ]


def get_intents() -> Intents:
    """Get the intents for the bot"""
    intents = Intents.default()
    intents.message_content = True

    return intents


def main() -> None:
    """Main function to run the bot"""
    setup_logging()
    logger = logging.getLogger("senile_rod")
    bot = SenileBot(
        command_prefix="!",
        intents=get_intents(),
        help_command=None,
    )

    try:
        bot.run(Constants.BOT_TOKEN.value)
    except LoginFailure as e:
        logger.fatal(f"Login failed: {e}")


if __name__ == "__main__":
    main()
