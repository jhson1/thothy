import asyncio
import base64
import os
import uuid
import aiohttp
from langchain_google_genai import ChatGoogleGenerativeAI
from openai import OpenAI
from supabase import create_client, Client

from slide_graph.ppt_generator.models.query_and_prompt_models import (
    ImagePromptWithThemeAndAspectRatio,
)
from slide_graph.api.utils import get_resource

BUCKET_NAME = "slide-agent-images"


async def upload_image_to_supabase_store(image_path: str, presentation_id: str) -> str:
    """Upload image to Supabase storage and return the public URL"""
    try:
        # Initialize Supabase client
        supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            print("Supabase credentials not found")
            return image_path

        supabase: Client = create_client(supabase_url, supabase_key)

        # Extract filename from path
        filename = os.path.basename(image_path)

        # Create folder path with presentation_id
        storage_path = f"{presentation_id}/{filename}"

        # Read image file
        with open(image_path, 'rb') as f:
            image_data = f.read()

        # Upload to Supabase storage bucket
        result = supabase.storage.from_(BUCKET_NAME).upload(
            storage_path, image_data, {"content-type": "image/jpeg"}
        )

        # Check if result is None
        if result is None:
            print("Upload result is None")
            return image_path

        # Check for upload errors - handle both dict and object formats
        if hasattr(result, 'error') and result.error:
            print(f"Error uploading to Supabase (object): {result.error}")
            return image_path
        elif isinstance(result, dict) and result.get("error"):
            print(f"Error uploading to Supabase (dict): {result['error']}")
            return image_path

        # Get public URL
        public_url_response = supabase.storage.from_(
            BUCKET_NAME).get_public_url(storage_path)

        # Check if public_url_response is None
        if public_url_response is None:
            print("Public URL response is None")
            return image_path

        # Extract URL from response according to Supabase docs
        # The response should be: { data: { publicUrl: "..." } }
        if hasattr(public_url_response, 'data') and hasattr(public_url_response.data, 'publicUrl'):
            public_url = public_url_response.data.publicUrl
        elif isinstance(public_url_response, dict) and 'data' in public_url_response:
            if isinstance(public_url_response['data'], dict) and 'publicUrl' in public_url_response['data']:
                public_url = public_url_response['data']['publicUrl']
            elif isinstance(public_url_response['data'], str):
                public_url = public_url_response['data']
            else:
                print(
                    f"Unexpected data structure in response: {public_url_response['data']}")
                return image_path
        elif hasattr(public_url_response, 'url'):
            # Fallback for older versions
            public_url = public_url_response.url
        elif isinstance(public_url_response, str):
            # Direct string response
            public_url = public_url_response
        else:
            print(
                f"Unexpected public URL response format: {type(public_url_response)} - {public_url_response}")
            return image_path

        # Final check if URL is valid
        if not public_url or public_url == "None":
            print("Generated public URL is invalid")
            return image_path

        # Remove trailing question mark if present
        # This can happen when Supabase URL generation includes empty query parameters
        if public_url.endswith('?'):
            public_url = public_url.rstrip('?')
            print(f"Removed trailing question mark from URL: {public_url}")

        print(f"Image uploaded to Supabase: {public_url}")
        return public_url

    except Exception as e:
        print(f"Error uploading image to Supabase: {e}")
        import traceback
        traceback.print_exc()
        return image_path


async def generate_image(
    input: ImagePromptWithThemeAndAspectRatio,
    output_directory: str,
    presentation_id: str,
) -> tuple[str, str]:  # Returns (local_path, supabase_url)
    image_prompt = f"{input.image_prompt}, {input.theme_prompt}"
    print(f"Request - Generating Image for {image_prompt}")

    try:
        image_gen_func = (
            generate_image_openai
            if os.getenv("LLM") == "openai"
            else generate_image_google
        )
        image_path = await image_gen_func(image_prompt, output_directory)

        if image_path and os.path.exists(image_path):
            # Upload image to Supabase storage
            supabase_url = await upload_image_to_supabase_store(image_path, presentation_id)
            print(
                f"Generated image - Local: {image_path}, Supabase: {supabase_url}")
            return image_path, supabase_url  # Return both local path and Supabase URL
        raise Exception(f"Image not found at {image_path}")

    except Exception as e:
        print(f"Error generating image: {e}")
        import traceback
        traceback.print_exc()
        placeholder_path = get_resource("assets/images/placeholder.jpg")
        print(
            f"Returning placeholder - Local: {placeholder_path}, Supabase: {placeholder_path}")
        return placeholder_path, placeholder_path  # Return same path for both if error


async def generate_image_openai(prompt: str, output_directory: str) -> str:
    client = OpenAI()
    result = await asyncio.to_thread(
        client.images.generate,
        model="dall-e-3",
        prompt=prompt,
        n=1,
        quality="standard",
        size="1024x1024",
    )
    image_url = result.data[0].url
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            image_bytes = await response.read()
            image_path = os.path.join(
                output_directory, f"{str(uuid.uuid4())}.jpg")
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            return image_path


async def generate_image_google(prompt: str, output_directory: str) -> str:
    response = await ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-preview-image-generation"
    ).ainvoke([prompt], generation_config={"response_modalities": ["TEXT", "IMAGE"]})

    image_block = next(
        block
        for block in response.content
        if isinstance(block, dict) and block.get("image_url")
    )

    base64_image = image_block["image_url"].get("url").split(",")[-1]
    image_path = os.path.join(output_directory, f"{str(uuid.uuid4())}.jpg")
    with open(image_path, "wb") as f:
        f.write(base64.b64decode(base64_image))

    return image_path
