import os
import json
import logging
from typing import List, Optional
from app.config import settings
from app.models import TrustedStack, TrustedDevicesConfig

logger = logging.getLogger(__name__)

class TrustConfigClient:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or settings.trusted_devices_config

    def get_config(self) -> TrustedDevicesConfig:
        if not os.path.exists(self.config_path):
            logger.warning(f"File di configurazione non trovato in {self.config_path}, restituisco config vuoto.")
            return TrustedDevicesConfig(trustedStacks=[])

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return TrustedDevicesConfig.model_validate(data)
        except Exception as e:
            logger.error(f"Errore durante la lettura di {self.config_path}: {e}")
            raise

    def list_stacks(self) -> List[TrustedStack]:
        return self.get_config().trusted_stacks

    def add_stack(self, stack: TrustedStack) -> TrustedStack:
        config = self.get_config()
        for existing in config.trusted_stacks:
            if existing.stack_id == stack.stack_id:
                raise ValueError(f"Lo stack '{stack.stack_id}' esiste gia'")

        config.trusted_stacks.append(stack)
        self._save_config(config)
        return stack

    def delete_stack(self, stack_id: str) -> bool:
        config = self.get_config()
        initial_count = len(config.trusted_stacks)
        config.trusted_stacks = [s for s in config.trusted_stacks if s.stack_id != stack_id]

        if len(config.trusted_stacks) == initial_count:
            raise KeyError(f"Lo stack '{stack_id}' non e' stato trovato")

        self._save_config(config)
        return True

    def _save_config(self, config: TrustedDevicesConfig) -> None:
        target_path = os.path.abspath(self.config_path)
        dir_name = os.path.dirname(target_path)
        os.makedirs(dir_name, exist_ok=True)

        temp_path = f"{target_path}.tmp.{os.getpid()}"
        data = config.model_dump(by_alias=True)
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        
        # Scrittura atomica tramite atomic rename (os.replace)
        os.replace(temp_path, target_path)

trust_config_client = TrustConfigClient()
