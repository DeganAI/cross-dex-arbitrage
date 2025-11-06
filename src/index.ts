import { createAgentApp } from "@lucid-agents/agent-kit";
import { Hono } from "hono";
import { z } from "zod";

// Input schema
const ArbitrageInputSchema = z.object({
  chain_id: z.number().describe("Chain ID to scan (1=Ethereum, 8453=Base, 42161=Arbitrum, etc.)"),
  min_profit_pct: z.number().describe("Minimum profit percentage threshold (e.g., 0.5 for 0.5%)"),
  token_addresses: z.array(z.string()).optional().describe("Optional: specific token addresses to check"),
});

// Output schema
const ArbitrageOutputSchema = z.object({
  opportunities: z.array(z.object({
    token_symbol: z.string(),
    token_address: z.string().optional(),
    buy_dex: z.string(),
    sell_dex: z.string(),
    buy_price: z.number(),
    sell_price: z.number(),
    profit_percentage: z.number(),
    profit_usd_per_1k: z.number(),
    gas_cost_usd: z.number(),
    net_profit_usd: z.number(),
    executable: z.boolean(),
  })),
  total_found: z.number(),
  timestamp: z.string(),
});

const { app, addEntrypoint, config } = createAgentApp(
  {
    name: "Cross DEX Arbitrage",
    version: "1.0.0",
    description: "Scan for price discrepancies and arbitrage opportunities across DEXes",
  },
  {
    config: {
      payments: {
        facilitatorUrl: "https://facilitator.daydreams.systems",
        payTo: "0x01D11F7e1a46AbFC6092d7be484895D2d505095c",
        network: "base",
        asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        defaultPrice: "$0.10", // 0.10 USDC
      },
    },
    useConfigPayments: true,
    ap2: {
      required: true,
      params: { roles: ["merchant"] },
    },
  }
);

interface ArbitrageOpportunity {
  token_symbol: string;
  token_address?: string;
  buy_dex: string;
  sell_dex: string;
  buy_price: number;
  sell_price: number;
  profit_percentage: number;
  profit_usd_per_1k: number;
  gas_cost_usd: number;
  net_profit_usd: number;
  executable: boolean;
}

const CHAIN_GAS_COSTS: Record<number, number> = {
  1: 5.0, // Ethereum mainnet
  8453: 0.01, // Base
  42161: 0.15, // Arbitrum
  10: 0.05, // Optimism
  137: 0.02, // Polygon
  56: 0.08, // BSC
};

async function findArbitrage(
  chainId: number,
  minProfitPct: number,
  tokenAddresses?: string[]
): Promise<ArbitrageOpportunity[]> {
  // This is a simplified implementation
  // In production, this would:
  // 1. Query multiple DEX aggregators (1inch, 0x, Paraswap)
  // 2. Fetch real-time prices from on-chain or API sources
  // 3. Calculate actual gas costs based on current network conditions
  // 4. Consider slippage and liquidity depth

  const gasCost = CHAIN_GAS_COSTS[chainId] || 2.5;

  // Mock opportunities for demonstration
  // In production, replace with actual DEX price queries
  const mockOpportunities: ArbitrageOpportunity[] = [
    {
      token_symbol: "USDC",
      token_address: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
      buy_dex: "Uniswap V3",
      sell_dex: "SushiSwap",
      buy_price: 0.998,
      sell_price: 1.002,
      profit_percentage: 0.4,
      profit_usd_per_1k: 4.0,
      gas_cost_usd: gasCost,
      net_profit_usd: 4.0 - gasCost,
      executable: 4.0 - gasCost > 0,
    },
    {
      token_symbol: "WETH",
      token_address: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
      buy_dex: "Curve",
      sell_dex: "Balancer",
      buy_price: 2485.5,
      sell_price: 2497.8,
      profit_percentage: 0.49,
      profit_usd_per_1k: 4.9,
      gas_cost_usd: gasCost,
      net_profit_usd: 4.9 - gasCost,
      executable: 4.9 - gasCost > 0,
    },
    {
      token_symbol: "USDT",
      token_address: "0xdAC17F958D2ee523a2206206994597C13D831ec7",
      buy_dex: "Uniswap V2",
      sell_dex: "Pancakeswap",
      buy_price: 0.9985,
      sell_price: 1.0005,
      profit_percentage: 0.2,
      profit_usd_per_1k: 2.0,
      gas_cost_usd: gasCost,
      net_profit_usd: 2.0 - gasCost,
      executable: 2.0 - gasCost > 0,
    },
  ];

  // Filter by minimum profit percentage
  let opportunities = mockOpportunities.filter(
    (opp) => opp.profit_percentage >= minProfitPct
  );

  // Filter by token addresses if provided
  if (tokenAddresses && tokenAddresses.length > 0) {
    opportunities = opportunities.filter((opp) =>
      tokenAddresses.some((addr) =>
        opp.token_address?.toLowerCase() === addr.toLowerCase()
      )
    );
  }

  return opportunities;
}

// Register entrypoint
addEntrypoint({
  key: "cross-dex-arbitrage",
  description: "Scan for arbitrage opportunities across DEXes with configurable profit thresholds",
  input: ArbitrageInputSchema,
  output: ArbitrageOutputSchema,
  price: "$0.10", // 0.10 USDC
  async handler({ input }) {
    const opportunities = await findArbitrage(
      input.chain_id,
      input.min_profit_pct,
      input.token_addresses
    );

    return {
      output: {
        opportunities,
        total_found: opportunities.length,
        timestamp: new Date().toISOString(),
      },
    };
  },
});

// Create wrapper app for internal API
const wrapperApp = new Hono();

// Internal API endpoint (no payment required)
wrapperApp.post("/api/internal/cross-dex-arbitrage", async (c) => {
  try {
    // Check API key authentication
    const apiKey = c.req.header("X-Internal-API-Key");
    const expectedKey = process.env.INTERNAL_API_KEY;

    if (!expectedKey) {
      console.error("[INTERNAL API] INTERNAL_API_KEY not set");
      return c.json({ error: "Server configuration error" }, 500);
    }

    if (apiKey !== expectedKey) {
      return c.json({ error: "Unauthorized" }, 401);
    }

    // Get input from request body
    const input = await c.req.json();

    // Validate input
    const validatedInput = ArbitrageInputSchema.parse(input);

    // Call the same logic as x402 endpoint
    const opportunities = await findArbitrage(
      validatedInput.chain_id,
      validatedInput.min_profit_pct,
      validatedInput.token_addresses
    );

    return c.json({
      opportunities,
      total_found: opportunities.length,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("[INTERNAL API] Error:", error);
    return c.json({ error: error instanceof Error ? error.message : "Internal error" }, 500);
  }
});

// Mount the x402 agent app (public, requires payment)
wrapperApp.route("/", app);

// Export for Bun
export default {
  port: parseInt(process.env.PORT || "3000"),
  fetch: wrapperApp.fetch,
};

console.log(`🚀 Cross DEX Arbitrage running on port ${process.env.PORT || 3000}`);
console.log(`📝 Manifest: ${process.env.BASE_URL}/.well-known/agent.json`);
console.log(`💰 Payment address: ${config.payments?.payTo}`);
console.log(`🔓 Internal API: /api/internal/cross-dex-arbitrage (requires API key)`);
