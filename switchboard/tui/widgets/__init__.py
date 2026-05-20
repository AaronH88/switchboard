"""Switchboard TUI widgets."""

from .header import SwitchboardHeader
from .operator_panel import OperatorPanel
from .projects_panel import ProjectsPanel
from .patch_panel import PatchPanel
from .active_lines import ActiveLines
from .party_line import PartyLine
from .footer import Footer

__all__ = [
    "SwitchboardHeader",
    "OperatorPanel",
    "ProjectsPanel",
    "PatchPanel",
    "ActiveLines",
    "PartyLine",
    "Footer",
]