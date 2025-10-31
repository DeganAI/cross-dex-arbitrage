# Production Setup - Enable Payment Enforcement

**IMPORTANT:** After testing is complete, FREE_MODE must be set to `false` to enforce x402 payments.

---

## Railway Environment Variables - PRODUCTION

Update these variables in Railway dashboard:

```bash
PORT=8000
BASE_URL=https://cross-dex-arbitrage-production.up.railway.app
PAYMENT_ADDRESS=0x01D11F7e1a46AbFC6092d7be484895D2d505095c
FREE_MODE=false  # ⚠️ MUST be false for production

# RPC URLs
ETHEREUM_RPC_URL=https://eth.llamarpc.com
POLYGON_RPC_URL=https://polygon-rpc.com
ARBITRUM_RPC_URL=https://arb1.arbitrum.io/rpc
OPTIMISM_RPC_URL=https://mainnet.optimism.io
BASE_RPC_URL=https://mainnet.base.org
BSC_RPC_URL=https://bsc-dataseed.binance.org
AVALANCHE_RPC_URL=https://api.avax.network/ext/bc/C/rpc
```

---

## How to Update Railway

1. **Go to:** https://railway.app/
2. **Select:** cross-dex-arbitrage project
3. **Click:** Variables tab
4. **Find:** `FREE_MODE`
5. **Change:** `true` → `false`
6. **Save:** Railway will auto-redeploy

---

## What Changes When FREE_MODE=false

### Before (FREE_MODE=true) - Testing
- All requests accepted without payment
- No x402 payment verification
- Used for testing and development

### After (FREE_MODE=false) - Production
- Requests without payment → **HTTP 402**
- Requires `X-Payment-TxHash` header with Base USDC payment
- Payment must be 0.05 USDC (50000 smallest units)
- Payment verified on Base network

---

## Payment Flow

When `FREE_MODE=false`:

1. **Client makes request without payment:**
   ```bash
   curl -X POST https://cross-dex-arbitrage-production.up.railway.app/entrypoints/cross-dex-arbitrage/invoke
   ```

2. **Server returns HTTP 402:**
   ```json
   {
     "x402Version": 1,
     "accepts": [{
       "scheme": "exact",
       "network": "base",
       "maxAmountRequired": "50000",
       "payTo": "0x01D11F7e1a46AbFC6092d7be484895D2d505095c",
       "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
     }]
   }
   ```

3. **Client sends 0.05 USDC on Base to payment address**

4. **Client retries with payment proof:**
   ```bash
   curl -X POST https://cross-dex-arbitrage-production.up.railway.app/entrypoints/cross-dex-arbitrage/invoke \
     -H "X-Payment-TxHash: 0xabc123..." \
     -H "Content-Type: application/json" \
     -d '{"token_in":"USDC","token_out":"USDT","amount_in":"1000","chains":[137,8453]}'
   ```

5. **Server verifies payment and processes request**

---

## Testing After Enabling Payment

### Test 402 Response (should still work)
```bash
curl -I https://cross-dex-arbitrage-production.up.railway.app/entrypoints/cross-dex-arbitrage/invoke
# Should return: HTTP/2 402
```

### Test Request Without Payment (should fail)
```bash
curl -X POST https://cross-dex-arbitrage-production.up.railway.app/entrypoints/cross-dex-arbitrage/invoke \
  -H "Content-Type: application/json" \
  -d '{"token_in":"USDC","token_out":"USDT","amount_in":"1000","chains":[137]}'
# Should return: HTTP 402 with payment info
```

### Test Health Check (should still work - free)
```bash
curl https://cross-dex-arbitrage-production.up.railway.app/health
# Should return: HTTP 200 with status
```

---

## Monitoring Payments

When `FREE_MODE=false`, monitor the payment address on Base:

**Payment Address:** `0x01D11F7e1a46AbFC6092d7be484895D2d505095c`

**View on BaseScan:**
https://basescan.org/address/0x01D11F7e1a46AbFC6092d7be484895D2d505095c

**Expected Revenue:**
- 0.05 USDC per request
- Paid in Base USDC: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`

---

## Rollback to Free Mode (if needed)

If you need to disable payment enforcement:

1. Set `FREE_MODE=true` in Railway
2. Railway will auto-redeploy
3. All requests accepted without payment

**Use free mode only for:**
- Testing
- Development
- Debugging
- Demo purposes

**NEVER use free mode for:**
- Production bounty submissions
- Public deployment
- Revenue generation

---

## Checklist for Production

- [ ] Set `FREE_MODE=false` in Railway
- [ ] Verify 402 response still works
- [ ] Test that requests without payment are rejected
- [ ] Confirm health check still free
- [ ] Monitor payment address for incoming USDC
- [ ] Update documentation if needed

---

**Current Status:** Testing complete ✅
**Action Required:** Set `FREE_MODE=false` in Railway for production

**Revenue:** 0.05 USDC per request × usage = earnings to `0x01D11F7e1a46AbFC6092d7be484895D2d505095c`
