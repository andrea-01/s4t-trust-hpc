import json
import asyncio
import logging
from pathlib import Path
from web3 import Web3
from notification.app.config import settings
from notification.app.owners_registry import OwnersRegistry
from notification.app.mailer import send_onboarding_email

logger = logging.getLogger(__name__)

class ChainListener:
    def __init__(self, registry: OwnersRegistry):
        self.registry = registry
        self.w3 = Web3(Web3.HTTPProvider(settings.rpc_url))
        self.contract = self._load_contract()
        self.last_processed_block = self._load_checkpoint()
        self.is_running = False

    def _load_contract(self):
        try:
            with open(settings.abi_path, 'r') as f:
                contract_json = json.load(f)
                abi = contract_json.get('abi', [])
            with open(settings.deployments_path, 'r') as f:
                deployments = json.load(f)
                address = deployments.get('OnboardingTrust')
            
            if not address:
                raise ValueError("Contract address not found in deployments file")
                
            return self.w3.eth.contract(address=address, abi=abi)
        except Exception as e:
            logger.error(f"Failed to load contract: {e}")
            return None

    def _load_checkpoint(self) -> int:
        try:
            with open(settings.checkpoint_file, 'r') as f:
                block = int(f.read().strip())
                logger.info(f"Loaded checkpoint: block {block}")
                return block
        except (FileNotFoundError, ValueError):
            logger.info("No valid checkpoint found. Starting from latest block.")
            try:
                return self.w3.eth.block_number
            except Exception:
                return 0

    def _save_checkpoint(self, block: int):
        try:
            path = Path(settings.checkpoint_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                f.write(str(block))
            self.last_processed_block = block
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    async def poll_events(self):
        self.is_running = True
        while self.is_running:
            try:
                if not self.contract:
                    self.contract = self._load_contract()
                    if not self.contract:
                        await asyncio.sleep(settings.poll_interval)
                        continue

                current_block = self.w3.eth.block_number
                
                if self.last_processed_block >= current_block:
                    await asyncio.sleep(settings.poll_interval)
                    continue
                    
                from_block = self.last_processed_block + 1
                to_block = current_block
                
                logger.info(f"Polling blocks {from_block} to {to_block}")
                
                events = self.contract.events.OnboardingRequested.get_logs(
                    fromBlock=from_block,
                    toBlock=to_block
                )
                
                for event in events:
                    self._process_event(event)
                    
                self._save_checkpoint(to_block)
                
            except Exception as e:
                logger.error(f"Error during polling: {e}")
                
            await asyncio.sleep(settings.poll_interval)

    def _process_event(self, event):
        try:
            args = event['args']
            device_id = args.get('deviceId')
            request_id = args.get('requestId')
            owner_address = args.get('owner')
            
            logger.info(f"Processing OnboardingRequested for {device_id} (req {request_id})")
            
            email = self.registry.get_email(owner_address)
            if not email:
                logger.warning(f"No email found for owner {owner_address}. Skipping notification.")
                return
                
            send_onboarding_email(email, device_id, request_id, owner_address)
            
        except Exception as e:
            logger.error(f"Error processing event {event}: {e}")

    def stop(self):
        self.is_running = False
