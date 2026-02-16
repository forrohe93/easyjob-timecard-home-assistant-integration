from __future__ import annotations

from dataclasses import dataclass

from .api import EasyjobClient
from .coordinator import EasyjobCoordinator


@dataclass
class RuntimeData:
    client: EasyjobClient
    coordinator: EasyjobCoordinator
