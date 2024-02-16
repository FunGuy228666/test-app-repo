from flask import Flask, request
from threading import Thread
from os import urandom
from tinyec import registry
import time
import json
import hashlib

 
class Blockchain:

    def __init__(self):
        self.chain = []
        self.transactions = []
        self.current_block = None
        self.difficulty = 5
        self.reward_for_block = 4
        self.max_supply = 100000
        self.time_per_block = 120
        self.time_to_mine = 30
        self.blocks_before_corection = 25
        self.transactions_per_block = 5
        self.curve = registry.get_curve('brainpoolP256r1')
        self.create_block(proof=1, previous_hash='0',contents="0")

    def create_block(self, proof, previous_hash, contents):
        block = {'index': len(self.chain) + 1,
                'timestamp': str(time.time()),
                'proof': proof,
                'previous_hash': previous_hash,
                'contents':contents}
        self.chain.append(block)
        return block
    
    def create_account(self):
        private_key = int(str(bin(int.from_bytes(urandom(33))))[2:258],base=2)
        public_key = private_key * self.curve.g
        wallet_adress = Blockchain.compress(public_key)
        return (hex(private_key),wallet_adress)
 
    def get_previous_block(self):return self.chain[-1]

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()
 
    def chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1
 
        while block_index < len(chain):
            block = chain[block_index]
            if block['previous_hash'] != self.hash(previous_block):
                return False
 
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(
                str(proof**2 - previous_proof**2).encode()).hexdigest()
 
            if hash_operation[:self.difficulty] != '0'*self.difficulty:
                return False
            previous_block = block
            block_index += 1
 
        return True
    
    def create_transaction(self,private_key,owners_wallet_adress,recipient_wallet_adress,amount):
        if not self.check_for_access(private_key,owners_wallet_adress) or self.get_balance(owners_wallet_adress)[0] < amount:return False
        self.transactions.append((owners_wallet_adress,recipient_wallet_adress,amount))
        return True

    def check_for_access(self,private_key,wallet_adress):
        public_key = int(private_key,base=16) * self.curve.g
        if Blockchain.compress(public_key) != wallet_adress:return False
        return True
    
    def get_balance(self,wallet):
        balance = 0
        pending_balance = 0
        for block in self.chain[1:]:
            if block['contents'] != []:
                for transaction in block['contents']:
                    if len(transaction) == 2 and transaction[0] == wallet:
                        balance += transaction[1]
                        continue
                    if transaction[0] == wallet:balance -= transaction[2]
                    elif transaction[1] == wallet:balance += transaction[2]
        if self.current_block is not None:
            if self.current_block != []:
                for transaction in self.current_block:
                    if len(transaction) == 2 and transaction[0] == wallet:
                        pending_balance += transaction[1]
                        continue
                    if transaction[0] == wallet:pending_balance -= transaction[2]
                    elif transaction[1] == wallet:pending_balance += transaction[2]
        elif self.transactions != []:
            if self.current_block != []:
                for transaction in self.transactions:
                    if len(transaction) == 2 and transaction[0] == wallet:
                        pending_balance += transaction[1]
                        continue
                    if transaction[0] == wallet:pending_balance -= transaction[2]
                    elif transaction[1] == wallet:pending_balance += transaction[2]
        return round(balance,6),round(pending_balance,6)
    
    def get_coins_circulated(self):
        wallets = {}
        for block in self.chain[1:]:
            if self.current_block != []:
                for transaction in block['contents']:
                    if len(transaction) == 2:
                        if transaction[0] not in wallets.keys():wallets.update({transaction[0]:0})
                        wallets[transaction[0]] += transaction[1]
                        continue
                    else:
                        if transaction[0] not in wallets.keys():wallets.update({transaction[0]:0})
                        if transaction[1] not in wallets.keys():wallets.update({transaction[1]:0})
                        wallets[transaction[0]] -= transaction[2]
                        wallets[transaction[1]] += transaction[2]
        return sum(wallets.values())      
            
    def submit_proof(self,proof,wallet):
        if self.current_block is None:return False
        previous_block = self.get_previous_block()
        previous_proof = previous_block['proof']
        hash_operation = hashlib.sha256(
            str(proof**2 - previous_proof**2).encode()).hexdigest()
        if hash_operation[:self.difficulty] != '0'*self.difficulty:
            return False
        previous_hash = self.hash(previous_block)
        self.create_block(proof, previous_hash, self.current_block)
        self.current_block = None
        self.transactions = []
        if self.get_coins_circulated() < self.max_supply:
            self.give_reward(self.reward_for_block,wallet)
        return True

    def get_previos_hash(self):
        if self.current_block is None:return None
        return self.hash(self.get_previous_block())
    
    def give_reward(self,amount,wallet):self.transactions.append((wallet,amount))

    @staticmethod   
    def compress(publicKey): 
        return hex(publicKey.x) + hex(publicKey.y % 2)[2:] 

app = Flask(__name__)
 
@app.route('/get_balance',methods=['POST'])
def get_balance():
    input_json = request.get_json(force=True)
    if 'wallet' not in input_json:return "Please send wallet adress",400
    balance = blockchain.get_balance(input_json['wallet'])
    return str(balance),200

@app.route('/generate_wallet')
def generate_wallet():
    return str(blockchain.create_account()),200

@app.route('/create_transaction',methods=['POST'])
def create_transaction():
    input_json = request.get_json(force=True)
    if not all([i in input_json.keys() for i in ['o_wallet','pkey','r_wallet','amount']]) :return "Please send your wallet, your private key, a recipient wallet and an amount",400
    response = blockchain.create_transaction(input_json['pkey'],input_json['o_wallet'],input_json['r_wallet'],int(input_json['amount']))
    if not response:return "Error",400
    return "Sucsess",200

@app.route('/submit_proof',methods=['POST'])
def submit_proof():
    input_json = request.get_json(force=True)
    if not all([i in input_json.keys() for i in ['wallet','proof']]):return "Please send a wallet and a proof",400
    response = blockchain.submit_proof(input_json['proof'],input_json['wallet'])
    if not response:return "Error",400
    return "Sucsess",200

@app.route('/get_previos_proof')
def get_previos_proof():
    previos_proof = blockchain.get_previous_block()['proof']
    return str(previos_proof),200

@app.route('/get_difficulty')
def get_difficulty():
    return str(blockchain.difficulty),200

@app.route('/get_chain')
def get_chain():
    return str(blockchain.chain),200

def main_loop():
    while True:
        if (len(blockchain.transactions) > blockchain.transactions_per_block or time.time() - float(blockchain.get_previous_block()["timestamp"]) > blockchain.time_per_block) and blockchain.current_block is None:
            if blockchain.chain[len(blockchain.chain)-1]['index'] % blockchain.blocks_before_corection == 0 and blockchain.current_block is None:blockchain.difficulty = blockchain.difficulty+1 if (blockchain.time_to_mine - (((time.time() - float(blockchain.chain[len(blockchain.chain)-blockchain.blocks_before_corection-1]['timestamp']))/blockchain.blocks_before_corection)))/16 > 0 else blockchain.difficulty
            blockchain.current_block = blockchain.transactions

if __name__ == '__main__':

    blockchain = Blockchain()

    t = Thread(target=main_loop)
    t.start()
    app.run()
    t.join()