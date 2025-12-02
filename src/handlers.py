from __future__ import annotations

__all__ = [
    "register",
    "unregister",
]

from typing import TYPE_CHECKING, Callable, ParamSpec, TypeVar
from functools import partial
from bpy.app.handlers import persistent, depsgraph_update_post
from bpy.app.timers import register as register_timer
from .operators import classes
from .utils import preferences, operators, handlers

if TYPE_CHECKING:
    from bpy.types import Depsgraph, Scene

    P = ParamSpec("P")
    T = TypeVar("T", float, None)

    def persistent(func: Callable[P, T]) -> Callable[P, T]:
        return func


def call_operators(updated_trees: list[str]) -> None:
    global handler_operators
    prefs = preferences.get_preferences()
    if not prefs:
        return
    active_handlers = prefs.get_active_handlers()
    for cls in handler_operators:
        if cls.bl_idname in active_handlers:
            for node_tree_name in updated_trees:
                if cls.poll_node_tree(node_tree_name):
                    op = operators.get_operator_func(cls.bl_idname)
                    op(node_tree_name=node_tree_name)


@persistent
def depsgraph_handler(scene: Scene, depsgraph: Depsgraph) -> None:
    updated_trees: list[str] = []
    for update in depsgraph.updates[:]:
        if update.id and update.id.id_type == "NODETREE":
            updated_trees.append(update.id.name)

    if not updated_trees:
        return

    # Use timer for delayed processing
    register_timer(
        partial(call_operators, updated_trees=updated_trees),
        first_interval=0.3,
    )

handler_operators: tuple[type[handlers.BaseNodeTreeHandler], ...] = {
    cls for cls in classes if handlers.is_handler_operator(cls)
}  # type: ignore


def register():
    prefs = preferences.get_preferences()
    if not prefs:
        return
    prefs.register_handlers(handler_operators)
    depsgraph_update_post.append(depsgraph_handler)


def unregister():
    if depsgraph_handler in depsgraph_update_post:
        depsgraph_update_post.remove(depsgraph_handler)
