#!/bin/bash
# Quick script to view Redis data

REDIS_URL="${REDIS_URL:-$(grep REDIS_URL .env 2>/dev/null | cut -d'=' -f2-)}"

if [ -z "$REDIS_URL" ]; then
    echo "Error: REDIS_URL not set"
    exit 1
fi

USER_ID="${1:-browser_user}"

echo "=== Redis Data for user: $USER_ID ==="
echo ""

# Count keys
echo "Counting keys..."
INTERVENTION_COUNT=$(redis-cli -u "$REDIS_URL" --scan --pattern "user:${USER_ID}:intervention:*" 2>/dev/null | wc -l | tr -d ' ')
REFLECTION_COUNT=$(redis-cli -u "$REDIS_URL" --scan --pattern "user:${USER_ID}:reflection:*" 2>/dev/null | wc -l | tr -d ' ')

echo "Interventions: $INTERVENTION_COUNT"
echo "Reflections: $REFLECTION_COUNT"
echo ""

# List intervention keys
echo "=== Intervention Keys ==="
redis-cli -u "$REDIS_URL" --scan --pattern "user:${USER_ID}:intervention:*" 2>/dev/null | head -5
echo ""

# Show one intervention example
FIRST_KEY=$(redis-cli -u "$REDIS_URL" --scan --pattern "user:${USER_ID}:intervention:*" 2>/dev/null | head -1)
if [ -n "$FIRST_KEY" ]; then
    echo "=== Example Intervention ==="
    redis-cli -u "$REDIS_URL" JSON.GET "$FIRST_KEY" 2>/dev/null | python3 -m json.tool 2>/dev/null || redis-cli -u "$REDIS_URL" JSON.GET "$FIRST_KEY" 2>/dev/null
    echo ""
    echo "TTL: $(redis-cli -u "$REDIS_URL" TTL "$FIRST_KEY" 2>/dev/null) seconds"
fi

echo ""
echo "=== To view in Redis CLI ==="
echo "redis-cli -u \"$REDIS_URL\""
echo "> KEYS user:${USER_ID}:*"
echo "> JSON.GET user:${USER_ID}:intervention:KEY_HERE"
