from __future__ import annotations

__all__ = ["HideResizeNode"]

from typing import TYPE_CHECKING
from ..utils.operators import BaseOperator, OperatorResult
from ..utils.nodes import get_selected_nodes

if TYPE_CHECKING:
    from bpy.types import Context


class HideResizeNode(BaseOperator):
    """Toggle: hide nodes and resize to minimum width"""

    bl_idname = "node.hide_resize_toggle"
    bl_label = "Hide and Resize"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def _poll(cls, context: Context):
        nodes = get_selected_nodes(context)
        if isinstance(nodes, str):
            return nodes

    def _execute(self, context: Context):
        # bpy.ops.node.hide_socket_toggle()
        # bpy.ops.node.hide_toggle()

        nodes = get_selected_nodes(context)
        if isinstance(nodes, str):
            return OperatorResult(
                return_type={"CANCELLED"},
                message_type={"ERROR"},
                message=nodes,
            )

        # Resize selected nodes to minimum width if hidden, else reset to default width
        for node in nodes:
            node.hide = not node.hide
            node.width = node.bl_width_min if node.hide else node.bl_width_default

        return OperatorResult(
            return_type={"FINISHED"},
        )