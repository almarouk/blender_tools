"""
Menu definitions for the node editor.
"""

from __future__ import annotations

__all__ = ["register", "unregister", "OperatorMenu"]

from typing import TYPE_CHECKING
from bpy.types import Menu, NODE_MT_context_menu
from bpy.utils import register_class, unregister_class
from ..operators import classes
from ..utils.handlers import is_handler_operator

if TYPE_CHECKING:
    from bpy.types import Context


class OperatorMenu(Menu):
    bl_idname = "NODE_MT_NodeTools"
    bl_label = "Node Tools"
    # bl_description = "Various tools for nodes"

    @classmethod
    def poll(cls, context: Context) -> bool:
        return any(
            not is_handler_operator(cls) and cls.poll(context) for cls in classes
        )

    def draw(self, context: Context) -> None:
        layout = self.layout
        if not layout:
            return
        layout.operator_context = "INVOKE_DEFAULT"
        for cls in classes:
            if not is_handler_operator(cls) and cls.poll(context):
                layout.operator(cls.bl_idname)


def _draw_node_context_menu(self: Menu, context: Context) -> None:
    if not self.layout:
        return
    col = self.layout.column(align=True)
    if OperatorMenu.poll(context):
        col.menu(OperatorMenu.bl_idname, text=OperatorMenu.bl_label)
    col.separator()

_classes: tuple[type[Menu], ...] = (OperatorMenu,)

def register():
    for cls in _classes:
        register_class(cls)
    NODE_MT_context_menu.prepend(_draw_node_context_menu)  # pyright: ignore[reportUnknownMemberType]


def unregister():
    NODE_MT_context_menu.remove(_draw_node_context_menu)  # pyright: ignore[reportUnknownMemberType]
    for cls in reversed(_classes):
        unregister_class(cls)
