#!/bin/bash

# NEST Monitoring Script for NASDAQ Stock Agent
# This script monitors NEST integration health and logs

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================="
echo "NEST Integration Monitoring"
echo "========================================="
echo ""

# Check if service is running
echo "1. Checking service status..."
if systemctl is-active --quiet nasdaq-agent; then
    echo -e "${GREEN}✓${NC} Service is running"
else
    echo -e "${RED}✗${NC} Service is not running"
    exit 1
fi

echo ""

# Check for NEST initialization in logs
echo "2. Checking NEST initialization..."
NEST_INIT=$(journalctl -u nasdaq-agent --since "10 minutes ago" | grep "NESTAdapter.*Initialized" | tail -1)
if [ -n "$NEST_INIT" ]; then
    echo -e "${GREEN}✓${NC} NEST adapter initialized"
    echo "   $NEST_INIT"
else
    echo -e "${YELLOW}⚠${NC} No recent NEST initialization found"
fi

echo ""

# Check for import errors
echo "3. Checking for import errors..."
IMPORT_ERRORS=$(journalctl -u nasdaq-agent --since "10 minutes ago" | grep -i "cannot import.*serve" | wc -l)
if [ "$IMPORT_ERRORS" -eq 0 ]; then
    echo -e "${GREEN}✓${NC} No python-a2a import errors"
else
    echo -e "${RED}✗${NC} Found $IMPORT_ERRORS import error(s)"
    journalctl -u nasdaq-agent --since "10 minutes ago" | grep -i "cannot import.*serve" | tail -3
fi

echo ""

# Check if A2A server started
echo "4. Checking A2A server status..."
A2A_STARTED=$(journalctl -u nasdaq-agent --since "10 minutes ago" | grep "A2A server started successfully" | tail -1)
if [ -n "$A2A_STARTED" ]; then
    echo -e "${GREEN}✓${NC} A2A server started successfully"
    echo "   $A2A_STARTED"
else
    echo -e "${YELLOW}⚠${NC} No recent A2A server start found"
fi

echo ""

# Check if port 6000 is listening
echo "5. Checking port 6000..."
if netstat -tuln 2>/dev/null | grep -q ":6000 "; then
    echo -e "${GREEN}✓${NC} Port 6000 is listening"
elif ss -tuln 2>/dev/null | grep -q ":6000 "; then
    echo -e "${GREEN}✓${NC} Port 6000 is listening"
else
    echo -e "${RED}✗${NC} Port 6000 is not listening"
fi

echo ""

# Check for registry registration
echo "6. Checking registry registration..."
REG_SUCCESS=$(journalctl -u nasdaq-agent --since "10 minutes ago" | grep "Successfully registered with NANDA Registry" | tail -1)
if [ -n "$REG_SUCCESS" ]; then
    echo -e "${GREEN}✓${NC} Registered with NANDA Registry"
    echo "   $REG_SUCCESS"
else
    echo -e "${YELLOW}⚠${NC} No recent registry registration found"
fi

echo ""

# Check for recent errors
echo "7. Checking for recent errors..."
ERROR_COUNT=$(journalctl -u nasdaq-agent --since "10 minutes ago" -p err | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓${NC} No errors in last 10 minutes"
else
    echo -e "${YELLOW}⚠${NC} Found $ERROR_COUNT error(s) in last 10 minutes"
    echo "Recent errors:"
    journalctl -u nasdaq-agent --since "10 minutes ago" -p err | tail -5
fi

echo ""

# Test REST API health
echo "8. Testing REST API..."
if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} REST API is responding"
    HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
    echo "   Response: $HEALTH_RESPONSE"
else
    echo -e "${RED}✗${NC} REST API is not responding"
fi

echo ""

# Test A2A endpoint (if NEST is enabled)
echo "9. Testing A2A endpoint..."
A2A_TEST=$(curl -s -X POST http://localhost:6000/a2a \
  -H "Content-Type: application/json" \
  -d '{"role":"user","content":{"type":"text","text":"/ping"},"conversation_id":"monitor-test"}' 2>&1)

if echo "$A2A_TEST" | grep -q "Pong"; then
    echo -e "${GREEN}✓${NC} A2A endpoint is responding"
    echo "   Response: $(echo $A2A_TEST | jq -r '.content.text' 2>/dev/null || echo $A2A_TEST)"
elif echo "$A2A_TEST" | grep -q "Connection refused"; then
    echo -e "${YELLOW}⚠${NC} A2A endpoint not available (NEST may be disabled)"
else
    echo -e "${RED}✗${NC} A2A endpoint error"
    echo "   Error: $A2A_TEST"
fi

echo ""

# Memory usage
echo "10. Checking resource usage..."
MEMORY_USAGE=$(ps aux | grep "[p]ython main.py" | awk '{print $4}')
if [ -n "$MEMORY_USAGE" ]; then
    echo -e "${GREEN}✓${NC} Memory usage: ${MEMORY_USAGE}%"
else
    echo -e "${YELLOW}⚠${NC} Could not determine memory usage"
fi

echo ""
echo "========================================="
echo "Monitoring complete"
echo "========================================="
echo ""
echo "To view live logs:"
echo "  sudo journalctl -u nasdaq-agent -f"
echo ""
echo "To view NEST-specific logs:"
echo "  sudo journalctl -u nasdaq-agent | grep NEST"
echo ""
