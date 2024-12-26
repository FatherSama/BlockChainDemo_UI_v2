from miner_server import bc, Block
from db_handler import BlockchainDB

def migrate_to_mysql():
    db = BlockchainDB()
    
    # 获取现有区块链数据
    old_blockchain = bc.blockchain
    
    # 逐个插入区块
    for block in old_blockchain:
        db.insert_block(block)
    
    print(f"Migrated {len(old_blockchain)} blocks to MySQL")

if __name__ == "__main__":
    migrate_to_mysql() 