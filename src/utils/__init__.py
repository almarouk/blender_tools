from __future__ import annotations

from typing import cast

PACKAGE = cast(str, __package__).rsplit(".", 2)[0]
ADDON_LABEL = "Node Tools"
ADDON_NAME = "NodeTools"
CUSTOM_PROPS_NAME = "node_tools"
