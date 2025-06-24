from typing import Annotated, List, TypedDict, Literal, Sequence
import operator  # Add this import
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.graph.ui import AnyUIMessage, ui_message_reducer


class Section(BaseModel):
    name: str = Field(
        description="Name for this section of the report.",
    )
    description: str = Field(
        description="Brief overview of the main topics and concepts to be covered in this section.",
    )
    research: bool = Field(
        description="Whether to perform web research for this section of the report."
    )
    content: str = Field(
        description="The content of the section."
    )


class Sections(BaseModel):
    sections: List[Section] = Field(
        description="Sections of the report.",
    )


class SearchQuery(BaseModel):
    search_query: str = Field(None, description="Query for web search.")


class Queries(BaseModel):
    queries: List[SearchQuery] = Field(
        description="List of search queries.",
    )


class Feedback(BaseModel):
    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
    )
    follow_up_queries: List[SearchQuery] = Field(
        description="List of follow-up search queries.",
    )


class ReportStateInput(TypedDict):
    messages: Sequence[BaseMessage]  # Messages from frontend


class ReportStateOutput(TypedDict):
    # messages: Sequence[BaseMessage]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]
    final_report: str  # Final report


def _keep_last_topic(left: str, right: str) -> str:
    """Reducer function to keep the last topic value - they should all be the same anyway."""

    return right if right else left


class ReportState(TypedDict):
    """State for the entire report."""

    # Messages with reducer for concurrent updates
    messages: Annotated[Sequence[BaseMessage], add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]

    # Report topic - use reducer for concurrent updates
    topic: Annotated[str, _keep_last_topic]

    # Feedback on the report plan
    feedback_on_report_plan: str

    # List of report sections - use reducer for concurrent updates
    sections: Annotated[list[Section], operator.add]

    # Use Annotated type with add reducer
    completed_sections: Annotated[list[Section], operator.add]

    # Report sections from research list with reducer for concurrent updates
    report_sections_from_research: Annotated[list[str], operator.add]

    # Final report - use reducer for concurrent updates
    final_report: str  # Final report


class SectionState(TypedDict):
    """State for a single section of the report."""

    # Messages with reducer for concurrent updates
    messages: Annotated[Sequence[BaseMessage], add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]

    # Report topic - use reducer for concurrent updates
    topic: Annotated[str, _keep_last_topic]

    # Section list with reducer for concurrent updates
    section: Annotated[list[Section], operator.add]

    # Search iterations list with reducer for concurrent updates
    search_iterations: Annotated[list[int], operator.add]

    # List of search queries - use reducer for concurrent updates
    search_queries: Annotated[list[SearchQuery], operator.add]

    # Source strings list with reducer for concurrent updates
    source_str: Annotated[list[str], operator.add]

    # Report sections from research list with reducer for concurrent updates
    report_sections_from_research: Annotated[list[str], operator.add]


class SectionOutputState(TypedDict):
    # Return completed section in list format
    completed_sections: Annotated[list[Section], operator.add]
