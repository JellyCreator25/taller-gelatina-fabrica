"""Registro de adaptadores, en el orden en que se ejecutan sus acciones. Cada `canal` es el id del canal en difusion/canales.json."""
from .bluesky import Bluesky
from .cloudflare import CloudflarePages
from .discord import Discord
from .indexnow import IndexNow
from .itch import ItchButler
from .mastodon import Mastodon
from .telegram import Telegram
from .youtube import YouTube

ADAPTADORES = [CloudflarePages(), IndexNow(), Bluesky(), Mastodon(), Telegram(), Discord(), YouTube(), ItchButler()]
