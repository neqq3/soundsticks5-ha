"""Start the SoundSticks Audio App."""

from aiohttp import web

from .config import load_config
from .server import SoundSticksAudioServer


async def create_app() -> web.Application:
    config = load_config()
    return await SoundSticksAudioServer(config).start()


if __name__ == "__main__":
    config = load_config()
    web.run_app(create_app(), host="0.0.0.0", port=config.port)
