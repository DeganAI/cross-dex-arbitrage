"""
Gas cost calculator for different chains
"""
import logging
from typing import Dict, Optional
from web3 import Web3
import os

logger = logging.getLogger(__name__)

# Chain configurations
CHAIN_CONFIG = {
    1: {  # Ethereum
        "name": "Ethereum",
        "symbol": "ETH",
        "rpc_env": "ETHEREUM_RPC_URL",
        "supports_eip1559": True,
        "base_swap_gas": 150000,  # Base gas for swap
        "avg_block_time": 12,
    },
    137: {  # Polygon
        "name": "Polygon",
        "symbol": "MATIC",
        "rpc_env": "POLYGON_RPC_URL",
        "supports_eip1559": True,
        "base_swap_gas": 180000,
        "avg_block_time": 2,
    },
    42161: {  # Arbitrum
        "name": "Arbitrum",
        "symbol": "ETH",
        "rpc_env": "ARBITRUM_RPC_URL",
        "supports_eip1559": True,
        "base_swap_gas": 200000,
        "avg_block_time": 0.25,
    },
    10: {  # Optimism
        "name": "Optimism",
        "symbol": "ETH",
        "rpc_env": "OPTIMISM_RPC_URL",
        "supports_eip1559": True,
        "base_swap_gas": 180000,
        "avg_block_time": 2,
    },
    8453: {  # Base
        "name": "Base",
        "symbol": "ETH",
        "rpc_env": "BASE_RPC_URL",
        "supports_eip1559": True,
        "base_swap_gas": 180000,
        "avg_block_time": 2,
    },
    56: {  # BNB Chain
        "name": "BNB Chain",
        "symbol": "BNB",
        "rpc_env": "BSC_RPC_URL",
        "supports_eip1559": False,
        "base_swap_gas": 200000,
        "avg_block_time": 3,
    },
    43114: {  # Avalanche
        "name": "Avalanche",
        "symbol": "AVAX",
        "rpc_env": "AVALANCHE_RPC_URL",
        "supports_eip1559": True,
        "base_swap_gas": 180000,
        "avg_block_time": 2,
    },
}


class GasCalculator:
    """Calculate gas costs for different chains"""

    def __init__(self, rpc_urls: Dict[int, str]):
        """
        Initialize with RPC URLs for each chain

        Args:
            rpc_urls: Mapping of chain_id to RPC URL
        """
        self.rpc_urls = rpc_urls
        self.w3_instances: Dict[int, Web3] = {}

        # Initialize Web3 instances
        for chain_id, rpc_url in rpc_urls.items():
            try:
                w3 = Web3(Web3.HTTPProvider(rpc_url))
                if w3.is_connected():
                    self.w3_instances[chain_id] = w3
                    logger.info(f"Connected to {CHAIN_CONFIG[chain_id]['name']} (chain {chain_id})")
                else:
                    logger.warning(f"Failed to connect to chain {chain_id}")
            except Exception as e:
                logger.error(f"Error connecting to chain {chain_id}: {e}")

    def get_chain_info(self, chain_id: int) -> Optional[Dict]:
        """Get chain configuration"""
        return CHAIN_CONFIG.get(chain_id)

    def get_available_chains(self) -> list[int]:
        """Get list of available chain IDs"""
        return list(self.w3_instances.keys())

    async def get_gas_price(self, chain_id: int) -> Optional[Dict]:
        """
        Get current gas price for a chain

        Returns:
            Dict with gas_price_gwei and optionally base_fee_gwei, priority_fee_gwei
        """
        if chain_id not in self.w3_instances:
            return None

        w3 = self.w3_instances[chain_id]
        config = CHAIN_CONFIG[chain_id]

        try:
            if config["supports_eip1559"]:
                # EIP-1559 chains
                latest_block = w3.eth.get_block("latest")
                base_fee = latest_block.get("baseFeePerGas", 0)

                # Get priority fee suggestion (or use default)
                try:
                    max_priority_fee = w3.eth.max_priority_fee
                except:
                    max_priority_fee = Web3.to_wei(1, "gwei")  # Default 1 gwei

                gas_price_wei = base_fee + max_priority_fee
                gas_price_gwei = float(Web3.from_wei(gas_price_wei, "gwei"))
                base_fee_gwei = float(Web3.from_wei(base_fee, "gwei"))
                priority_fee_gwei = float(Web3.from_wei(max_priority_fee, "gwei"))

                return {
                    "gas_price_gwei": gas_price_gwei,
                    "base_fee_gwei": base_fee_gwei,
                    "priority_fee_gwei": priority_fee_gwei,
                    "symbol": config["symbol"],
                    "name": config["name"],
                }
            else:
                # Legacy chains
                gas_price_wei = w3.eth.gas_price
                gas_price_gwei = float(Web3.from_wei(gas_price_wei, "gwei"))

                return {
                    "gas_price_gwei": gas_price_gwei,
                    "symbol": config["symbol"],
                    "name": config["name"],
                }

        except Exception as e:
            logger.error(f"Error fetching gas price for chain {chain_id}: {e}")
            return None

    def calculate_gas_cost(
        self,
        chain_id: int,
        gas_price_gwei: float,
        swap_complexity: int = 1,
    ) -> Optional[Dict]:
        """
        Calculate gas cost for a swap operation

        Args:
            chain_id: Chain ID
            gas_price_gwei: Gas price in gwei
            swap_complexity: 1 for simple swap, 2+ for multi-hop

        Returns:
            Dict with gas_units, gas_cost_native, etc.
        """
        config = self.get_chain_info(chain_id)
        if not config:
            return None

        # Calculate total gas needed
        base_gas = config["base_swap_gas"]
        total_gas = base_gas * swap_complexity

        # Calculate cost in native token
        gas_cost_wei = Web3.to_wei(gas_price_gwei, "gwei") * total_gas
        gas_cost_native = float(Web3.from_wei(gas_cost_wei, "ether"))

        return {
            "gas_units": total_gas,
            "gas_price_gwei": gas_price_gwei,
            "gas_cost_native": gas_cost_native,
            "symbol": config["symbol"],
            "chain_name": config["name"],
        }


def initialize_gas_calculator() -> GasCalculator:
    """Initialize gas calculator with RPC URLs from environment"""
    rpc_urls = {}

    for chain_id, config in CHAIN_CONFIG.items():
        rpc_url = os.getenv(config["rpc_env"])
        if rpc_url:
            rpc_urls[chain_id] = rpc_url

    return GasCalculator(rpc_urls)
