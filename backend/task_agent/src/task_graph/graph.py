"""Task agent using LangGraph."""

from typing import Literal
import logging
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.store.base import BaseStore
from langgraph.types import Command, interrupt
from langgraph.prebuilt.interrupt import (
    ActionRequest,
    HumanInterrupt,  
    HumanInterruptConfig,
    HumanResponse,
)

from task_graph.configuration import TaskConfigurable
from blog_graph.graph import graph as blog_graph
from chat_graph.graph import graph as chat_graph
from news_graph.graph import graph as news_graph
from thothy.backend.libs.utils import (  # type: ignore
    initialize_store
)

# Initialize store with reconnection capability
store = initialize_store()
llm = init_chat_model("gpt-4o-mini", model_provider="openai", temperature=0.8)


def start_node(
    state: MessagesState,
    config: TaskConfigurable
) -> dict:
    """Start node that processes state and adds user message if latest is AI message."""

    logging.info(f"Start node: {state}")
    logging.info(f"messages: {state.get('messages')}")

    messages = state.get("messages", [])

    # Check if we have messages and if the latest message is an AI message
    if messages and isinstance(messages[-1], AIMessage):
        # Find the first user message in the conversation
        first_user_message = None
        for msg in messages:
            if isinstance(msg, HumanMessage):
                first_user_message = HumanMessage(content=msg.content)
                break

        # If we found a first user message, add it to the message list
        if first_user_message:
            logging.info(
                f"Adding first user message back to state: {first_user_message.content}")
            updated_messages = messages + [first_user_message]
            logging.info(f"first_user_message: {first_user_message}")
            logging.info(f"updated messages: {updated_messages}")
            return {"messages": updated_messages}

    # Return the state as-is if no changes needed
    return state


async def task_assistant(
    state: MessagesState,
    config: TaskConfigurable,
    *,
    store: BaseStore
) -> dict:
    """Task assistant node that processes messages and generates responses."""

    logging.info(f"Task assistant: {state}")
    logging.info(f"messages: {state.get('messages')}")

    # Get configurable values
    configurable = TaskConfigurable.from_runnable_config(config)
    graph_name = configurable.graph_name

    # Route to the appropriate agent based on graph_name
    if graph_name == "blog_graph":
        # Call blog agent
        result = await blog_graph.ainvoke(state, config)
    elif graph_name == "news_graph":
        # Call news agent
        result = await news_graph.ainvoke(state, config)
    elif graph_name == "chat_graph":
        # Call chat agent
        result = await chat_graph.ainvoke(state, config)
    else:
        raise ValueError(f"Invalid graph_name: {graph_name}")

    response = result["messages"][-1]

    # Wrap response with AIMessage type and return as list
    if not isinstance(response, AIMessage):
        response = AIMessage(content=str(response.content) if hasattr(
            response, 'content') else str(response))

    return {"messages": [response]}


def task_feedback(state: MessagesState, config: TaskConfigurable) -> Command[Literal["start_node"]]:
    """Get human feedback on the task response and handle user interaction."""

    logging.info(f"Task feedback: {state}")
    logging.info(f"messages: {state.get('messages')}")

    # Get the latest message and response
    messages = state.get("messages", [])
    if not messages:
        return Command(goto="start_node")

    latest_response = messages[-1]
    user_message = messages[-2] if len(messages) > 1 else None

    # Get configurable values for context
    configurable = TaskConfigurable.from_runnable_config(config)
    project_id = configurable.project_id
    graph_name = configurable.graph_name

    action_request = ActionRequest(
        action="Review Task Response",
        args={
            "project_id": project_id,
            "graph_name": graph_name,
            "user_request": user_message.content if user_message else "",
            "agent_response": latest_response.content if hasattr(latest_response, 'content') else str(latest_response),
        }
    )

    interrupt_config = HumanInterruptConfig(
        allow_ignore=True,
        allow_respond=True,
        allow_edit=False,
        allow_accept=True
    )

    description = f"""Task Agent ({graph_name}) has completed processing your request.

You can:
- Accept the response as-is
- Provide additional feedback or follow-up questions
- Ignore to end the conversation

Project ID: {project_id}
Agent Type: {graph_name}"""

    request = HumanInterrupt(
        action_request=action_request,
        config=interrupt_config,
        description=description
    )

    human_response: HumanResponse = interrupt([request])[0]
    logging.info(f"Human response: {human_response}")

    # return {"messages": [latest_response]}

    if human_response.get("type") == "accept":
        return Command(goto="start_node", update={"messages": [latest_response]})
    elif human_response.get("type") == "response":
        # Add the human response as a new message and continue processing
        new_message = HumanMessage(
            content=f"Follow-up: {human_response.get('args', '')}")
        return Command(
            update={"messages": [new_message]},
            goto="task_assistant"
        )
    elif human_response.get("type") == "ignore":
        return Command(goto="start_node", update={"messages": [latest_response]})
    else:
        return Command(goto="start_node", update={"messages": [latest_response]})


"""Build and return the task graph."""

# Initialize graph builder with state schema
workflow = StateGraph(MessagesState, TaskConfigurable)

# Add nodes
workflow.add_node("start_node", start_node)
workflow.add_node("task_assistant", task_assistant)
workflow.add_node("task_feedback", task_feedback)

# Add edges - start at start_node, then task_assistant, then feedback, then back to start_node
workflow.add_edge(START, "start_node")
workflow.add_edge("start_node", "task_assistant")
workflow.add_edge("task_assistant", "task_feedback")
workflow.add_edge("task_feedback", "start_node")

# Compile graph
graph = workflow.compile(store=store)
graph.name = "task_graph"
