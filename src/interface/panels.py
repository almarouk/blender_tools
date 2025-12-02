from __future__ import annotations

__all__ = ["register", "unregister"]

from typing import TYPE_CHECKING
from bpy.types import Panel
from bpy.utils import register_class, unregister_class
from ..utils import ADDON_LABEL
from ..utils.nodes import get_node_tree
from ..utils.preferences import get_preferences
from .menus import OperatorMenu

if TYPE_CHECKING:
    from bpy.types import Context


class PanelBase(Panel):
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = ADDON_LABEL
    @classmethod
    def poll(cls, context: Context) -> bool:
        node_tree = get_node_tree(context)
        return not isinstance(node_tree, str)


class PreferencesPanel(PanelBase):
    bl_label = "Preferences"
    bl_idname = "NODE_PT_node_tools_preferences"

    def draw(self, context: Context) -> None:
        layout = self.layout
        if not layout:
            return
        prefs = get_preferences(context)
        if not prefs:
            return
        prefs.draw_preferences(layout, compact=True)


class OperatorPanel(PanelBase):
    bl_label = "Operators"
    bl_idname = "NODE_PT_node_tools_operators"

    @classmethod
    def poll(cls, context: Context) -> bool:
        return super().poll(context) and OperatorMenu.poll(context)

    def draw(self, context: Context) -> None:
        layout = self.layout
        if not layout:
            return
        if OperatorMenu.poll(context):
            col = layout.column(align=True)
            col.menu_contents(OperatorMenu.bl_idname)

classes: tuple[type[PanelBase], ...] = (
    OperatorPanel,
    PreferencesPanel,
)

def register():
    for cls in classes:
        register_class(cls)


def unregister():
    for cls in reversed(classes):
        unregister_class(cls)
