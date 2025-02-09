#!/bin/bash
#author: Tuna<2351055032@qq.com>
#desc: "description"

cd /home/ubuntu/docker/tuna_erp/addons/tuna-erp
git fetch
git pull
docker restart tuna_erp