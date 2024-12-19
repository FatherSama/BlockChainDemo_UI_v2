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
def proof_of_work(last_proof):
    """
    简单的工作量证明算法：
     - 找到一个数字 p'��得哈希值 hash(pp') 包含前四个零，其中 p 是上一个 p'
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
# 设置超���时间
timeout = 3

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
    # 只有主节点才能挖矿
    if not pbft.is_primary():
        return jsonify(["Not the primary node"])
    
    # 原有的挖矿逻辑保持不变
    last_block = bc.blockchain[len(bc.blockchain) - 1]
    last_proof = last_block.data['proof-of-work']
    proof = proof_of_work(last_proof)
    
    this_node_transactions.append(
        {"from": "Network", "to": miner_name, "amount": 1}
    )
    
    new_block_data = {
        "proof-of-work": proof,
        "transactions": list(this_node_transactions)
    }
    new_block_index = last_block.index + 1
    new_block_timestamp = date.datetime.now()
    last_block_hash = last_block.hash
    this_node_transactions[:] = []
    
    mined_block = Block(
        new_block_index,
        new_block_timestamp,
        new_block_data,
        last_block_hash
    )
    
    # 使用PBFT共识
    if pbft.broadcast_prepare(mined_block):
        # 如果准备阶段成功，进入提交阶段
        if pbft.broadcast_commit(mined_block):
            # 共识成功，将区块添加到链上
            bc.blockchain.append(mined_block)
            return jsonify(["Block added successfully"])
    
    return jsonify(["Consensus failed"])

# 在Block类后添加区块验证函数
def valid_block(block):
    """
    验证区块的有效性
    1. 检查区块的索引是否连续
    2. 检查区块的previous_hash是否正确
    3. 验证工作量证明
    """
    # 如果是创世块，直接返回True
    if block.index == 0:
        return True
        
    # 获取前一个区块
    previous_block = bc.blockchain[-1]
    
    # 验证区块索引是否连续
    if block.index != previous_block.index + 1:
        print(f"Invalid block index: {block.index}")
        return False
        
    # 验证前一个区块的哈希值
    if block.previous_hash != previous_block.hash:
        print(f"Invalid previous hash: {block.previous_hash}")
        return False
        
    # 验证工作量证明
    last_proof = previous_block.data['proof-of-work']
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
                bc.blockchain.append(block)
            return "OK"
        else:
            return "Invalid block", 400
    except Exception as e:
        print(f"Error in handle_commit: {str(e)}")
        return "Error processing commit message", 500

# 在现有的路由之前添加新的路由
@node.route('/parse_transaction', methods=['POST'])
def parse_transaction():
    """解析自然语言并转换为交易"""
    try:
        # 获取用户输入的文本
        text = request.get_json()['text']
        
        # 调用大语言模型解析文本
        # 这里使用一个简单的示例解析逻辑，你需要替换为实际的大语言模型API调用
        transaction = parse_text_to_transaction(text)
        
        if transaction:
            # 将解析后的交易发送到/txion端点
            response = requests.post(
                f"{my_node}txion",
                json=transaction,
                timeout=timeout
            )
            
            if response.status_code == 200:
                return jsonify({
                    "success": True,
                    "message": "Transaction processed successfully",
                    "transaction": transaction
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "Failed to process transaction"
                }), 400
        else:
            return jsonify({
                "success": False,
                "message": "Could not parse transaction from text"
            }), 400
            
    except Exception as e:
        print(f"Error processing natural language transaction: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

def parse_text_to_transaction(text):
    """
    使用大语言模型解析文本为交易信息
    示例文本：
    - "Alice 向 Bob 转账 5 个币"
    - "从 Charlie 转 10 个币给 Dave"
    """
    try:
        # 这里替换为实际的大语言模型API调用
        # 示例：使用OpenAI的API
        import openai
        
        # 设置你的API密钥
        openai.api_key = 'your-api-key'
        
        # 构造提示词
        prompt = f"""
        请将以下文本解析为交易信息，返回JSON格式：
        {text}
        
        格式要求：
        {{
            "from": "发送方名称",
            "to": "接收方名称",
            "amount": 数字金额
        }}
        """
        
        # 调用API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一个交易解析助手，负责将自然语言转换为结构化的交易信息。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        # 解析返回的JSON
        import json
        transaction = json.loads(response.choices[0].message.content)
        
        # 验证必要字段
        if all(k in transaction for k in ['from', 'to', 'amount']):
            # 确保amount是数字
            transaction['amount'] = float(transaction['amount'])
            return transaction
            
        return None
        
    except Exception as e:
        print(f"Error parsing text: {str(e)}")
        return None

# 运行应用
if __name__ == "__main__":
    # node.run('127.0.0.1', 5000)
    node.run('0.0.0.0', 5000, debug=True)
