import hashlib
import json
from os import urandom
from tinyec import registry
from threading import Thread
from multiprocessing import Pool,freeze_support
from multiprocessing import SimpleQueue
from numba import prange
import time

def compress(publicKey): 
    return hex(publicKey.x) + hex(publicKey.y % 2)[2:] 

curve = registry.get_curve('brainpoolP256r1')
 
class Blockchain:
 
    # This function is created
    # to create the very first
    # block and set its hash to "0"
    def __init__(self):
        self.chain = []
        self.transactions = []
        self.current_block = None
        self.difficulty = 8
        self.reward_for_block = 4
        self.max_supply = 100000
        self.time_for_block = 30
        self.create_block(proof=1, previous_hash='0',contents='0')
 
    # This function is created
    # to add further blocks
    # into the chain
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
        public_key = private_key * curve.g
        wallet_adress = compress(public_key)
        return (hex(private_key),wallet_adress)
 
    # This function is created
    # to display the previous block
    def get_previous_block(self):return self.chain[-1]
 
    # This is the function for proof of work
    # and used to successfully mine the block
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
        if not self.check_for_access(private_key,owners_wallet_adress) or self.get_balance(private_key,owners_wallet_adress)[0] < amount:return False
        self.transactions.append((owners_wallet_adress,recipient_wallet_adress,amount))

    def check_for_access(self,private_key,wallet_adress):
        public_key = int(private_key,base=16) * curve.g
        if compress(public_key) != wallet_adress:return False
        return True
    
    def get_balance(self,wallet):
        balance = 0
        pending_balance = 0
        for block in self.chain[1:]:
            for transaction in block['contents']:
                if len(transaction) == 2 and transaction[0] == wallet:
                    balance += transaction[1]
                    continue
                if transaction[0] == wallet:balance -= transaction[2]
                elif transaction[1] == wallet:balance += transaction[2]
        if self.current_block is not None:
            pending_balance = balance
            for transaction in self.current_block:
                if len(transaction) == 2 and transaction[0] == wallet:
                    pending_balance += transaction[1]
                    continue
                if transaction[0] == wallet:pending_balance -= transaction[2]
                elif transaction[1] == wallet:pending_balance += transaction[2]
        elif self.transactions != []:
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

    def main_cycle(self):
        while True:
            if len(self.transactions) > 2:
                if self.chain[len(self.chain)-1]['index'] % 20 == 0 and self.current_block is None:
                    self.difficulty = self.difficulty+1 if (self.time_for_block - (((time.time() - float(self.chain[len(self.chain)-21]['timestamp']))/20)))/16 > 0 else self.difficulty
                self.current_block = self.transactions
                self.transactions = []
            
            
    def submit_proof(self,proof,wallet,start,start_miner):
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
        if self.get_coins_circulated() < self.max_supply:
            self.give_reward(self.reward_for_block,wallet)
        duration = time.time()-start
        print(duration)
        hashrate = round(((proof-1-start_miner)/(duration)),3)
        if round(duration) < self.time_for_block:
            self.difficulty = self.difficulty+1 if abs(16**(self.difficulty+1)/hashrate - self.time_for_block) < abs(self.time_for_block - duration) else self.difficulty
        elif round(duration) > self.time_for_block:
            self.difficulty = self.difficulty-1 if abs(16**(self.difficulty-1)/hashrate - self.time_for_block) < abs(self.time_for_block - duration) else self.difficulty
        print(f'Hashrate: {hashrate} h/second')

    def get_previos_hash(self):
        if self.current_block is None:return None
        return self.hash(self.get_previous_block())
    
    def give_reward(self,amount,wallet):self.transactions.append((wallet,amount))
        
blockchain = Blockchain()
main_thread = Thread(target=blockchain.main_cycle)
#main_thread.start()

def proof_of_work(previous_proof):
    new_proof = 1
    check_proof = False

    while check_proof is False:
        hash_operation = hashlib.sha256(
            str(new_proof**2 - previous_proof**2).encode()).hexdigest()
        if hash_operation[:blockchain.difficulty] == '0'*blockchain.difficulty:
            check_proof = True
        else:
            new_proof += 1

    return new_proof

def proof_of_work_proc(all):
    previous_proof = all[0]
    start,end = all[1]
    new_proof = start
    check_proof = False

    while check_proof is False:
        hash_operation = hashlib.sha256(
            str(new_proof**2 - previous_proof**2).encode()).hexdigest()
        if hash_operation[:blockchain.difficulty] == '0'*blockchain.difficulty:
            check_proof = True
        else:
            new_proof += 1
        if new_proof == end:break

    queue.put((new_proof,start))

def init_worker(arg_queue):
    global queue
    queue = arg_queue

def proof_of_work_multiprocessing(previous_proof,workers):
    queue = SimpleQueue()
    ranges = [(i,(i+16**blockchain.difficulty//workers)) for i in prange(0,16**blockchain.difficulty,16**blockchain.difficulty//workers)]
    del ranges[len(ranges)-1]
    with Pool(workers,initializer=init_worker, initargs=(queue,)) as pool:
        _ = pool.map_async(proof_of_work_proc,[(previous_proof,i) for i in ranges])
        proof = queue.get()
        if proof[0] is not None:pool.terminate()
    return proof

def mine_block(wallet):
    global main_thread
    previous_proof = blockchain.get_previous_block()['proof']

    start = time.time()
    del main_thread
    #proof = proof_of_work(previous_proof)
    proof = proof_of_work_multiprocessing(previous_proof,12)
    main_thread = Thread(target=blockchain.main_cycle)
    main_thread.start()
    time.sleep(0.02)#only here
    blockchain.submit_proof(proof[0],wallet,start-0.02,proof[1])

if __name__ == '__main__':
    freeze_support()
    myid = blockchain.create_account()
    otherid = blockchain.create_account()
    blockchain.give_reward(1,myid[1])
    blockchain.give_reward(2,myid[1])
    blockchain.give_reward(0.5,myid[1])
    previous_proof = blockchain.get_previous_block()['proof']
    print(myid)
    mine_block(myid[1])
    print(blockchain.chain)
    
# blockchain.give_reward(0.3,myid[1])
# blockchain.create_transaction(myid[0],myid[1],otherid[1],3.3)
# #print(len(blockchain.transactions))
# mine_block(myid[1])
# print(blockchain.get_balance(*myid))
# print(blockchain.chain)
# print(blockchain.chain_valid(blockchain.chain))

# print(int(myid[1],base=16)*curve.g)
  
# Function to calculate compress point  
# of elliptic curves 
  
# Generation of secret key and public key 
# Ka = secrets.randbelow(curve.field.n)
# X = Ka * curve.g  
# print("X:", compress(X)) 
# Kb = secrets.randbelow(curve.field.n) 
# Y = Kb * curve.g  
# print("Y:", compress(Y)) 
# print("Currently exchange the publickey (e.g. through Internet)") 