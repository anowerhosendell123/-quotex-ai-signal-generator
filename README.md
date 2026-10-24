# Quotex AI Smart Signal Generator starter

## What's included
- Mobile-friendly Bengali web UI (`static/index.html`)
- Screenshot upload endpoint scaffold (`POST /api/analyze-screenshot`)
- Candle-data endpoint scaffold (`GET /api/candles`)
- Explicitly returns errors until real providers are configured; it does not fabricate signals.

## Run locally
1. Install Python 3.10+.
2. In this folder run: `pip install -r requirements.txt`
3. Run: `uvicorn app:app --host 0.0.0.0 --port 8000`
4. Open `http://127.0.0.1:8000`.

## Required before real use
- Implement a vision provider adapter in `app.py` using the provider's official API and response schema.
- Implement a market-data adapter for a licensed/authorized provider.
- Set `VISION_API_URL`, `VISION_API_KEY`, `MARKET_DATA_URL`, and `MARKET_DATA_API_KEY` as server environment variables.
- Do not put secrets in HTML or expose them to the browser.
- Deploy the Python backend to a Python-capable host. Static-only hosting (for example, a basic HTML drop) will not run this API.
- Add authentication, rate limits, upload limits, logging controls, and HTTPS before public deployment.

## API response contracts
Screenshot endpoint:
`{"direction":"BUY|SELL|WAIT","confidence_score":0-100,"explanation":"..."}`
Treat confidence_score as a model score, not a calibrated win probability unless separately validated.

Candle endpoint:
`{"symbol":"EURUSD","interval":"1min","candles":[{"time":"ISO-8601","open":1.1,"high":1.2,"low":1.0,"close":1.15}]}`

OTC prices on Quotex may differ from external providers. This is an educational analysis scaffold, not a trading recommendation or guarantee of profit.
