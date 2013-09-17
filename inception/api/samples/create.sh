#!/bin/bash

TENANT_ID=4d0046aff188439d8aeb5cdf3033492d
API_PORT=${API_PORT-7653}


# Cloud A:
#IMAGE="u1204-130531-gv"
#KEY_NAME='af-keypair' or 'af2'

# Cloud B:
#IMAGE="?"
#KEY_NAME='af'

curl -k -X 'POST' \
     -H 'Content-type: application/json' \
     -v http://localhost:${API_PORT}/${TENANT_ID}/att-inception-clouds \
     -d '
{
        "OS_AUTH_URL":"'$OS_AUTH_URL'",
        "OS_PASSWORD":"'$OS_PASSWORD'",
        "OS_TENANT_ID":"'$OS_TENANT_ID'",
        "OS_TENANT_NAME":"'$OS_TENANT_NAME'",
        "OS_USERNAME":"'$OS_USERNAME'",
        "prefix": "af4",
        "num_workers":2,
        "flavor":"m1.medium",
        "gateway_flavor":"m1.small",
        "image":"u1204-130531-gv",
        "user":"ubuntu",
        "pool":"research",
        "key_name":"af-iad1-incept-kp",
        "security_groups":["default"],
        "chef_repo": "git://github.com/att/inception-chef-repo.git",
        "chef_repo_branch": "master",
        "chefserver_image": "u1204-130531-gv",
        "dst_dir":"/home/ubuntu/",
        "userdata":""
}'
