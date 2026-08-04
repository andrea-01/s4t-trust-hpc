import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class OwnersRegistry:
    def __init__(self, file_path: str = "owners.json"):
        base_dir = Path(__file__).parent
        # If file_path is absolute, base_dir / file_path evaluates to file_path
        self.file_path = base_dir / file_path
        self._owners = {}
        self._load()

    def _load(self):
        try:
            with open(self.file_path, "r") as f:
                self._owners = json.load(f)
            logger.info(f"Loaded {len(self._owners)} owners from registry.")
        except FileNotFoundError:
            logger.warning(f"Owners file {self.file_path} not found. Registry is empty.")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing owners file {self.file_path}: {e}")

    def get_email(self, address: str) -> Optional[str]:
        if not address:
            return None
        normalized_address = address.lower()
        for known_addr, email in self._owners.items():
            if known_addr.lower() == normalized_address:
                return email
        return None
