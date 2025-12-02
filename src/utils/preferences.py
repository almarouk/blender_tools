from __future__ import annotations

__all__ = ["get_preferences"]

from typing import TYPE_CHECKING, cast
import bpy
from . import PACKAGE

if TYPE_CHECKING:
    from bpy.types import Context
    from ..preferences import Preferences


def get_preferences(context: Context | None = None) -> Preferences | None:
    if context is None:
        context = bpy.context
    if context.preferences is None:
        return None
    addon = context.preferences.addons.get(PACKAGE)
    if addon is None:
        return None
    return cast("Preferences | None", addon.preferences)
