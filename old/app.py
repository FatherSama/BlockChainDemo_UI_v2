# v3文件夹中的app.py
# 控制界面服务端程序，用于控制miner_server.py, dig.py等脚本运行与停止；将脚本输出内容实时显示到html页面。


from flask import Flask, jsonify, render_template, send_from_directory, Response, request
import os
import sys
import requests
import pickle
import hashlib as hasher
import json
import subprocess
from miner_server import  Block, Blockchain


my_node = 'http://localhost:5000/'

app = Flask(__name__)

# 全局变量，用于存储子进程和它们的输出
miner_server_process = None
dig_process = None
miner_server_output = ""
dig_output = ""
my_py_path = os.getcwd() + '\\.venv\\Scripts\\python.exe'

# 配置节点信息
# node1 = 'http://192.168.2.42:5000/'       # 矿工1，thinkbook笔记本
node1 = 'http://127.0.0.1:5000/'            # 矿工1，thinkbook笔记本
node2 = 'http://192.168.2.229:5000/'        # 矿工2，双清服务器
all_nodes = {node1, node2}


# ======================================================================================================================
# # 函数，用于启动miner_server.py脚本
# def start_miner_server():
#     global miner_server_process
#     env = os.environ.copy()
#     env['PYTHONPATH'] = os.path.dirname(os.path.abspath(my_py_path))
#     python_executable = sys.executable
#     miner_server_process = subprocess.Popen([python_executable, 'miner_server.py'], env=env, stdout=subprocess.PIPE,
#                                             stderr=subprocess.STDOUT, text=True)
#
#
# # 函数，用于停止miner_server.py脚本
# def stop_miner_server():
#     global miner_server_process
#     if miner_server_process:
#         miner_server_process.terminate()
#         miner_server_process = None
#
#
# # 函数，用于启动dig.py脚本
# def start_dig():
#     global dig_process
#     env = os.environ.copy()
#     env['PYTHONPATH'] = os.path.dirname(os.path.abspath(my_py_path))
#     python_executable = sys.executable
#     dig_process = subprocess.Popen([python_executable, 'dig.py'], env=env, stdout=subprocess.PIPE,
#                                    stderr=subprocess.STDOUT, text=True)
#
#
# # 函数，用于停止dig.py脚本
# def stop_dig():
#     global dig_process
#     if dig_process:
#         dig_process.terminate()
#         dig_process = None


# ==================================================================================================

subprocess_miner = None


# 路由，用于处理Start MinerServer按钮的请求
@app.route('/start', methods=['GET'])
def start_sub_app():
    global subprocess_miner
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.dirname(os.path.abspath(my_py_path))        # 指定脚本运行使用的python环境
    python_executable = sys.executable

    if sub_app_process and sub_app_process.poll() is None:
        return jsonify({"status": "error", "message": "Sub Flask app is already running."})
    try:
        # 启动Flask子项目
        sub_app_process = subprocess.Popen(
            [python_executable, 'miner_server.py'], env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True  # 输出日志为字符串
        )
        stdout, stderr = sub_app_process.communicate(timeout=5)
        print(f"Subprocess STDOUT: {stdout}")
        print(f"Subprocess STDERR: {stderr}")
        return jsonify({"status": "success", "message": "Sub Flask app started.", "pid": sub_app_process.pid})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# 路由，用于处理Stop 按钮的请求
@app.route('/stop', methods=['GET'])
def stop_sub_app():
    global subprocess_miner
    if not sub_app_process or sub_app_process.poll() is not None:
        return jsonify({"status": "error", "message": "Sub Flask app is not running."})

    try:
        sub_app_process.terminate()     # 停止子 Flask 项目
        sub_app_process.wait()          # 确保进程完全终止
        return jsonify({"status": "success", "message": "Sub Flask app stopped."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# 路由，用于处理Start Dig按钮的请求
@app.route('/start_dig', methods=['GET'])
def start_dig():
    response = requests.get(my_node + 'mine')  # 发送GET请求
    if response.status_code == 200:
        miner_data = response.json()
    else:
        miner_data = "Error"

    blockchain = requests.get(my_node + 'blocks')
    blockchain = pickle.loads(blockchain.content)

    blocks = []
    for block in blockchain:
        blocks.append({
            "index": block.index,
            "timestamp": str(block.timestamp),
            "data": block.data,
            "previous_hash": block.previous_hash,
            "hash": block.hash
        })
    # blocks_json = json.dumps(blocks, indent=2)
    # print("The last block xxxxxxxxxx: ", blocks[-1])
    dig_str = "The last block:{}".format(blocks[-1])
    res_dict = {
        "miner_data": miner_data,
        'dig_str': dig_str
    }

    return jsonify(res_dict)

# # 路由，用于处理Start Dig按钮的请求
# @app.route('/start_dig', methods=['GET'])
# def start_dig():
#     response = requests.get(my_node + 'mine')  # 发送GET请求
#     if response.status_code == 200:
#         miner_data = response.json()
#     else:
#         miner_data = "Error"
#
#     blockchain = requests.get(my_node + 'blocks')
#     blockchain = pickle.loads(blockchain.content)
#
#     blocks = []
#     for block in blockchain:
#         blocks.append({
#             "index": block.index,
#             "timestamp": str(block.timestamp),
#             "data": block.data,
#             "previous_hash": block.previous_hash,
#             "hash": block.hash
#         })
#     blocks_json = json.dumps(blocks, indent=2)
#     # print("Current Book: ", blocks_json)
#     print("The last block of the book: ", blocks[-1])
#     dig_str = "The last block of the book:{}".format(blocks[-1])
#     res_dict = {
#         "miner_data": miner_data,
#         'dig_str': dig_str
#     }
#
#     return jsonify(res_dict)


# 路由，用于处理“提交交易信息”按钮的请求
@app.route('/process', methods=['POST'])
def process_transaction():
    from_user = request.form.get('from')
    to_user = request.form.get('to')
    amount = request.form.get('amount')

    # 构建交易数据的JSON对象
    transaction_data = {
        'from': from_user,
        'to': to_user,
        'amount': amount
    }

    # 使用requests发送POST请求到/txion端点
    response = requests.post('http://localhost:5000/txion', json=transaction_data)

    # 检查请求是否成功
    if response.status_code == 200:
        return jsonify({
            "status": "success",
            "message": f"Transaction processed: {from_user} sent {amount} to {to_user}"
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to submit transaction"
        })


# 路由，用于处理查询按钮的请求
@app.route('/inquiry')
def inquiry():
    node_url = node1
    blockchain = requests.get(my_node + 'blocks', timeout=3)        # 获取区块链信息
    blockchain = pickle.loads(blockchain.content)
    blocks = []
    for block in blockchain:
        blocks.append({
            "index": block.index,
            "timestamp": str(block.timestamp),
            "data": block.data,
            "previous_hash": block.previous_hash,
            "hash": block.hash
        })
    blocks_json = json.dumps(blocks, indent=2)
    print('节点{}返回账本结果如下: '.format(node_url))
    print(blocks_json)
    return jsonify(blocks)


@app.route('/')
def index():
    return render_template('index2.html')


# ==================================================================================================
# 运行应用
if __name__ == "__main__":
    app.run('0.0.0.0', 5008)    # 在本机5008端口运行ui界面
