import os
import requests
from typing import Any, Dict, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults

import torch
from data_research_graph.utils import CHRONOS_PIPELINE

UI_COMPONENT_NAME = "data_research_graph"

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
        current_date = datetime.now() - timedelta(days=1)
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
        
        if not price_data:
            print("No price data received from API")
            return {"error": "No price data available"}
        
        close_price = [item["close"] for item in price_data["prices"]]

        quantiles, mean = CHRONOS_PIPELINE.predict_quantiles(
            context=torch.tensor(close_price),
            prediction_length=15,
            quantile_levels=[0.05, 0.5, 0.95]
        )

        # Format the response
        result = {
            "ticker": input.ticker,
            "prices": price_data,
            "date_range": {
                "start": start_date,
                "end": end_date
            },
            "predictions": {
                "quantiles": quantiles.detach().cpu().numpy().tolist(), 
                "mean": mean.detach().cpu().numpy().tolist()
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


class InsiderTradesInput(BaseModel):
    ticker: str = Field(..., description="The ticker symbol of the company. Example: 'AAPL'")
    # start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format. Defaults to 30 days ago.")
    # end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format. Defaults to today.")


@tool("insider_trades", args_schema=InsiderTradesInput, response_format="content_and_artifact")
def insider_trades_tool(input: InsiderTradesInput = None, **kwargs) -> Tuple[str, dict]:
    """Retrieves insider trading data for a specific company."""
    try:
        if input is None:
            input = InsiderTradesInput(**kwargs)

        print(f"Fetching insider trades for {input.ticker}")

        data = call_financial_dataset_api(
            "/insider-trades",
            {
                "ticker": input.ticker,
                "limit": 100,
            }
        )

        latest_holdings = defaultdict(lambda: {'filing_date': '', 'shares': 0})

        for d in data["insider_trades"]:
            name = d['name']
            date = d['filing_date']
            shares = d.get('shares_owned_after_transaction', 0)

            # 최신 filing_date만 유지
            if latest_holdings[name]['filing_date'] < date:
                latest_holdings[name]['filing_date'] = date
                latest_holdings[name]['shares'] = shares
            elif latest_holdings[name]['filing_date'] == date:
                latest_holdings[name]['shares'] += shares  # 같은 날짜일 경우 누적

        # 파이차트용 데이터 준비
        labels = []
        values = []
        for name, data in latest_holdings.items():
            if data['shares'] > 0:
                labels.append(name)
                values.append(data['shares'])

        # others로 묶기 (Top 5)
        sorted_data = sorted(zip(labels, values), key=lambda x: x[1], reverse=True)
        top_n = 5
        top_labels = [x[0] for x in sorted_data[:top_n]]
        top_values = [x[1] for x in sorted_data[:top_n]]
        others_sum = sum(x[1] for x in sorted_data[top_n:])

        if others_sum > 0:
            top_labels.append("Others")
            top_values.append(others_sum)

        graph_data = {
            "names": top_labels,
            "shares": top_values,
            "percentages": [round((v / sum(top_values)) * 100, 2) for v in top_values],
        }

        return graph_data, {"title": "Insider Trades", "insider_trades": graph_data}

    except Exception as e:
        return f"An error occurred while fetching insider trades: {e}", {}


class IncomeStatementsInput(BaseModel):
    ticker: str = Field(..., description="The ticker symbol of the company. Example: 'AAPL'")
    period: Optional[str] = Field("quarterly", description="Period for financial statements. Options: 'annual', 'quarterly'")
    limit: Optional[int] = Field(30, description="Number of periods to retrieve. Defaults to 30.")


@tool("income_statements", args_schema=IncomeStatementsInput, response_format="content_and_artifact")
def income_statements_tool(input: IncomeStatementsInput = None, **kwargs) -> Tuple[str, dict]:
    """Retrieves income statements for a specific company."""
    try:
        if input is None:
            input = IncomeStatementsInput(**kwargs)

        print(f"Fetching income statements for {input.ticker} - {input.period}")

        data = call_financial_dataset_api(
            "/financials/income-statements",
            {
                "ticker": input.ticker,
                "period": input.period,
                "limit": input.limit,
            }
        )
        revenue = [(items["fiscal_period"], items["revenue"]) for items in data["income_statements"]]
        revenue.reverse()
        net_income = [(items["fiscal_period"], items["net_income"]) for items in data["income_statements"]]
        net_income.reverse()

        quarters = [q for q, _ in revenue]
        revenue_vals = [v / 1e9 for _, v in revenue]
        net_vals = [v / 1e9 for _, v in net_income]

        graph_data = {
            "quarters": quarters,
            "revenue": revenue_vals,
            "net_income": net_vals,
        }

        return graph_data, {"title": "Income Statements", "income_statements": graph_data}

    except Exception as e:
        return f"An error occurred while fetching income statements: {e}", {}


class BalanceSheetsInput(BaseModel):
    ticker: str = Field(..., description="The ticker symbol of the company. Example: 'AAPL'")
    period: Optional[str] = Field("annual", description="Period for financial statements. Options: 'annual', 'quarterly'")
    limit: Optional[int] = Field(30, description="Number of periods to retrieve. Defaults to 30.")


@tool("balance_sheets", args_schema=BalanceSheetsInput, response_format="content_and_artifact")
def balance_sheets_tool(input: BalanceSheetsInput = None, **kwargs) -> Tuple[str, dict]:
    """Retrieves balance sheets for a specific company."""
    try:
        if input is None:
            input = BalanceSheetsInput(**kwargs)

        print(f"Fetching balance sheets for {input.ticker} - {input.period}")

        data = call_financial_dataset_api(
            "/financials/balance-sheets",
            {
                "ticker": input.ticker,
                "period": input.period,
                "limit": input.limit,
            }
        )

        leverage = [
            (items["fiscal_period"], items["shareholders_equity"] / items["total_assets"] * 100) 
            for items in data["balance_sheets"][:-1]
        ]
        leverage.reverse()

        debt_to_equity = [
            (items["fiscal_period"], items["total_liabilities"] / items["shareholders_equity"] * 100) 
            for items in data["balance_sheets"][:-1]
        ]
        debt_to_equity.reverse()

        years = [item[0] for item in leverage]
        equity_ratios = [item[1] for item in leverage]
        debt_equity_ratios = [item[1] for item in debt_to_equity]

        graph_data = {
            "years": years,
            "equity_ratios": equity_ratios,
            "debt_equity_ratios": debt_equity_ratios,
        }

        return graph_data, {"title": "Balance Sheets", "balance_sheets": graph_data}

    except Exception as e:
        return f"An error occurred while fetching balance sheets: {e}", {}


class CashFlowStatementsInput(BaseModel):
    ticker: str = Field(..., description="The ticker symbol of the company. Example: 'AAPL'")
    period: Optional[str] = Field("annual", description="Period for financial statements. Options: 'annual', 'quarterly'")
    limit: Optional[int] = Field(30, description="Number of periods to retrieve. Defaults to 30.")


@tool("cash_flow_statements", args_schema=CashFlowStatementsInput, response_format="content_and_artifact")
def cash_flow_statements_tool(input: CashFlowStatementsInput = None, **kwargs) -> Tuple[str, dict]:
    """Retrieves cash flow statements for a specific company."""
    try:
        if input is None:
            input = CashFlowStatementsInput(**kwargs)

        print(f"Fetching cash flow statements for {input.ticker} - {input.period}")

        data = call_financial_dataset_api(
            "/financials/cash-flow-statements",
            {
                "ticker": input.ticker,
                "period": input.period,
                "limit": input.limit,
            }
        )

        operation = [
            (items["fiscal_period"], items["net_cash_flow_from_operations"]) 
            for items in data["cash_flow_statements"]
        ]
        operation.reverse()

        investment = [
            (items["fiscal_period"], items["net_cash_flow_from_investing"]) 
            for items in data["cash_flow_statements"]
        ]
        investment.reverse()

        financing = [
            (items["fiscal_period"], items["net_cash_flow_from_financing"]) 
            for items in data["cash_flow_statements"]
        ]
        financing.reverse()

        years = [item[0] for item in operation]
        operation_vals = [item[1] / 1e6 for item in operation] # Millions
        investment_vals = [item[1] / 1e6 for item in investment] # Millions
        financing_vals = [item[1] / 1e6 for item in financing] # Millions

        graph_data = {
            "years": years,
            "operation": operation_vals,
            "investment": investment_vals,
            "financing": financing_vals,
        }

        return graph_data, {"title": "Cash Flow Statements", "cash_flow_statements": graph_data}

    except Exception as e:
        return f"An error occurred while fetching cash flow statements: {e}", {}


ALL_TOOLS_LIST = [
    company_financials_tool,
    company_facts_tool,
    price_history_tool,
    web_search_tool,
    insider_trades_tool,
    income_statements_tool,
    balance_sheets_tool,
    cash_flow_statements_tool,
]

__all__ = ["ALL_TOOLS_LIST"]
