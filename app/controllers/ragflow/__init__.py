from fastapi import APIRouter
from .chats import view as chats_view
from .webhook import view as webhook_view

# Package-level router includes sub-routers (each defines their own prefixes)
view = APIRouter()
view.include_router(chats_view)
view.include_router(webhook_view)

__all__ = ["view"]
