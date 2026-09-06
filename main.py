import os
from dotenv import load_dotenv
import argparse

import yfinance as yf

from google import genai
from google.genai import types

def process(ticker, routine):
    
    #Initialize Ticker Object
    data = yf.Ticker(ticker)

    #Get financials and data
    info = data.info

    balance_sheet = data.balance_sheet
    key = balance_sheet.keys()[0]

    pe_ratio = data.info["forwardPE"]
    pb_ratio = data.info["priceToBook"]
    current_price = data.info["currentPrice"]

    long_term_debt = balance_sheet[key]["Long Term Debt"]
    short_term_debt = 0

    equity = balance_sheet[key]["Stockholders Equity"]

    try:
        short_term_debt = balance_sheet[key]["Short Long Term Debt"]
    except:
        print("No Short Long Term Debt Exists...")

    total_debt = long_term_debt + short_term_debt

    if routine == 'heuristic':
        return

    if data.info["industry"] == "Banks - Diversified":

        if pe_ratio > 50:
            print("Price-to-Earnings Ratio Too High...")
            return None
        elif pb_ratio < 1 and pb_ratio > 2.5:
            print("Price-to-Book Ratio Not Optimal...")
            return None
        elif pb_ratio * pe_ratio > 35:
            print("Graham Number Too High...")
            return None
        elif total_debt / equity < 2:
            print(total_debt / equity)
            print("Debt-to-Equity Ratio Too High")
            return None

    #print("JPM is a solid stock to buy")

    return ticker

def main():

    load_dotenv()

    #ArgParse code in case I want to make this more CLI based rather than hard-code tickers
    """
    parser = argparse.ArgumentParser()
    parser.add_argument()
    args = parser.parse_args()
    """

    #Gemini API key to scrape relevant news of stocks
    try:
        gemini_api_key = os.getenv("API_TOKEN")
        os.environ["GEMINI_API_KEY"] = gemini_api_key
        print("✅ Gemini API key setup complete.")
    except:
        print(f"Authentication Error: {e}")

    tickers = ["JPM"] #, "COST", "SMFG"]
    valid_stocks = []

    for stock in tickers:
        print("Fetching data for %s" % (stock))
        ticker = process(stock)
        if type(ticker) == "str":
            valid_stocks.append()

    if valid_stocks:

        client = genai.Client()

        response = client.models.generate_content(
            model = "gemini-3-flash-preview",
            contents = "Gather all news released in the last 6 months about JPM stock, positive and negative. Analyze everything and provide brief points about your analysis. Based on your analysis, should I buy right now?",
            config = types.GenerateContentConfig(thinking_config = types.ThinkingConfig(thinking_level = "low"))
        )

        print(response.text)


if __name__ == '__main__':
    main()