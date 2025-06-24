"""Simple chat agent using LangGraph."""

import logging
import os
from typing import Optional, Annotated, Sequence, TypedDict
import json

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph.message import add_messages
from langgraph.graph.ui import AnyUIMessage, ui_message_reducer, push_ui_message
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from ui_graph.prompts import get_coding_prompt
from ui_graph.tools import generate_shadcn_widget


# Configure logging to hide INFO messages
logging.basicConfig(level=logging.INFO)

# Initialize global LLM
VLLM_API_URL = os.getenv("VLLM_API_URL")
llm: Optional[ChatGoogleGenerativeAI] = None

UI_COMPONENT_NAME = "ui_graph"


class AgentState(TypedDict):  # noqa: D101
    messages: Annotated[Sequence[BaseMessage], add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]


def get_llm() -> ChatGoogleGenerativeAI:
    """Get or initialize the LLM with shadcn tools bound."""
    global llm
    if llm is None:
        llm = ChatOpenAI(model="gpt-4o-mini")
        # llm = ChatGoogleGenerativeAI(
        #     model="gemini-2.5-flash-preview-05-20",
        #     temperature=0.5
        # )
    return llm


tool_node = ToolNode([generate_shadcn_widget])

model = get_llm()
model_with_tools = model.bind_tools([generate_shadcn_widget],
                                    tool_choice="any",
                                    strict=True)


def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END


async def call_model(state: AgentState):
    messages = [{"role": "system", "content": get_coding_prompt()}] + \
        state["messages"]
    response = await model_with_tools.ainvoke(messages)

    artifact = extract_artifact_from_response(response)

    class Code(TypedDict):
        code: str
    code: Code = {
        "code": artifact
    }

    push_ui_message(UI_COMPONENT_NAME, code, message=response)
    logging.info(f"code: {code}")
    logging.info(f"response: {response}")

    return {
        "messages": [response],
    }


def extract_artifact_from_response(response: AIMessage) -> Optional[str]:
    # 1. Get tool_calls from additional_kwargs
    tool_calls = response.additional_kwargs.get("tool_calls", [])
    for tool_call in tool_calls:
        # 2. Get the function arguments (as a JSON string)
        function = tool_call.get("function", {})
        arguments = function.get("arguments")
        if arguments:
            try:
                # 3. Parse the arguments JSON string
                args_dict = json.loads(arguments)
                # 4. Extract the artifact
                artifact = args_dict.get("artifact")
                if artifact:
                    return artifact
            except Exception as e:
                print(f"Error parsing tool call arguments: {e}")
    return None


"""Build and return the chat graph."""

# Initialize graph builder with new state schema
workflow = StateGraph(AgentState)

# Add chatbot node
workflow.add_node("call_model", call_model)
workflow.add_node("tools", tool_node)

# Add edges - start at chatbot and can end after chatbot
workflow.add_edge(START, "call_model")
workflow.add_edge("call_model", END)

# workflow.add_conditional_edges("call_model", should_continue, ["tools", END])
# workflow.add_edge("tools", END)

# Compile graph
graph = workflow.compile()
graph.name = UI_COMPONENT_NAME

__all__ = ["graph"]
