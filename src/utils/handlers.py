from __future__ import annotations

__all__ = ["BaseNodeTreeHandler", "is_handler_operator"]

from typing import TYPE_CHECKING, cast
from abc import abstractmethod
from .nodes import get_editable_node_tree
from .operators import BaseOperator
from bpy.props import StringProperty  # type: ignore

if TYPE_CHECKING:
    from bpy.types import Context, NodeTree

def is_handler_operator(cls: type[BaseOperator]) -> bool:
    return issubclass(cls, BaseNodeTreeHandler)


class BaseNodeTreeHandler(BaseOperator):
    node_tree_name: StringProperty(  # type: ignore
        name="Node Tree Name",
        description="Name of the node tree to operate on (overrides context)",
        default="",
        options={"SKIP_SAVE", "HIDDEN"},
    )
    if TYPE_CHECKING:
        node_tree_name: str = ""

    @abstractmethod
    def _execute_node_tree(
        self, node_tree: NodeTree
    ) -> tuple[set[str], str] | set[str] | str | None: ...

    @classmethod
    @abstractmethod
    def _poll_node_tree(cls, node_tree: NodeTree) -> str | None: ...

    @classmethod
    def poll_node_tree(cls, node_tree_name: str) -> bool:
        node_tree = get_editable_node_tree(name=node_tree_name)
        msg = (
            node_tree if isinstance(node_tree, str) else cls._poll_node_tree(node_tree)
        )
        if isinstance(msg, str):
            cls.poll_message_set(msg)
            return False
        return True

    @classmethod
    def _poll(cls, context: Context):
        pass
        # node_tree = get_node_tree(context)
        # if isinstance(node_tree, str):
        #     return node_tree
        # msg = cls._poll_node_tree(node_tree)
        # if isinstance(msg, str):
        #     return msg

    def _execute(self, context: Context):
        if self.node_tree_name:
            node_tree = get_editable_node_tree(name=self.node_tree_name)
        else:
            node_tree = get_editable_node_tree(context=context)
        msg = (
            node_tree if isinstance(node_tree, str) else self._poll_node_tree(node_tree)
        )
        if isinstance(msg, str):
            self.poll_message_set(msg)
            return msg
        self._execute_node_tree(cast("NodeTree", node_tree))
