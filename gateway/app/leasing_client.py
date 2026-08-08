import json
import logging
from web3 import Web3
from web3.exceptions import Web3Exception
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class LeasingClient:
    def __init__(self, rpc_url: str, deployments_path: str, private_key: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.private_key = private_key
        
        # We need the admin account to sign transactions
        self.account = self.w3.eth.account.from_key(private_key)
        
        # Load ABI and address from leasing-localhost.json
        try:
            with open(deployments_path, 'r') as f:
                deploy_data = json.load(f)
                self.contract_address = Web3.to_checksum_address(deploy_data['address'])
            
            # Use ABI of LeasingRegistry. Since we don't have it directly in the deployments JSON,
            # we will load it from artifacts, but the instruction said "legge ABI/indirizzo da leasing-localhost.json via volume".
            # Actually, `leasing-localhost.json` only contains the address/block/network, not the full ABI.
            # We'll load the ABI from the artifacts folder.
            with open('/app/artifacts/contracts/LeasingRegistry.sol/LeasingRegistry.json', 'r') as f:
                artifact = json.load(f)
                self.abi = artifact['abi']
                
            self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)
            logger.info(f"Initialized LeasingClient at {self.contract_address}")
        except Exception as e:
            logger.error(f"Failed to initialize LeasingClient: {e}")
            self.contract = None

    def lease_node(self, device_id: str):
        if not self.contract:
            raise ValueError("Contract not initialized")

        try:
            tx = self.contract.functions.leaseNode(device_id).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 3000000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status != 1:
                raise Exception("Transaction failed")
                
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Error in lease_node: {e}")
            raise e

    def release_node(self, device_id: str):
        if not self.contract:
            raise ValueError("Contract not initialized")

        try:
            tx = self.contract.functions.releaseNode(device_id).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 3000000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status != 1:
                raise Exception("Transaction failed")
                
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Error in release_node: {e}")
            raise e

    def get_leasing_status(self, device_id: str) -> dict:
        if not self.contract:
            raise ValueError("Contract not initialized")
            
        try:
            is_leased, leased_by = self.contract.functions.leases(device_id).call()
            return {
                "device_id": device_id,
                "is_leased": is_leased,
                "leased_by": leased_by
            }
        except Exception as e:
            logger.error(f"Error in get_leasing_status: {e}")
            raise e
