# Cross DEX Arbitrage Alert

Real-time arbitrage opportunity detection across multiple DEXs with gas cost and fee analysis.

## Features

- **Multi-Chain Support**: Ethereum, Polygon, Arbitrum, Optimism, Base, BNB Chain, Avalanche
- **DEX Aggregation**: Integrated with 0x API for comprehensive DEX coverage
- **Cost Analysis**: Accurate gas cost and DEX fee calculations
- **High Accuracy**: Price spread calculations within 1% of on-chain quotes
- **x402 Payments**: Usage-based micropayments via x402 protocol

## Live Deployment

- **Production**: https://cross-dex-arbitrage-production.up.railway.app
- **API Docs**: https://cross-dex-arbitrage-production.up.railway.app/docs
- **x402 Endpoint**: https://cross-dex-arbitrage-production.up.railway.app/entrypoints/cross-dex-arbitrage/invoke

## API Usage

### Detect Arbitrage Opportunities

```bash
curl -X POST https://cross-dex-arbitrage-production.up.railway.app/arbitrage \
  -H "Content-Type: application/json" \
  -d '{
    "token_in": "USDC",
    "token_out": "USDT",
    "amount_in": "1000",
    "chains": [1, 137, 42161, 8453]
  }'
```

### Response

```json
{
  "best_route": {
    "chain_id": 137,
    "chain_name": "Polygon",
    "dex_sources": ["Uniswap_V3", "SushiSwap"],
    "amount_out": "999500000000000000000",
    "effective_price": 0.9995,
    "gas_cost_usd": 0.05,
    "dex_fee_bps": 30,
    "est_fill_cost": 3.05,
    "confidence_score": 85.0
  },
  "alt_routes": [...],
  "net_spread_bps": 15.5,
  "est_fill_cost": 3.05,
  "profit_usd": 1.55,
  "is_profitable": true,
  "timestamp": "2025-10-31T12:00:00Z"
}
```

## Supported Chains

| Chain | ID | Native Token |
|-------|----|--------------|
| Ethereum | 1 | ETH |
| Polygon | 137 | MATIC |
| Arbitrum | 42161 | ETH |
| Optimism | 10 | ETH |
| Base | 8453 | ETH |
| BNB Chain | 56 | BNB |
| Avalanche | 43114 | AVAX |

## Local Development

### Prerequisites

- Python 3.11+
- RPC URLs for supported chains

### Setup

1. Clone repository:
```bash
git clone https://github.com/DeganAI/cross-dex-arbitrage.git
cd cross-dex-arbitrage
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your RPC URLs
```

4. Run locally:
```bash
uvicorn src.main:app --reload --port 8000
```

5. Visit http://localhost:8000

## Environment Variables

```bash
# Server
PORT=8000
BASE_URL=https://cross-dex-arbitrage-production.up.railway.app

# Payment
PAYMENT_ADDRESS=0x01D11F7e1a46AbFC6092d7be484895D2d505095c
FREE_MODE=true

# RPC URLs (required for each chain)
ETHEREUM_RPC_URL=https://eth.llamarpc.com
POLYGON_RPC_URL=https://polygon-rpc.com
ARBITRUM_RPC_URL=https://arb1.arbitrum.io/rpc
OPTIMISM_RPC_URL=https://mainnet.optimism.io
BASE_RPC_URL=https://mainnet.base.org
BSC_RPC_URL=https://bsc-dataseed.binance.org
AVALANCHE_RPC_URL=https://api.avax.network/ext/bc/C/rpc
```

## Architecture

- **src/main.py**: FastAPI application with AP2/x402 endpoints
- **src/dex_integrations.py**: 0x API integration for DEX quotes
- **src/gas_calculator.py**: Gas price fetching and cost calculation
- **src/price_feed.py**: Token price feeds from CoinGecko
- **src/arbitrage_detector.py**: Arbitrage opportunity detection logic

## x402 Payment Protocol

This service implements the x402 micropayment protocol:

- **Price**: 0.05 USDC per request
- **Network**: Base
- **Payment Address**: 0x01D11F7e1a46AbFC6092d7be484895D2d505095c
- **Asset**: USDC on Base (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913)

## Accuracy

Spread and cost calculations match on-chain quotes within 1% by:
- Using 0x API for aggregated DEX pricing
- Direct RPC calls for real-time gas prices
- Accounting for DEX fees and gas costs
- Conservative estimates for slippage

## License

MIT

## Built By

DeganAI - Bounty #2 Submission for Daydreams AI Agent Bounties
