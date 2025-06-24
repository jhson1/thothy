"""Simple slide agent using LangGraph."""

import logging
import uuid
import json
from typing import Optional, List, TypedDict, Annotated, Sequence

from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.ui import AnyUIMessage, ui_message_reducer, push_ui_message
from langgraph.store.base import BaseStore
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from dashboard_graph.configuration import SlideConfigurable
from dashboard_graph.api.routers.presentation.handlers.generate_presentation_requirements import (
    GeneratePresentationRequirementsHandler,
)
from dashboard_graph.api.routers.presentation.handlers.generate_titles import (
    PresentationTitlesGenerateHandler,
)
from dashboard_graph.api.routers.presentation.handlers.generate_data import (
    PresentationGenerateDataHandler,
)
from dashboard_graph.api.routers.presentation.handlers.generate_stream import (
    PresentationGenerateStreamHandler,
)
from dashboard_graph.api.routers.presentation.handlers.update_slide_models import (
    UpdateSlideModelsHandler,
)
from dashboard_graph.api.routers.presentation.models import (
    GeneratePresentationRequirementsRequest,
    GenerateTitleRequest,
    PresentationGenerateRequest,
    PresentationUpdateRequest,
    PresentationAndSlides,
)
from dashboard_graph.api.sql_models import PresentationSqlModel
from dashboard_graph.api.services.logging import LoggingService
from dashboard_graph.api.models import LogMetadata, SessionModel
from dashboard_graph.ppt_generator.models.slide_model import SlideModel

# UI Component name for slide agent
UI_COMPONENT_NAME = "slide_graph"
UI_COMPONENT_ID = str(uuid.uuid4())


class PresentationState(TypedDict):
    """State for the presentation workflow."""
    # Input parameters
    prompt: Optional[str]
    n_slides: int
    language: str
    documents: Optional[List[str]]
    research_reports: Optional[List[str]]
    images: Optional[List[str]]

    # Intermediate and output data
    presentation_id: Optional[str]
    presentation: Optional[PresentationSqlModel]

    # New fields for generate data and stream processes
    theme: Optional[dict]
    titles: Optional[List[str]]
    watermark: Optional[bool]
    session: Optional[str]
    session_model: Optional[SessionModel]
    stream_result: Optional[dict]

    # Fields for update slides process
    slides: Optional[List[SlideModel]]
    presentation_and_slides: Optional[PresentationAndSlides]

    # UI messages field
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]

    # Messages field
    messages: Annotated[Sequence[BaseMessage], add_messages]

    error: Optional[str]


llm: Optional[ChatGoogleGenerativeAI] = None


def extract_prompt_from_state(state: PresentationState) -> str:
    """Extract prompt from state messages or fallback to direct prompt field."""
    prompt = ""

    # Try to get prompt from messages first
    if state.get("messages"):
        # Get the last user/human message content as prompt
        for message in reversed(state["messages"]):
            if hasattr(message, 'content') and message.content:
                # Prefer human messages over AI messages for prompts
                if hasattr(message, 'type') and message.type in ['human', 'user']:
                    prompt = message.content
                    break
                elif not prompt:  # Use any message content as fallback
                    prompt = message.content

    # Fallback to direct prompt field if no message content found
    if not prompt:
        prompt = state.get("prompt", "")

    return prompt


def get_llm() -> ChatGoogleGenerativeAI:
    """Get or initialize the LLM asynchronously."""
    global llm
    if llm is None:
        llm = init_chat_model(
            model="gemini-2.5-flash-preview-05-20", model_provider="google_genai")
    return llm


async def create_presentation_node(
    state: PresentationState,
    config: SlideConfigurable,
    *,
    store: BaseStore
) -> dict:
    """Node that creates a presentation using the GeneratePresentationRequirementsHandler."""

    try:
        # Generate a unique presentation ID
        presentation_id = str(uuid.uuid4())

        # Extract prompt from messages or fallback to direct prompt field
        prompt = extract_prompt_from_state(state)

        # Create the request object
        request_data = GeneratePresentationRequirementsRequest(
            prompt=prompt,
            n_slides=int(state.get("n_slides", 10)),
            language=state.get("language", "en"),
            documents=state.get("documents", []),
            research_reports=state.get("research_reports", []),
            images=state.get("images", [])
        )

        # Create mock logging service and metadata for the handler
        # Note: In a real implementation, you'd want to properly initialize these
        logging_service = LoggingService()
        log_metadata = LogMetadata(
            presentation_id=presentation_id,
            endpoint="/ppt/create"
        )

        # Call the GeneratePresentationRequirementsHandler
        presentation = await GeneratePresentationRequirementsHandler(
            presentation_id, request_data).post(logging_service, log_metadata)

        return {
            "presentation_id": presentation_id,
            "presentation": presentation,
            "error": None
        }

    except Exception as e:
        return {
            "error": f"Failed to create presentation: {str(e)}"
        }


async def generate_titles_node(
    state: PresentationState,
    config: SlideConfigurable,
    *,
    store: BaseStore
) -> dict:
    """Node that generates titles for the presentation using PresentationTitlesGenerateHandler."""

    try:
        # Check if we have a presentation ID from the previous step
        if not state.get("presentation_id"):
            return {"error": "No presentation ID available from previous step"}

        # Create the request object
        request_data = GenerateTitleRequest(
            presentation_id=state["presentation_id"]
        )

        # Create mock logging service and metadata for the handler
        logging_service = LoggingService()
        log_metadata = LogMetadata(
            presentation_id=state["presentation_id"],
            endpoint="/ppt/titles/generate"
        )

        # Call the PresentationTitlesGenerateHandler
        presentation = await PresentationTitlesGenerateHandler(
            request_data).post(logging_service, log_metadata)

        return {
            "presentation": presentation,
            "titles": presentation.titles,
            "error": None
        }

    except Exception as e:
        return {
            "error": f"Failed to generate titles: {str(e)}"
        }


async def generate_data_node(
    state: PresentationState,
    config: SlideConfigurable,
    *,
    store: BaseStore
) -> dict:
    """Node that generates presentation data using PresentationGenerateDataHandler."""

    try:
        # Check if we have required data from previous steps
        if not state.get("presentation_id"):
            return {"error": "No presentation ID available from previous step"}

        if not state.get("titles"):
            return {"error": "No titles available from previous step"}

        # Create the request object
        request_data = PresentationGenerateRequest(
            presentation_id=state["presentation_id"],
            theme=state.get("theme"),
            images=state.get("images", []),
            watermark=state.get("watermark", True),
            titles=state["titles"]
        )

        # Create logging service and metadata for the handler
        logging_service = LoggingService()
        log_metadata = LogMetadata(
            presentation_id=state["presentation_id"],
            endpoint="/ppt/generate/data"
        )

        # Call the PresentationGenerateDataHandler
        session_model = await PresentationGenerateDataHandler(
            request_data).post(logging_service, log_metadata)

        return {
            "session": session_model.session,
            "session_model": session_model,
            "error": None
        }

    except Exception as e:
        return {
            "error": f"Failed to generate presentation data: {str(e)}"
        }


async def generate_stream_node(
    state: PresentationState,
    config: SlideConfigurable,
    *,
    store: BaseStore
) -> dict:
    """Node that generates presentation stream using PresentationGenerateStreamHandler."""

    try:
        # Check if we have required data from previous steps
        if not state.get("presentation_id"):
            return {"error": "No presentation ID available from previous step"}

        if not state.get("session"):
            return {"error": "No session available from previous step"}

        # Create logging service and metadata for the handler
        logging_service = LoggingService()
        log_metadata = LogMetadata(
            presentation_id=state["presentation_id"],
            endpoint="/ppt/generate/stream"
        )

        # Create the handler and call get method to get StreamingResponse
        handler = PresentationGenerateStreamHandler(
            state["presentation_id"], state["session"])

        # Call the get method which returns a StreamingResponse
        streaming_response = await handler.get(logging_service, log_metadata)

        # Extract the body_iterator from StreamingResponse and collect results
        stream_results = []
        async for result in streaming_response.body_iterator:
            stream_results.append(result)

        return {
            "stream_result": {"results": stream_results},
            "error": None
        }

    except Exception as e:
        return {
            "error": f"Failed to generate presentation stream: {str(e)}"
        }


async def update_slides_node(
    state: PresentationState,
    config: SlideConfigurable,
    *,
    store: BaseStore
) -> dict:
    """Node that updates slides using UpdateSlideModelsHandler."""

    try:
        # Check if we have required data for slide updates
        if not state.get("presentation_id"):
            return {"error": "No presentation ID available for slide update"}

        if not state.get("stream_result"):
            return {"error": "No stream result available for slide update"}

        # Create logging service for debugging
        logging_service = LoggingService()
        log_metadata = LogMetadata(
            presentation_id=state["presentation_id"],
            endpoint="/ppt/slides/update"
        )

        # Find the "complete" event in stream results
        slides_data = None
        stream_results = state["stream_result"].get("results", [])

        for result in stream_results:
            try:
                # Handle both string and bytes data
                if isinstance(result, bytes):
                    result_str = result.decode('utf-8')
                else:
                    result_str = str(result)

                # Handle SSE format - split by lines and look for data lines
                lines = result_str.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('data: '):
                        data_line = line[6:].strip()  # Remove 'data: ' prefix

                        # Parse JSON data
                        if data_line and not data_line.startswith('[DONE]'):
                            try:
                                data = json.loads(data_line)

                                logging.info(f"Parsed stream data: {data}")

                                # Check if this is the completion event
                                if data.get("type") == "complete" and "presentation" in data:
                                    presentation_data = data["presentation"]
                                    if "slides" in presentation_data:
                                        slides_data = presentation_data["slides"]

                                        logging.info(
                                            f"Found completion event with {len(slides_data)} slides")
                                        break

                            except json.JSONDecodeError as json_e:
                                logging.warning(
                                    f"Failed to parse JSON from data line: {json_e}")
                                continue

                # Break out of outer loop if we found slides_data
                if slides_data:
                    break

            except (UnicodeDecodeError, KeyError) as e:
                logging.warning(f"Failed to process stream result: {e}")
                continue

        if not slides_data:
            return {"error": "No completion event found in stream results"}

        # Convert slides data to SlideModel objects
        slides = []
        for slide_data in slides_data:
            try:
                slide_model = SlideModel.from_dict(slide_data)
                slides.append(slide_model)

                # Log both local and Supabase image URLs for verification
                if slide_model.images:
                    logging.info(
                        f"Slide {slide_model.index} local images: {slide_model.images}")
                if slide_model.supabase_images:
                    logging.info(
                        f"Slide {slide_model.index} Supabase images: {slide_model.supabase_images}")

            except Exception as e:
                return {"error": f"Failed to convert slide data to SlideModel: {str(e)}"}

        # Create the request object
        request_data = PresentationUpdateRequest(
            presentation_id=state["presentation_id"],
            slides=slides
        )

        # Call the UpdateSlideModelsHandler
        result = await UpdateSlideModelsHandler(request_data).post(
            logging_service, log_metadata
        )

        # Push UI message with result data
        push_ui_message(UI_COMPONENT_NAME, {
            "presentation_and_slides": result,
            "slides_count": len(slides),
            "presentation_id": state["presentation_id"],
            "local_images_count": sum(len(slide.images or []) for slide in slides),
            "supabase_images_count": sum(len(slide.supabase_images or []) for slide in slides)
        }, id=UI_COMPONENT_ID)

        from langchain_core.messages import AIMessage
        local_images_count = sum(len(slide.images or []) for slide in slides)
        supabase_images_count = sum(
            len(slide.supabase_images or []) for slide in slides)
        ai_message = AIMessage(
            content=f"Successfully generated presentation with {len(slides)} slides, {local_images_count} local images, and {supabase_images_count} Supabase-hosted images")

        return {
            "presentation_and_slides": result,
            "messages": [ai_message],
            "error": None
        }

    except Exception as e:
        return {
            "error": f"Failed to update slides: {str(e)}"
        }


"""Build and return the slide graph."""

# Initialize graph builder with state schema
workflow = StateGraph(PresentationState, SlideConfigurable)

# Add nodes
workflow.add_node("create_presentation", create_presentation_node)
workflow.add_node("generate_titles", generate_titles_node)
workflow.add_node("generate_data", generate_data_node)
workflow.add_node("generate_stream", generate_stream_node)
workflow.add_node("update_slides", update_slides_node)

# Add edges - sequential flow: create presentation -> generate titles -> generate data -> generate stream -> update slides
workflow.add_edge(START, "create_presentation")
workflow.add_edge("create_presentation", "generate_titles")
workflow.add_edge("generate_titles", "generate_data")
workflow.add_edge("generate_data", "generate_stream")
workflow.add_edge("generate_stream", "update_slides")
workflow.add_edge("update_slides", END)

# Compile graph
graph = workflow.compile()
graph.name = "slide_graph"
