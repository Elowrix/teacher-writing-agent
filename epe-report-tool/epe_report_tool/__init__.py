"""EPE report generation package."""

from .session_extensions import register_session_extensions

register_session_extensions()

__all__ = ["runner"]
