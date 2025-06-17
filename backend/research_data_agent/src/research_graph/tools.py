import os
import requests
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults

UI_COMPONENT_NAME = "research_graph"

FINANCIAL_DATASETS_API_KEY = os.getenv("FINANCIAL_DATASETS_API_KEY")
BASE_URL = "https://api.financialdatasets.ai"

def call_financial_dataset_api(endpoint: str, params: Dict[str, str]) -> Any:
    """Call the financial datasets API with the given endpoint and parameters."""
    if not FINANCIAL_DATASETS_API_KEY:
        raise RuntimeError("FINANCIAL_DATASETS_API_KEY is not set")
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, params=params, headers={
        "X-API-KEY": FINANCIAL_DATASETS_API_KEY
    })
    if not response.ok:
        try:
            res = response.json()
        except Exception:
            res = response.text
        raise RuntimeError(
            f"Failed to fetch data from {endpoint}. Response: {res}")
    return response.json()


class CompanyFinancialsInput(BaseModel):
    ticker: str = Field(..., description="The ticker symbol of the company. Example: 'AAPL'")
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format. Defaults to 30 days ago.")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format. Defaults to today.")


@tool("company_financials", args_schema=CompanyFinancialsInput)
def company_financials_tool(input: CompanyFinancialsInput = None, **kwargs) -> dict:
    """Fetches comprehensive financial data for a company including price history and other financial metrics."""
    print("company_financials_tool called with input:", input)
    print("company_financials_tool called with kwargs:", kwargs)
    
    # If input is None but we have kwargs, create input from kwargs
    if input is None and kwargs:
        try:
            input = CompanyFinancialsInput(**kwargs)
            print("Created input from kwargs:", input)
        except Exception as e:
            print(f"Error creating input from kwargs: {str(e)}")
            return {"error": f"Invalid input: {str(e)}"}
    
    if not input or not input.ticker:
        print("No ticker provided")
        return {"error": "No ticker provided"}
    
    try:
        # Set default dates if not provided
        current_date = datetime.now()
        end_date = input.end_date or current_date.strftime("%Y-%m-%d")
        if not input.start_date:
            start_date = (current_date - timedelta(days=30)).strftime("%Y-%m-%d")
        else:
            start_date = input.start_date

        print(f"Fetching financial data for {input.ticker} from {start_date} to {end_date}")
        
        # Make the API call directly using call_financial_dataset_api
        price_data = call_financial_dataset_api(
            "/prices",
            {
                "ticker": input.ticker,
                "interval": "day",
                "interval_multiplier": "1",
                "start_date": start_date,
                "end_date": end_date,
            }
        )

        print("API response:")
        
        if not price_data:
            print("No price data received from API")
            return {"error": "No price data available"}
        
        # Format the response
        result = {
            "ticker": input.ticker,
            "prices": price_data,
            "date_range": {
                "start": start_date,
                "end": end_date
            }
        }
        
        # print("Returning formatted result:", result)
        return result
        
    except Exception as e:
        print(f"Error in company_financials_tool: {str(e)}")
        return {"error": str(e)}


class CompanyFactsInput(BaseModel):
    ticker: str = Field(..., description="The ticker symbol of the company. Example: 'AAPL'")


@tool("company_facts", args_schema=CompanyFactsInput, response_format="content_and_artifact")
def company_facts_tool(input: CompanyFactsInput = None, **kwargs) -> Tuple[str, dict]:
    """Provides key facts and information about a specified company."""
    try:
        if input is None:
            input = CompanyFactsInput(**kwargs)
        data = call_financial_dataset_api(
            "/company/facts",
            {"ticker": input.ticker},
        )
        return str(data), {"title": "Company Facts", "company_facts": data}
    except Exception as e:
        return f"An error occurred while fetching company facts: {e}", {}


class PriceHistoryInput(BaseModel):
    ticker: str = Field(..., description="The ticker symbol of the company. Example: 'AAPL'")
    interval: Optional[str] = Field("day", description="The interval of the prices. Example: 'day'")
    interval_multiplier: Optional[str] = Field("1", description="The interval multiplier of the prices. Example: '1'")
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format. Defaults to 30 days ago.")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format. Defaults to today.")


@tool("price_history", args_schema=PriceHistoryInput, response_format="content_and_artifact")
def price_history_tool(input: PriceHistoryInput = None, **kwargs) -> Tuple[str, dict]:
    """Retrieves historical stock price data for a specific ticker between two dates."""
    try:
        if input is None:
            input = PriceHistoryInput(**kwargs)

        # Set default dates if not provided
        current_date = datetime.now()
        end_date = input.end_date or current_date.strftime("%Y-%m-%d")
        if not input.start_date:
            start_date = (current_date - timedelta(days=30)).strftime("%Y-%m-%d")
        else:
            start_date = input.start_date

        print(f"Fetching price history for {input.ticker} from {start_date} to {end_date}")

        data = call_financial_dataset_api(
            "/prices",
            {
                "ticker": input.ticker,
                "interval": input.interval,
                "interval_multiplier": input.interval_multiplier,
                "start_date": start_date,
                "end_date": end_date,
            }
        )

        return str(data), {"title": "Price History", "price_history": data}

    except Exception as e:
        return f"An error occurred while fetching price history: {e}", {}


@tool("web_search", args_schema=None, response_format="content_and_artifact")
async def web_search_tool(query: str) -> Tuple[str, dict]:
    """Search the web using Tavily and return the top result(s)."""
    try:
        tavily = TavilySearchResults(max_results=1)
        results = await tavily.ainvoke(query)
        if not results:
            return "No results found.", {"title": "Web Search", "web_search": "No results found."}
        # Tavily returns a list of dicts with 'title', 'url', and 'content'
        top = results[0]
        content = f"{top.get('title', '')}: {top.get('url', '')}\n{top.get('content', '')}"
        return content, {"title": "Web Search", "web_search": top}
    except Exception as e:
        return f"Web search error: {e}", {}


ALL_TOOLS_LIST = [
    company_financials_tool,
    company_facts_tool,
    price_history_tool,
    web_search_tool,
]

__all__ = ["ALL_TOOLS_LIST"]
