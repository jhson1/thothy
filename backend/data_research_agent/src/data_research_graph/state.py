from typing import Annotated, List, TypedDict, Literal, Sequence, Optional
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


class TickerInfo(BaseModel):
    """Information about a company's ticker symbol."""
    symbol: str = Field(description="The ticker symbol")
    company_name: Optional[str] = Field(None, description="The full company name")
    sector: Optional[str] = Field(None, description="The sector the company operates in")
    industry: Optional[str] = Field(None, description="The specific industry")
    market_cap: Optional[float] = Field(None, description="Market capitalization in USD")
    currency: Optional[str] = Field(None, description="The currency used for financial data")


class SearchQuery(BaseModel):
    """A search query with optional ticker information."""
    search_query: str = Field(..., description="The search query string")
    ticker_info: Optional[TickerInfo] = Field(None, description="Ticker information if the query is about a specific company")


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


def _reset_sections_on_topic_change(left: list[Section], right: list[Section]) -> list[Section]:
    """Reducer function to handle completed sections, with complete replacement on topic changes."""
    if not right:
        return left
    
    # If we get an empty list, it means we're resetting everything
    if len(right) == 0:
        print(f"[DEBUG] COMPLETE RESET: Clearing all completed sections")
        return []
    
    # If we have sections, completely replace the existing ones
    # This is much simpler and avoids all the complex merging logic
    print(f"[DEBUG] REPLACING ALL SECTIONS: {len(left)} old sections → {len(right)} new sections")
    print(f"[DEBUG] Old sections: {[s.name for s in left]}")
    print(f"[DEBUG] New sections: {[s.name for s in right]}")
    
    # Remove any special reset markers from content
    cleaned_sections = []
    for section in right:
        if hasattr(section, 'content') and section.content.startswith("__RESET__"):
            # Remove the reset marker
            cleaned_content = section.content[9:]  # Remove "__RESET__" prefix
            cleaned_section = type(section)(
                name=section.name,
                description=section.description,
                research=section.research,
                content=cleaned_content
            )
            cleaned_sections.append(cleaned_section)
        else:
            cleaned_sections.append(section)
    
    # Additional safety check - ensure no duplicates by name
    unique_sections = {}
    for section in cleaned_sections:
        if section.name in unique_sections:
            print(f"[DEBUG] Removing duplicate section: {section.name}")
        unique_sections[section.name] = section
    
    final_sections = list(unique_sections.values())
    print(f"[DEBUG] Final sections after deduplication: {[s.name for s in final_sections]}")
    
    return final_sections


def _track_topic_changes(left: str, right: str) -> str:
    """Reducer function to track topic changes and reset sections if needed."""
    if right and left and right != left:
        print(f"[DEBUG] Topic changed from '{left}' to '{right}'")
    return right if right else left


def _replace_sections(left: list[Section], right: list[Section]) -> list[Section]:
    """Reducer function to replace sections completely when new ones are provided."""
    return right if right else left


def _merge_unique_sections(left: list[Section], right: list[Section]) -> list[Section]:
    """Reducer function to merge sections, replacing sections with the same name."""
    if not right:
        return left
    if not left:
        return right
    
    # Create a dictionary of existing sections by name
    merged = {section.name: section for section in left}
    
    # Update or add new sections
    for section in right:
        if section.name in merged:
            print(f"[DEBUG] Replacing existing section: {section.name}")
        else:
            print(f"[DEBUG] Adding new section: {section.name}")
        merged[section.name] = section
    
    result = list(merged.values())
    print(f"[DEBUG] Final merged sections: {[s.name for s in result]}")
    
    # Additional safety check - remove any duplicates by name
    unique_sections = []
    seen_names = set()
    for section in result:
        if section.name not in seen_names:
            unique_sections.append(section)
            seen_names.add(section.name)
        else:
            print(f"[DEBUG] _merge_unique_sections: Removing duplicate section: {section.name}")
    
    return unique_sections


def _replace_string_list(left: list[str], right: list[str]) -> list[str]:
    """Reducer function to replace string list completely when new ones are provided."""
    return right if right else left


def _handle_reset_flag(left: bool, right: bool) -> bool:
    """Reducer function to handle reset flag."""
    return right if right is not None else left


class ReportState(TypedDict):
    """State for the entire report."""

    # Messages with reducer for concurrent updates
    messages: Annotated[Sequence[BaseMessage], add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]

    # Report topic - use reducer for concurrent updates
    topic: Annotated[str, _track_topic_changes]
    
    # Previous topic to track changes
    previous_topic: str
    
    # Reset flag to trigger complete state reset
    reset_sections: Annotated[bool, _handle_reset_flag]

    # Feedback on the report plan
    feedback_on_report_plan: str

    # List of report sections - replace completely when new sections are generated
    sections: Annotated[list[Section], _replace_sections]

    # Completed sections - merge unique sections to prevent duplicates
    completed_sections: Annotated[list[Section], _reset_sections_on_topic_change]

    # Report sections from research list - replace completely when new ones are provided
    report_sections_from_research: Annotated[list[str], _replace_string_list]

    # Final report - use reducer for concurrent updates
    final_report: str  # Final report


def _merge_unique_section_single(left: list[Section], right: list[Section]) -> list[Section]:
    """Reducer function for SectionState that handles single section updates."""
    if not right:
        return left
    if not left:
        return right
    
    # For section state, we typically work with single sections
    # Replace any section with the same name
    merged = {section.name: section for section in left}
    
    for section in right:
        merged[section.name] = section
    
    result = list(merged.values())
    
    # Additional safety check - ensure no duplicates
    unique_sections = []
    seen_names = set()
    for section in result:
        if section.name not in seen_names:
            unique_sections.append(section)
            seen_names.add(section.name)
    
    return unique_sections


def _merge_unique_queries(left: list[SearchQuery], right: list[SearchQuery]) -> list[SearchQuery]:
    """Reducer function to merge search queries, avoiding duplicates."""
    if not right:
        return left
    if not left:
        return right
    
    # Create a set of existing query strings to avoid duplicates
    existing_queries = {query.search_query for query in left}
    merged = list(left)
    
    # Add new unique queries
    for query in right:
        if query.search_query not in existing_queries:
            merged.append(query)
            existing_queries.add(query.search_query)
    
    return merged


class SectionState(TypedDict):
    """State for a single section of the report."""

    # Messages with reducer for concurrent updates
    messages: Annotated[Sequence[BaseMessage], add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]

    # Report topic - use reducer for concurrent updates
    topic: Annotated[str, _keep_last_topic]

    # Section list - replace when new section is provided
    section: Annotated[list[Section], _replace_sections]

    # Search iterations list with reducer for concurrent updates
    search_iterations: Annotated[list[int], operator.add]

    # List of search queries - merge unique queries to avoid duplicates
    search_queries: Annotated[list[SearchQuery], _merge_unique_queries]

    # Source strings list - replace when new source is provided
    source_str: Annotated[list[str], _replace_string_list]

    # Report sections from research list - replace when new ones are provided
    report_sections_from_research: Annotated[list[str], _replace_string_list]

    ticker_info: List[SearchQuery]  # Changed from List[str] to List[SearchQuery]
    api_data: Optional[dict]


class SectionOutputState(TypedDict):
    # Return completed section in list format
    completed_sections: Annotated[list[Section], _merge_unique_sections]
