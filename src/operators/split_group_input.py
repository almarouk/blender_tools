from __future__ import annotations

__all__ = ["SplitMergeGroupInput"]

from typing import cast, TYPE_CHECKING
from bpy.props import BoolProperty, EnumProperty  # type: ignore
from ..utils.operators import BaseOperator, OperatorResult
from ..utils.nodes import get_selected_nodes, find_common_parent
from enum import StrEnum, auto
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from bpy.types import (
        Context,
        NodeGroupInput,
        NodeLink,
        NodeTree,
        SpaceNodeEditor,
        Node,
        Event,
    )


class Mode(StrEnum):
    SPLIT_ALL = auto()
    DEST_NODE = auto()
    SOURCE_SOCKET = auto()
    MERGE_ALL = auto()


@dataclass
class Location:
    parent: Node | None
    node: Node | None
    x: float
    y: float


@dataclass
class LinksGroup:
    location: Location | None = None
    links: list[tuple[int, NodeLink]] = field(default_factory=list)  # type: ignore


class SplitMergeGroupInput(BaseOperator):
    """Split/Merge Group Input nodes"""

    bl_idname = "node.split_merge_group_input"
    bl_label = "Split/Merge"
    bl_description = "Split/Merge Group Input nodes"
    bl_options = {"REGISTER", "UNDO"}

    process_individually: BoolProperty(  # type: ignore
        name="Process Individually",
        description="Process selected Group Input nodes individually, otherwise they're merged before processing",
        default=False,
    )

    mode: EnumProperty(  # type: ignore
        name="Mode",
        description="How to split/merge the Group Input nodes",
        items=[
            (Mode.SPLIT_ALL, "Split All", "Create one Group Input node per link"),
            (
                Mode.DEST_NODE,
                "Destination Node",
                "Create one Group Input node per destination node",
            ),
            (
                Mode.SOURCE_SOCKET,
                "Source Socket",
                "Create one Group Input node per source socket",
            ),
            (
                Mode.MERGE_ALL,
                "Merge All",
                "Merge all selected Group Input nodes into one",
            ),
        ],
        default=Mode.SPLIT_ALL,
    )

    @classmethod
    def _poll(cls, context: Context):
        result = get_selected_nodes(
            context,
            node_type="NodeGroupInput",
        )
        if isinstance(result, str):
            return result

    def _execute(self, context: Context):
        nodes = get_selected_nodes(context, node_type="NodeGroupInput")
        if isinstance(nodes, str):
            return OperatorResult(
                return_type={"CANCELLED"},
                message_type={"ERROR"},
                message=nodes,
            )

        node_tree = cast(
            "NodeTree", cast("SpaceNodeEditor", context.space_data).edit_tree
        )

        # TODO: filter out nodes that would be unchanged by the operation

        mappings: list[dict[Node | int | None, LinksGroup]] = []
        locations: dict[Node | None, Location] = {}
        x_offset = -nodes[0].bl_width_default - 25
        node_type = nodes[0].bl_idname
        for node in nodes:
            node = cast("NodeGroupInput", node)

            if not mappings or (
                self.process_individually  # type: ignore
                and self.mode in {Mode.SOURCE_SOCKET, Mode.DEST_NODE}  # type: ignore
            ):
                mappings.append({})
            mapping = mappings[-1]

            for socket_index, socket in enumerate(node.outputs):
                if socket.links:
                    for link in socket.links:
                        if not link.to_node:
                            continue
                        group_key = None
                        location = None
                        if self.mode == Mode.MERGE_ALL:  # type: ignore
                            group_key = None
                            location = locations.setdefault(
                                None,
                                Location(None, None, node.location.x, node.location.y),
                            )
                        elif self.mode == Mode.SOURCE_SOCKET:  # type: ignore
                            group_key = socket_index
                            if self.process_individually:  # type: ignore
                                location = locations.setdefault(
                                    node,
                                    Location(
                                        node.parent,
                                        node,
                                        node.location.x,
                                        node.location.y,
                                    ),
                                )
                            else:
                                location = locations.setdefault(
                                    None,
                                    Location(
                                        None,
                                        None,
                                        node.location.x,
                                        node.location.y,
                                    ),
                                )
                        elif self.mode == Mode.DEST_NODE:  # type: ignore
                            group_key = link.to_node
                            location = locations.setdefault(
                                link.to_node,
                                Location(
                                    link.to_node.parent,
                                    link.to_node,
                                    link.to_node.location.x + x_offset,
                                    link.to_node.location.y,
                                ),
                            )
                        mapping.setdefault(
                            group_key, LinksGroup(location=location)
                        ).links.append((socket_index, link))

        for mapping in mappings:
            for group_key, group in mapping.items():
                if not group.links:
                    continue
                location = group.location
                parent = location.parent if location else None
                location = cast("Location", location)
                if self.mode != Mode.SPLIT_ALL:  # type: ignore
                    connected_nodes: set[Node] = {
                        link.to_node for _, link in group.links
                    }  # type: ignore
                    if not location.node or len(connected_nodes) == 1:
                        # find left most node
                        left_most_node = min(
                            connected_nodes,
                            key=lambda n: n.location.x,
                        )
                        location = locations.setdefault(
                            left_most_node,
                            Location(
                                left_most_node.parent,
                                left_most_node,
                                left_most_node.location.x + x_offset,
                                left_most_node.location.y,
                            ),
                        )
                        parent = find_common_parent(connected_nodes)

                new_node: Node | None = None
                for socket_index, link in group.links:
                    if not link.to_node:
                        continue
                    if not new_node or self.mode == Mode.SPLIT_ALL:  # type: ignore
                        # Create a new Group Input node
                        new_node = node_tree.nodes.new(type=node_type)
                        # new_node.hide = self.mode == Mode.LINK or len(group.links) == 1
                        new_node.hide = True
                        if self.mode == Mode.SPLIT_ALL:  # type: ignore
                            location = locations.setdefault(
                                link.to_node,
                                Location(
                                    link.to_node.parent,
                                    link.to_node,
                                    link.to_node.location.x + x_offset,
                                    link.to_node.location.y,
                                ),
                            )
                            parent = link.to_node.parent
                        if parent:
                            new_node.parent = parent
                        new_node.location = [location.x, location.y]
                        new_node.select = True

                        # Hide unconnected outputs
                        for output in new_node.outputs:
                            output.hide = True

                    new_node.outputs[socket_index].hide = False
                    to_socket = link.to_socket
                    if not to_socket:
                        continue
                    node_tree.links.remove(link)
                    node_tree.links.new(
                        new_node.outputs[socket_index],
                        to_socket,
                        verify_limits=True,
                    )

                    if self.mode == Mode.SPLIT_ALL:  # type: ignore
                        # location.y -= new_node.dimensions.y / bpy.context.preferences.system.ui_scale
                        location.y -= new_node.bl_height_min
                new_node = cast("Node", new_node)
                if self.mode != Mode.SPLIT_ALL:  # type: ignore
                    # location.y -= new_node.dimensions.y / bpy.context.preferences.system.ui_scale
                    location.y -= new_node.bl_height_min

        for node in nodes:
            node_tree.nodes.remove(node)

        return OperatorResult(
            return_type={"FINISHED"},
        )

    def invoke(self, context: Context, event: Event):  # type: ignore
        wm = context.window_manager
        if not wm:
            self.report({"ERROR"}, "No window manager found.")
            return {"CANCELLED"}
        return wm.invoke_props_popup(self, event)

    def draw(self, context: Context) -> None:
        layout = self.layout
        if not layout:
            return
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(self, "process_individually")
        layout.prop(self, "mode", expand=True)
