from __future__ import annotations

__all__ = ["BaseNodeTreeHandler", "is_handler_operator"]

from typing import TYPE_CHECKING
from abc import abstractmethod
from .nodes import get_editable_node_tree
from .operators import BaseOperator, OperatorResult
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
    def _execute_node_tree(self, node_tree: NodeTree) -> OperatorResult: ...

    @classmethod
    def _poll(cls, context: Context) -> str | None:
        # return "Not available as a direct operator. Use as a handler."
        pass

    def _execute(self, context: Context):
        is_called_as_handler = bool(self.node_tree_name)
        if is_called_as_handler:
            node_tree = get_editable_node_tree(name=self.node_tree_name)
        else:
            node_tree = get_editable_node_tree(context=context)
        if isinstance(node_tree, str):
            if is_called_as_handler:
                return OperatorResult(
                    return_type={"CANCELLED"},
                )
            else:
                return OperatorResult(
                    return_type={"CANCELLED"},
                    message_type={"ERROR"},
                    message=node_tree,
                )

        res = self._execute_node_tree(node_tree)
        if is_called_as_handler:
            res.message_type = None
            res.message = None
            # self.report({"INFO"}, f"Handler executed: {self.bl_label}")
        return res