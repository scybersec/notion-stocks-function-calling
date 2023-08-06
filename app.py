import openai
import json
import os
import requests
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
rapid_api_key = os.getenv("X-RapidAPI-Key")
notion_api_key = os.getenv("NOTION_API_KEY")
notion_database_id = os.getenv("DATABASE_ID")

notion = Client(auth=notion_api_key)

function_descriptions = [
    {
        "name": "get_stock_movers",
        "description": "Get the stocks that has biggest price/volume moves, e.g. actives, gainers, losers, etc.",
        "parameters": {
            "type": "object",
            "properties": {
            },
        }
    },
    {
        "name": "get_stock_news",
        "description": "Get the latest news for a stock",
        "parameters": {
            "type": "object",
            "properties": {
                "performanceId": {
                    "type": "string",
                    "description": "id of the stock, which is referred as performanceID in the API"
                },
            },
            "required": ["performanceId"]
        }
    },
    {
        "name": "add_stock_news_notion",
        "description": "Add the stock, news summary & price move to Notion",
        "parameters": {
            "type": "object",
            "properties": {
                "stock": {
                    "type": "string",
                    "description": "stock ticker"
                },
                "move": {
                    "type": "string",
                    "description": "price move in %"
                },
                "news_summary": {
                    "type": "string",
                    "description": "news summary of the stock"
                },
            }
        }
    }
]

def add_stock_news_notion(stock, move, news_summary):
    notion.pages.create(
        parent={"database_id": notion_database_id},
        properties={
            "stock": {"title": [{"type": "text", "text": {"content": stock}}]},
            "move": {"number": float(move.strip('%'))},
            "news_summary": {"rich_text": [{"type": "text", "text": {"content": news_summary}}]}
        }
    )

def get_stock_news(performanceId):
    url = "https://ms-finance.p.rapidapi.com/news/list"

    querystring = {"performanceId":performanceId}

    headers = {
        "X-RapidAPI-Key": rapid_api_key,
        "X-RapidAPI-Host": "ms-finance.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    short_news_list = response.json()[:5]

    print("response:", response, " json response:", short_news_list)

    return short_news_list

def get_stock_movers():
    url = "https://ms-finance.p.rapidapi.com/market/v2/get-movers"

    headers = {
        "X-RapidAPI-Key": rapid_api_key,
        "X-RapidAPI-Host": "ms-finance.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers)
    
    return response.json()

def function_call(ai_response):
    function_call = ai_response["choices"][0]["message"]["function_call"]
    function_name = function_call["name"]
    arguments = function_call["arguments"]
    if function_name == "get_stock_movers":
        return get_stock_movers()
    elif function_name == "get_stock_news":
        performanceId = eval(arguments).get("performanceId")
        return get_stock_news(performanceId)
    elif function_name == "add_stock_news_notion":
        stock = eval(arguments).get("stock")
        news_summary = eval(arguments).get("news_summary")
        move = eval(arguments).get("move")
        return add_stock_news_notion(stock, move, news_summary)
    else:
        return

def ask_function_calling(query):
    messages = [{"role": "user", "content": query}]

    response = openai.ChatCompletion.create(
        model="gpt-4-0613",
        messages=messages,
        functions = function_descriptions,
        function_call="auto"
    )

    print(response)

    while response["choices"][0]["finish_reason"] == "function_call":
        function_response = function_call(response)
        messages.append({
            "role": "function",
            "name": response["choices"][0]["message"]["function_call"]["name"],
            "content": json.dumps(function_response)
        })

        print("messages: ", messages) 

        response = openai.ChatCompletion.create(
            model="gpt-4-0613",
            messages=messages,
            functions = function_descriptions,
            function_call="auto"
        )   

        print("response: ", response) 
    else:
        print(response)


while True:
    user_query = input("Enter your query: ")
    ask_function_calling(user_query)

"""what is the stock that has the biggest price movement today and what are the latest news about this stock that might cause the price movement? Please add a record to Notion with the stock ticker, price move and news summary."""