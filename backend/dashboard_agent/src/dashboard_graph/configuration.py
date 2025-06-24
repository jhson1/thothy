"""Define the configurable parameters for the chat bot."""

import os
from dataclasses import dataclass, fields
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig

from dashboard_graph.prompts import SYSTEM_PROMPT


@dataclass(kw_only=True)
class SlideConfigurable:
    """The configurable fields for the chatbot."""

    model: str = "gpt-4o-mini"
    system_prompt: str = SYSTEM_PROMPT

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "SlideConfigurable":
        """Load configuration."""

        configurable = (
            config.get("configurable", {}) if config else {}
        )

        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }

        return cls(**{k: v for k, v in values.items() if v})
