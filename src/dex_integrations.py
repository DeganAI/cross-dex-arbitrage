"""
DEX Integration module for fetching quotes from multiple DEXs
Uses 0x API as the primary aggregator for accurate pricing
"""
import httpx
import logging
from typing import Dict, List, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

# Chain ID to 0x API endpoint mapping
ZEROX_API_ENDPOINTS = {
    1: "https://api.0x.org",  # Ethereum
    137: "https://polygon.api.0x.org",  # Polygon
    42161: "https://arbitrum.api.0x.org",  # Arbitrum
    10: "https://optimism.api.0x.org",  # Optimism
    8453: "https://base.api.0x.org",  # Base
    56: "https://bsc.api.0x.org",  # BNB Chain
    43114: "https://avalanche.api.0x.org",  # Avalanche
}

# DEX fee structures (in basis points)
DEX_FEES = {
    "uniswap_v2": 30,  # 0.3%
    "uniswap_v3": 30,  # 0.3% (can be 0.05%, 0.3%, or 1%)
    "sushiswap": 30,  # 0.3%
    "pancakeswap": 25,  # 0.25%
    "quickswap": 30,  # 0.3%
    "camelot": 30,  # 0.3%
}

# Common token addresses by chain
COMMON_TOKENS = {
    1: {  # Ethereum
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    },
    137: {  # Polygon
        "WMATIC": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
        "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
        "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
        "WETH": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
    },
    42161: {  # Arbitrum
        "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        "USDC": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
        "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        "ARB": "0x912CE59144191C1204E64559FE8253a0e49E6548",
    },
    10: {  # Optimism
        "WETH": "0x4200000000000000000000000000000000000006",
        "USDC": "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
        "USDT": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
        "OP": "0x4200000000000000000000000000000000000042",
    },
    8453: {  # Base
        "WETH": "0x4200000000000000000000000000000000000006",
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
    },
    56: {  # BNB Chain
        "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
        "USDT": "0x55d398326f99059fF775485246999027B3197955",
        "BUSD": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
    },
    43114: {  # Avalanche
        "WAVAX": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
        "USDC": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
        "USDT": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
    },
}


class DEXIntegration:
    """Integration with multiple DEXs via 0x API"""

    def __init__(self):
        self.client_timeout = 15.0

    async def get_quote(
        self,
        chain_id: int,
        token_in: str,
        token_out: str,
        amount_in: str,
    ) -> Optional[Dict]:
        """
        Get swap quote from 0x API (aggregates multiple DEXs)

        Args:
            chain_id: Blockchain ID
            token_in: Input token address
            token_out: Output token address
            amount_in: Amount in (in wei/smallest unit)

        Returns:
            Quote data including price, estimated gas, sources
        """
        if chain_id not in ZEROX_API_ENDPOINTS:
            logger.warning(f"Chain {chain_id} not supported by 0x")
            return None

        api_endpoint = ZEROX_API_ENDPOINTS[chain_id]

        try:
            params = {
                "sellToken": token_in,
                "buyToken": token_out,
                "sellAmount": amount_in,
            }

            url = f"{api_endpoint}/swap/v1/quote"

            async with httpx.AsyncClient(timeout=self.client_timeout) as client:
                response = await client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()

                    # Extract relevant information
                    quote = {
                        "chain_id": chain_id,
                        "sell_token": token_in,
                        "buy_token": token_out,
                        "sell_amount": data.get("sellAmount"),
                        "buy_amount": data.get("buyAmount"),
                        "price": data.get("price"),
                        "estimated_gas": data.get("estimatedGas", 0),
                        "gas_price": data.get("gasPrice", "0"),
                        "sources": data.get("sources", []),
                        "protocol_fee": data.get("protocolFee", "0"),
                        "minimum_protocol_fee": data.get("minimumProtocolFee", "0"),
                    }

                    logger.info(
                        f"Got quote on chain {chain_id}: "
                        f"{data.get('sellAmount')} {token_in[:6]}... -> "
                        f"{data.get('buyAmount')} {token_out[:6]}..."
                    )

                    return quote
                else:
                    logger.warning(
                        f"0x API returned status {response.status_code} for chain {chain_id}: {response.text}"
                    )
                    return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting quote for chain {chain_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting quote for chain {chain_id}: {e}")
            return None

    async def get_multi_chain_quotes(
        self,
        chains: List[int],
        token_in: str,
        token_out: str,
        amount_in: str,
    ) -> Dict[int, Optional[Dict]]:
        """
        Get quotes from multiple chains in parallel

        Args:
            chains: List of chain IDs
            token_in: Input token address
            token_out: Output token address
            amount_in: Amount in (in wei)

        Returns:
            Dictionary mapping chain_id to quote data
        """
        import asyncio

        tasks = []
        for chain_id in chains:
            task = self.get_quote(chain_id, token_in, token_out, amount_in)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        quotes = {}
        for chain_id, result in zip(chains, results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching quote for chain {chain_id}: {result}")
                quotes[chain_id] = None
            else:
                quotes[chain_id] = result

        return quotes

    def calculate_effective_price(
        self,
        sell_amount: str,
        buy_amount: str,
        include_fee: bool = True,
        fee_bps: int = 30,
    ) -> Optional[float]:
        """
        Calculate effective price accounting for fees

        Args:
            sell_amount: Amount sold (in wei)
            buy_amount: Amount bought (in wei)
            include_fee: Whether to include DEX fee in calculation
            fee_bps: Fee in basis points (default 30 = 0.3%)

        Returns:
            Effective price (buy_amount / sell_amount adjusted for fees)
        """
        try:
            sell = Decimal(sell_amount)
            buy = Decimal(buy_amount)

            if sell == 0:
                return None

            # Raw price
            price = float(buy / sell)

            # Adjust for fees if requested
            if include_fee:
                fee_multiplier = Decimal(1) - (Decimal(fee_bps) / Decimal(10000))
                adjusted_buy = buy * fee_multiplier
                price = float(adjusted_buy / sell)

            return price

        except Exception as e:
            logger.error(f"Error calculating effective price: {e}")
            return None

    def get_token_address(self, chain_id: int, symbol: str) -> Optional[str]:
        """Get token address for a symbol on a given chain"""
        chain_tokens = COMMON_TOKENS.get(chain_id, {})
        return chain_tokens.get(symbol.upper())
