"""Data models for the vendor desk agent."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class VendorDeskResult(BaseModel):
    """The structured answer the agent must return for one vendor document."""

    vendor: str = Field(description="Vendor name exactly as written in the document.")
    sku: str | None = Field(
        default=None,
        description="Campus Customs SKU (e.g. CC-HD-006), or null if the document gives none.",
    )
    unit_price: float | None = Field(
        default=None,
        description="Quoted price per unit in USD, or null if the document does not say.",
    )
    lead_time_days: int | None = Field(
        default=None,
        description="Lead time as the number of days stated in the document, or null if not stated.",
    )
    min_order: int | None = Field(
        default=None,
        description="Minimum order in units, or null if the document does not say.",
    )
    decision: Literal["recommend", "do_not_recommend"] = Field(
        description="Decision from the handbook purchasing rules (section 4)."
    )
    reason: str = Field(
        description="One sentence naming the purchasing check that decided the outcome."
    )


@dataclass(frozen=True)
class Defenses:
    """Which safety layers are on. `Defenses.none()` reproduces the undefended Problem 5 agent."""

    content_checks: bool = True  # layer 1: strip unseen text and instruction-like lines before the model
    agent_design: bool = True  # layer 2: facts checked and decision made in code; risky tools held
    prompt_rules: bool = True  # layer 3: the stricter rules in prompts/prompt.md

    @classmethod
    def all(cls) -> "Defenses":
        return cls(True, True, True)

    @classmethod
    def none(cls) -> "Defenses":
        return cls(False, False, False)

    def label(self) -> str:
        on = [n for n, v in (("L1", self.content_checks), ("L2", self.agent_design), ("L3", self.prompt_rules)) if v]
        return "+".join(on) or "none"


@dataclass
class VendorDeskDeps:
    """Per-run context handed to the prompt builder and the tools."""

    handbook: str  # full handbook text, sent with every model call
    document_path: Path  # the one document this run is allowed to read
    output_dir: Path  # where logs are written
    use_cache: bool = True  # False makes every request's prefix unique so nothing is reused
    defenses: Defenses = field(default_factory=Defenses.all)
    seen_text: str = ""  # what read_document actually returned to the model (for layer 2 checks)
    scan_events: list = field(default_factory=list)  # text layer 1 removed, kept for the audit trail
