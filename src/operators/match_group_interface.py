from __future__ import annotations

__all__ = ["MatchGroupInterface"]

from typing import cast, TYPE_CHECKING, Iterable
from ..utils.operators import BaseOperator, OperatorResult
from ..utils.nodes import (
    get_selected_nodes,
    check_nodetree_editable,
)

if TYPE_CHECKING:
    from bpy.types import (
        Context,
        NodeGroup,
        NodeTree,
        NodeTreeInterface,
        NodeTreeInterfaceItem,
        NodeTreeInterfaceSocket,
        NodeTreeInterfacePanel,
        bpy_prop_collection,
        SpaceNodeEditor,
    )

    class _NodeTreeInterfaceItem(NodeTreeInterfaceItem):
        parent: _NodeTreeInterfacePanel  # type: ignore

    class _NodeTreeInterface(NodeTreeInterface):
        items_tree: bpy_prop_collection[_NodeTreeInterfaceItem]  # type: ignore

    class _NodeTree(NodeTree):
        interface: _NodeTreeInterface  # type: ignore

    class _NodeGroup(NodeGroup):
        node_tree: _NodeTree  # type: ignore

    class _NodeTreeInterfacePanel(NodeTreeInterfacePanel):
        parent: _NodeTreeInterfacePanel  # type: ignore

    class _NodeTreeInterfaceSocket(NodeTreeInterfaceSocket):
        parent: _NodeTreeInterfacePanel  # type: ignore


def get_editable_nodegroups(context: Context) -> Iterable[_NodeGroup] | str:
    nodes = get_selected_nodes(
        context,
        node_type=[
            "CompositorNodeGroup",
            "GeometryNodeGroup",
            "ShaderNodeGroup",
            "TextureNodeGroup",
        ],
    )
    if isinstance(nodes, str):
        return nodes
    nodes = cast("list[NodeGroup]", nodes)
    nodes = [
        node
        for node in nodes
        if node.node_tree
        and check_nodetree_editable(node.node_tree) is None
        and node.node_tree.interface
    ]
    if not nodes:
        return "No editable Group nodes selected."
    return nodes  # type: ignore


def copy_socket_properties(
    source: NodeTreeInterfaceSocket, target: NodeTreeInterfaceSocket
) -> None:
    target.attribute_domain = source.attribute_domain
    target.default_attribute_name = source.default_attribute_name
    target.default_input = source.default_input
    target.description = source.description
    target.hide_in_modifier = source.hide_in_modifier
    target.hide_value = source.hide_value
    target.is_panel_toggle = source.is_panel_toggle
    target.menu_expanded = source.menu_expanded
    target.name = source.name
    target.socket_type = source.socket_type
    target.structure_type = source.structure_type

    if target.socket_type == "NodeSocketMenu":
        return

    attrs = ["default_value", "min_value", "max_value", "subtype", "dimensions"]
    for attr in attrs:
        if hasattr(target, attr) and hasattr(source, attr):
            if getattr(target, attr) is type(getattr(source, attr)):
                setattr(target, attr, getattr(source, attr))

def is_panel_empty(panel: _NodeTreeInterfacePanel) -> bool:
    for item in panel.interface_items:
        if item.item_type == "PANEL":
            item = cast("_NodeTreeInterfacePanel", item)
            if not is_panel_empty(item):
                return False
        else:
            return False
    return True

class MatchGroupInterface(BaseOperator):
    """Match a Group Node's interface to the Group Input/Output nodes connected to it"""

    bl_idname = "node.match_group_interface"
    bl_label = "Match Group Interface"
    bl_description = (
        "Match a Group Node's interface to the Group Input/Output nodes connected to it"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def _poll(cls, context: Context):
        result = get_editable_nodegroups(context)
        if isinstance(result, str):
            return result

    def _execute(self, context: Context):
        nodes = get_editable_nodegroups(context)
        if isinstance(nodes, str):
            return OperatorResult(
                return_type={"CANCELLED"},
                message_type={"ERROR"},
                message=nodes,
            )

        node_tree = cast(
            "NodeTree", cast("SpaceNodeEditor", context.space_data).edit_tree
        )
        node_tree = cast("_NodeTree", node_tree)

        # Map source socket IDs to the set of panel IDs they are contained in
        source_id_to_panels: dict[str, set[int]] = {}
        for source_item in node_tree.interface.items_tree:
            if source_item.item_type != "SOCKET":
                continue
            source_item = cast("NodeTreeInterfaceSocket", source_item)
            parents: set[int] = set()
            parent = source_item.parent
            while parent:
                parents.add(parent.persistent_uid)
                parent = parent.parent
            source_id_to_panels[source_item.identifier] = parents

        # Process each node individually
        for node in nodes:
            # Map target socket IDs to their corresponding interface items
            target_id_to_interface: dict[str, NodeTreeInterfaceSocket] = {
                cast("NodeTreeInterfaceSocket", item).identifier: cast(
                    "NodeTreeInterfaceSocket", item
                )
                for item in node.node_tree.interface.items_tree
                if item.item_type == "SOCKET"
            }

            # Map source socket IDs to target socket IDs
            sockets_map: dict[str, str] = {}
            # Set of panel IDs to create in the target node tree
            panels: set[int] = set()
            for link in node_tree.links:
                if not (
                    link.from_node
                    and link.to_node
                    and link.from_socket
                    and link.to_socket
                    and link.from_node.bl_idname == "NodeGroupInput"
                    and link.to_node == node
                ):
                    continue
                sockets_map[link.from_socket.identifier] = link.to_socket.identifier
                panels.update(source_id_to_panels[link.from_socket.identifier])

            # Map source panel IDs to created target panels
            panels_map: dict[int, NodeTreeInterfacePanel] = {
                0: node.node_tree.interface.new_panel("Root_temp")
            }
            for source_item in node_tree.interface.items_tree:
                if source_item.item_type == "PANEL":
                    source_item = cast("_NodeTreeInterfacePanel", source_item)
                    if source_item.persistent_uid not in panels:
                        continue
                    target_item = node.node_tree.interface.new_panel(
                        name=source_item.name,
                        description=source_item.description,
                        default_closed=source_item.default_closed,
                    )
                    panels_map[source_item.persistent_uid] = target_item
                else:
                    source_item = cast("_NodeTreeInterfaceSocket", source_item)
                    target_id = sockets_map.get(source_item.identifier)
                    if not target_id:
                        continue
                    target_item = target_id_to_interface[target_id]
                    copy_socket_properties(source_item, target_item)
                node.node_tree.interface.move_to_parent(
                    target_item,
                    panels_map[source_item.parent.persistent_uid],
                    source_item.position,
                )

            # Remove temporary root panel
            node.node_tree.interface.remove(panels_map[0], move_content_to_parent=True)
            del panels_map
            del target_id_to_interface
            # Remove empty panels
            panels_to_delete = [
                item
                for item in node.node_tree.interface.items_tree
                if item.item_type == "PANEL"
                and is_panel_empty(cast("_NodeTreeInterfacePanel", item))
            ]
            for item in reversed(panels_to_delete):
                node.node_tree.interface.remove(item, move_content_to_parent=False)

        return OperatorResult(
            return_type={"FINISHED"},
        )