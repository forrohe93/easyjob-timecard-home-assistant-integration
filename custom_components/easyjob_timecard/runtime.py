from __future__ import annotations

from dataclasses import dataclass, field

from .api import EasyjobClient
from .coordinator import EasyjobCoordinator


@dataclass
class RuntimeData:
    client: EasyjobClient
    coordinator: EasyjobCoordinator

    # Cache für ResourceStateTypes (Caption -> IdResourceStateType),
    # damit Services nicht jedes Mal die API abfragen müssen.
    resource_state_caption_to_id: dict[str, int] = field(default_factory=dict)

    # Merkt sich die Select-Entity-ID auf dem Device (wird von select.py gesetzt)
    resource_state_select_entity_id: str | None = None
