import json
from web3 import Web3
from app.config import settings

class ChainClient:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.rpc_url))
        self._load_contract()
        
    def _load_contract(self):
        # Load ABI
        with open(settings.abi_path, "r") as f:
            artifact = json.load(f)
            abi = artifact["abi"]
            
        # Load address
        with open(settings.deployments_path, "r") as f:
            deploy_data = json.load(f)
            address = deploy_data["address"]
            
        self.contract = self.w3.eth.contract(address=address, abi=abi)
        
    def request_onboarding(self, device_id: str, owner_address: str) -> dict:
        """
        Sends an onboarding request. 
        """
        # Sign with admin private key from server config
        account = self.w3.eth.account.from_key(settings.admin_private_key)
        tx = self.contract.functions.requestOnboarding(device_id, owner_address).build_transaction({
            'from': account.address,
            'nonce': self.w3.eth.get_transaction_count(account.address),
        })
        signed_tx = self.w3.eth.account.sign_transaction(tx, settings.admin_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Decode event to get requestId
        logs = self.contract.events.OnboardingRequested().process_receipt(receipt)
        request_id = logs[0].args.requestId if logs else None
        
        return {
            "tx_hash": tx_hash.hex(),
            "request_id": request_id
        }

    def get_status(self, request_id: int) -> dict:
        """
        Reads the status of a request directly from the chain.
        """
        # Returns tuple: (deviceId, requester, owner, status)
        try:
            req = self.contract.functions.requests(request_id).call()
            status_map = {0: "Pending", 1: "Approved", 2: "Rejected", 3: "Revoked"}
            return {
                "device_id": req[0],
                "requester": req[1],
                "owner": req[2],
                "status": status_map.get(req[3], "Unknown")
            }
        except Exception as e:
            return {"error": str(e)}

chain_client = ChainClient()
