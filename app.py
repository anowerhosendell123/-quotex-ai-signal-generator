import os
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import httpx

app = FastAPI(title="AI Smart Signal Generator API")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.post("/api/analyze-screenshot")
async def analyze_screenshot(
    image: UploadFile = File(...),
    asset: str = Form("EUR/USD"),
    timeframe: str = Form("1m")
):
    """
    Plug your chosen vision model in here.
    Keep provider API keys in server environment variables, never in browser HTML.
    Return: {"direction":"BUY|SELL|WAIT","confidence_score":0-100,"explanation":"..."}
    """
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(400, "Please upload an image file.")
    data = await image.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "Image must be 8 MB or smaller.")
    # Deliberately do not fabricate AI results. Configure a real vision provider here.
    if not os.getenv("VISION_API_URL") or not os.getenv("VISION_API_KEY"):
        raise HTTPException(
            503,
            "Vision API is not configured. Set VISION_API_URL and VISION_API_KEY on the server."
        )
    # Provider-specific request/response schemas differ. Implement the adapter for
    # your chosen provider here; do not blindly forward untrusted model output.
    raise HTTPException(
        501,
        "Vision provider credentials are present, but provider adapter is not implemented yet."
    )

@app.get("/api/candles")
async def candles(symbol: str = "EURUSD", interval: str = "1min"):
    """
    Example adapter slot for an authorized market-data provider.
    Configure MARKET_DATA_URL and MARKET_DATA_API_KEY server-side.
    Expected normalized response:
      {"symbol":"EURUSD","interval":"1min","candles":[
        {"time":"...","open":1.1,"high":1.2,"low":1.0,"close":1.15}
      ]}
    """
    base = os.getenv("MARKET_DATA_URL")
    key = os.getenv("MARKET_DATA_API_KEY")
    if not base or not key:
        raise HTTPException(
            503,
            "Live data is not configured. Set MARKET_DATA_URL and MARKET_DATA_API_KEY on the server."
        )
    # Provider-specific params/JSON must be adapted to the selected vendor.
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(base, params={
                "symbol": symbol, "interval": interval, "apikey": key
            })
            resp.raise_for_status()
            raw = resp.json()
    except Exception as exc:
        raise HTTPException(502, f"Market data provider request failed: {exc}") from exc
    # This basic normalization accepts only an already-normalized candles array.
    candles = raw.get("candles") if isinstance(raw, dict) else None
    if not isinstance(candles, list):
        raise HTTPException(502, "Provider response must be adapted to {'candles': [...]} format.")
    return {"symbol": symbol, "interval": interval, "candles": candles[-100:]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
