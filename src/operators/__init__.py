"""
Operators for the node tree.
"""

from __future__ import annotations

__all__ = [
    "register",
    "unregister",
    "classes",
    "SplitMergeGroupInput",
    "HideRenameSingleOutputNode",
    "HideResizeNode",
    "MatchGroupInterface",
    "RandomizeSeed",
]

from typing import TYPE_CHECKING
from bpy.utils import register_class, unregister_class
from .resize_node import HideResizeNode
from .split_group_input import SplitMergeGroupInput
from .rename_node import HideRenameSingleOutputNode
from .randomize_seed import RandomizeSeed
from .match_group_interface import MatchGroupInterface

if TYPE_CHECKING:
    from ..utils.operators import BaseOperator

classes: tuple[type[BaseOperator], ...] = (
    HideResizeNode,
    SplitMergeGroupInput,
    HideRenameSingleOutputNode,
    MatchGroupInterface,
    RandomizeSeed,
)


def register():
    for cls in classes:
        register_class(cls)


def unregister():
    for cls in reversed(classes):
        unregister_class(cls)
