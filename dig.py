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
from requests.exceptions import ConnectionError
import pickle
import json
import time

from miner_server import Block, Blockchain

my_node = 'http://localhost:5000/'
MAX_RETRIES = 3
RETRY_DELAY = 5

while True:
    try:
        # 开始挖矿
        print("Attempting to connect to miner server...")
        response = requests.get(my_node + 'mine')       
        blockchain_response = requests.get(my_node + 'blocks')   

        try:
            # 使用pickle加载数据
            blockchain = pickle.loads(blockchain_response.content)
            
            blocks = []
            for block in blockchain:
                # 确保所有值都被正确转换为JSON兼容格式
                block_data = {
                    "index": str(block.index),
                    "timestamp": str(block.timestamp),
                    "data": str(block.data) if block.data else "",
                    "previous_hash": str(block.previous_hash),
                    "hash": str(block.hash)
                }
                blocks.append(block_data)
            
            if blocks:
                print("Current blockchain length:", len(blocks))
                print("The last block: ", json.dumps(blocks[-1], ensure_ascii=False))
            else:
                print("No blocks in the chain yet")
                
        except pickle.UnpicklingError as e:
            print(f"Error unpickling data: {e}")
        except AttributeError as e:
            print(f"Error accessing block attributes: {e}")
        except json.JSONDecodeError as e:
            print(f"JSON encoding error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            print(f"Response content: {blockchain_response.content[:100]}")  # 打印前100个字符用于调试
        
        time.sleep(1)  # 添加短暂延迟避免过于频繁的请求
        
    except ConnectionError as e:
        print(f"Connection failed: Miner server not running at {my_node}")
        print(f"Please ensure miner_server.py is running")
        print(f"Retrying in {RETRY_DELAY} seconds...")
        time.sleep(RETRY_DELAY)
        continue
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    time.sleep(1)
