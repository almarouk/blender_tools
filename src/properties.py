from __future__ import annotations

__all__ = ["register", "unregister", "get_custom_properties"]

from typing import TYPE_CHECKING, overload
from bpy.types import NodeTree, PropertyGroup
from bpy.props import PointerProperty, IntProperty  # type: ignore
from bpy.utils import register_class, unregister_class
from types import MappingProxyType
from .utils import CUSTOM_PROPS_NAME

if TYPE_CHECKING:
    from bpy.types import ID


class AutoSeedCounterProp(PropertyGroup):
    auto_seed_counter: IntProperty(  # type: ignore
        name="Auto Seed Counter",
        description="Auto-incremented counter for seed value generation",
        default=0,
        options={"HIDDEN"},
    )
    if TYPE_CHECKING:
        auto_seed_counter: int = 0

property_groups_to_register: MappingProxyType[type[ID], type[PropertyGroup]] = (
    MappingProxyType(
        {
            NodeTree: AutoSeedCounterProp,
        }
    )
)


@overload
def get_custom_properties(object: NodeTree) -> AutoSeedCounterProp | None: ...
@overload
def get_custom_properties(object: ID) -> PropertyGroup | None: ...
def get_custom_properties(object: ID) -> PropertyGroup | None:
    """Get the custom properties of the object, if they exist."""
    return getattr(object, CUSTOM_PROPS_NAME, None)


def register():
    for prop in set(property_groups_to_register.values()):
        if not getattr(prop, "is_registered", False):
            register_class(prop)

    for cls, prop in property_groups_to_register.items():
        setattr(
            cls,
            CUSTOM_PROPS_NAME,
            PointerProperty(type=prop, options={"HIDDEN"}),
        )


def unregister():
    for cls in property_groups_to_register.keys():
        if hasattr(cls, CUSTOM_PROPS_NAME):
            delattr(cls, CUSTOM_PROPS_NAME)

    for prop in reversed(list(set(property_groups_to_register.values()))):
        if getattr(prop, "is_registered", False):
            unregister_class(prop)
