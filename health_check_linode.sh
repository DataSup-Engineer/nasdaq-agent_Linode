#!/bin/bash

###############################################################################
# NASDAQ Stock Agent - Health Check Script (Linode)
#
# This script queries the /health endpoint and validates the response.
# Exit codes:
#   0 - Service is healthy
#   1 - Service is unhealthy or unreachable
#
# Usage:
#   ./health_check_linode.sh
###############################################################################

# Configuration
HEALTH_URL="http://localhost:8000/health"
TIMEOUT=5
MAX_RETRIES=3
RETRY_DELAY=2

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if curl is installed
if ! command -v curl &> /dev/null; then
    echo -e "${RED}ERROR: curl is not installed${NC}"
    exit 1
fi

# Function to query health endpoint
check_health() {
    local attempt=$1
    
    # Query the health endpoint with timeout
    HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT "$HEALTH_URL" 2>/dev/null)
    
    # Extract HTTP status code (last line)
    HTTP_CODE=$(echo "$HTTP_RESPONSE" | tail -n1)
    
    # Extract response body (all but last line)
    RESPONSE_BODY=$(echo "$HTTP_RESPONSE" | sed '$d')
    
    # Check if we got a response
    if [ -z "$HTTP_CODE" ]; then
        echo -e "${RED}✗ Failed to connect to service (attempt $attempt/$MAX_RETRIES)${NC}"
        return 1
    fi
    
    # Check HTTP status code
    if [ "$HTTP_CODE" -eq 200 ]; then
        echo -e "${GREEN}✓ Service is healthy${NC}"
        echo "  HTTP Status: $HTTP_CODE"
        echo "  Response: $RESPONSE_BODY"
        return 0
    else
        echo -e "${RED}✗ Service returned non-200 status (attempt $attempt/$MAX_RETRIES)${NC}"
        echo "  HTTP Status: $HTTP_CODE"
        echo "  Response: $RESPONSE_BODY"
        return 1
    fi
}

# Main execution with retry logic
echo "========================================="
echo "NASDAQ Stock Agent Health Check (Linode)"
echo "========================================="
echo "Endpoint: $HEALTH_URL"
echo ""

for i in $(seq 1 $MAX_RETRIES); do
    if check_health $i; then
        echo ""
        echo "Linode deployment is healthy!"
        exit 0
    fi
    
    # Wait before retry (except on last attempt)
    if [ $i -lt $MAX_RETRIES ]; then
        echo -e "${YELLOW}Retrying in ${RETRY_DELAY} seconds...${NC}"
        sleep $RETRY_DELAY
    fi
done

echo ""
echo -e "${RED}Health check failed after $MAX_RETRIES attempts${NC}"
echo ""
echo "Troubleshooting steps:"
echo "1. Check if service is running: sudo systemctl status nasdaq-agent"
echo "2. View logs: sudo journalctl -u nasdaq-agent -n 50"
echo "3. Verify firewall: sudo ufw status"
echo "4. Check port: sudo netstat -tuln | grep 8000"
exit 1
