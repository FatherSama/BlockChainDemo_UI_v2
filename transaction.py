"""记录一笔交易
通过更改交易信息，向所有节点发送记录交易请求
"""

import requests

# 设置超时时间
timeout = 3
# 配置节点信息
node1 = 'http://127.0.0.1:5000/'    # 矿工1
# node1 = 'http://192.168.2.42:5000/'    # 矿工1，thinkbook笔记本
node2 = 'http://192.168.2.229:5000/'    # 矿工2，双清服务器
all_nodes = {node1, node2}

# 要发布的交易信息
data = {
    'from': 'aaaaaaaa',
    'to': 'bbbbbbbb',
    'amount': 66666666
    }

# 把一笔交易同时发给所有节点（矿工）来记录, POST请求
for node_url in all_nodes:
    try:
        response = requests.post(node_url+'txion', json=data, timeout=timeout)
        print('节点{}返回交易结果如下: '.format(node_url))
        print(response.status_code)
        print(response.text)
    except requests.exceptions.RequestException as e:
        print("节点{}连接失败, 该节点不记录交易: ".format(node_url))
        # print(e)
