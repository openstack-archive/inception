#!/bin/bash

TENANT_ID=4d0046aff188439d8aeb5cdf3033492d
API_PORT=${API_PORT-7653}

curl -k -X 'GET' \
     -H 'Content-type: application/json' \
     -v http://localhost:${API_PORT}/${TENANT_ID}/att-inception-clouds
