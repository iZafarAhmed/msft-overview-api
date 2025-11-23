# lambda_function.py
import json, os, re
import requests
from bs4 import BeautifulSoup

TICKER_RE = re.compile(r"^[A-Z]{1,5}(-[A-Z]{2})?$")   # naive sanity check
URL_TMPL  = "https://fiscal.ai/company/{exchange}-{ticker}/"

def lambda_handler(event, context):
    # 1. validate input
    ticker = (event.get("pathParameters") or {}).get("ticker", "").upper()
    if not TICKER_RE.match(ticker):
        return {"statusCode": 400, "body": json.dumps({"error": "invalid ticker"})}

    # 2. download page
    url = URL_TMPL.format(exchange="NasdaqGS", ticker=ticker)
    try:
        r = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Company-Overview-Bot 1.0; +https://yourdomain.com/bot)"
        })
        r.raise_for_status()
    except requests.RequestException as e:
        return {"statusCode": 502, "body": json.dumps({"error": "upstream unreachable", "detail": str(e)})}

    # 3. parse
    soup = BeautifulSoup(r.text, "lxml")
    card = soup.find("h2", string=re.compile("Company Overview"))
    if not card:
        return {"statusCode": 404, "body": json.dumps({"error": "overview not found"})}
    root = card.find_parent("div", class_="mantine-Stack-root")

    # 4. extract text block
    spoiler = root.find("div", class_="mantine-Spoiler-content")
    description = spoiler.get_text(" ", strip=True) if spoiler else ""

    # 5. extract key/value list
    kv = {}
    for li in root.select("li.mantine-List-item"):
        key = li.select_one("p").get_text(strip=True)
        val = li.select_all("p")[-1].get_text(strip=True)   # right-hand <p>
        kv[key] = val

    # 6. return
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "ticker": ticker,
            "description": description,
            "metadata": kv
        }, ensure_ascii=False)
    }
