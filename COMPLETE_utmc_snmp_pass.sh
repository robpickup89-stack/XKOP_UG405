#!/bin/bash
# SNMP pass script for UTMC - COMPLETE

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
    
    if [ "$resp_type" == "string" ]; then
        snmp_type="string"
    else
        snmp_type="integer"
    fi
    
    echo "$REQ_OID"
    echo "$snmp_type"
    echo "$value"
    log "GET $REQ_OID = $value ($snmp_type)"
    ;;
    
  -n)
    # GETNEXT
    echo "NONE"
    log "GETNEXT $REQ_OID = NONE"
    ;;
    
  -s)
    # SET operation
    curl -s -X POST "$APP_URL/snmp/set" \
      -H "Content-Type: application/json" \
      -d "{\"oid\":\"$REQ_OID\",\"type\":\"$TYPE\",\"value\":$VALUE}" > /dev/null
    
    echo "$REQ_OID"
    echo "$TYPE"
    echo "$VALUE"
    log "SET $REQ_OID = $VALUE ($TYPE)"
    ;;
    
  *)
    log "ERROR: Unknown command: $CMD"
    exit 1
    ;;
esac

exit 0
