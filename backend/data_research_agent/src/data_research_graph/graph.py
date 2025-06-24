from typing import Literal
import logging

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.constants import Send

from langgraph.graph import START, END, StateGraph
from langgraph.graph.ui import push_ui_message
from langgraph.types import Command, interrupt
from langgraph.prebuilt.interrupt import (
    ActionRequest,
    HumanInterrupt,
    HumanInterruptConfig,
    HumanResponse,
)

from data_research_graph.state import (
    ReportStateInput,
    ReportStateOutput,
    Sections,
    ReportState,
    SectionState,
    SectionOutputState,
    Queries,
    Feedback
)

from data_research_graph.prompts import (
    report_planner_query_writer_instructions,
    report_planner_instructions,
    query_writer_instructions,
    section_writer_instructions,
    final_section_writer_instructions,
    section_grader_instructions,
    section_writer_inputs
)

from data_research_graph.configuration import Configuration
from data_research_graph.utils import (
    init_model_with_provider,
    format_sections,
    get_config_value,
    get_search_params,
    select_and_execute_search
)

# Set up logger with the specified name
logger = logging.getLogger("thothy-devlop")

# UI Component name for data research agent
UI_COMPONENT_NAME = "data_research_graph"

# Global variable to store UI message ID
ui_message_id = None


async def generate_report_plan(state: ReportState, config: RunnableConfig):
    """Generate the initial report plan with sections.

    This node:
    1. Gets configuration for the report structure and search parameters
    2. Generates search queries to gather context for planning
    3. Performs web searches using those queries
    4. Uses an LLM to generate a structured plan with sections

    Args:
        state: Current graph state containing the report topic
        config: Configuration for models, search APIs, etc.

    Returns:
        Dict containing the generated sections
    """

    # Get topic from the latest message
    messages = state.get("messages", [])

    if not messages:
        raise ValueError(
            "No messages found. Please provide a topic for report generation.")

    # Get the latest message content as topic
    latest_message = messages[-1]
    if isinstance(latest_message, dict):
        topic = latest_message.get("content", "")
    else:
        topic = getattr(latest_message, "content", "")

    if not topic:
        raise ValueError(
            "No topic found in the latest message. Please provide a topic for report generation.")

    feedback = state.get("feedback_on_report_plan", None)

    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    report_structure = configurable.report_structure
    number_of_queries = configurable.number_of_queries
    search_api = get_config_value(configurable.search_api)

    # Get the config dict, default to empty
    search_api_config = configurable.search_api_config or {}
    params_to_pass = get_search_params(
        search_api, search_api_config)  # Filter parameters

    # Convert JSON object to string if necessary
    if isinstance(report_structure, dict):
        report_structure = str(report_structure)

    # Set writer model (model used for query writing)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_model_with_provider(writer_model_name, writer_provider)
    structured_llm = writer_model.with_structured_output(Queries)

    # Format system instructions
    system_instructions_query = report_planner_query_writer_instructions.format(
        topic=topic, report_organization=report_structure, number_of_queries=number_of_queries)

    # Generate queries
    results = await structured_llm.ainvoke(
        [SystemMessage(content=system_instructions_query),
         HumanMessage(content="Generate search queries that will help with planning the sections of the report.")])

    # Web search
    query_list = [query.search_query for query in results.queries]

    # Search the web with parameters
    source_str = await select_and_execute_search(search_api, query_list, params_to_pass)

    # Format system instructions
    system_instructions_sections = report_planner_instructions.format(
        topic=topic, report_organization=report_structure, context=source_str, feedback=feedback)

    # Get the planner
    planner_provider = get_config_value(configurable.planner_provider)
    planner_model = get_config_value(configurable.planner_model)

    # Report planner instructions
    planner_message = """Generate the sections of the report. Each section must have: name, description, research (boolean indicating if research is needed), and content fields. Format your response as a valid JSON object containing a 'sections' array."""

    # Use structured output for all providers
    if planner_model == "claude-3-7-sonnet-latest":
        planner_llm = init_chat_model(model=planner_model,
                                      model_provider=planner_provider,
                                      max_tokens=20_000,
                                      thinking={"type": "enabled", "budget_tokens": 16_000})
    else:
        planner_llm = init_chat_model(model=planner_model,
                                      model_provider=planner_provider)

    # Generate the report sections with structured output
    structured_llm = planner_llm.with_structured_output(Sections)
    report_sections = await structured_llm.ainvoke(
        [SystemMessage(content=system_instructions_sections),
         HumanMessage(content=planner_message)])

    # Get sections
    sections = report_sections.sections

    # Push the report sections to the UI with message
    global ui_message_id
    ai_message = AIMessage(
        content="Report sections generated successfully!"
    )
    ui_message = push_ui_message(
        UI_COMPONENT_NAME, {"topic": topic, "sections": sections})
    ui_message_id = ui_message["id"]

    return {"topic": topic, "sections": sections, "messages": [ai_message]}


def human_feedback(state: ReportState, config: RunnableConfig) -> Command[Literal["generate_report_plan", "build_section_with_web_research"]]:
    """Get human feedback on the report plan and route to next steps.

    This node:
    1. Formats the current report plan for human review
    2. Gets feedback via an interrupt
    3. Routes to either:
       - Section writing if plan is approved
       - Plan regeneration if feedback is provided

    Args:
        state: Current graph state with sections to review
        config: Configuration for the workflow

    Returns:
        Command to either regenerate plan or start section writing
    """

    # Get sections
    topic = state["topic"]
    sections = state['sections']

    action_request = ActionRequest(
        action="Check Report Plan",
        args={
            "request": state["topic"],
            "response": state["sections"],
        }
    )

    interrupt_config = HumanInterruptConfig(
        allow_ignore=True,
        allow_respond=True,
        allow_edit=True,
        allow_accept=True
    )

    description = """Please review this report plan. You can:
- Accept the report plan as-is
- Edit the report plan before sending
- Provide feedback or instructions for regeneration
- Make any necessary corrections
"""

    request = HumanInterrupt(
        action_request=action_request,
        config=interrupt_config,
        description=description
    )

    return Command(goto=[
        Send(
            "build_section_with_web_research",
            {"topic": topic, "section": [s], "search_iterations": [0]}
        )
        for s in sections
        if s.research
    ])

    # TODO: Handle later
    human_response: HumanResponse = interrupt([request])[0]

    # TODO: Handle multiple feedbacks
    logger.info(f"human_response: {human_response}")

    # If the user approves the report plan, kick off section writing
    if human_response.get("type") == "accept":
        return Command(goto=[
            Send(
                "build_section_with_web_research",
                {"topic": topic, "section": [s], "search_iterations": [0]}
            )
            for s in sections
            if s.research
        ])
    elif human_response.get("type") == "response":
        return Command(goto="generate_report_plan",
                       update={"feedback_on_report_plan": human_response.get("args")})
    elif human_response.get("type") == "ignore":
        return Command(goto=END)
    else:
        raise TypeError(
            f"Interrupt value of type {type(human_response)} is not supported.")


async def generate_queries(state: SectionState, config: RunnableConfig):
    """Generate search queries for researching a specific section.

    This node uses an LLM to generate targeted search queries based on the
    section topic and description.

    Args:
        state: Current state containing section details
        config: Configuration including number of queries to generate

    Returns:
        Dict containing the generated search queries
    """

    # Get state
    topic = state["topic"]

    # Get the first (current) section from the list
    section = state["section"][0] if state["section"] else None

    # Error handling
    if not section:
        raise ValueError("No section found in state for query generation")

    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    number_of_queries = configurable.number_of_queries

    # Generate queries
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(
        model=writer_model_name, model_provider=writer_provider)
    structured_llm = writer_model.with_structured_output(Queries)

    # Format system instructions
    system_instructions = query_writer_instructions.format(topic=topic,
                                                           section_topic=section.description,
                                                           number_of_queries=number_of_queries)

    # Generate queries
    queries = await structured_llm.ainvoke([SystemMessage(content=system_instructions),
                                            HumanMessage(content="Generate search queries on the provided topic.")])

    # Return the updated messages
    return {"search_queries": queries.queries}


async def search_web(state: SectionState, config: RunnableConfig):
    """Execute web searches for the section queries.

    This node:
    1. Takes the generated queries
    2. Executes searches using configured search API
    3. Formats results into usable context

    Args:
        state: Current state with search queries
        config: Search API configuration

    Returns:
        Dict with search results and updated iteration count
    """

    # Get state
    search_queries = state["search_queries"]

    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    search_api = get_config_value(configurable.search_api)
    # Get the config dict, default to empty
    search_api_config = configurable.search_api_config or {}
    params_to_pass = get_search_params(
        search_api, search_api_config)  # Filter parameters

    # Web search
    query_list = [query.search_query for query in search_queries]
    # print("\n-------Query List:----------",query_list)
    # Search the web with parameters
    source_str = await select_and_execute_search(search_api, query_list, params_to_pass)

    # Get current search iterations (use last value or 0 if empty)
    current_iterations = state["search_iterations"][-1] if state["search_iterations"] else 0

    # Return the updated messages
    return {"source_str": [source_str], "search_iterations": [current_iterations + 1]}


async def write_section(state: SectionState, config: RunnableConfig) -> Command[Literal["__end__", "search_web"]]:
    """Write a section of the report and evaluate if more research is needed.

    This node:
    1. Writes section content using search results
    2. Evaluates the quality of the section
    3. Either:
       - Completes the section if quality passes
       - Triggers more research if quality fails

    Args:
        state: Current state with search results and section info
        config: Configuration for writing and evaluation

    Returns:
        Command to either complete section or do more research
    """

    # Get state
    topic = state["topic"]

    # Get the first (current) section from the list
    section = state["section"][0] if state["section"] else None

    # Get the latest source string from the list
    source_str = state["source_str"][-1] if state["source_str"] else ""

    if not section:
        raise ValueError("No section found in state for writing")

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Format system instructions
    section_writer_inputs_formatted = \
        section_writer_inputs.format(topic=topic,
                                     section_name=section.name,
                                     section_topic=section.description,
                                     context=source_str,
                                     section_content=section.content)
    logger.info(f"section_writer_inputs_formatted: {section_writer_inputs_formatted}")

    # Generate section
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(
        model=writer_model_name, model_provider=writer_provider)

    section_content = await writer_model.ainvoke(
        [SystemMessage(content=section_writer_instructions),
         HumanMessage(content=section_writer_inputs_formatted)])

    # Use temporary variable instead of modifying section directly
    temp_section_content = section_content.content

    # Grade prompt
    section_grader_message = (
        "Grade the report and consider follow-up questions for missing information. "
        "If the grade is 'pass', return empty strings for all follow-up queries. "
        "If the grade is 'fail', provide specific search queries to gather missing information.")

    section_grader_instructions_formatted = \
        section_grader_instructions.format(topic=topic,
                                           section_topic=section.description,
                                           section=temp_section_content,
                                           number_of_follow_up_queries=configurable.number_of_queries)

    # Use planner model for reflection
    planner_provider = get_config_value(configurable.planner_provider)
    planner_model = get_config_value(configurable.planner_model)

    if planner_model == "claude-3-7-sonnet-latest":
        # Allocate a thinking budget for claude-3-7-sonnet-latest as the planner model
        reflection_model = init_chat_model(model=planner_model,
                                           model_provider=planner_provider,
                                           max_tokens=20_000,
                                           thinking={"type": "enabled", "budget_tokens": 16_000}).with_structured_output(Feedback)
    else:
        reflection_model = init_chat_model(model=planner_model,
                                           model_provider=planner_provider).with_structured_output(Feedback)
    # Generate feedback
    feedback = await reflection_model.ainvoke(
        [SystemMessage(content=section_grader_instructions_formatted),
         HumanMessage(content=section_grader_message)])

    # Get current search iterations (use last value or 0 if empty)
    current_iterations = \
        state["search_iterations"][-1] if state["search_iterations"] else 0

    # If the section is passing or the max search depth is reached, publish the section to completed sections
    if feedback.grade == "pass" or current_iterations >= configurable.max_search_depth:
        # Create a temporary section object with updated content
        temp_section = type(section)(
            name=section.name,
            description=section.description,
            research=section.research,
            content=temp_section_content
        )

        # Push the completed section to UI with message
        # global ui_message_id
        # push_ui_message(UI_COMPONENT_NAME, {
        #                 "completed_sections": [temp_section]}, id=ui_message_id)

        # Return the completed section
        return Command(
            update={"completed_sections": [temp_section]},
            goto=END
        )

    # Return the updated messages
    return Command(
        update={"search_queries": feedback.follow_up_queries},
        goto="search_web"
    )


async def write_final_sections(state: SectionState, config: RunnableConfig):
    """Write sections that don't require research using completed sections as context.

    This node handles sections like conclusions or summaries that build on
    the researched sections rather than requiring direct research.

    Args:
        state: Current state with completed sections as context
        config: Configuration for the writing model

    Returns:
        Dict containing the newly written section
    """

    # Get configuration
    configurable = Configuration.from_runnable_config(config)

    # Get state
    topic = state["topic"]
    # Get the first (current) section from the list
    section = state["section"][0] if state["section"] else None
    # Get the latest report sections from research (join all if multiple)
    completed_report_sections = "\n\n".join(
        state["report_sections_from_research"]) if state["report_sections_from_research"] else ""

    if not section:
        raise ValueError("No section found in state for final section writing")

    # Format system instructions
    system_instructions = final_section_writer_instructions.format(
        topic=topic, section_name=section.name, section_topic=section.description, context=completed_report_sections)

    # Generate section
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(
        model=writer_model_name, model_provider=writer_provider)

    section_content = await writer_model.ainvoke([SystemMessage(content=system_instructions),
                                                  HumanMessage(content="Generate a report section based on the provided sources.")])

    # Use temporary variable instead of modifying section directly
    temp_section_content = section_content.content

    # Create a temporary section object with updated content
    temp_section = type(section)(
        name=section.name,
        description=section.description,
        research=section.research,
        content=temp_section_content
    )

    # Push the section content to the UI with message
    # global ui_message_id
    # push_ui_message(UI_COMPONENT_NAME, {"completed_sections": [
    #                 temp_section]}, id=ui_message_id)

    # Return the completed section
    return {"completed_sections": [temp_section]}


def gather_completed_sections(state: ReportState):
    """Format completed sections as context for writing final sections.

    This node takes all completed research sections and formats them into
    a single context string for writing summary sections.

    Args:
        state: Current state with completed sections

    Returns:
        Dict with formatted sections as context
    """

    logger.info("gather_completed_sections start")

    # List of completed sections
    completed_sections = state["completed_sections"]

    # Format completed section to str to use as context for final sections
    completed_report_sections = format_sections(completed_sections)

    logger.info("gather_completed_sections end")

    return {"report_sections_from_research": [completed_report_sections]}


def compile_final_report(state: ReportState):
    """Compile all sections into the final report."""

    # Get sections
    sections = state["sections"]
    completed_sections = {
        s.name: s.content for s in state["completed_sections"]}

    # Create temporary sections with completed content while maintaining original order
    temp_sections = []
    for section in sections:
        temp_section_content = completed_sections.get(section.name, "")
        temp_sections.append(temp_section_content)

    global ui_message_id
    push_ui_message(UI_COMPONENT_NAME, {
                    "completed_sections": state["completed_sections"]}, id=ui_message_id)

    # Compile final report using temporary sections
    all_sections = "\n\n".join(temp_sections)

    # Wrap the final report with AIMessage type
    # ai_message = AIMessage(content=all_sections)

    # TODO: With messages, canvas would be reset
    # return ReportStateOutput(final_report=all_sections, messages=[ai_message])
    return {"final_report": all_sections}


def initiate_final_section_writing(state: ReportState):
    """Create parallel tasks for writing non-research sections.

    This edge function identifies sections that don't need research and
    creates parallel writing tasks for each one.

    Args:
        state: Current state with all sections and research context

    Returns:
        List of Send commands for parallel section writing
    """

    # Kick off section writing in parallel via Send() API for any sections that do not require research
    return [
        Send("write_final_sections", {"topic": state["topic"], "section": [s],
             "report_sections_from_research": state["report_sections_from_research"]})
        for s in state["sections"]
        if not s.research
    ]

# Add this fallback node at the end of the file, before compiling the graph


def fallback_handler(state: ReportState) -> ReportStateOutput:
    """Handle errors and provide a fallback response."""
    print("Executing fallback handler")
    # Get whatever information we have
    topic = state.get("topic", "")

    # Create a fallback report
    fallback_report = f"""
# Report on {topic}

## Introduction
This is a fallback report generated due to an error in the report generation process.

## Key Points
- The requested topic was: {topic}
- Due to technical limitations, a full report could not be generated
- Please try again with a more specific topic or different configuration
    """

    return ReportStateOutput(final_report=fallback_report)

# Report section sub-graph --


# Add nodes
section_builder = StateGraph(SectionState, output=SectionOutputState)
section_builder.add_node("generate_queries", generate_queries)
section_builder.add_node("search_web", search_web)
section_builder.add_node("write_section", write_section)

# Add edges
section_builder.add_edge(START, "generate_queries")
section_builder.add_edge("generate_queries", "search_web")
section_builder.add_edge("search_web", "write_section")

# Outer graph for initial report plan compiling results from each section --


# Add Nodes
builder = StateGraph(ReportState, input=ReportStateInput,
                     output=ReportStateOutput, config_schema=Configuration)
builder.add_node("generate_report_plan", generate_report_plan)
builder.add_node("human_feedback", human_feedback)
builder.add_node("build_section_with_web_research", section_builder.compile())
builder.add_node("gather_completed_sections", gather_completed_sections)
builder.add_node("write_final_sections", write_final_sections)
builder.add_node("compile_final_report", compile_final_report)

# Add edges
builder.add_edge(START, "generate_report_plan")
builder.add_edge("generate_report_plan", "human_feedback")
builder.add_edge("build_section_with_web_research",
                 "gather_completed_sections")
builder.add_conditional_edges("gather_completed_sections",
                              initiate_final_section_writing, ["write_final_sections"])
builder.add_edge("write_final_sections", "compile_final_report")
builder.add_edge("compile_final_report", END)

graph = builder.compile()
