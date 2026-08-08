# Inside Strategy Bot

This project is the first Python conversion of the supplied Pine strategy.

## Current strategy rules

- Previous candle green
- Current candle red
- Current volume < previous volume
- Current candle is an inside bar
- Buy buffer: 0.02%
- SL buffer: 0.02%
- Risk amount: ₹50
- Quantity = floor(risk / risk-per-share), minimum 2
- Target = 1:2
- Maximum 3 entries per day
- SL hit -> same setup can re-enter
- 1:2 target hit -> position remains OPEN
- Target hit -> SL is cancelled
- Target hit -> no new setup
- Target hit -> no new entry
- Target hit -> no re-entry
- Target hit -> no SL processing
- Next day -> lock resets
- Entry labels/alerts are numbered 1st, 2nd, 3rd...

## Important

PAPER_MODE=true is intentional.

The current first version uses yfinance for market-data testing and Telegram notifications. It does NOT place real broker orders yet.

For real trading, the broker adapter must be connected for:
1. live quotes
2. stop-entry order
3. stop-loss order
4. stop-loss cancellation after target
5. real position/order status

Do not switch PAPER_MODE to false until the broker adapter is implemented and tested.

## Render

Use a Render Background Worker. `render.yaml` is included.

## GitHub

Upload:
- bot.py
- requirements.txt
- stocks.txt
- render.yaml
- .env.example
- README.md

Do NOT upload real Telegram tokens or broker API secrets.
