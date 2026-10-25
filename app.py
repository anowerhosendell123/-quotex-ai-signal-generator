import os
import base64
import json
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
    # OpenAI Responses API adapter.
    endpoint = os.getenv("VISION_API_URL", "").strip()
    api_key = os.getenv("VISION_API_KEY", "").strip()
    if "api.openai.com" not in endpoint:
        raise HTTPException(
            500,
            "This adapter expects VISION_API_URL=https://api.openai.com/v1/responses."
        )

    mime_type = image.content_type or "image/png"
    encoded = base64.b64encode(data).decode("ascii")
    image_data_url = f"data:{mime_type};base64,{encoded}"

    prompt = f"""Analyze this trading-chart screenshot for educational purposes.
Asset/pair: {asset}
Chart timeframe: {timeframe}

Return ONLY a valid JSON object with:
- direction: BUY, SELL, or WAIT
- confidence_score: integer from 0 to 100
- explanation: a brief explanation in Bengali

Be cautious. If the chart is unclear or evidence is mixed, use WAIT and a low confidence score.
Never guarantee a future price movement."""
    payload = {
        "model": os.getenv("VISION_MODEL", "gpt-4.1-mini"),
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": image_data_url}
            ]
        }],
        "max_output_tokens": 300
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            if resp.is_error:
                # Do not include the secret key in any error message.
                raise HTTPException(
                    status_code=502,
                    detail=f"OpenAI API error ({resp.status_code}): {resp.text[:1000]}"
                )
            raw = resp.json()
    except HTTPException:
        raise
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "OpenAI API request timed out. Please try again.") from exc
    except Exception as exc:
        raise HTTPException(502, f"Could not contact the vision provider: {type(exc).__name__}") from exc

    output_text = raw.get("output_text", "")
    if not output_text:
        pieces = []
        for item in raw.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    pieces.append(content.get("text", ""))
        output_text = "\\n".join(pieces)

    try:
        start = output_text.find("{")
        end = output_text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("No JSON object in model response")
        result = json.loads(output_text[start:end + 1])
        direction = str(result.get("direction", "WAIT")).upper()
        if direction not in {"BUY", "SELL", "WAIT"}:
            direction = "WAIT"
        confidence = max(0, min(100, int(result.get("confidence_score", 0))))
        explanation = str(result.get("explanation", "স্পষ্ট সংকেত পাওয়া যায়নি।"))[:1200]
        return {
            "direction": direction,
            "confidence_score": confidence,
            "explanation": explanation
        }
    except Exception as exc:
        raise HTTPException(
            502,
            "AI response could not be parsed. Try a clear chart screenshot again."
        ) from exc

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
