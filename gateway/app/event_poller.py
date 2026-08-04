import asyncio
from typing import List, Dict
from app.chain_client import chain_client
from app.config import settings

class EventPoller:
    def __init__(self):
        self.events_cache: List[Dict] = []
        self.last_block_processed = 0
        self.running = False
        
    async def start(self):
        self.running = True
        
        # Start from the block where the contract was deployed, or 0
        try:
            self.last_block_processed = chain_client.w3.eth.block_number
        except:
            self.last_block_processed = 0
            
        asyncio.create_task(self._poll_loop())
        
    async def stop(self):
        self.running = False

    async def _poll_loop(self):
        while self.running:
            try:
                latest_block = chain_client.w3.eth.block_number
                if latest_block > self.last_block_processed:
                    self._fetch_events(self.last_block_processed + 1, latest_block)
                    self.last_block_processed = latest_block
            except Exception as e:
                print(f"Error polling events: {e}")
                
            await asyncio.sleep(settings.poll_interval)
            
    def _fetch_events(self, from_block: int, to_block: int):
        events_types = [
            chain_client.contract.events.OnboardingRequested,
            chain_client.contract.events.OnboardingApproved,
            chain_client.contract.events.OnboardingRejected,
            chain_client.contract.events.OnboardingRevoked
        ]
        
        for event_type in events_types:
            try:
                logs = event_type.get_logs(fromBlock=from_block, toBlock=to_block)
                for log in logs:
                    # Simplify the event data for the API response
                    event_data = {
                        "event": log.event,
                        "blockNumber": log.blockNumber,
                        "transactionHash": log.transactionHash.hex(),
                        "args": dict(log.args)
                    }
                    self.events_cache.append(event_data)
            except Exception as e:
                print(f"Error fetching event {event_type.event_name}: {e}")
                
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        return self.events_cache[-limit:]

event_poller = EventPoller()
