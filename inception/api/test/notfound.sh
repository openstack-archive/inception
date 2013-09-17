TENANT_ID=4d0046aff188439d8aeb5cdf3033492d
API_PORT=${API_PORT-7653}

curl -k -X 'GET' \
     -H 'Content-type: application/json' \
     -v http://localhost:${API_PORT}/${TENANT_ID}/att-inception-clouds/0ec5e84d4fe54bbd93d149bdb27695e6 \
     -d '{}'
