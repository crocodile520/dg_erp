# gateway_inverter

充电桩 gateway_inverter模块


启动docker后，需要进去手动安装依赖:

docker exec -it charge_odoo /bin/bash 

pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

pip install -r ./mnt/extra-addons/gateway_inverter/requirements.txt



## 启动调试模式


find . -type f  -exec sed -i 's/api\//apiv2\//g' {} +


查odoo的日志：
docker logs -f --tail=1000 gateway_inverter


docker exec -it gateway_inverter_db /bin/bash
psql -U odoo -d gateway_inverter




修改docker-compose.yml时，想要生效，那么先需要stop，再 up -d
docker-compose stop 
docker-compose up -d  

或者一步到位也行： docker-compose up -d  






