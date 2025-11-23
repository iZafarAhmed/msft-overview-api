from flask import Flask, jsonify, request
import requests, json, os, re
from bs4 import BeautifulSoup

app = Flask(__name__)

TICKER_RE = re.compile(r"^[A-Z]{1,5}(-[A-Z]{2})?$")
URL_TMPL = "https://fiscal.ai/company/{exchange}-{ticker}/"

@app.route("/<ticker>")
def overview(ticker: str):
    if not TICKER_RE.match(ticker.upper()):
        return jsonify({"error": "invalid ticker"}), 400

    url = URL_TMPL.format(exchange="NasdaqGS", ticker=ticker.upper())
    try:
        r = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Company-Overview-Bot 1.0; +https://yourdomain.com/bot)"
        })
        r.raise_for_status()
    except requests.RequestException as e:
        return jsonify({"error": "upstream unreachable", "detail": str(e)}), 502

    soup = BeautifulSoup(r.text, "html.parser")   # NOT "lxml"
    card = soup.find("h2", string=re.compile("Company Overview"))
    if not card:
        return jsonify({"error": "overview not found"}), 404
    root = card.find_parent("div", class_="mantine-Stack-root")

    spoiler = root.find("div", class_="mantine-Spoiler-content")
    description = spoiler.get_text(" ", strip=True) if spoiler else ""

    kv = {}
    for li in root.select("li.mantine-List-item"):
        key = li.select_one("p").get_text(strip=True)
        val = li.select("p")[-1].get_text(strip=True)
        kv[key] = val

    return jsonify({
        "ticker": ticker.upper(),
        "description": description,
        "metadata": kv
    })

@app.route("/")
def root():
    return jsonify({"message": "MSFT overview service"})
