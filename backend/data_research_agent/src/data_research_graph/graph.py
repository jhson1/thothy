from typing import Literal
import logging
from datetime import datetime, timedelta
import json

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
    ticker_writer_instructions,
    section_writer_instructions,
    financial_section_writer_instructions,
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
    select_and_execute_search,
    format_financial_table,
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

    logger.info(f"Topic extracted from latest message: {topic}")
    
    # Check if topic has changed
    previous_topic = state.get("previous_topic", "")
    topic_changed = previous_topic and previous_topic != topic
    
    if topic_changed:
        logger.info(f"TOPIC CHANGED: '{previous_topic}' → '{topic}' - COMPLETELY RESETTING ALL STATE")
        # When topic changes, reset EVERYTHING related to sections
        update_dict = {
            "topic": topic, 
            "previous_topic": topic,
            "completed_sections": [],  # Complete reset
            "report_sections_from_research": [],  # Complete reset
            "sections": [],  # Will be replaced with new sections
            "reset_sections": False,  # Clear any reset flags
            "final_report": ""  # Clear final report
        }
    else:
        logger.info(f"Topic unchanged or first time: {topic}")
        update_dict = {
            "topic": topic, 
            "previous_topic": topic,
            "reset_sections": False
        }

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
    logger.info(f"NEW SECTIONS GENERATED: {[s.name for s in sections]}")

    # Push the report sections to the UI with message
    global ui_message_id
    ai_message = AIMessage(
        content="Report sections generated successfully!"
    )
    ui_message = push_ui_message(
        UI_COMPONENT_NAME, {"topic": topic, "sections": sections})
    ui_message_id = ui_message["id"]

    # Add sections to the update dict - this will REPLACE existing sections completely
    update_dict["sections"] = sections
    update_dict["messages"] = [ai_message]

    logger.info(f"UPDATE DICT: topic={update_dict.get('topic')}, sections={len(update_dict.get('sections', []))}, completed_sections={len(update_dict.get('completed_sections', []))}")

    return update_dict


def human_feedback(state: ReportState, config: RunnableConfig) -> Command[Literal["generate_report_plan", "build_section_with_web_research"]]:
    """Get human feedback on the report plan and route to next steps.

    This node:
    1. Formats the current report plan for human review
    2. Gets feedback via an interrupt
    3. Routes to either:
       - Section writing if plan is approved (excluding financial sections)
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

    # Filter out financial analysis sections - they will be processed later
    non_financial_sections = [
        s for s in sections 
        if s.research and not any(keyword in s.name.lower() for keyword in ["financial analysis", "stock", "price", "revenue"])
    ]
    
    logger.info(f"Non-financial research sections: {[s.name for s in non_financial_sections]}")

    # Find the first non-financial research section
    next_section = next(iter(non_financial_sections), None)
    logger.info(f"next_section: {next_section}")

    if next_section:
        logger.info(f"Processing next non-financial section: {next_section.name}")
        return Command(goto=[
            Send(
                "build_section_with_web_research",
                {"topic": topic, "section": [next_section], "search_iterations": [0]}
            )
        ])
    else:
        # If all non-financial research sections are completed, move to final sections
        logger.info("All non-financial research sections completed, moving to gather completed sections")
        return Command(goto="gather_completed_sections")

    # TODO: Handle later
    human_response: HumanResponse = interrupt([request])[0]

    # TODO: Handle multiple feedbacks
    logger.info(f"human_response: {human_response}")

    # If the user approves the report plan, kick off section writing (excluding financial sections)
    if human_response.get("type") == "accept":
        return Command(goto=[
            Send(
                "build_section_with_web_research",
                {"topic": topic, "section": [s], "search_iterations": [0]}
            )
            for s in sections
            if s.research and not any(keyword in s.name.lower() for keyword in ["financial analysis", "stock", "price", "revenue"])
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

    Args:
        state: Current state containing section details
        config: Configuration including number of queries to generate

    Returns:
        Dict containing the generated search queries
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

    # Generate search queries
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider)
    
    # Use structured output for query generation
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
    
    # Add message for query generation
    query_message = AIMessage(
        content=f"Generated {len(general_results.queries)} search queries for the section."
    )
    messages = messages + [query_message]
    
    return {
        "search_queries": general_results.queries,
        "messages": messages
    }


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
    messages = state.get("messages", [])
    section = state["section"][0] if state["section"] else None
    
    if not section:
        raise ValueError("No section found in state for search")
    
    logger.info(f"Processing {len(search_queries)} search queries")

    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    search_api = get_config_value(configurable.search_api)
    search_api_config = configurable.search_api_config or {}
    params_to_pass = get_search_params(search_api, search_api_config)

    # Process queries
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
        "messages": messages
    }


async def write_section(state: SectionState, config: RunnableConfig) -> Command[Literal[END, "search_web"]]:
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
    section = state["section"][0] if state["section"] else None
    completed_sections = state.get("completed_sections", [])
    source_str = state["source_str"][-1] if state["source_str"] else ""
    messages = state.get("messages", [])

    if not section:
        raise ValueError("No section found in state for writing")

    # Check if we have source content
    if not source_str:
        print(f"[write_section] No source content available for section: {section.name}")
        error_message = AIMessage(
            content=f"Unable to generate content for section '{section.name}' due to missing source information."
        )
        return Command(
            update={"messages": messages + [error_message]},
            goto=END
        )

    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider)

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
    
    # Properly merge with existing sections to avoid duplicates
    logger.info(f"[write_section] Completing section: {section.name}")
    merged_sections = {s.name: s for s in completed_sections}
    
    if section.name in merged_sections:
        logger.info(f"[write_section] Replacing existing section: {section.name}")
    else:
        logger.info(f"[write_section] Adding new section: {section.name}")
    
    merged_sections[section.name] = temp_section
    final_sections = list(merged_sections.values())
    
    return Command(
        update={"completed_sections": final_sections},
        goto=END
    )


async def write_all_final_sections(state: ReportState, config: RunnableConfig):
    """Write all non-research sections that haven't been completed yet.
    
    This node processes all final sections (like conclusions, summaries) in sequence.
    
    Args:
        state: Current state with completed sections as context
        config: Configuration for the writing model
        
    Returns:
        Dict containing all newly written sections
    """
    # Get completed section names for filtering
    completed_names = {s.name for s in state.get("completed_sections", [])}
    
    # Get sections that don't require research and haven't been completed
    non_research_sections = [
        s for s in state["sections"]
        if not s.research and s.name not in completed_names
    ]
    
    logger.info(f"[write_all_final_sections] Current topic: {state.get('topic', 'N/A')}")
    logger.info(f"[write_all_final_sections] All sections: {[s.name for s in state['sections']]}")
    logger.info(f"[write_all_final_sections] Completed sections: {[s.name for s in state.get('completed_sections', [])]}")
    logger.info(f"[write_all_final_sections] Processing {len(non_research_sections)} non-research sections: {[s.name for s in non_research_sections]}")
    
    if not non_research_sections:
        logger.info("[write_all_final_sections] No non-research sections to process")
        # Keep existing completed sections
        existing_sections = state.get("completed_sections", [])
        return {"completed_sections": existing_sections}
    
    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider)
    
    # Get context from research sections
    completed_report_sections = "\n\n".join(
        state.get("report_sections_from_research", [])) if state.get("report_sections_from_research") else ""
    
    newly_completed = []
    
    for section in non_research_sections:
        try:
            logger.info(f"[write_all_final_sections] Writing final section: {section.name} for topic: {state['topic']}")
            
            # Format system instructions
            system_instructions = final_section_writer_instructions.format(
                topic=state["topic"], 
                section_name=section.name, 
                section_topic=section.description, 
                context=completed_report_sections
            )
            
            # Generate section content
            section_content = await writer_model.ainvoke([
                SystemMessage(content=system_instructions),
                HumanMessage(content="Generate a report section based on the provided sources.")
            ])
            
            # Create completed section
            temp_section = type(section)(
                name=section.name,
                description=section.description,
                research=section.research,
                content=section_content.content
            )
            newly_completed.append(temp_section)
            logger.info(f"[write_all_final_sections] Completed final section: {section.name}")
            
        except Exception as e:
            logger.error(f"[write_all_final_sections] Error processing final section {section.name}: {str(e)}")
            # Create section with error explanation
            temp_section = type(section)(
                name=section.name,
                description=section.description,
                research=section.research,
                content=f"Section could not be completed due to error: {str(e)}"
            )
            newly_completed.append(temp_section)
    
    # Simply merge with existing sections - no complex logic needed
    existing_sections = state.get("completed_sections", [])
    logger.info(f"[write_all_final_sections] Merging {len(newly_completed)} newly completed sections with {len(existing_sections)} existing sections")
    
    # Create merged dictionary to avoid duplicates
    merged_sections = {s.name: s for s in existing_sections}
    for section in newly_completed:
        if section.name in merged_sections:
            logger.info(f"[write_all_final_sections] Replacing existing section: {section.name}")
        else:
            logger.info(f"[write_all_final_sections] Adding new section: {section.name}")
        merged_sections[section.name] = section
    
    final_sections = list(merged_sections.values())
    logger.info(f"[write_all_final_sections] Final merged sections: {[s.name for s in final_sections]}")
    return {"completed_sections": final_sections}


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


async def process_financial_sections(state: ReportState, config: RunnableConfig):
    """Process financial sections separately using tools and financial data.

    This node:
    1. Identifies financial sections that haven't been completed
    2. For each financial section, fetches ticker information and comprehensive financial data
    3. Writes financial content using all retrieved data including statements and insider trades

    Args:
        state: Current state with all sections and completed sections
        config: Configuration for the workflow

    Returns:
        Dict with newly completed financial sections
    """
    # Get state
    topic = state["topic"]
    sections = state["sections"]
    completed_sections = state.get("completed_sections", [])
    
    # Find financial sections
    financial_sections = [
        s for s in sections 
        if s.research and any(keyword in s.name.lower() for keyword in ["financial analysis", "stock", "price", "revenue"])
    ]
    
    logger.info(f"Processing {len(financial_sections)} financial sections")
    
    # If no financial sections to process, return current state
    if not financial_sections:
        return {"completed_sections": completed_sections}
    
    # Get configuration
    configurable = Configuration.from_runnable_config(config)
    writer_provider = get_config_value(configurable.writer_provider)
    writer_model_name = get_config_value(configurable.writer_model)
    writer_model = init_chat_model(model=writer_model_name, model_provider=writer_provider)
    
    newly_completed = []
    
    for section in financial_sections:
        try:
            # Step 1: Get ticker symbol
            ticker_instructions = ticker_writer_instructions.format(
                topic=topic,
                section_topic=section.description
            )
            
            ticker_response = await writer_model.ainvoke([
                SystemMessage(content=ticker_instructions),
                HumanMessage(content="Find the ticker symbol for the company mentioned in the topic.")
            ])
            
            ticker_symbol = ticker_response.content.strip() if ticker_response.content else None
            
            if not ticker_symbol:
                logger.warning(f"No ticker symbol found for financial section: {section.name}")
                # Create a section with explanation of missing data
                temp_section = type(section)(
                    name=section.name,
                    description=section.description,
                    research=section.research,
                    content="Financial analysis could not be completed due to missing ticker symbol."
                )
                newly_completed.append(temp_section)
                continue
            
            logger.info(f"Found ticker symbol: {ticker_symbol} for section: {section.name}")
            
            # Step 2: Fetch comprehensive financial data using all tools
            from data_research_graph.tools import ALL_TOOLS_LIST
            
            # Find all financial tools
            financial_tools = {
                "company_financials": next((tool for tool in ALL_TOOLS_LIST if tool.name == "company_financials"), None),
                "income_statements": next((tool for tool in ALL_TOOLS_LIST if tool.name == "income_statements"), None),
                "balance_sheets": next((tool for tool in ALL_TOOLS_LIST if tool.name == "balance_sheets"), None),
                "cash_flow_statements": next((tool for tool in ALL_TOOLS_LIST if tool.name == "cash_flow_statements"), None),
                "insider_trades": next((tool for tool in ALL_TOOLS_LIST if tool.name == "insider_trades"), None),
            }
            
            # Collect all financial data
            financial_data = {}
            
            # Get stock prices and predictions
            if financial_tools["company_financials"]:
                try:
                    price_data = await financial_tools["company_financials"].ainvoke({
                        "ticker": ticker_symbol,
                        "start_date": None,
                        "end_date": None
                    })
                    financial_data["prices"] = price_data
                    logger.info(f"Successfully retrieved price data for {ticker_symbol}")
                except Exception as e:
                    logger.error(f"Error fetching price data: {str(e)}")
                    financial_data["prices"] = None
            
            # Get income statements
            if financial_tools["income_statements"]:
                try:
                    income_data = await financial_tools["income_statements"].ainvoke({"ticker": ticker_symbol})
                    financial_data["income_statements"] = income_data[1].get("income_statements") if isinstance(income_data, tuple) else income_data
                    logger.info(f"Successfully retrieved income statements for {ticker_symbol}")
                except Exception as e:
                    logger.error(f"Error fetching income statements: {str(e)}")
                    financial_data["income_statements"] = None
            
            # Get balance sheets  
            if financial_tools["balance_sheets"]:
                try:
                    balance_data = await financial_tools["balance_sheets"].ainvoke({"ticker": ticker_symbol})
                    financial_data["balance_sheets"] = balance_data[1].get("balance_sheets") if isinstance(balance_data, tuple) else balance_data
                    logger.info(f"Successfully retrieved balance sheets for {ticker_symbol}")
                except Exception as e:
                    logger.error(f"Error fetching balance sheets: {str(e)}")
                    financial_data["balance_sheets"] = None
            
            # Get cash flow statements
            if financial_tools["cash_flow_statements"]:
                try:
                    cashflow_data = await financial_tools["cash_flow_statements"].ainvoke({"ticker": ticker_symbol})
                    financial_data["cash_flow_statements"] = cashflow_data[1].get("cash_flow_statements") if isinstance(cashflow_data, tuple) else cashflow_data
                    logger.info(f"Successfully retrieved cash flow statements for {ticker_symbol}")
                except Exception as e:
                    logger.error(f"Error fetching cash flow statements: {str(e)}")
                    financial_data["cash_flow_statements"] = None
            
            # Get insider trades
            if financial_tools["insider_trades"]:
                try:
                    insider_data = await financial_tools["insider_trades"].ainvoke({"ticker": ticker_symbol})
                    financial_data["insider_trades"] = insider_data[1].get("insider_trades") if isinstance(insider_data, tuple) else insider_data
                    logger.info(f"Successfully retrieved insider trades for {ticker_symbol}")
                except Exception as e:
                    logger.error(f"Error fetching insider trades: {str(e)}")
                    financial_data["insider_trades"] = None
            
            if not any(financial_data.values()):
                logger.warning(f"No financial data retrieved for ticker: {ticker_symbol}")
                temp_section = type(section)(
                    name=section.name,
                    description=section.description,
                    research=section.research,
                    content=f"Financial analysis for {ticker_symbol} could not be completed due to missing financial data."
                )
                newly_completed.append(temp_section)
                continue
            
            # Step 3: Format all financial data and generate comprehensive section content
            # Format price data
            price_data_rows = ""
            predicted_price_rows = ""
            if financial_data["prices"]:
                price_info = financial_data["prices"]
                if isinstance(price_info, str):
                    price_info = json.loads(price_info)
                
                prices = price_info.get("prices", {}).get("prices", [])
                if prices:
                    for price_entry in prices:
                        date = datetime.strptime(price_entry["time"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
                        open_price = f"{price_entry['open']:.2f}" if isinstance(price_entry['open'], (int, float)) else price_entry['open']
                        high_price = f"{price_entry['high']:.2f}" if isinstance(price_entry['high'], (int, float)) else price_entry['high']
                        low_price = f"{price_entry['low']:.2f}" if isinstance(price_entry['low'], (int, float)) else price_entry['low']
                        close_price = f"{price_entry['close']:.2f}" if isinstance(price_entry['close'], (int, float)) else price_entry['close']
                        volume = f"{price_entry['volume']:,}" if isinstance(price_entry['volume'], (int, float)) else price_entry['volume']
                        
                        price_data_rows += f"| {date} | {open_price} | {high_price} | {low_price} | {close_price} | {volume} |\n"
                
                # Format predictions
                predictions = price_info.get("predictions", {}).get("quantiles", [])
                if predictions and len(predictions) > 0:
                    predictions = predictions[0]
                    end_date = price_info.get("date_range", {}).get("end", "N/A")
                    # Generate prediction dates excluding weekends
                    pred_dates = []
                    n_pred = len(predictions)
                    
                    try:
                        start_pred_date = datetime.strptime(end_date, "%Y-%m-%d")
                        current = start_pred_date
                        while len(pred_dates) < n_pred:
                            current += timedelta(days=1)
                            if current.weekday() < 5:  # Monday to Friday only
                                pred_dates.append(current.strftime("%Y-%m-%d"))
                    except Exception:
                        pred_dates = [f"Day {i+1}" for i in range(n_pred)]
                    
                    predicted_price_rows = "| Date | Lower Bound | Close | Upper Bound |\n|------|-------------|-------|-------------|\n"
                    for i, day_vals in enumerate(predictions):
                        lower = float(day_vals[0])
                        close = float(day_vals[1]) 
                        upper = float(day_vals[2])
                        pred_date = pred_dates[i] if i < len(pred_dates) else f"Day {i+1}"
                        predicted_price_rows += f"| {pred_date} | {lower:.2f} | {close:.2f} | {upper:.2f} |\n"
            
            # Format financial statements data
            income_statements_section = format_financial_table(financial_data.get("income_statements"), "Income Statement")
            balance_sheets_section = format_financial_table(financial_data.get("balance_sheets"), "Balance Sheet") 
            cash_flow_section = format_financial_table(financial_data.get("cash_flow_statements"), "Cash Flow Statement")
            insider_trades_section = format_financial_table(financial_data.get("insider_trades"), "Insider Trades")
            
            # Generate comprehensive section content
            instructions = financial_section_writer_instructions.format(
                topic=topic,
                section_topic=section.description,
                ticker=ticker_symbol,
                price_data_rows=price_data_rows,
                predicted_price_rows=predicted_price_rows,
                income_statements_section=income_statements_section,
                balance_sheets_section=balance_sheets_section,
                cash_flow_section=cash_flow_section,
                insider_trades_section=insider_trades_section
            )
            
            section_content = await writer_model.ainvoke([
                SystemMessage(content=instructions),
                HumanMessage(content=f"Write a comprehensive financial analysis using all the provided data for {ticker_symbol}.")
            ])
            
            # Create completed section
            temp_section = type(section)(
                name=section.name,
                description=section.description,
                research=section.research,
                content=section_content.content
            )
            newly_completed.append(temp_section)
            logger.info(f"Successfully completed comprehensive financial section: {section.name}")
            
        except Exception as e:
            logger.error(f"Error processing financial section {section.name}: {str(e)}")
            # Create section with error explanation
            temp_section = type(section)(
                name=section.name,
                description=section.description,
                research=section.research,
                content=f"Financial analysis could not be completed due to technical error: {str(e)}"
            )
            newly_completed.append(temp_section)
    
    # Properly merge sections to avoid duplicates
    logger.info(f"[process_financial_sections] Merging {len(newly_completed)} newly completed sections with {len(completed_sections)} existing sections")
    
    # Create a merged dictionary to avoid duplicates
    merged_sections = {s.name: s for s in completed_sections}
    for section in newly_completed:
        if section.name in merged_sections:
            logger.info(f"[process_financial_sections] Replacing existing section: {section.name}")
        else:
            logger.info(f"[process_financial_sections] Adding new section: {section.name}")
        merged_sections[section.name] = section
    
    final_sections = list(merged_sections.values())
    logger.info(f"[process_financial_sections] Final merged sections: {[s.name for s in final_sections]}")
    
    return {"completed_sections": final_sections}


def compile_final_report(state: ReportState):
    """Compile all sections into the final report."""

    # Get sections
    sections = state["sections"]
    completed_sections_raw = state["completed_sections"]
    
    logger.info(f"[compile_final_report] Original sections: {[s.name for s in sections]}")
    logger.info(f"[compile_final_report] Completed sections: {[s.name for s in completed_sections_raw]}")
    
    # Simple deduplication - keep the last occurrence of each section name
    unique_completed = {}
    for section in completed_sections_raw:
        if section.name in unique_completed:
            logger.warning(f"[compile_final_report] Found duplicate section '{section.name}' - keeping the latest")
        unique_completed[section.name] = section
    
    completed_sections_list = list(unique_completed.values())
    logger.info(f"[compile_final_report] After deduplication: {len(completed_sections_list)} unique sections")
    
    # Create the lookup dictionary
    completed_sections = {s.name: s.content for s in completed_sections_list}

    # Create sections with completed content while maintaining original order
    temp_sections = []
    for section in sections:
        temp_section_content = completed_sections.get(section.name, "")
        if temp_section_content:
            logger.info(f"[compile_final_report] Adding section: {section.name}")
        else:
            logger.warning(f"[compile_final_report] Missing content for section: {section.name}")
        temp_sections.append(temp_section_content)

    global ui_message_id
    push_ui_message(UI_COMPONENT_NAME, {
                    "completed_sections": completed_sections_list}, id=ui_message_id)

    # Compile final report using sections
    all_sections = "\n\n".join(temp_sections)

    # Simple final check for duplicates in the final report
    section_pattern_counts = {}
    for section in sections:
        if section.name and temp_section_content:
            count = all_sections.count(f"## {section.name}")
            if count > 1:
                section_pattern_counts[section.name] = count
    
    if section_pattern_counts:
        logger.error(f"[compile_final_report] WARNING: Final report contains duplicate section headers: {section_pattern_counts}")

    return {"final_report": all_sections}


def route_after_web_research(state: ReportState) -> Literal["process_financial_sections"]:
    """After web research is complete, always go to financial sections."""
    return "process_financial_sections"


def route_after_financial(state: ReportState) -> Literal["gather_completed_sections"]:
    """After financial sections are complete, always gather completed sections."""
    return "gather_completed_sections"


def route_after_gather(state: ReportState) -> Literal["write_all_final_sections", "compile_final_report"]:
    """After gathering sections, check if final sections need to be written."""
    # Get completed section names for filtering
    completed_names = {s.name for s in state.get("completed_sections", [])}
    
    # Check for non-research sections that haven't been completed yet
    non_research_sections = [
        s for s in state["sections"]
        if not s.research and s.name not in completed_names
    ]
    
    if non_research_sections:
        logger.info(f"Writing {len(non_research_sections)} final sections: {[s.name for s in non_research_sections]}")
        return "write_all_final_sections"
    else:
        logger.info("No final sections to write, moving to compile report")
        return "compile_final_report"


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
builder.add_node("process_financial_sections", process_financial_sections)
builder.add_node("write_all_final_sections", write_all_final_sections)
builder.add_node("compile_final_report", compile_final_report)

# Add edges
builder.add_edge(START, "generate_report_plan")
builder.add_edge("generate_report_plan", "human_feedback")
builder.add_edge("build_section_with_web_research", "process_financial_sections")
builder.add_edge("process_financial_sections", "gather_completed_sections")
builder.add_conditional_edges("gather_completed_sections", route_after_gather,
                              {"write_all_final_sections": "write_all_final_sections",
                               "compile_final_report": "compile_final_report"})
builder.add_edge("write_all_final_sections", "compile_final_report")
builder.add_edge("compile_final_report", END)

graph = builder.compile()
