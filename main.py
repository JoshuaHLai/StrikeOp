import argparse
import logging
import os

import yfinance as yf
from dotenv import load_dotenv
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def process(ticker, routine):
    """Fetch fundamentals for `ticker` and screen it.

    `routine` == 'heuristic' computes the ratios and returns without
    screening (useful for inspecting numbers without the bank-only filter).
    Any other value applies the bank-specific value screen.

    Returns the ticker string if it passes screening (or if no screening
    applies), otherwise None.
    """
    data = yf.Ticker(ticker)
    info = data.info

    balance_sheet = data.balance_sheet
    if balance_sheet.empty:
        logger.warning("No balance sheet data available for %s, skipping.", ticker)
        return None
    key = balance_sheet.keys()[0]

    pe_ratio = info["forwardPE"]
    pb_ratio = info["priceToBook"]

    long_term_debt = balance_sheet[key]["Long Term Debt"]
    short_term_debt = 0

    equity = balance_sheet[key]["Stockholders Equity"]

    try:
        short_term_debt = balance_sheet[key]["Short Long Term Debt"]
    except KeyError:
        logger.info("No Short Long Term Debt line item for %s.", ticker)

    total_debt = long_term_debt + short_term_debt

    if routine == "heuristic":
        return ticker

    if info["industry"] == "Banks - Diversified":
        if pe_ratio > 50:
            logger.info("%s: Price-to-Earnings Ratio Too High.", ticker)
            return None
        elif pb_ratio < 1 or pb_ratio > 2.5:
            logger.info("%s: Price-to-Book Ratio Not Optimal.", ticker)
            return None
        elif pb_ratio * pe_ratio > 35:
            logger.info("%s: Graham Number Too High.", ticker)
            return None
        elif total_debt / equity > 2:
            logger.info("%s: Debt-to-Equity Ratio Too High (%.2f).", ticker, total_debt / equity)
            return None

    return ticker


def parse_args():
    parser = argparse.ArgumentParser(description="Screen stocks and summarize recent news via Gemini.")
    parser.add_argument("--tickers", nargs="+", default=["JPM"], help="Ticker symbols to screen.")
    parser.add_argument(
        "--routine",
        choices=["heuristic", "full"],
        default="full",
        help="'heuristic' skips the bank value screen; 'full' applies it.",
    )
    return parser.parse_args()


def main():
    """Load config, screen the requested tickers, and ask Gemini about any that pass."""
    load_dotenv()
    args = parse_args()

    gemini_api_key = os.getenv("API_TOKEN")
    if not gemini_api_key:
        logger.error("Authentication Error: API_TOKEN is not set in the environment.")
        return
    os.environ["GEMINI_API_KEY"] = gemini_api_key
    logger.info("Gemini API key setup complete.")

    valid_stocks = []

    for stock in args.tickers:
        logger.info("Fetching data for %s", stock)
        ticker = process(stock, args.routine)
        if isinstance(ticker, str):
            valid_stocks.append(ticker)

    if valid_stocks:
        client = genai.Client()

        tickers_str = ", ".join(valid_stocks)
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=(
                f"Gather all news released in the last 6 months about the following stocks, "
                f"positive and negative: {tickers_str}. Analyze everything and provide brief "
                f"points about your analysis. Based on your analysis, should I buy right now?"
            ),
            config=types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level="low")),
        )

        print(response.text)


if __name__ == "__main__":
    main()
