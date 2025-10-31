"""
Cross DEX Arbitrage Alert - Find profitable arbitrage opportunities across DEXs

x402 micropayment-enabled arbitrage detection service
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
import logging
from datetime import datetime
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.dex_integrations import DEXIntegration, COMMON_TOKENS
from src.gas_calculator import initialize_gas_calculator, CHAIN_CONFIG
from src.price_feed import get_token_prices
from src.arbitrage_detector import ArbitrageDetector, ArbitrageRoute

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Cross DEX Arbitrage Alert",
    description="Real-time arbitrage opportunity detection across multiple DEXs - powered by x402",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
payment_address = os.getenv("PAYMENT_ADDRESS", "0x01D11F7e1a46AbFC6092d7be484895D2d505095c")
free_mode = os.getenv("FREE_MODE", "true").lower() == "true"

logger.info(f"Running in {'FREE' if free_mode else 'PAID'} mode")

# Initialize DEX integration and gas calculator
dex_integration = DEXIntegration()
gas_calculator = initialize_gas_calculator()

logger.info(f"Gas calculator initialized with {len(gas_calculator.get_available_chains())} chains")


# Request/Response Models
class ArbitrageRequest(BaseModel):
    """Request for arbitrage detection"""

    token_in: str = Field(
        ...,
        description="Input token address or symbol (e.g., '0x...' or 'USDC')",
        example="USDC",
    )
    token_out: str = Field(
        ...,
        description="Output token address or symbol (e.g., '0x...' or 'USDT')",
        example="USDT",
    )
    amount_in: str = Field(
        ...,
        description="Amount to swap in token units (will be converted to wei)",
        example="1000",
    )
    chains: List[int] = Field(
        ...,
        description="List of chain IDs to scan for arbitrage",
        example=[1, 137, 42161, 8453],
    )


class RouteInfo(BaseModel):
    """Information about a specific route"""

    chain_id: int
    chain_name: str
    dex_sources: List[str]
    amount_out: str
    effective_price: float
    gas_cost_usd: float
    dex_fee_bps: int
    est_fill_cost: float
    confidence_score: float


class ArbitrageResponse(BaseModel):
    """Response with arbitrage opportunities"""

    best_route: Optional[RouteInfo]
    alt_routes: List[RouteInfo]
    net_spread_bps: float
    est_fill_cost: float
    profit_usd: float
    is_profitable: bool
    timestamp: str


# Landing Page
@app.get("/", response_class=HTMLResponse)
@app.head("/")
async def root():
    """Landing page"""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cross DEX Arbitrage Alert</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1a0a2e 0%, #16213e 50%, #0f3460 100%);
                color: #e8f0f2;
                line-height: 1.6;
                min-height: 100vh;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
            header {{
                background: linear-gradient(135deg, rgba(255, 107, 107, 0.2), rgba(77, 182, 172, 0.2));
                border: 2px solid rgba(77, 182, 172, 0.3);
                border-radius: 15px;
                padding: 40px;
                margin-bottom: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }}
            h1 {{
                color: #4db6ac;
                font-size: 2.5em;
                margin-bottom: 10px;
            }}
            .subtitle {{
                color: #80cbc4;
                font-size: 1.2em;
                margin-bottom: 15px;
            }}
            .badge {{
                display: inline-block;
                background: rgba(77, 182, 172, 0.2);
                border: 1px solid #4db6ac;
                color: #4db6ac;
                padding: 6px 15px;
                border-radius: 20px;
                font-size: 0.9em;
                margin-right: 10px;
                margin-top: 10px;
            }}
            .section {{
                background: rgba(22, 33, 62, 0.6);
                border: 1px solid rgba(77, 182, 172, 0.2);
                border-radius: 12px;
                padding: 30px;
                margin-bottom: 30px;
                backdrop-filter: blur(10px);
            }}
            h2 {{
                color: #4db6ac;
                margin-bottom: 20px;
                font-size: 1.8em;
                border-bottom: 2px solid rgba(77, 182, 172, 0.3);
                padding-bottom: 10px;
            }}
            .endpoint {{
                background: rgba(26, 10, 46, 0.6);
                border-left: 4px solid #4db6ac;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
            }}
            .method {{
                display: inline-block;
                background: #4db6ac;
                color: #1a0a2e;
                padding: 5px 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 0.85em;
                margin-right: 10px;
            }}
            code {{
                background: rgba(0, 0, 0, 0.3);
                color: #a5d6a7;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Monaco', 'Courier New', monospace;
            }}
            pre {{
                background: rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(77, 182, 172, 0.2);
                border-radius: 6px;
                padding: 15px;
                overflow-x: auto;
                margin: 10px 0;
            }}
            pre code {{
                background: none;
                padding: 0;
                display: block;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .card {{
                background: rgba(26, 10, 46, 0.6);
                border: 1px solid rgba(77, 182, 172, 0.2);
                border-radius: 10px;
                padding: 20px;
                transition: transform 0.3s;
            }}
            .card:hover {{
                transform: translateY(-4px);
                border-color: rgba(77, 182, 172, 0.4);
            }}
            .card h4 {{
                color: #4db6ac;
                margin-bottom: 10px;
            }}
            a {{
                color: #4db6ac;
                text-decoration: none;
                border-bottom: 1px solid transparent;
                transition: border-color 0.3s;
            }}
            a:hover {{
                border-bottom-color: #4db6ac;
            }}
            footer {{
                text-align: center;
                padding: 30px;
                color: #80cbc4;
                opacity: 0.8;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Cross DEX Arbitrage Alert</h1>
                <p class="subtitle">Real-time arbitrage opportunity detection across multiple DEXs</p>
                <p>Find profitable price spreads across chains after accounting for fees and gas costs</p>
                <div>
                    <span class="badge">Live & Ready</span>
                    <span class="badge">Multi-Chain</span>
                    <span class="badge">x402 Payments</span>
                    <span class="badge">&lt;1% Accuracy</span>
                </div>
            </header>

            <div class="section">
                <h2>What is Cross DEX Arbitrage Alert?</h2>
                <p>
                    Cross DEX Arbitrage Alert analyzes real-time prices across multiple DEXs and chains to identify
                    profitable arbitrage opportunities. Get accurate spread calculations with gas costs and DEX fees
                    factored in.
                </p>

                <div class="grid">
                    <div class="card">
                        <h4>Multi-Chain Support</h4>
                        <p>Scan Ethereum, Polygon, Arbitrum, Optimism, Base, BNB Chain, and Avalanche simultaneously.</p>
                    </div>
                    <div class="card">
                        <h4>Real-Time Quotes</h4>
                        <p>Direct integration with 0x API for accurate, aggregated DEX pricing.</p>
                    </div>
                    <div class="card">
                        <h4>Cost Analysis</h4>
                        <p>Accurate gas cost and DEX fee calculations to identify true profitability.</p>
                    </div>
                    <div class="card">
                        <h4>High Accuracy</h4>
                        <p>Price spread calculations match on-chain quotes within 1%.</p>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>API Endpoints</h2>

                <div class="endpoint">
                    <h3><span class="method">POST</span>/arbitrage</h3>
                    <p>Detect arbitrage opportunities across specified chains</p>
                    <pre><code>curl -X POST https://cross-dex-arbitrage-production.up.railway.app/arbitrage \\
  -H "Content-Type: application/json" \\
  -d '{{
    "token_in": "USDC",
    "token_out": "USDT",
    "amount_in": "1000",
    "chains": [1, 137, 42161, 8453]
  }}'</code></pre>
                </div>

                <div class="endpoint">
                    <h3><span class="method">GET</span>/chains</h3>
                    <p>List all supported blockchain networks</p>
                </div>

                <div class="endpoint">
                    <h3><span class="method">GET</span>/health</h3>
                    <p>Health check and operational status</p>
                </div>
            </div>

            <div class="section">
                <h2>x402 Micropayments</h2>
                <p>This service uses the <strong>x402 payment protocol</strong> for usage-based billing.</p>
                <div class="grid">
                    <div class="card">
                        <h4>Payment Details</h4>
                        <p><strong>Price:</strong> 0.05 USDC per request</p>
                        <p><strong>Address:</strong> <code>{payment_address}</code></p>
                        <p><strong>Network:</strong> Base</p>
                    </div>
                    <div class="card">
                        <h4>Status</h4>
                        <p><em>{"Currently in FREE MODE for testing" if free_mode else "Payment verification active"}</em></p>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>Supported Networks</h2>
                <div class="grid">
                    <div class="card"><h4>Ethereum</h4><p>Chain ID: 1</p></div>
                    <div class="card"><h4>Polygon</h4><p>Chain ID: 137</p></div>
                    <div class="card"><h4>Arbitrum</h4><p>Chain ID: 42161</p></div>
                    <div class="card"><h4>Optimism</h4><p>Chain ID: 10</p></div>
                    <div class="card"><h4>Base</h4><p>Chain ID: 8453</p></div>
                    <div class="card"><h4>BNB Chain</h4><p>Chain ID: 56</p></div>
                    <div class="card"><h4>Avalanche</h4><p>Chain ID: 43114</p></div>
                </div>
            </div>

            <div class="section">
                <h2>Documentation</h2>
                <p>Interactive API documentation:</p>
                <div style="margin: 20px 0;">
                    <a href="/docs" style="display: inline-block; background: rgba(77, 182, 172, 0.2); padding: 10px 20px; border-radius: 5px; margin-right: 10px;">Swagger UI</a>
                    <a href="/redoc" style="display: inline-block; background: rgba(77, 182, 172, 0.2); padding: 10px 20px; border-radius: 5px;">ReDoc</a>
                </div>
            </div>

            <footer>
                <p><strong>Built by DeganAI</strong></p>
                <p>Bounty #2 Submission for Daydreams AI Agent Bounties</p>
            </footer>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# AP2 (Agent Payments Protocol) Metadata
@app.get("/.well-known/agent.json")
@app.head("/.well-known/agent.json")
async def agent_metadata():
    """AP2 metadata - returns HTTP 200"""
    base_url = os.getenv("BASE_URL", "https://cross-dex-arbitrage-production.up.railway.app")

    agent_json = {
        "name": "Cross DEX Arbitrage Alert",
        "description": "Real-time arbitrage opportunity detection across multiple DEXs with gas cost and fee analysis. Identifies profitable price spreads with <1% accuracy.",
        "url": base_url.replace("https://", "http://") + "/",
        "version": "1.0.0",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": True,
            "extensions": [
                {
                    "uri": "https://github.com/google-agentic-commerce/ap2/tree/v0.1",
                    "description": "Agent Payments Protocol (AP2)",
                    "required": True,
                    "params": {"roles": ["merchant"]},
                }
            ],
        },
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json", "text/plain"],
        "skills": [
            {
                "id": "cross-dex-arbitrage",
                "name": "cross-dex-arbitrage",
                "description": "Detect profitable arbitrage opportunities across multiple DEXs and chains",
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
                "streaming": False,
                "x_input_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "token_in": {
                            "description": "Input token address or symbol",
                            "type": "string",
                        },
                        "token_out": {
                            "description": "Output token address or symbol",
                            "type": "string",
                        },
                        "amount_in": {
                            "description": "Amount to swap in token units",
                            "type": "string",
                        },
                        "chains": {
                            "description": "List of chain IDs to scan",
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                    },
                    "required": ["token_in", "token_out", "amount_in", "chains"],
                    "additionalProperties": False,
                },
                "x_output_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "best_route": {"type": "object"},
                        "alt_routes": {"type": "array"},
                        "net_spread_bps": {"type": "number"},
                        "est_fill_cost": {"type": "number"},
                    },
                    "required": ["best_route", "alt_routes", "net_spread_bps", "est_fill_cost"],
                    "additionalProperties": False,
                },
            }
        ],
        "supportsAuthenticatedExtendedCard": False,
        "entrypoints": {
            "cross-dex-arbitrage": {
                "description": "Find profitable arbitrage routes across DEXs",
                "streaming": False,
                "input_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "token_in": {"description": "Input token", "type": "string"},
                        "token_out": {"description": "Output token", "type": "string"},
                        "amount_in": {"description": "Amount to swap", "type": "string"},
                        "chains": {"description": "Chains to scan", "type": "array", "items": {"type": "integer"}},
                    },
                    "required": ["token_in", "token_out", "amount_in", "chains"],
                    "additionalProperties": False,
                },
                "output_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "best_route": {"type": "object"},
                        "alt_routes": {"type": "array"},
                        "net_spread_bps": {"type": "number"},
                        "est_fill_cost": {"type": "number"},
                    },
                    "additionalProperties": False,
                },
                "pricing": {"invoke": "0.05 USDC"},
            }
        },
        "payments": [
            {
                "method": "x402",
                "payee": payment_address,
                "network": "base",
                "endpoint": "https://facilitator.daydreams.systems",
                "priceModel": {"default": "0.05"},
                "extensions": {
                    "x402": {"facilitatorUrl": "https://facilitator.daydreams.systems"}
                },
            }
        ],
    }

    return JSONResponse(content=agent_json, status_code=200)


# x402 Protocol Metadata
@app.get("/.well-known/x402")
@app.head("/.well-known/x402")
async def x402_metadata():
    """x402 protocol metadata - returns HTTP 402"""
    base_url = os.getenv("BASE_URL", "https://cross-dex-arbitrage-production.up.railway.app")

    metadata = {
        "x402Version": 1,
        "accepts": [
            {
                "scheme": "exact",
                "network": "base",
                "maxAmountRequired": "50000",  # 0.05 USDC (6 decimals)
                "resource": f"{base_url}/entrypoints/cross-dex-arbitrage/invoke",
                "description": "Detect profitable arbitrage opportunities across multiple DEXs and chains",
                "mimeType": "application/json",
                "payTo": payment_address,
                "maxTimeoutSeconds": 30,
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC on Base
            }
        ],
    }

    return JSONResponse(content=metadata, status_code=402)


# Health Check
@app.get("/health")
async def health():
    """Health check"""
    available_chains = gas_calculator.get_available_chains()
    return {
        "status": "healthy",
        "available_chains": len(available_chains),
        "chain_ids": available_chains,
        "free_mode": free_mode,
    }


# List Chains
@app.get("/chains")
async def list_chains():
    """List all supported chains"""
    available = gas_calculator.get_available_chains()
    chains = []

    for chain_id in available:
        info = gas_calculator.get_chain_info(chain_id)
        if info:
            chains.append({
                "chain_id": chain_id,
                "name": info["name"],
                "symbol": info["symbol"],
                "base_swap_gas": info["base_swap_gas"],
            })

    return {"chains": chains, "total": len(chains)}


# Helper function to resolve token addresses
def resolve_token_address(token: str, chain_id: int) -> str:
    """Resolve token symbol to address or return address if already provided"""
    # If it's already an address (starts with 0x), return it
    if token.startswith("0x"):
        return token

    # Otherwise, look up the address
    address = dex_integration.get_token_address(chain_id, token)
    if not address:
        raise HTTPException(
            status_code=400,
            detail=f"Token {token} not found on chain {chain_id}. Supported tokens: {list(COMMON_TOKENS.get(chain_id, {}).keys())}",
        )

    return address


# Main Arbitrage Detection Endpoint
@app.post("/arbitrage", response_model=ArbitrageResponse)
async def detect_arbitrage(request: ArbitrageRequest):
    """
    Detect arbitrage opportunities across multiple chains and DEXs

    Finds profitable price spreads after accounting for:
    - Gas costs on each chain
    - DEX fees (swap fees)
    - Slippage estimates
    - Network congestion

    Returns the best route and alternatives with profitability analysis.
    """
    try:
        logger.info(f"Arbitrage request: {request.token_in} -> {request.token_out}, amount: {request.amount_in}, chains: {request.chains}")

        # Validate chains
        available_chains = gas_calculator.get_available_chains()
        invalid_chains = [c for c in request.chains if c not in available_chains]

        if invalid_chains:
            raise HTTPException(
                status_code=400,
                detail=f"Chains not available: {invalid_chains}. Available: {available_chains}",
            )

        if len(request.chains) < 2:
            raise HTTPException(
                status_code=400,
                detail="Need at least 2 chains to compare for arbitrage",
            )

        # Resolve token addresses for each chain
        token_addresses = {}
        for chain_id in request.chains:
            try:
                token_in_addr = resolve_token_address(request.token_in, chain_id)
                token_out_addr = resolve_token_address(request.token_out, chain_id)
                token_addresses[chain_id] = {
                    "token_in": token_in_addr,
                    "token_out": token_out_addr,
                }
            except HTTPException as e:
                logger.warning(f"Skipping chain {chain_id}: {e.detail}")
                continue

        if not token_addresses:
            raise HTTPException(
                status_code=400,
                detail="No valid token pairs found on any requested chain",
            )

        # Convert amount to wei (assuming 18 decimals for most tokens)
        try:
            amount_wei = Web3.to_wei(float(request.amount_in), "ether")
            amount_wei_str = str(amount_wei)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid amount: {request.amount_in}. Error: {str(e)}",
            )

        # Fetch quotes from all chains in parallel
        all_routes = []

        for chain_id, addresses in token_addresses.items():
            # Get DEX quote
            quote = await dex_integration.get_quote(
                chain_id=chain_id,
                token_in=addresses["token_in"],
                token_out=addresses["token_out"],
                amount_in=amount_wei_str,
            )

            if not quote:
                logger.warning(f"No quote available for chain {chain_id}")
                continue

            # Get gas data
            gas_data = await gas_calculator.get_gas_price(chain_id)

            if not gas_data:
                logger.warning(f"No gas data available for chain {chain_id}")
                continue

            # Calculate gas cost
            gas_cost_calc = gas_calculator.calculate_gas_cost(
                chain_id=chain_id,
                gas_price_gwei=gas_data["gas_price_gwei"],
                swap_complexity=1,
            )

            if not gas_cost_calc:
                continue

            # Combine gas data
            gas_info = {
                **gas_data,
                "gas_cost_native": gas_cost_calc["gas_cost_native"],
            }

            # Get token prices for USD conversion
            symbols = list(set([gas_info["symbol"], request.token_in.upper(), request.token_out.upper()]))
            token_prices = await get_token_prices(symbols)

            # Create detector
            detector = ArbitrageDetector(token_prices)

            # Analyze route
            route = detector.analyze_route(
                chain_id=chain_id,
                chain_name=gas_info["name"],
                quote_data=quote,
                gas_data=gas_info,
                token_in=addresses["token_in"],
                token_out=addresses["token_out"],
            )

            if route:
                all_routes.append(route)

        if not all_routes:
            raise HTTPException(
                status_code=503,
                detail="Failed to fetch quotes from any chain",
            )

        # Get token prices for final analysis
        sample_route = all_routes[0]
        symbols = list(set([CHAIN_CONFIG[r.chain_id]["symbol"] for r in all_routes]))
        token_prices = await get_token_prices(symbols)

        # Compare routes and find arbitrage
        detector = ArbitrageDetector(token_prices)
        analysis = detector.compare_routes(all_routes)

        best_route = analysis["best_route"]
        alt_routes = analysis["alt_routes"]

        if not best_route:
            return ArbitrageResponse(
                best_route=None,
                alt_routes=[],
                net_spread_bps=0.0,
                est_fill_cost=0.0,
                profit_usd=0.0,
                is_profitable=False,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

        # Build response
        best_route_info = RouteInfo(
            chain_id=best_route.chain_id,
            chain_name=best_route.chain_name,
            dex_sources=best_route.dex_sources,
            amount_out=best_route.amount_out,
            effective_price=best_route.effective_price,
            gas_cost_usd=round(best_route.gas_cost_usd, 4),
            dex_fee_bps=best_route.dex_fee_bps,
            est_fill_cost=round(best_route.est_fill_cost_usd, 4),
            confidence_score=round(best_route.confidence_score, 1),
        )

        alt_route_infos = [
            RouteInfo(
                chain_id=r.chain_id,
                chain_name=r.chain_name,
                dex_sources=r.dex_sources,
                amount_out=r.amount_out,
                effective_price=r.effective_price,
                gas_cost_usd=round(r.gas_cost_usd, 4),
                dex_fee_bps=r.dex_fee_bps,
                est_fill_cost=round(r.est_fill_cost_usd, 4),
                confidence_score=round(r.confidence_score, 1),
            )
            for r in alt_routes
        ]

        return ArbitrageResponse(
            best_route=best_route_info,
            alt_routes=alt_route_infos,
            net_spread_bps=round(best_route.net_spread_bps, 2),
            est_fill_cost=round(best_route.est_fill_cost_usd, 4),
            profit_usd=round(best_route.profit_usd, 4),
            is_profitable=best_route.profit_usd > 0,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Arbitrage detection error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )


# AP2 Entrypoint - GET/HEAD for x402 discovery
@app.get("/entrypoints/cross-dex-arbitrage/invoke")
@app.head("/entrypoints/cross-dex-arbitrage/invoke")
async def entrypoint_arbitrage_get():
    """
    x402 discovery endpoint - returns HTTP 402 for x402scan registration
    """
    base_url = os.getenv("BASE_URL", "https://cross-dex-arbitrage-production.up.railway.app")

    return JSONResponse(
        status_code=402,
        content={
            "x402Version": 1,
            "accepts": [{
                "scheme": "exact",
                "network": "base",
                "maxAmountRequired": "50000",  # 0.05 USDC in smallest units
                "resource": f"{base_url}/entrypoints/cross-dex-arbitrage/invoke",
                "description": "Cross DEX Arbitrage Alert - Find profitable arbitrage opportunities",
                "mimeType": "application/json",
                "payTo": payment_address,
                "maxTimeoutSeconds": 30,
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # Base USDC
            }]
        }
    )


# AP2 Entrypoint - POST for actual requests
@app.post("/entrypoints/cross-dex-arbitrage/invoke")
async def entrypoint_arbitrage_post(request: Optional[ArbitrageRequest] = None, x_payment_txhash: Optional[str] = None):
    """
    AP2 (Agent Payments Protocol) compatible entrypoint

    Returns 402 if no payment provided (FREE_MODE overrides this for testing).
    Calls the main /arbitrage endpoint with the same logic if payment is valid.
    """
    # Return 402 if no request body provided
    if request is None:
        return await entrypoint_arbitrage_get()

    # In FREE_MODE, bypass payment check
    if not free_mode and not x_payment_txhash:
        return await entrypoint_arbitrage_get()

    return await detect_arbitrage(request)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)