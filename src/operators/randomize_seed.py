from __future__ import annotations

__all__ = ["RandomizeSeed"]

from typing import TYPE_CHECKING
from ..utils.handlers import BaseNodeTreeHandler
from ..utils.nodes import is_socket_hidden, get_socket_location
from ..utils.properties import get_custom_properties

if TYPE_CHECKING:
    from bpy.types import (
        NodeTreeInterfaceSocket,
        NodeLink,
        NodeTree,
        Node,
        NodeSocket,
        NodeSocketInt,
        NodeGroupInput,
        FunctionNodeRandomValue,
        FunctionNodeInputInt,
    )

TAG = "AutoSeedRandomizer"


def get_seed_links(node_tree: NodeTree) -> list[NodeLink] | str:
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
                link.to_node.bl_idname == "FunctionNodeRandomValue"
                and link.to_node.label == TAG
            ):
                seed_links.append(link)

    if not seed_links:
        return "No seed links found"

    return seed_links


class RandomizeSeed(BaseNodeTreeHandler):
    """Randomize the seed value for the node tree."""

    bl_idname = "node.randomize_seed"
    bl_label = "Randomize Seed"
    bl_description = "Randomize the seed value for the node tree."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def _poll_node_tree(cls, node_tree: NodeTree):
        result = get_seed_links(node_tree)
        if isinstance(result, str):
            return result

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
            random_node: FunctionNodeRandomValue = node_tree.nodes.new(
                type="FunctionNodeRandomValue"
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
            random_node.label = TAG
            random_node.data_type = "INT"
            if to_node.parent:
                random_node.parent = to_node.parent  # type: ignore

            # Set default range for integer random values
            socket: NodeSocketInt = random_node.inputs["Min"]  # type: ignore
            socket.default_value = 0
            socket: NodeSocketInt = random_node.inputs["Max"]  # type: ignore
            socket.default_value = 1000000

            # Add an Integer Value Node
            int_value_node: FunctionNodeInputInt = node_tree.nodes.new(
                type="FunctionNodeInputInt"
            )  # type: ignore
            int_value_node.hide = True
            int_value_node.select = False
            int_value_node.width = int_value_node.bl_width_min
            int_value_node.location = (
                random_node.location_absolute.x - int_value_node.width - 25,
                random_node.location_absolute.y,
            )
            int_value_node.label = str(counter)
            int_value_node.integer = counter
            counter = counter + 1
            if to_node.parent:
                int_value_node.parent = to_node.parent  # type: ignore

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
            # group_input_node.location = (random_node.location.x - group_input_node.width - 25, int_value_node.location.y - int_value_node.dimensions.y / bpy.context.preferences.system.ui_scale - 5)
            group_input_node.location = (
                random_node.location_absolute.x - group_input_node.width - 25,
                int_value_node.location_absolute.y - int_value_node.bl_height_min - 5,
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
                random_node.outputs["Value"], to_socket, verify_limits=True
            )
            node_tree.links.new(
                int_value_node.outputs["Integer"],
                random_node.inputs["ID"],
                verify_limits=True,
            )

            # # Remove the original link
            # node_tree.links.remove(link)

            # Check if group input node has no links, remove it
            if not any(socket.is_linked for socket in from_node.outputs):
                node_tree.nodes.remove(from_node)

        props.auto_seed_counter = counter
