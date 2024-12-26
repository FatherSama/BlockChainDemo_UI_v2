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
from consensus import PBFTConsensus
from db_handler import BlockchainDB

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
        self.db = BlockchainDB()
        # 检查是否需要创建创世块
        if not self.db.get_last_block():
            genesis_block = create_genesis_block()
            self.db.insert_block(genesis_block)
    
    @property
    def blockchain(self):
        """获取完整的区块链"""
        return self.db.get_all_blocks()
    
    def append(self, block):
        """添加新区块"""
        return self.db.insert_block(block)
    
    def __getitem__(self, index):
        """支持使用索引访问区块"""
        blocks = self.blockchain
        if 0 <= index < len(blocks):
            return blocks[index]
        raise IndexError("Block index out of range")
    
    def __len__(self):
        """获取区块链长度"""
        return len(self.blockchain)


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
    """获取其他节点的区块链数据"""
    other_chains = []
    for node_url in peer_nodes:
        try:
            block = requests.get(
                node_url + "/blocks", 
                timeout=timeout  # 使用全局timeout变量
            )
            block = pickle.loads(block.content)
            other_chains.append(block)
            print('----------Got the other miners books---------')
        except requests.exceptions.Timeout:
            print(f'----------Request to {node_url} timed out after {timeout} seconds-----------')
        except Exception as e:
            print(f'----------Error connecting to {node_url}: {str(e)}-----------')
    return other_chains


# 挖矿算法：工作量证明
def proof_of_work(last_proof):
    """
    简单的工作量证明算法：
     - 找到一个数字 p'得哈希值 hash(pp') 包含前四个零，其中 p 是上一个 p'
     - p 是上一个证明，p' 是新的证明
    :param last_proof: <int>
    :return: <int>
    """
    incrementor = 0  # 初始化新的证明
    # 不断寻找满足条件的新的证明
    while not valid_proof(last_proof, incrementor):
        incrementor += 1
    return incrementor

def valid_proof(last_proof, incrementor):
    """
    验证工作量证明是否有效
    :param last_proof: <int> 上一个证明
    :param incrementor: <int> 当前尝试的证明
    :return: <bool> 是否有效
    """
    # 将上一个证明和当前证明拼接
    guess = f'{last_proof}{incrementor}'.encode()  # 编码为字节
    guess_hash = hashlib.sha256(guess).hexdigest()  # 计算哈希值
    # 检查哈希值是否以四个零开头
    return guess_hash[:2] == "00"


# ==================================================================================================


# 本机ip
ip_local = '127.0.0.1'
# ip_local = '192.168.2.42'
my_node = 'http://' + ip_local + ':5000/'
# 本机名称
miner_name = "Alice"

# 所有矿工的ip
node1 = my_node
ip_node2 = '192.168.2.229'
node2 = 'http://' + ip_node2 + ':5000/'
all_nodes = {node1,node2}
# 集合差集，即其他节点
peer_nodes = all_nodes.difference({my_node})
# 设置超时间
timeout = 30  # 将超时时间从3秒改为30秒

# 创建一个区块链
bc = Blockchain()
bc.blockchain.append(create_genesis_block())
# 创建本节点待处理交易列表
this_node_transactions = []

node = Flask(__name__)

# 在Flask应用初始化后添加PBFT共识实例
pbft = PBFTConsensus(all_nodes, my_node)

# ==================================================================================================
# 处理 POST 请求，接收交易信息
@node.route('/txion', methods=['POST'])
def transaction():
    try:
        # 提取交易数据
        new_txion = request.get_json()
        
        # 验证交易数据格式
        if not all(k in new_txion for k in ['from', 'to', 'amount']):
            return "Invalid transaction data", 400
            
        # 确保amount是数值类型
        try:
            new_txion['amount'] = float(new_txion['amount'])
        except (ValueError, TypeError):
            return "Invalid amount value", 400
            
        # 添加交易到待处理列表
        this_node_transactions.append(new_txion)
        
        # 显示提交的交易
        print("New transaction")
        print("FROM: {}".format(new_txion['from']))
        print("TO: {}".format(new_txion['to']))
        print("AMOUNT: {}\n".format(new_txion['amount']))
        
        return jsonify({
            "message": "Transaction submission successful",
            "transaction": new_txion
        })
        
    except Exception as e:
        print(f"Error processing transaction: {e}")
        return str(e), 500


# 处理 GET 请求，返回区块链的信息
@node.route('/blocks', methods=['GET'])
def get_blocks():
    try:
        # 从数据库获取所有区块
        blocks = bc.blockchain  # 这里会调用Blockchain类的blockchain属性方法
        if not blocks:
            return pickle.dumps([])
            
        # blocks已经是正确格式，直接返回
        return pickle.dumps(blocks)
    except Exception as e:
        print(f"Error getting blocks: {e}")
        return pickle.dumps([])


# 处理 GET 请求 /mine，用于挖矿
@node.route('/mine', methods=['GET'])
def mine():
    try:
        if not pbft.is_primary():
            return jsonify({"status": "error", "message": "Not the primary node"})
        
        # 获取最后一个区块
        last_block = bc.blockchain[-1]
        if not last_block:
            return jsonify({"status": "error", "message": "No blocks in chain"})
            
        last_proof = last_block['data']['proof-of-work']
        
        # 设置更长的超时时间
        proof = proof_of_work(last_proof)
        
        # 准备区块数据
        block_transactions = list(this_node_transactions)  # 创建交易列表的副本
        
        # 添加挖矿奖励交易
        block_transactions.append({
            "from": "Network",
            "to": miner_name,
            "amount": 1.0
        })
        
        new_block_data = {
            "proof-of-work": proof,
            "transactions": block_transactions
        }
        
        new_block_index = last_block['block_index'] + 1
        new_block_timestamp = date.datetime.now()
        last_block_hash = last_block['hash']
        
        # 清空待处理交易列表
        this_node_transactions.clear()
        
        mined_block = Block(
            new_block_index,
            new_block_timestamp,
            new_block_data,
            last_block_hash
        )
        
        # 添加超时处理
        try:
            if pbft.broadcast_prepare(mined_block):
                if pbft.broadcast_commit(mined_block):
                    bc.append(mined_block)
                    return jsonify({
                        "status": "success",
                        "message": "Block added successfully",
                        "block": {
                            "index": mined_block.index,
                            "timestamp": mined_block.timestamp.isoformat(),
                            "transactions": mined_block.data["transactions"]
                        }
                    })
            return jsonify({"status": "error", "message": "Consensus failed"})
        except requests.exceptions.Timeout:
            return jsonify({
                "status": "error",
                "message": f"Mining operation timed out after {timeout} seconds. Please try again."
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Mining error: {str(e)}"
            })
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        })

# 在Block类后添加区块验证函数
def valid_block(block):
    if block.index == 0:
        return True
        
    previous_block = bc.blockchain[-1]
    
    if block.index != previous_block['block_index'] + 1:
        print(f"Invalid block index: {block.index}")
        return False
        
    if block.previous_hash != previous_block['hash']:
        print(f"Invalid previous hash: {block.previous_hash}")
        return False
        
    last_proof = previous_block['data']['proof-of-work']
    current_proof = block.data['proof-of-work']
    if not valid_proof(last_proof, current_proof):
        print(f"Invalid proof of work: {current_proof}")
        return False
        
    return True

# 修改handle_prepare函数中的验证逻辑
@node.route('/prepare', methods=['POST'])
def handle_prepare():
    try:
        data = pickle.loads(request.get_data())
        block = data['block']
        node_from = data['from']
        
        # 验证区块
        if valid_block(block):
            # 添加准备投票
            if pbft.add_prepare_vote(block.hash, node_from):
                # 如果收到足够的准备投票，进入提交阶段
                pbft.broadcast_commit(block)
            return "OK"
        else:
            return "Invalid block", 400
    except Exception as e:
        print(f"Error in handle_prepare: {str(e)}")
        return "Error processing prepare message", 500

# 修改handle_commit函数，添加验证
@node.route('/commit', methods=['POST'])
def handle_commit():
    try:
        data = pickle.loads(request.get_data())
        block = data['block']
        node_from = data['from']
        
        # 再次验证区块（以防万一）
        if valid_block(block):
            # 添加提交投票
            if pbft.add_commit_vote(block.hash, node_from):
                # 如果收到足够的提交投票，将区块添加到链上
                bc.append(block)
            return "OK"
        else:
            return "Invalid block", 400
    except Exception as e:
        print(f"Error in handle_commit: {str(e)}")
        return "Error processing commit message", 500

# 运行应用
if __name__ == "__main__":
    # node.run('127.0.0.1', 5000)
    node.run('0.0.0.0', 5000, debug=True)
