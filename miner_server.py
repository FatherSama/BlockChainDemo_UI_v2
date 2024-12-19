"""矿工服务端代码
1、交易记录功能
2、提供挖矿功能
3、提供账本查询功能
"""
import sys

print(f"Python interpreter: {sys.executable}")

from flask import Flask, jsonify
from flask import request
import json
import requests
import hashlib as hasher
import datetime as date
import pickle
import time
import hashlib


# ==================================================================================================
# 定义区块结构
class Block:
    # 初始化函数
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index  # 索引
        self.timestamp = timestamp  # 时间戳
        self.data = data  # 区块数据
        self.previous_hash = previous_hash  # 前一区块哈希值
        self.hash = self.hash_block()  # 自身哈希值

    # SHA-256哈希算法
    def hash_block(self):
        sha = hasher.sha256()
        sha.update(str(self.index).encode('utf-8')
                   + str(self.timestamp).encode('utf-8')
                   + str(self.data).encode('utf-8')
                   + str(self.previous_hash).encode('utf-8'))
        return sha.hexdigest()


class Blockchain:
    def __init__(self):
        self.blockchain = []  # 用列表记录区块链


# 生成创世块
def create_genesis_block():
    # 构建一个 index=0、previous_hash=0 的区块
    return Block(0,
                 date.datetime.now(),
                 {
                     "proof-of-work": 9,
                     "transactions": None
                 },
                 "0")


# 获取其他节点的数据
def find_new_chains():
    # 用 GET 请求获取每个节点的区块链
    other_chains = []
    for node_url in peer_nodes:
        # 使用try避免一个节点（矿工）没开机，网络请求失败把自己搞崩
        try:
            block = requests.get(node_url + "/blocks", timeout=timeout)
            # 将 JSON 格式转成 Python 字典
            block = pickle.loads(block.content)
            # 将获取的区块链添加到列表
            other_chains.append(block)
            print('----------Got the other miners books---------')
        except:
            print('----------No other miners were found-----------')
            pass
    return other_chains


# 挖矿算法：工作量证明
# 要求返回值能够被9和上一次last_proof整除
# 简单的工作量证明算法
def proof_of_work(last_proof):
    """
    Simple Proof of Work Algorithm:
     - Find a number p' such that hash(pp') contains leading 1 zeroe, where p is the previous p'
     - p is the previous proof, and p' is the new proof
    :param last_proof: <int>
    :return: <int>
    """
    incrementor = 0  # 新的证明 p'
    while True:
        # 计算哈希值
        guess = f'{last_proof}{incrementor}'.encode()  # 将 last_proof 和 incrementor 组合
        guess_hash = hashlib.sha256(guess).hexdigest()  # 计算 SHA-256 哈希值
        
        # 检查哈希值是否以 4 个零开头
        if guess_hash[0] == "0":
            return incrementor  # 找到符合条件的证明，返回 incrementor
        incrementor += 1  # 增加 incrementor，继续寻找



# ==================================================================================================


# 本机ip
ip_local = '127.0.0.1'
# ip_local = '192.168.2.42'
my_node = 'http://' + ip_local + ':5000/'
# 本机名称
miner_name = "Miner_jy_ThinkBook"

# 所有矿工的ip
node1 = my_node
ip_node2 = '192.168.2.229'
node2 = 'http://' + ip_node2 + ':5000/'
all_nodes = {node1, node2}
# 集合差集，即其他节点
peer_nodes = all_nodes.difference({my_node})
# 设置超时时间
timeout = 3

# 创建一个区块链
bc = Blockchain()
bc.blockchain.append(create_genesis_block())
# 创建本节点待处理交易列表
this_node_transactions = []

node = Flask(__name__)


# ==================================================================================================
# 处理 POST 请求，接收交易信息
@node.route('/txion', methods=['POST'])
def transaction():
    # 提取交易数据
    new_txion = request.get_json()
    # 添加交易到待处理列表 this_node_transactions 中
    this_node_transactions.append(new_txion)
    # 显示提交的交易
    print("New transaction")
    print("FROM: {}".format(new_txion['from'].encode('ascii', 'replace')))
    print("TO: {}".format(new_txion['to'].encode('ascii', 'replace')))
    print("AMOUNT: {}\n".format(new_txion['amount']))
    # 回应客户端交易已提交
    return "Transaction submission successful! \n"


# 处理 GET 请求，返回区块链的信息
@node.route('/blocks', methods=['GET'])
def get_blocks():
    # 处理成 JSON 格式
    blocks = []
    for block in bc.blockchain:
        blocks.append({
            "index": block.index,
            "timestamp": str(block.timestamp),
            "data": block.data,
            "previous_hash": block.previous_hash,
            "hash": block.hash
        })
    chain_to_send = json.dumps(blocks, indent=2)
    chain_to_send_object = pickle.dumps(bc.blockchain)
    return chain_to_send_object


# 处理 GET 请求 /mine，用于挖矿
@node.route('/mine', methods=['GET'])
def mine():
    # 获取上一个块的 proof of work
    last_block = bc.blockchain[len(bc.blockchain) - 1]
    last_proof = last_block.data['proof-of-work']
    # 使用PoW算法挖矿
    proof = proof_of_work(last_proof)

    # 当找到一个有效的 proof of work，通过添加交易来奖励挖矿者
    this_node_transactions.append(
        {"from": "Network", "to": miner_name, "amount": 1}
    )
    # 收集所需数据来创建新的块
    new_block_data = {
        "proof-of-work": proof,
        "transactions": list(this_node_transactions)
    }
    new_block_index = last_block.index + 1
    new_block_timestamp = this_timestamp = date.datetime.now()
    last_block_hash = last_block.hash
    # 清空待处理交易列表
    this_node_transactions[:] = []
    # 创建新块
    mined_block = Block(
        new_block_index,
        new_block_timestamp,
        new_block_data,
        last_block_hash
    )
    res_list = []
    res_list.append("----------- I Got One Coin ------------")

    print("----------- I Got One Coin ------------")  # 这里应该先跟别人长度对比，再决定是否把自己的加进去
    # 共识算法
    # 获取其他节点的区块链
    other_chains = find_new_chains()
    # 如果自己的区块链不是最长的，则设为最长的区块链
    longest_chain = bc.blockchain
    res_list.append("Length of my own book：{}".format(len(bc.blockchain)))
    print("Length of my own book", len(bc.blockchain))
    for chain in other_chains:
        res_list.append("Length of others book", len(chain))
        print("Length of others book", len(chain))
        if len(longest_chain) < len(chain):
            res_list.append('---------My BookLen < Others----------')
            print('---------My BookLen < Others----------')
            longest_chain = chain
    # 如果自己是最长的区块或者和别人等长，那么把新挖到的区块添加进去
    if len(bc.blockchain) == len(longest_chain):
        bc.blockchain.append(mined_block)
    # 如果最长的区块链不是自己的，则停止挖矿并将自己的区块链设为其他矿工中最长的
    else:
        bc.blockchain = longest_chain
    res_list.append("My BookLen after Consensus:{}".format(len(bc.blockchain)))
    print("My BookLen after Consensus: ", len(bc.blockchain))
    return jsonify(res_list)





# 运行应用
if __name__ == "__main__":
    # node.run('127.0.0.1', 5000)
    node.run('0.0.0.0', 5000, debug=True)
