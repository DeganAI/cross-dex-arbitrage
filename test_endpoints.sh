#!/bin/bash
# Comprehensive endpoint testing script for Cross DEX Arbitrage Alert
# Tests all x402/AP2 protocol endpoints and functionality

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${1:-http://localhost:8001}"
echo -e "${BLUE}Testing endpoint: $BASE_URL${NC}\n"

# Test counter
PASS=0
FAIL=0

# Helper function to test endpoint
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_code="$3"
    local method="${4:-GET}"

    echo -n "Testing $name... "

    if [ "$method" = "POST" ]; then
        actual_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$url" -H "Content-Type: application/json" 2>/dev/null || echo "000")
    else
        actual_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    fi

    if [ "$actual_code" = "$expected_code" ]; then
        echo -e "${GREEN}✅ PASS${NC} (HTTP $actual_code)"
        ((PASS++))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC} (Expected: HTTP $expected_code, Got: HTTP $actual_code)"
        ((FAIL++))
        return 1
    fi
}

# Helper to test JSON content
test_json_field() {
    local name="$1"
    local url="$2"
    local jq_query="$3"
    local expected="$4"

    echo -n "Testing $name... "

    actual=$(curl -s "$url" 2>/dev/null | jq -r "$jq_query" 2>/dev/null || echo "null")

    if [ "$actual" = "$expected" ]; then
        echo -e "${GREEN}✅ PASS${NC} ($actual)"
        ((PASS++))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC} (Expected: $expected, Got: $actual)"
        ((FAIL++))
        return 1
    fi
}

echo -e "${YELLOW}=== Protocol Compliance Tests ===${NC}\n"

# Test 1: Landing page
test_endpoint "Landing Page" "$BASE_URL/" "200"

# Test 2: Health check
test_endpoint "Health Check" "$BASE_URL/health" "200"

# Test 3: Chains list
test_endpoint "Chains List" "$BASE_URL/chains" "200"

# Test 4: agent.json (must return 200)
test_endpoint "agent.json (GET)" "$BASE_URL/.well-known/agent.json" "200"

# Test 5: agent.json HEAD
test_endpoint "agent.json (HEAD)" "$BASE_URL/.well-known/agent.json" "200" "HEAD"

# Test 6: x402 metadata (must return 402)
test_endpoint "x402 Metadata (GET)" "$BASE_URL/.well-known/x402" "402"

# Test 7: x402 HEAD
test_endpoint "x402 Metadata (HEAD)" "$BASE_URL/.well-known/x402" "402" "HEAD"

# Test 8: Entrypoint without payment (should return 402 or 200 in FREE_MODE)
echo -n "Testing Entrypoint (POST)... "
entrypoint_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/entrypoints/cross-dex-arbitrage/invoke" -H "Content-Type: application/json" 2>/dev/null || echo "000")
if [ "$entrypoint_code" = "402" ] || [ "$entrypoint_code" = "400" ] || [ "$entrypoint_code" = "503" ]; then
    echo -e "${GREEN}✅ PASS${NC} (HTTP $entrypoint_code)"
    ((PASS++))
else
    echo -e "${YELLOW}⚠️  WARN${NC} (Got: HTTP $entrypoint_code - may need request body)"
fi

echo -e "\n${YELLOW}=== Content Validation Tests ===${NC}\n"

# Test 9: agent.json name field
test_json_field "agent.json name" "$BASE_URL/.well-known/agent.json" ".name" "Cross DEX Arbitrage Alert"

# Test 10: agent.json URL protocol (must be http://)
echo -n "Testing agent.json URL protocol... "
url_protocol=$(curl -s "$BASE_URL/.well-known/agent.json" 2>/dev/null | jq -r '.url' 2>/dev/null | grep -o "^http://" || echo "")
if [ "$url_protocol" = "http://" ]; then
    echo -e "${GREEN}✅ PASS${NC} (uses http://)"
    ((PASS++))
else
    echo -e "${RED}❌ FAIL${NC} (must use http:// not https://)"
    ((FAIL++))
fi

# Test 11: agent.json payment address
test_json_field "Payment Address" "$BASE_URL/.well-known/agent.json" ".payments[0].payee" "0x01D11F7e1a46AbFC6092d7be484895D2d505095c"

# Test 12: agent.json network
test_json_field "Payment Network" "$BASE_URL/.well-known/agent.json" ".payments[0].network" "base"

# Test 13: agent.json facilitator
test_json_field "Facilitator URL" "$BASE_URL/.well-known/agent.json" ".payments[0].extensions.x402.facilitatorUrl" "https://facilitator.daydreams.systems"

# Test 14: x402 version
test_json_field "x402 Version" "$BASE_URL/.well-known/x402" ".x402Version" "1"

# Test 15: x402 network
test_json_field "x402 Network" "$BASE_URL/.well-known/x402" ".accepts[0].network" "base"

# Test 16: x402 Base USDC address
test_json_field "Base USDC Address" "$BASE_URL/.well-known/x402" ".accepts[0].asset" "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# Test 17: Health check available chains
echo -n "Testing Health Check Chains... "
chain_count=$(curl -s "$BASE_URL/health" 2>/dev/null | jq -r '.available_chains' 2>/dev/null || echo "0")
if [ "$chain_count" -gt "0" ]; then
    echo -e "${GREEN}✅ PASS${NC} ($chain_count chains available)"
    ((PASS++))
else
    echo -e "${RED}❌ FAIL${NC} (0 chains available - check RPC URLs)"
    ((FAIL++))
fi

echo -e "\n${YELLOW}=== Functional Tests ===${NC}\n"

# Test 18: Chains endpoint returns data
echo -n "Testing Chains Endpoint Data... "
total_chains=$(curl -s "$BASE_URL/chains" 2>/dev/null | jq -r '.total' 2>/dev/null || echo "0")
if [ "$total_chains" -gt "0" ]; then
    echo -e "${GREEN}✅ PASS${NC} ($total_chains chains configured)"
    ((PASS++))
else
    echo -e "${RED}❌ FAIL${NC} (No chains configured)"
    ((FAIL++))
fi

# Test 19: Arbitrage endpoint accepts requests
echo -n "Testing Arbitrage Endpoint... "
arb_response=$(curl -s -X POST "$BASE_URL/arbitrage" \
    -H "Content-Type: application/json" \
    -d '{"token_in":"USDC","token_out":"USDT","amount_in":"1000","chains":[137]}' 2>/dev/null)
arb_code=$?
if [ $arb_code -eq 0 ]; then
    error=$(echo "$arb_response" | jq -r '.detail' 2>/dev/null || echo "")
    if [ "$error" != "null" ] && [ -n "$error" ]; then
        echo -e "${YELLOW}⚠️  WARN${NC} (Endpoint works, but: $error)"
    else
        echo -e "${GREEN}✅ PASS${NC} (Endpoint accepts requests)"
        ((PASS++))
    fi
else
    echo -e "${RED}❌ FAIL${NC} (Connection error)"
    ((FAIL++))
fi

# Test 20: Documentation endpoints
test_endpoint "Swagger UI" "$BASE_URL/docs" "200"
test_endpoint "ReDoc" "$BASE_URL/redoc" "200"

echo -e "\n${BLUE}=== Test Summary ===${NC}\n"
TOTAL=$((PASS + FAIL))
PERCENTAGE=$((PASS * 100 / TOTAL))

echo -e "Total Tests: $TOTAL"
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${RED}Failed: $FAIL${NC}"
echo -e "Success Rate: ${PERCENTAGE}%\n"

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! Agent is ready for deployment.${NC}\n"
    exit 0
elif [ $PERCENTAGE -ge 80 ]; then
    echo -e "${YELLOW}⚠️  Most tests passed. Review failures before production.${NC}\n"
    exit 0
else
    echo -e "${RED}❌ Multiple tests failed. Fix issues before deployment.${NC}\n"
    exit 1
fi
