from typing import Literal
import logging
from datetime import datetime, timedelta

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
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
from langgraph.prebuilt import ToolNode


from research_graph.state import (
    ReportStateInput,
    ReportStateOutput,
    Sections,
    ReportState,
    SectionState,
    SectionOutputState,
    Queries,
    Feedback,
    TickerInfo,
    SearchQuery
)

from research_graph.prompts import (
    report_planner_query_writer_instructions,
    report_planner_instructions,
    query_writer_instructions,
    ticker_writer_instructions,
    section_writer_instructions,
    financial_section_writer_instructions,
    final_section_writer_instructions,
    section_grader_instructions,
    section_writer_inputs
)

from research_graph.configuration import Configuration
from research_graph.utils import (
    init_model_with_provider,
    format_sections,
    get_config_value,
    get_search_params,
    select_and_execute_search,
)

from research_graph.tools import ALL_TOOLS_LIST

# Set up logger with the specified name
logger = logging.getLogger("thothy-devlop")

# UI Component name for data research agent
UI_COMPONENT_NAME = "research_graph"

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

    logger.info(f"Topic extracted from latest message: {topic}")

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
    results = await structured_llm.ainvoke([SystemMessage(content=system_instructions_query),
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
    planner_message = """Generate the sections of the report. Each section must have: name, description, research (boolean indicating if research is needed), and content fields.
                      Format your response as a valid JSON object containing a 'sections' array."""

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

    logger.info(f"report_sections: {report_sections}")

    # Get sections
    sections = report_sections.sections
    logger.info(f"sections1: {sections}")

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
    logger.info(f"sections: {sections}")
    completed_sections = state.get("completed_sections", [])
    completed_names = {s.name for s in completed_sections}

    logger.info(f"Current completed sections: {[s.name for s in completed_sections]}")
    logger.info(f"Total sections: {[s.name for s in sections]}")
    logger.info(f"Research sections not completed: {[s.name for s in sections if s.research and s.name not in completed_names]}")

    # Find the first research section that hasn't been completed
    next_section = next(
        (s for s in sections if s.research and s.name not in completed_names),
        None
    )
    logger.info(f"next_section: {next_section}")

    if next_section:
        logger.info(f"Processing next section: {next_section.name}")
        return Command(goto=[
            Send(
                "build_section_with_web_research",
                {"topic": topic, "section": [next_section], "search_iterations": [0]}
            )
        ])
    else:
        # If all research sections are completed, move to final sections
        logger.info("All research sections completed, moving to final sections")
        return Command(goto="gather_completed_sections")

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

    This node:
    1. Uses an LLM to generate targeted search queries based on the section topic
    2. If the topic is about a specific company, gets its ticker symbol
    3. Returns both general search queries and ticker information if applicable

    Args:
        state: Current state containing section details
        config: Configuration including number of queries to generate

    Returns:
        Dict containing the generated search queries and ticker information
    """
    # Get state
    topic = state["topic"]
    section = state["section"][0] if state["section"] else None
    messages = state.get("messages", [])

    if not section:
        raise ValueError("No section found in state for query generation")

    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    number_of_queries = configurable.number_of_queries

    # First, try to get the ticker symbol
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider)
    
    # Format system instructions for ticker search
    ticker_instructions = ticker_writer_instructions.format(
        topic=topic,
        section_topic=section.description
    )
    
    # Get ticker symbol using the model
    ticker_response = await writer_model.ainvoke([
        SystemMessage(content=ticker_instructions),
        HumanMessage(content="Find the ticker symbol for the company mentioned in the topic.")
    ])   
    
    # Process ticker response
    ticker_info = None
    if ticker_response.content and ticker_response.content.strip():
        ticker_symbol = ticker_response.content.strip()
        print(f"Found ticker symbol: {ticker_symbol}")
        
        # Create a SearchQuery with TickerInfo
        ticker_info = [SearchQuery(
            search_query=ticker_symbol,
            ticker_info=TickerInfo(
                symbol=ticker_symbol,
                company_name=None,
                sector=None,
                industry=None,
                market_cap=None,
                currency=None
            )
        )]
        
        # Create tool call for company_financials
        tool_call = {
            "id": f"call_company_financials_{ticker_symbol}",
            "name": "company_financials",
            "args": {
                "ticker": ticker_symbol,
                "start_date": None,
                "end_date": None
            },
            "type": "function"
        }
        
        # Add message for ticker search with tool call
        ticker_message = AIMessage(
            content=f"I will fetch financial data for {ticker_symbol} using the company_financials tool.",
            tool_calls=[tool_call]
        )
        # print("Created ticker message with tool call:", ticker_message)
        
        # tool_call 메시지 추가 전 체크
        if not any(isinstance(msg, AIMessage) and msg.tool_calls and msg.tool_calls[0]['name'] == 'company_financials' for msg in messages):
            messages = messages + [ticker_message]
        
        # Return immediately if we have a ticker (prioritize financial data)
        if any(keyword in section.name.lower() for keyword in ["financial analysis", "stock", "price", "revenue"]):
            print("Financial section with ticker found, returning early")
            return {
                "search_queries": [],
                "ticker_info": ticker_info,
                "messages": messages
            }
    
    # Generate general queries only if we don't have a ticker or it's not a financial section
    general_llm = writer_model.with_structured_output(Queries)
    general_instructions = query_writer_instructions.format(
        topic=topic,
        section_topic=section.description,
        number_of_queries=number_of_queries
    )
    
    general_results = await general_llm.ainvoke([
        SystemMessage(content=general_instructions),
        HumanMessage(content="Generate search queries on the provided topic.")
    ])
    
    # Add message for general queries
    query_message = AIMessage(
        content=f"Generated {len(general_results.queries)} search queries for the section."
    )
    messages = messages + [query_message]
    
    return {
        "search_queries": general_results.queries,
        "ticker_info": ticker_info if ticker_info else [],
        "messages": messages
    }


async def search_web(state: SectionState, config: RunnableConfig):
    """Execute web searches for the section queries.

    This node:
    1. Takes the generated queries
    2. Executes searches using configured search API
    3. For ticker queries, attempts to extract ticker information from search results
    4. Formats results into usable context

    Args:
        state: Current state with search queries
        config: Search API configuration

    Returns:
        Dict with search results and updated iteration count
    """
    # Get state
    search_queries = state["search_queries"]
    ticker_queries = state.get("ticker_info", [])
    messages = state.get("messages", [])
    section = state["section"][0] if state["section"] else None
    
    if not section:
        raise ValueError("No section found in state for search")
    
    logger.info(f"Processing {len(search_queries)} general queries and {len(ticker_queries)} ticker queries")

    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    search_api = get_config_value(configurable.search_api)
    search_api_config = configurable.search_api_config or {}
    params_to_pass = get_search_params(search_api, search_api_config)

    # For financial sections, we don't need web search
    is_financial_section = any(keyword in section.name.lower() for keyword in 
                             ["financial analysis", "stock", "price", "revenue"])
    if is_financial_section and ticker_queries:
        logger.info("Financial section with ticker found, skipping web search")
        return {
            "source_str": [""],  # Empty source for financial sections
            "search_iterations": [0],
            "ticker_info": ticker_queries,
            "messages": messages
        }

    # Process general queries
    query_list = [q.search_query for q in search_queries]
    source_str = await select_and_execute_search(search_api, query_list, params_to_pass)

    # Create a message to indicate search completion
    search_message = AIMessage(
        content=f"Completed search with {len(query_list)} queries."
    )
    messages = messages + [search_message]

    return {
        "source_str": [source_str],
        "search_iterations": [0],
        "ticker_info": ticker_queries,
        "messages": messages
    }


async def write_section(state: SectionState, config: RunnableConfig) -> Command[Literal[END, "search_web", "tools"]]:
    """Write a section of the report and evaluate if more research is needed.

    This node:
    1. Receives data from either search_web or tools
    2. Writes section content using the received data
    3. Evaluates the quality of the section
    4. Either:
       - Completes the section if quality passes
       - Triggers more research if quality fails

    Args:
        state: Current state with data from search_web or tools
        config: Configuration for writing and evaluation

    Returns:
        Command to either complete section or do more research
    """
    # Get state
    topic = state["topic"]
    section = state["section"][0] if state["section"] else None
    completed_sections = state.get("completed_sections", [])
    print(f"[write_section] section: {section.name if section else None}, completed_sections: {[s.name for s in completed_sections]}")
    source_str = state["source_str"][-1] if state["source_str"] else ""
    messages = state.get("messages", [])

    if not section:
        raise ValueError("No section found in state for writing")

    # Check if this section is already completed
    if any(s.name == section.name for s in completed_sections):
        print(f"[write_section] Section {section.name} already completed, skipping")
        return Command(goto=END)

    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider)

    # Check if this is a financial section
    is_financial_section = any(keyword in section.name.lower() for keyword in 
                             ["financial analysis", "stock", "price", "revenue"])
    print("[write_section] is_financial_section", is_financial_section, section.name)
    
    # For financial sections, check if we have API data
    if is_financial_section:
        # Get the last ToolMessage
        tool_message = next((msg for msg in reversed(messages) 
                           if isinstance(msg, ToolMessage)), None)
        
        if tool_message:
            # print("Found tool message with results:", tool_message)
            try:
                # Parse the tool message content as JSON
                import json
                financial_data = json.loads(tool_message.content)
                
                # Format the financial data for the section
                formatted_data = {
                    "ticker": financial_data.get("ticker", "N/A"),
                    "prices": financial_data.get("prices", {}),
                    "date_range": financial_data.get("date_range", {})
                }

                predicted_price_rows = ""

                # predicted_prices = financial_data.get("predictions", {}).get("mean", [])[0]
                # for i, price in enumerate(predicted_prices):
                #     predicted_price_rows += f"Day {i+1}: {price}\n"
                # n_pred = len(predicted_prices) if financial_data.get("predictions", {}) else 0

                predicted_prices = financial_data.get("predictions", {}).get("quantiles", [])[0]
                end_date = formatted_data["date_range"].get("end", "N/A")

                # end_date가 str임을 명확히 하고, 예측 날짜 생성 시 주말 제외
                pred_dates = []
                n_pred = len(predicted_prices) if financial_data.get("predictions", {}) else 0

                try:
                    start_pred_date = datetime.strptime(end_date, "%Y-%m-%d")
                    current = start_pred_date
                    while len(pred_dates) < n_pred:
                        current += timedelta(days=1)
                        if current.weekday() < 5:  # 월~금만
                            pred_dates.append(current.strftime("%Y-%m-%d"))
                except Exception:
                    pred_dates = [f"Day {i+1}" for i in range(n_pred)]
                predicted_price_rows = "| Date | lower_bound | close | upper_bound |\n|-----|------------|-------------|-------|-------------|\n"
                if financial_data.get("predictions", {}) and len(predicted_prices) > 0:
                    for i, day_vals in enumerate(predicted_prices):
                        lower = float(day_vals[0])
                        close = float(day_vals[1])
                        upper = float(day_vals[2])
                        pred_date = pred_dates[i] if i < len(pred_dates) else f"Day {i+1}"
                        predicted_price_rows += f"| {pred_date} | {lower:.2f} | {close:.2f} | {upper:.2f} |\n"

                # Generate section content using financial data
                instructions = financial_section_writer_instructions.format(
                    topic=topic,
                    section_topic=section.description,
                    ticker=formatted_data["ticker"],
                    price_data_rows="",  # Will be formatted by the LLM
                    start_date=formatted_data["date_range"].get("start", "N/A"),
                    end_date=formatted_data["date_range"].get("end", "N/A"),
                    prediction_length=n_pred,
                    predicted_price_rows=predicted_price_rows
                )
                
                section_content = await writer_model.ainvoke([
                    SystemMessage(content=instructions),
                    HumanMessage(content=f"Write a concise financial section using this price data: {formatted_data['prices']}. Focus on key trends and insights.")
                ])
                
                # Create and return the completed financial section
                temp_section = type(section)(
                    name=section.name,
                    description=section.description,
                    research=section.research,
                    content=section_content.content
                )
                return Command(
                    update={"completed_sections": completed_sections + [temp_section]},
                    goto=END
                )
            except Exception as e:
                print(f"[write_section] Error processing financial data: {str(e)}")
                return Command(goto=END)
        
        # If no tool message found, check if we have a ticker
        ticker_info = state.get("ticker_info", [])
        if ticker_info and ticker_info[0].ticker_info and ticker_info[0].ticker_info.symbol:
            print("[write_section] No tool message but have ticker, routing to tools")
            return Command(goto="tools")
        
        print("[write_section] No tool message or ticker info for financial section")
        return Command(goto=END)

    # For non-financial sections, require source content
    if not source_str:
        print(f"[write_section] No source content available for section: {section.name}")
        # Add a message to indicate missing content
        error_message = AIMessage(
            content=f"Unable to generate content for section '{section.name}' due to missing source information."
        )
        return Command(
            update={"messages": messages + [error_message]},
            goto=END
        )

    # Use the search results to generate content
    section_writer_inputs_formatted = section_writer_inputs.format(
        topic=topic,
        section_name=section.name,
        section_topic=section.description,
        context=source_str,
        section_content=section.content,
        api_data=None
    )
    
    section_content = await writer_model.ainvoke([
        SystemMessage(content=section_writer_instructions),
        HumanMessage(content=section_writer_inputs_formatted)
    ])

    # Create temporary section with the content
    temp_section = type(section)(
        name=section.name,
        description=section.description,
        research=section.research,
        content=section_content.content
    )
    
    return Command(
        update={"completed_sections": completed_sections + [temp_section]},
        goto=END
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
    """Create parallel tasks for writing both research and non-research sections.
    
    This function:
    1. Handles sections that require research (if not completed)
    2. Handles sections that don't require research (like conclusion)
    3. Ensures all sections are processed exactly once
    """
    completed_names = {s.name for s in state["completed_sections"]}
    
    # Log the current state
    logger.info(f"Current completed sections: {[s.name for s in state['completed_sections']]}")
    logger.info(f"Total sections: {[s.name for s in state['sections']]}")
    logger.info(f"Research sections not completed: {[s.name for s in state['sections'] if s.research and s.name not in completed_names]}")
    logger.info(f"Non-research sections not completed: {[s.name for s in state['sections'] if not s.research and s.name not in completed_names]}")
    
    # Process both research and non-research sections that haven't been completed
    return [
        Send("build_section_with_web_research", {"topic": state["topic"], "section": [s], "search_iterations": [0]})
        for s in state["sections"]
        if s.name not in completed_names  # Remove the research check to process all incomplete sections
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

def route_after_queries(state: SectionState) -> Literal["search_web", "tools"]:
    """Route to either search_web or tools based on section type."""
    section = state["section"][0] if state["section"] else None
    if not section:
        return "search_web"
    
    # Check if this is a financial section
    is_financial_section = any(keyword in section.name.lower() for keyword in 
                             ["financial analysis", "stock", "price", "revenue"])
    
    # Only route to tools for financial sections
    if is_financial_section:
        # Check if we have ticker info
        ticker_info = state.get("ticker_info", [])
        has_ticker = len(ticker_info) > 0 and ticker_info[0].ticker_info and ticker_info[0].ticker_info.symbol
        
        print(f"[route_after_queries] Section: {section.name}, is_financial: {is_financial_section}, has_ticker: {has_ticker}")
        
        if has_ticker:
            print(f"[route_after_queries] Routing to tools for financial section with ticker: {ticker_info[0].ticker_info.symbol}")
            return "tools"
    
    print(f"[route_after_queries] Routing to search_web for section: {section.name}")
    return "search_web"

def should_continue(state: SectionState) -> Literal["tools", "write_section"]:
    """Determine if we need to continue with tools or move to writing."""
    messages = state.get("messages", [])
    if not messages:
        return "write_section"
    
    # Get the last few messages to check the sequence
    last_messages = messages[-3:] if len(messages) >= 3 else messages
    
    for msg in reversed(last_messages):
        if isinstance(msg, ToolMessage):
            print("[should_continue] Found tool message with results, moving to write_section")
            return "write_section"
        if isinstance(msg, AIMessage) and msg.content == "Financial data has been successfully retrieved.":
            print("[should_continue] Found acknowledgment message, moving to write_section")
            return "write_section"
        if isinstance(msg, AIMessage) and msg.tool_calls:
            print("[should_continue] Found pending tool calls, continuing with tools")
            return "tools"
    print("[should_continue] No tool-related messages found, moving to write_section")
    return "write_section"

async def call_model(state: SectionState, config: RunnableConfig) -> dict:
    """Call the model to process the current state and determine next actions."""
    # Get state
    messages = state.get("messages", [])
    if not messages:
        return state

    # print("Current messages in state:", messages)
    
    # Check if we have a ToolMessage with results
    tool_message = next((msg for msg in reversed(messages) 
                        if isinstance(msg, ToolMessage)), None)
    
    if tool_message:
        # acknowledgment 메시지 추가
        if not any(isinstance(msg, AIMessage) and msg.content == "Financial data has been successfully retrieved." for msg in messages):
            acknowledgment_message = AIMessage(
                content="Financial data has been successfully retrieved.",
                tool_calls=[]
            )
            # tool call 메시지 제거
            messages = [msg for msg in messages if not (isinstance(msg, AIMessage) and msg.tool_calls)]
            return {"messages": messages + [acknowledgment_message]}
        return {"messages": messages}
    
    # If no tool message, look for AIMessage with tool calls
    last_message = next((msg for msg in reversed(messages) 
                        if isinstance(msg, AIMessage) and msg.tool_calls), None)
    
    if not last_message:
        print("No message with tool calls found, returning state")
        return state
    
    # print("Found message with tool calls:", last_message)
    
    # If we don't have tool call results yet, proceed with model call
    configurable = Configuration.from_runnable_config(config)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider)
    
    # Create a new message that combines the tool call with a clear instruction
    tool_instruction = HumanMessage(content=(
        f"I need to get financial data for {last_message.tool_calls[0]['args']['ticker']}. "
        "Please use the company_financials tool to fetch this data."
    ))
    
    # Call the model with just the tool instruction
    try:
        response = await writer_model.ainvoke([tool_instruction])
        # print("Model response:", response)
        
        # Create a new AIMessage that includes both the response and the tool calls
        tool_calls = [{
            "id": call["id"],
            "name": call["name"],
            "args": call["args"],
            "type": "function"
        } for call in last_message.tool_calls]
        
        combined_message = AIMessage(
            content=response.content,
            tool_calls=tool_calls
        )
        
        # Add the combined message to the messages
        updated_messages = messages + [combined_message]
        return {"messages": updated_messages}
    except Exception as e:
        print(f"Error calling model: {str(e)}")
        return {"messages": messages}

section_builder.add_node("call_model", call_model)
section_builder.add_node("tools", ToolNode(ALL_TOOLS_LIST, messages_key="messages"))
section_builder.add_node("write_section", write_section)

# Add edges
section_builder.add_edge(START, "generate_queries")
section_builder.add_conditional_edges(
    "generate_queries",
    route_after_queries,
    {
        "search_web": "search_web",
        "tools": "call_model"  # Route to call_model first
    }
)

# Add edges for handling tool calls
section_builder.add_conditional_edges(
    "call_model",
    should_continue,
    {
        "tools": "tools",
        "write_section": "write_section"
    }
)
section_builder.add_edge("tools", "call_model")  # After tools, go back to call_model
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
