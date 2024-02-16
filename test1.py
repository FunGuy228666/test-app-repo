import hashlib

def proof_of_work(previous_proof):
    new_proof = 1
    check_proof = False

    while check_proof is False:
        hash_operation = hashlib.sha256(
            str(new_proof**2 - previous_proof**2).encode()).hexdigest()
        if hash_operation[:5] == '0'*5:
            check_proof = True
        else:
            new_proof += 1

    return new_proof

print(proof_of_work(1))