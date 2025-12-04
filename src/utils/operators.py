from __future__ import annotations

__all__ = ["BaseOperator", "get_operator_func", "OperatorResult"]

from typing import TYPE_CHECKING, cast, Literal
from abc import abstractmethod
from dataclasses import dataclass
from bpy.types import Operator
import bpy

if TYPE_CHECKING:
    from bpy.types import Context

    OperatorReturnType = set[
        Literal[
            "RUNNING_MODAL",  # Running Modal.Keep the operator running with blender.
            "CANCELLED",  # Cancelled.The operator exited without doing anything, so no undo entry should be pushed.
            "FINISHED",  # Finished.The operator exited after completing its action.
            "PASS_THROUGH",  # Pass Through.Do nothing and pass the event on.
            "INTERFACE",  # Interface.Handled but not executed (popup menus).
        ]
    ]

    WmReportType = set[
        Literal[
            "DEBUG",  # Debug.
            "INFO",  # Info.
            "OPERATOR",  # Operator.
            "PROPERTY",  # Property.
            "WARNING",  # Warning.
            "ERROR",  # Error.
            "ERROR_INVALID_INPUT",  # Invalid Input.
            "ERROR_INVALID_CONTEXT",  # Invalid Context.
            "ERROR_OUT_OF_MEMORY",  # Out of Memory.
        ]
    ]


def get_operator_func(idname: str):
    module, func = idname.split(".", 1)
    return getattr(getattr(bpy.ops, module), func)

@dataclass
class OperatorResult:
    return_type: set[str]
    message_type: set[str] | None = None
    message: str | None = None


class BaseOperator(Operator):
    @classmethod
    @abstractmethod
    def _poll(cls, context: Context) -> str | None: ...

    @abstractmethod
    def _execute(self, context: Context) -> OperatorResult: ...

    @classmethod
    def poll(cls, context: Context) -> bool:
        msg = cls._poll(context)
        if isinstance(msg, str):
            cls.poll_message_set(msg)
            return False
        return True

    def execute(self, context: Context) -> OperatorReturnType:
        result = self._execute(context)
        if result.message and result.message_type:
            self.report(
                cast(
                    "WmReportType",
                    result.message_type,
                ),
                result.message,
            )
        return cast(
            "OperatorReturnType",
            result.return_type,
        )
