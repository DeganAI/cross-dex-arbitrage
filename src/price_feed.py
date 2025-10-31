"""
Price feed module for fetching token prices from CoinGecko
"""
import httpx
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# CoinGecko API endpoint
COINGECKO_API = "https://api.coingecko.com/api/v3"

# Token ID mappings
TOKEN_IDS = {
    "ETH": "ethereum",
    "MATIC": "matic-network",
    "BNB": "binancecoin",
    "AVAX": "avalanche-2",
    "OP": "optimism",
    "ARB": "arbitrum",
    "FTM": "fantom",
    "USDC": "usd-coin",
    "USDT": "tether",
    "DAI": "dai",
    "WETH": "weth",
    "WBTC": "wrapped-bitcoin",
}


async def get_token_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Fetch token prices in USD from CoinGecko

    Args:
        symbols: List of token symbols (e.g., ["ETH", "MATIC", "BNB"])

    Returns:
        Dictionary mapping symbol to USD price
    """
    try:
        # Map symbols to CoinGecko IDs
        ids = []
        symbol_to_id = {}

        for symbol in symbols:
            token_id = TOKEN_IDS.get(symbol.upper())
            if token_id:
                ids.append(token_id)
                symbol_to_id[token_id] = symbol.upper()

        if not ids:
            logger.warning(f"No valid token IDs found for symbols: {symbols}")
            return {}

        # Fetch prices from CoinGecko
        ids_str = ",".join(ids)
        url = f"{COINGECKO_API}/simple/price?ids={ids_str}&vs_currencies=usd"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        # Map back to symbols
        prices = {}
        for token_id, symbol in symbol_to_id.items():
            if token_id in data and "usd" in data[token_id]:
                prices[symbol] = float(data[token_id]["usd"])

        logger.info(f"Fetched prices for {len(prices)} tokens: {prices}")
        return prices

    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching token prices: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error fetching token prices: {e}")
        return {}


async def get_token_price(symbol: str) -> float:
    """
    Fetch price for a single token

    Args:
        symbol: Token symbol (e.g., "ETH")

    Returns:
        Token price in USD, or 0 if fetch fails
    """
    prices = await get_token_prices([symbol])
    return prices.get(symbol.upper(), 0.0)
