from __future__ import annotations

__all__ = [
    "get_editable_node_tree",
    "get_selected_nodes",
    "find_common_parent",
    "get_socket_location",
    "is_socket_hidden",
]

from typing import TYPE_CHECKING, cast, Iterable
import bpy

if TYPE_CHECKING:
    from bpy.types import (
        Node,
        NodeSocket,
        Context,
        SpaceNodeEditor,
        NodeTree,
        Preferences,
        Library,
        Nodes,
    )


# Code for node socket location adapted from: https://blender.stackexchange.com/a/252856/248376
def is_socket_hidden(socket: NodeSocket) -> bool:
    """Check if a node socket is hidden or disabled."""
    return socket.hide or not socket.enabled


def get_socket_location(
    socket: NodeSocket, is_input: bool, absolute: bool = True
) -> tuple[float, float] | None:
    """Calculate the screen position of a node socket.

    Args:
        socket: The node socket to locate
        is_input: True for input socket, False for output socket
        absolute: If True, return absolute coordinates

    Returns:
        (x, y) coordinates of the socket, or None if node/socket is hidden
    """

    X_OFFSET = -1.0
    Y_TOP = -34.0
    Y_BOTTOM = 16.0
    Y_OFFSET = 22.0
    # 2 offsets
    VEC_BOTTOM = 28.0
    VEC_TOP = 32.0

    def _is_tall(node: Node, socket: NodeSocket) -> bool:
        """Check if a socket should use tall spacing (vector sockets with visible values)."""
        if socket.type != "VECTOR":
            return False
        if socket.hide_value:
            return False
        if socket.is_linked:
            return False
        if node.type == "BSDF_PRINCIPLED" and socket.identifier == "Subsurface Radius":
            return False  # an exception confirms a rule?
        return True

    node = cast("Node", socket.node)
    scale = cast("Preferences", bpy.context.preferences).system.ui_scale
    try:
        if node.hide:
            return None
        node_location = node.location_absolute if absolute else node.location

        if not is_input:
            x = node_location.x + node.dimensions.x / scale + X_OFFSET
            y = node_location.y + Y_TOP
            for _, _socket in node.outputs.items():
                if is_socket_hidden(_socket):
                    if _socket.identifier == socket.identifier:
                        return None
                    continue
                if _socket.identifier == socket.identifier:
                    return x, y
                y -= Y_OFFSET
        else:
            x = node_location.x
            y = node_location.y - node.dimensions.y / scale + Y_BOTTOM
            for _, _socket in reversed(node.inputs.items()):
                if is_socket_hidden(_socket):
                    if _socket.identifier == socket.identifier:
                        return None
                    continue
                tall = _is_tall(node, _socket)
                y += VEC_BOTTOM * tall
                if _socket.identifier == socket.identifier:
                    return x, y
                y += Y_OFFSET + VEC_TOP * tall
    except Exception as e:
        print(f"Error getting socket location: {e}")
        return None

def get_editable_node_tree(
    context: Context | None = None, name: str | None = None
) -> NodeTree | str:
    if context is not None:
        # Check space type
        space = context.space_data
        if space is None:
            return "No active space found."
        if space.type != "NODE_EDITOR":
            return "Current editor is not a node editor."
        space = cast("SpaceNodeEditor", space)

        # Check node tree is editable and has nodes
        node_tree = space.edit_tree
        if node_tree is None:
            return "No node tree was found in the current node editor."
    elif name is not None:
        node_tree = bpy.data.node_groups.get(name, None)
        if node_tree is None:
            return f"Node tree '{name}' not found."
    else:
        return "Cannot find node tree."

    if not node_tree.is_editable:
        return "Current node tree is not editable."
    if cast("Library | None", node_tree.library) is not None:
        return (
            "Current node tree is linked from another .blend file and cannot be edited."
        )
    if cast("Nodes | None", node_tree.nodes) is None:
        return "Current node tree does not contain any nodes."

    return node_tree


def get_selected_nodes(
    context: Context,
    node_type: str | list[str] | None = None,
) -> list[Node] | str:
    node_tree = get_editable_node_tree(context=context)
    if isinstance(node_tree, str):
        return node_tree

    # Check nodes are selected
    selected_nodes = context.selected_nodes
    if not selected_nodes:
        return "No nodes selected."

    # Filter by node type if specified
    if node_type:
        if isinstance(node_type, str):
            node_type = [node_type]
        selected_nodes = [
            node for node in selected_nodes if node.bl_idname in node_type
        ]
        if not selected_nodes:
            return f"No selected nodes of type {node_type}."

    return selected_nodes


def find_common_parent(nodes: Iterable[Node]) -> Node | None:
    """Find the common parent node for a list of nodes, if any."""

    def get_parents(node: Node) -> list[Node]:
        parents: list[Node] = []
        parent = node.parent
        while parent:
            parents.append(parent)
            parent = parent.parent
        return parents

    parents = [get_parents(node) for node in nodes]
    if not parents:
        return None
    for parent in parents[0]:
        if all(parent in p for p in parents[1:]):
            return parent
    return None
