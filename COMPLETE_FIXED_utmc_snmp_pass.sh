#!/bin/bash
# SNMP pass script - COMPLETE FIX for OctetString in both directions

APP_URL="http://localhost:5000"
LOG_FILE="/tmp/utmc_snmp_pass.log"

log() {
    echo "[$(date '+%H:%M:%S')] $*" >> "$LOG_FILE"
}

CMD="$1"
REQ_OID="$2"
TYPE="$3"
VALUE="$4"

case "$CMD" in
  -g)
    # GET operation
    result=$(curl -s "$APP_URL/snmp/get?oid=$REQ_OID" 2>&1)
    value=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('value',0))")
    resp_type=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('type','integer'))")
    
    log "GET $REQ_OID: Flask returned value=$value type=$resp_type"
    
    if [ "$resp_type" == "string" ]; then
        # Bitmask - return as OctetString (hex format)
        # Convert decimal to hex
        hex_value=$(printf "%02X" "$value" 2>/dev/null || echo "00")
        
        echo "$REQ_OID"
        echo "string"
        echo "$hex_value"
        log "GET response: OctetString 0x$hex_value (decimal $value)"
    else
        # Scalar - return as integer
        echo "$REQ_OID"
        echo "integer"
        echo "$value"
        log "GET response: integer $value"
    fi
    ;;
    
  -n)
    # GETNEXT
    echo "NONE"
    log "GETNEXT $REQ_OID = NONE"
    ;;
    
  -s)
    # SET operation
    log "SET called: OID=$REQ_OID TYPE=$TYPE VALUE=$VALUE"
    
    # Convert OctetString hex to integer if needed
    if [ "$TYPE" == "string" ] || [ "$TYPE" == "octet" ]; then
        # VALUE is hex (e.g., "06" or "0x06")
        # Convert to decimal
        if [[ "$VALUE" =~ ^0x ]]; then
            INT_VALUE=$((VALUE))
        else
            # Hex without prefix
            INT_VALUE=$((16#$VALUE))
        fi
        log "Converted OctetString 0x$VALUE to integer: $INT_VALUE"
    else
        # Already integer
        INT_VALUE="$VALUE"
    fi
    
    # Send to Flask
    curl_result=$(curl -s -X POST "$APP_URL/snmp/set" \
      -H "Content-Type: application/json" \
      -d "{\"oid\":\"$REQ_OID\",\"type\":\"integer\",\"value\":$INT_VALUE}")
    
    log "Flask response: $curl_result"
    
    echo "$REQ_OID"
    echo "$TYPE"
    echo "$VALUE"
    log "SET response: $TYPE $VALUE"
    ;;
    
  *)
    log "ERROR: Unknown command: $CMD"
    exit 1
    ;;
esac

exit 0