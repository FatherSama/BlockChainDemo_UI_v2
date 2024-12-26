import pickle
import requests
from collections import defaultdict
from typing import List, Dict, Set

class PBFTConsensus:
    def __init__(self, nodes: Set[str], my_node: str):
        self.nodes = nodes  # 所有节点地址
        self.my_node = my_node  # 本节点地址
        self.current_view = 0  # 当前视图编号
        self.prepare_votes = defaultdict(set)  # 准备阶段投票
        self.commit_votes = defaultdict(set)  # 提交阶段投票
        self.timeout = 30  # 修改默认超时时间为30秒
        
    
    def is_primary(self) -> bool:
        """判断当前节点是否为主节点"""   
        # 如果只有一个节点，则该节点就是主节点
        if len(self.nodes) == 1:
            return True
            
        nodes_list = sorted(list(self.nodes))
        primary_index = self.current_view % len(nodes_list)
        return nodes_list[primary_index] == self.my_node
    
    def get_required_votes(self) -> int:
        """
        计算需要的投票数
        单节点时返回0，多节点时需要2/3多数
        """
        if len(self.nodes) <= 1:
            return 0
        return (1 * len(self.nodes)) // 3
    
    def broadcast_prepare(self, block) -> bool:
        """广播准备消息"""
        success_count = 1  # 包括自己的投票
        
        for node in self.nodes:
            if node == self.my_node:
                continue
            
            try:
                data = pickle.dumps({
                    'block': block,
                    'from': self.my_node
                })
                
                response = requests.post(
                    f"{node}prepare",
                    data=data,
                    timeout=self.timeout  # 使用类的timeout属性
                )
                
                if response.status_code == 200:
                    success_count += 1
                    
            except requests.exceptions.Timeout:
                print(f"Prepare broadcast to {node} timed out after {self.timeout} seconds")
                continue
            except Exception as e:
                print(f"Error in prepare broadcast to {node}: {e}")
                continue
            
        return success_count >= self.get_required_votes()
    
    def broadcast_commit(self, block) -> bool:
        """广播提交消息"""
        success_count = 1  # 包括自己的投票
        
        for node in self.nodes:
            if node == self.my_node:
                continue
            
            try:
                data = pickle.dumps({
                    'block': block,
                    'from': self.my_node
                })
                
                response = requests.post(
                    f"{node}commit",
                    data=data,
                    timeout=self.timeout  # 使用类的timeout属性
                )
                
                if response.status_code == 200:
                    success_count += 1
                    
            except requests.exceptions.Timeout:
                print(f"Commit broadcast to {node} timed out after {self.timeout} seconds")
                continue
            except Exception as e:
                print(f"Error in commit broadcast to {node}: {e}")
                continue
            
        return success_count >= self.get_required_votes()
    
    def add_prepare_vote(self, block_hash: str, node: str) -> bool:
        """添加准备阶段投票"""
        # 如果是单节点，直接返回True
        if len(self.nodes) <= 1:
            return True
            
        self.prepare_votes[block_hash].add(node)
        return len(self.prepare_votes[block_hash]) >= self.get_required_votes()
    
    def add_commit_vote(self, block_hash: str, node: str) -> bool:
        """添加提交阶段投票"""
        # 如果是单节点，直接返回True
        if len(self.nodes) <= 1:
            return True
            
        self.commit_votes[block_hash].add(node)
        return len(self.commit_votes[block_hash]) >= self.get_required_votes()