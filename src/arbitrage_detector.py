"""
Arbitrage detection logic for Cross DEX Arbitrage Alert
Detects profitable arbitrage opportunities across multiple chains and DEXs
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class ArbitrageRoute:
    """Represents an arbitrage opportunity"""

    chain_id: int
    chain_name: str
    dex_sources: List[str]
    token_in: str
    token_out: str
    amount_in: str
    amount_out: str
    effective_price: float
    gas_cost_native: float
    gas_cost_usd: float
    dex_fee_bps: int
    net_spread_bps: float
    est_fill_cost_usd: float
    profit_usd: float
    estimated_gas_units: int
    confidence_score: float


class ArbitrageDetector:
    """
    Detects arbitrage opportunities across chains and DEXs
    """

    def __init__(self, token_prices: Dict[str, float]):
        """
        Initialize detector with token prices

        Args:
            token_prices: Dictionary mapping token symbols to USD prices
        """
        self.token_prices = token_prices

    def calculate_spread(
        self,
        buy_price: float,
        sell_price: float,
    ) -> float:
        """
        Calculate spread in basis points

        Args:
            buy_price: Price to buy at
            sell_price: Price to sell at

        Returns:
            Spread in basis points (can be negative if no arbitrage)
        """
        if buy_price == 0:
            return 0.0

        spread = (sell_price - buy_price) / buy_price
        return spread * 10000  # Convert to basis points

    def calculate_net_spread(
        self,
        gross_spread_bps: float,
        gas_cost_usd: float,
        dex_fee_bps: int,
        trade_size_usd: float,
    ) -> float:
        """
        Calculate net spread after fees and gas

        Args:
            gross_spread_bps: Gross spread in basis points
            gas_cost_usd: Gas cost in USD
            dex_fee_bps: DEX fee in basis points
            trade_size_usd: Trade size in USD

        Returns:
            Net spread in basis points
        """
        # Convert gross spread to dollar amount
        gross_profit = (gross_spread_bps / 10000) * trade_size_usd

        # Subtract gas cost
        profit_after_gas = gross_profit - gas_cost_usd

        # Subtract DEX fees (both buy and sell sides)
        dex_fee_amount = (dex_fee_bps * 2 / 10000) * trade_size_usd
        net_profit = profit_after_gas - dex_fee_amount

        # Convert back to basis points
        if trade_size_usd == 0:
            return 0.0

        net_spread_bps = (net_profit / trade_size_usd) * 10000
        return net_spread_bps

    def calculate_confidence_score(
        self,
        quote_data: Dict,
        gas_data: Dict,
        net_spread_bps: float,
    ) -> float:
        """
        Calculate confidence score for the arbitrage opportunity

        Factors:
        - Liquidity depth (from quote sources)
        - Gas price stability
        - Net spread magnitude
        - Number of DEX sources

        Returns:
            Confidence score 0-100
        """
        score = 50.0  # Base score

        # Factor 1: Net spread magnitude (higher = more confident)
        if net_spread_bps > 100:  # > 1%
            score += 20
        elif net_spread_bps > 50:  # > 0.5%
            score += 10
        elif net_spread_bps > 20:  # > 0.2%
            score += 5

        # Factor 2: Number of DEX sources (more = better liquidity)
        sources = quote_data.get("sources", [])
        active_sources = [s for s in sources if float(s.get("proportion", 0)) > 0]
        if len(active_sources) >= 3:
            score += 15
        elif len(active_sources) >= 2:
            score += 10
        elif len(active_sources) >= 1:
            score += 5

        # Factor 3: Gas price (lower congestion = more reliable)
        gas_price_gwei = gas_data.get("gas_price_gwei", 0)
        if gas_price_gwei < 20:
            score += 10
        elif gas_price_gwei < 50:
            score += 5

        # Factor 4: Estimated gas accuracy
        estimated_gas = quote_data.get("estimated_gas", 0)
        if estimated_gas > 0:
            score += 5

        # Cap at 100
        return min(score, 100.0)

    def analyze_route(
        self,
        chain_id: int,
        chain_name: str,
        quote_data: Dict,
        gas_data: Dict,
        token_in: str,
        token_out: str,
    ) -> Optional[ArbitrageRoute]:
        """
        Analyze a single route for arbitrage potential

        Args:
            chain_id: Chain ID
            chain_name: Chain name
            quote_data: Quote data from DEX
            gas_data: Gas price data
            token_in: Input token address
            token_out: Output token address

        Returns:
            ArbitrageRoute if profitable, None otherwise
        """
        try:
            # Extract data
            sell_amount = quote_data.get("sell_amount", "0")
            buy_amount = quote_data.get("buy_amount", "0")
            estimated_gas = quote_data.get("estimated_gas", 0)
            sources = quote_data.get("sources", [])

            # Get DEX source names
            dex_sources = [
                s.get("name", "unknown")
                for s in sources
                if float(s.get("proportion", 0)) > 0
            ]

            # Calculate gas cost
            gas_price_gwei = gas_data.get("gas_price_gwei", 0)
            gas_cost_native = gas_data.get("gas_cost_native", 0)

            # Convert gas cost to USD
            native_symbol = gas_data.get("symbol", "ETH")
            native_price_usd = self.token_prices.get(native_symbol, 0)
            gas_cost_usd = gas_cost_native * native_price_usd

            # Calculate effective price
            if sell_amount == "0" or buy_amount == "0":
                return None

            effective_price = float(Decimal(buy_amount) / Decimal(sell_amount))

            # Estimate trade size in USD (using input token)
            # For simplicity, assume stablecoin or use ETH price
            trade_size_usd = float(Decimal(sell_amount) / Decimal(10**18)) * native_price_usd

            # DEX fee (assume 0.3% = 30 bps for most DEXs)
            dex_fee_bps = 30

            # Calculate fill cost (gas + DEX fees)
            dex_fee_amount = (dex_fee_bps / 10000) * trade_size_usd
            est_fill_cost_usd = gas_cost_usd + dex_fee_amount

            # Calculate spreads
            # For arbitrage, we need to compare against another chain
            # For now, calculate net profitability assuming we can buy cheaper elsewhere
            # This will be refined when comparing multiple routes
            gross_spread_bps = 0  # Will be set when comparing routes
            net_spread_bps = -dex_fee_bps - (gas_cost_usd / trade_size_usd * 10000)

            # Calculate profit (will be negative if not profitable)
            profit_usd = -est_fill_cost_usd

            # Confidence score
            confidence = self.calculate_confidence_score(quote_data, gas_data, net_spread_bps)

            route = ArbitrageRoute(
                chain_id=chain_id,
                chain_name=chain_name,
                dex_sources=dex_sources,
                token_in=token_in,
                token_out=token_out,
                amount_in=sell_amount,
                amount_out=buy_amount,
                effective_price=effective_price,
                gas_cost_native=gas_cost_native,
                gas_cost_usd=gas_cost_usd,
                dex_fee_bps=dex_fee_bps,
                net_spread_bps=net_spread_bps,
                est_fill_cost_usd=est_fill_cost_usd,
                profit_usd=profit_usd,
                estimated_gas_units=estimated_gas,
                confidence_score=confidence,
            )

            return route

        except Exception as e:
            logger.error(f"Error analyzing route for chain {chain_id}: {e}")
            return None

    def compare_routes(
        self,
        routes: List[ArbitrageRoute],
    ) -> Dict:
        """
        Compare all routes and identify arbitrage opportunities

        Args:
            routes: List of ArbitrageRoute objects

        Returns:
            Dict with best_route, alt_routes, and analysis
        """
        if not routes:
            return {
                "best_route": None,
                "alt_routes": [],
                "opportunities_found": 0,
            }

        # Sort by effective price (best price first)
        sorted_routes = sorted(routes, key=lambda r: r.effective_price, reverse=True)

        # Best route (highest output for same input)
        best = sorted_routes[0]
        worst = sorted_routes[-1]

        # Calculate actual spread between best and worst
        if worst.effective_price > 0:
            actual_spread_bps = (
                (best.effective_price - worst.effective_price) / worst.effective_price * 10000
            )
        else:
            actual_spread_bps = 0

        # Update best route with actual spread calculations
        best_trade_size_usd = float(Decimal(best.amount_in) / Decimal(10**18)) * self.token_prices.get(best.chain_name, 2000)

        net_spread = self.calculate_net_spread(
            gross_spread_bps=actual_spread_bps,
            gas_cost_usd=best.gas_cost_usd + worst.gas_cost_usd,  # Both legs
            dex_fee_bps=best.dex_fee_bps,
            trade_size_usd=best_trade_size_usd,
        )

        # Calculate profit
        gross_profit = (actual_spread_bps / 10000) * best_trade_size_usd
        net_profit = gross_profit - (best.gas_cost_usd + worst.gas_cost_usd) - (
            (best.dex_fee_bps * 2 / 10000) * best_trade_size_usd
        )

        # Update best route
        best.net_spread_bps = net_spread
        best.profit_usd = net_profit

        # Alternatives (exclude best)
        alternatives = []
        for route in sorted_routes[1:]:
            # Calculate spread vs best
            if best.effective_price > 0:
                spread_vs_best = (
                    (route.effective_price - best.effective_price) / best.effective_price * 10000
                )
            else:
                spread_vs_best = 0

            route.net_spread_bps = spread_vs_best
            alternatives.append(route)

        # Count profitable opportunities
        profitable = sum(1 for r in routes if r.net_spread_bps > 0)

        return {
            "best_route": best,
            "alt_routes": alternatives[:5],  # Top 5 alternatives
            "opportunities_found": profitable,
            "total_routes_analyzed": len(routes),
            "gross_spread_bps": actual_spread_bps,
        }
