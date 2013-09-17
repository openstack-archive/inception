#!/bin/bash

TENANT_ID=4d0046aff188439d8aeb5cdf3033492d
CLOUD=${1-0ec5e84d4fe54bbd93d149bdb27695e5}
API_PORT=${API_PORT-7653}


curl -k -X 'DELETE' \
     -H 'Content-type: application/json' \
     -v http://localhost:${API_PORT}/${TENANT_ID}/att-inception-clouds/${CLOUD} \
     -d '{
    "OS_AUTH_URL":"'$OS_AUTH_URL'",
    "OS_PASSWORD":"'$OS_PASSWORD'",
    "OS_TENANT_ID":"'$OS_TENANT_ID'",
    "OS_TENANT_NAME":"'$OS_TENANT_NAME'",
    "OS_USERNAME":"'$OS_USERNAME'"
}'
