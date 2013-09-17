TENANT_ID=4d0046aff188439d8aeb5cdf3033492d
API_PORT=${API_PORT-7653}


# Cloud A:
#IMAGE="8848d4cd-1bdf-4627-ae31-ce9bf61440a4"
#KEY_NAME='af-keypair' or 'af2'

# Cloud B:
#IMAGE="2fe7633c-85bd-42b8-a857-80d5efa78d9f"
#KEY_NAME='af'

curl -k -X 'POST' \
     -H 'Content-type: application/json' \
     -v http://localhost:${API_PORT}/${TENANT_ID}/att-inception-clouds \
     -d '
{
	"prefix": "af4",
	"num_workers":2,
	"flavor":2,
	"gateway_flavor":1,
	"image":"8848d4cd-1bdf-4627-ae31-ce9bf61440a4",
	"user":"ubuntu",
	"pool":"research",
	"key_name":"af2",
	"security_groups":["default"],
	"chef_repo": "git://github.com/att/inception-chef-repo.git",
        "chef_repo_branch": "master",
       	"chefserver_image": "8848d4cd-1bdf-4627-ae31-ce9bf61440a4",
        "dst_dir":"/home/ubuntu/",
       	"userdata":""
}'
