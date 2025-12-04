from __future__ import annotations

__all__ = ["HideRenameSingleOutputNode"]

from typing import TYPE_CHECKING
from ..utils.handlers import BaseNodeTreeHandler
from ..utils.operators import OperatorResult
from ..utils.nodes import is_socket_hidden

if TYPE_CHECKING:
    from bpy.types import Node, NodeTree


def get_nodes_with_single_output(node_tree: NodeTree) -> list[tuple[Node, str]] | str:
    nodes: list[tuple[Node, str]] = []
    for node in node_tree.nodes:
        # if node.label:
        #     continue
        if any(not is_socket_hidden(socket) for socket in node.inputs):
            continue
        sockets = [socket for socket in node.outputs if not is_socket_hidden(socket)]
        if len(sockets) != 1:
            continue
        if sockets[0].name == node.label:
            continue
        nodes.append((node, sockets[0].name))

    if not nodes:
        return "No nodes to process."

    return nodes


class HideRenameSingleOutputNode(BaseNodeTreeHandler):
    """Hides single output nodes and sets their label to the output socket name."""

    bl_idname = "node.hide_rename_single_output_node"
    bl_label = "Hide and Rename"
    bl_description = (
        "Hide single output nodes and set their label to the output socket name"
    )
    bl_options = {"REGISTER", "UNDO"}

    def _execute_node_tree(self, node_tree: NodeTree):
        nodes = get_nodes_with_single_output(node_tree)
        if isinstance(nodes, str):
            return OperatorResult(
                return_type={"CANCELLED"},
                message_type={"ERROR"},
                message=nodes,
            )

        for node, new_label in nodes:
            node.label = new_label
            node.hide = True
            node.location.x += node.width - node.bl_width_min
            node.width = node.bl_width_min

        return OperatorResult(
            return_type={"FINISHED"},
        )