"""控制本地矿工不断挖矿
当挖到币并通过一致性检验时：
    1、系统会奖励该矿工一个币
    2、该矿工会打包所有记录的交易上链
当挖到币未通过一致性检验时：
    使用所有矿工手里最长的账本替代自己的账本，重新开始挖矿
"""

# dig.py脚本本身并不进行挖,挖矿过程在miner_server.mine()
# dig.py向miner_server发送'/mine'请求，开始挖矿

import requests
import pickle
import json
import time

from miner_server import Block, Blockchain

my_node = 'http://localhost:5000/'


while True:
    # 开始挖矿，在这里会停留一段时间，直到做完题挖到一个币
    response = requests.get(my_node + 'mine')       # 发送GET请求，控制miner_server挖矿
    blockchain = requests.get(my_node + 'blocks')   # 挖矿完毕，返回区块链数据
    blockchain = pickle.loads(blockchain.content)   # pickle加载数据

    blocks = []
    # 将返回的区块链数据写入到blocks列表中，用于输出显示
    for block in blockchain:
        blocks.append({
            "index": block.index,
            "timestamp": str(block.timestamp),
            "data": block.data,
            "previous_hash": block.previous_hash,
            "hash": block.hash
        })
    blocks_json = json.dumps(blocks, indent=2)
    print("The last block: ", blocks[-1])
    # time.sleep(0.5)
