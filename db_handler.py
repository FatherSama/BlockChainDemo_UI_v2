import mysql.connector
from mysql.connector import Error
from config import MYSQL_CONFIG
import json
import datetime
import time
from typing import List, Dict, Optional
from decimal import Decimal

class BlockchainDB:
    def __init__(self, max_retries=3):
        self.max_retries = max_retries
        self.connect_to_database()
    
    def connect_to_database(self):
        """建立数据库连接，包含重试机制"""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                self.conn = mysql.connector.connect(**MYSQL_CONFIG)
                self.cursor = self.conn.cursor(dictionary=True)
                print("Successfully connected to MySQL database")
                self.create_tables()
                break
            except Error as err:
                retry_count += 1
                print(f"Connection attempt {retry_count} failed: {err}")
                if retry_count < self.max_retries:
                    print(f"Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    raise Exception("Failed to connect to database after maximum retries")

    def reconnect_if_needed(self):
        """检查连接是否断开，如果断开则重新连接"""
        try:
            self.conn.ping(reconnect=True, attempts=3, delay=5)
        except Error as err:
            print(f"Connection lost: {err}")
            self.connect_to_database()

    def create_tables(self):
        """创建必要的数据库表"""
        try:
            # 区块表
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS blocks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    block_index INT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    previous_hash VARCHAR(64) NOT NULL,
                    hash VARCHAR(64) NOT NULL,
                    proof_of_work INT NOT NULL,
                    UNIQUE KEY unique_hash (hash),
                    UNIQUE KEY unique_index (block_index)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # 交易表
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    block_hash VARCHAR(64) NOT NULL,
                    sender VARCHAR(255) NOT NULL,
                    recipient VARCHAR(255) NOT NULL,
                    amount DECIMAL(20, 8) NOT NULL,
                    FOREIGN KEY (block_hash) REFERENCES blocks(hash)
                    ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            self.conn.commit()
            print("Database tables created successfully")
        except Error as err:
            print(f"Error creating tables: {err}")
            raise
    
    def execute_with_retry(self, func, *args, **kwargs):
        """执行数据库操作，带有重试机制"""
        for attempt in range(self.max_retries):
            try:
                self.reconnect_if_needed()
                return func(*args, **kwargs)
            except Error as err:
                print(f"Database operation failed (attempt {attempt + 1}): {err}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2)

    def insert_block(self, block) -> bool:
        """插入新区块"""
        def _insert():
            try:
                # 插入区块数据
                self.cursor.execute("""
                    INSERT INTO blocks (block_index, timestamp, previous_hash, hash, proof_of_work)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    block.index,
                    block.timestamp,
                    block.previous_hash,
                    block.hash,
                    block.data['proof-of-work']
                ))
                
                # 插入交易数据
                if block.data['transactions']:
                    for tx in block.data['transactions']:
                        # 确保amount是浮点数
                        amount = float(tx['amount'])
                        self.cursor.execute("""
                            INSERT INTO transactions (block_hash, sender, recipient, amount)
                            VALUES (%s, %s, %s, %s)
                        """, (
                            block.hash,
                            str(tx['from']),  # 确保是字符串
                            str(tx['to']),    # 确保是字符串
                            amount
                        ))
                
                self.conn.commit()
                return True
            except Exception as e:
                print(f"Error inserting block: {e}")
                self.conn.rollback()
                return False
                
        return self.execute_with_retry(_insert)
    
    def get_all_blocks(self) -> List[Dict]:
        """获取所有区块"""
        try:
            # 首先获取所有区块
            self.cursor.execute("""
                SELECT * FROM blocks 
                ORDER BY block_index
            """)
            blocks = self.cursor.fetchall()
            
            formatted_blocks = []
            for block in blocks:
                # 为每���区块获取其交易
                self.cursor.execute("""
                    SELECT sender as 'from', recipient as 'to', amount 
                    FROM transactions 
                    WHERE block_hash = %s
                """, (block['hash'],))
                transactions = self.cursor.fetchall()
                
                # 转换交易中的Decimal为float
                formatted_transactions = []
                for tx in transactions:
                    formatted_tx = dict(tx)
                    if isinstance(formatted_tx['amount'], Decimal):
                        formatted_tx['amount'] = float(formatted_tx['amount'])
                    formatted_transactions.append(formatted_tx)
                
                block_data = {
                    'block_index': block['block_index'],
                    'timestamp': block['timestamp'],
                    'previous_hash': block['previous_hash'],
                    'hash': block['hash'],
                    'proof_of_work': block['proof_of_work'],
                    'data': {
                        'proof-of-work': block['proof_of_work'],
                        'transactions': formatted_transactions
                    }
                }
                
                formatted_blocks.append(block_data)
            
            return formatted_blocks
        except Exception as e:
            print(f"Error getting blocks: {e}")
            return []
    
    def get_last_block(self) -> Optional[Dict]:
        """获取最后一个区块"""
        try:
            self.cursor.execute("""
                SELECT * FROM blocks 
                ORDER BY block_index DESC 
                LIMIT 1
            """)
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Error getting last block: {e}")
            return None
    
    def close(self):
        """关闭数据库连接"""
        self.cursor.close()
        self.conn.close() 