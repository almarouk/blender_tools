from __future__ import annotations

__all__ = ["RandomizeSeed", "ResetSeeds"]

from typing import TYPE_CHECKING, cast
from ..utils.operators import BaseOperator
from ..utils.handlers import BaseNodeTreeHandler
from ..utils.nodes import is_socket_hidden, get_socket_location, get_editable_node_tree
from ..properties import get_custom_properties

if TYPE_CHECKING:
    from bpy.types import (
        NodeTreeInterfaceSocket,
        NodeLink,
        NodeTree,
        Node,
        NodeSocket,
        NodeSocketInt,
        NodeGroupInput,
        FunctionNodeHashValue,
        Context,
    )

TAG = "AutoSeedRandomizer"

def check_node_tree(node_tree: NodeTree) -> str | None:
    if node_tree.interface is None:
        return "Node tree has no interface"

    # Check if the node tree has a seed input
    has_seed_input = False
    for item in node_tree.interface.items_tree:  # type: ignore
        if item.item_type == "SOCKET":
            item: NodeTreeInterfaceSocket
            if item.in_out == "INPUT" and item.name.strip().lower() == "seed":
                has_seed_input = True
                break

    if not has_seed_input:
        return "Node tree has no seed input"

    has_linked_seed_inputs = False
    for node in node_tree.nodes:
        if node.bl_idname == "NodeGroupInput":
            for socket in node.outputs:
                if socket.name.strip().lower() == "seed":
                    if not is_socket_hidden(socket) and socket.is_linked:
                        has_linked_seed_inputs = True
                    break
        if has_linked_seed_inputs:
            break

    if not has_linked_seed_inputs:
        return "No linked seed inputs found"

def get_seed_links(node_tree: NodeTree, poll: bool = False) -> list[NodeLink] | str:
    # Find all seed links in the node tree
    seed_links: list[NodeLink] = []
    for link in node_tree.links:
        if (
            link.from_socket
            and link.to_socket
            and link.to_node
            and link.from_node
            and link.from_node.bl_idname == "NodeGroupInput"
            and link.from_socket.name.strip().lower() == "seed"
            and link.to_node.bl_idname != "NodeReroute"
        ):  # and link.to_socket.name.strip().lower() == "seed":
            if not (
                link.to_node.bl_idname == "FunctionNodeHashValue"
                and link.to_node.label.endswith(TAG)
            ):
                if poll:
                    return []
                seed_links.append(link)

    if not seed_links:
        return "No seed links found"

    return seed_links

def get_tagged_nodes(node_tree: NodeTree) -> list[Node]:
    tagged_nodes: list[Node] = []
    for node in node_tree.nodes:
        if node.bl_idname == "FunctionNodeHashValue" and node.label.endswith(TAG):
            tagged_nodes.append(node)
    return tagged_nodes

class RandomizeSeed(BaseNodeTreeHandler):
    """Randomize the seed value for the node tree."""

    bl_idname = "node.randomize_seed"
    bl_label = "Randomize Seed"
    bl_description = "Randomize the seed value for the node tree."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def _poll_node_tree(cls, node_tree: NodeTree):
        check = check_node_tree(node_tree)
        if isinstance(check, str):
            return check
        links = get_seed_links(node_tree, poll=True)
        if isinstance(links, str):
            return links
        return None

    def _execute_node_tree(self, node_tree: NodeTree):
        links = get_seed_links(node_tree)
        if isinstance(links, str):
            return links

        props = get_custom_properties(node_tree)
        if props is None:
            return "Failed to get custom properties for node tree."

        counter = props.auto_seed_counter
        for link in links:
            from_node: NodeGroupInput = link.from_node  # type: ignore
            to_node: Node = link.to_node  # type: ignore
            to_socket: NodeSocket = link.to_socket  # type: ignore
            # Create Random Value node
            random_node: FunctionNodeHashValue = node_tree.nodes.new(
                type="FunctionNodeHashValue"
            )  # type: ignore
            random_node.hide = True
            random_node.select = False
            random_node.width = random_node.bl_width_min
            location = get_socket_location(to_socket, True)
            if location is None:
                location = (
                    to_node.location_absolute.x,
                    to_node.location_absolute.y,
                )
            random_node.location = (
                location[0] - random_node.width - 25,
                location[1] + 15,
            )
            random_node.label = f"{counter} {TAG}"
            random_node.data_type = "INT"
            cast("NodeSocketInt", random_node.inputs["Value"]).default_value = counter
            counter = counter + 1
            if to_node.parent:
                random_node.parent = to_node.parent  # type: ignore

            # Add a Group Input Node with Seed shown only
            group_input_node: NodeGroupInput = node_tree.nodes.new(
                type="NodeGroupInput"
            )  # type: ignore
            group_input_node.hide = True
            group_input_node.select = False
            group_input_node.width = group_input_node.bl_width_min
            group_input_node.label = "Seed"
            for socket_out in group_input_node.outputs:
                if socket_out.name.strip().lower() == "seed":
                    socket_out.hide = False
                else:
                    socket_out.hide = True
            group_input_node.location = (
                random_node.location_absolute.x - group_input_node.width - 25,
                random_node.location_absolute.y,
            )
            if to_node.parent:
                group_input_node.parent = to_node.parent  # type: ignore

            # Create new links through the Random Value node
            node_tree.links.new(
                group_input_node.outputs["Seed"],
                random_node.inputs["Seed"],
                verify_limits=True,
            )
            node_tree.links.new(
                random_node.outputs["Hash"], to_socket, verify_limits=True
            )

            # # Remove the original link
            # node_tree.links.remove(link)

            # Check if group input node has no links, remove it
            if not any(socket.is_linked for socket in from_node.outputs):
                node_tree.nodes.remove(from_node)

        props.auto_seed_counter = counter

class ResetSeeds(BaseOperator):
    """Reset all seed randomizers in the node tree."""

    bl_idname = "node.reset_seeds"
    bl_label = "Reset Seeds"
    bl_description = "Reset all seed randomizers in the node tree."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def _poll(cls, context: Context):
        node_tree = get_editable_node_tree(context=context)
        if isinstance(node_tree, str):
            return node_tree
        props = get_custom_properties(node_tree)
        if props is None:
            return "Failed to get custom properties for node tree."
        counter = props.auto_seed_counter
        if counter == 0:
            return "No seeds to reset."

    def _execute(self, context: Context):
        node_tree = get_editable_node_tree(context=context)
        if isinstance(node_tree, str):
            return node_tree

        props = get_custom_properties(node_tree)
        if props is None:
            return "Failed to get custom properties for node tree."
        # props.auto_seed_counter = 0
        counter = 0

        tagged_nodes = get_tagged_nodes(node_tree)
        for node in tagged_nodes:
            node.label = f"{counter} {TAG}"
            cast("NodeSocketInt", node.inputs["Value"]).default_value = counter
            counter = counter + 1

        props.auto_seed_counter = counter

        return None
