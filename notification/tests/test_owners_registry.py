import json
from notification.app.owners_registry import OwnersRegistry

def test_owners_registry_lookup(tmp_path):
    owners_data = {
        "0x70997970C51812dc3A010C7d01b50e0d17dc79C8": "owner@test.local",
        "0xabc123": "other@test.local"
    }
    file_path = tmp_path / "test_owners.json"
    with open(file_path, "w") as f:
        json.dump(owners_data, f)
        
    registry = OwnersRegistry(file_path=str(file_path))
    
    assert registry.get_email("0x70997970C51812dc3A010C7d01b50e0d17dc79C8") == "owner@test.local"
    assert registry.get_email("0x70997970c51812dc3a010c7d01b50e0d17dc79c8") == "owner@test.local"
    assert registry.get_email("0xnonexistent") is None

def test_owners_registry_file_not_found(tmp_path):
    registry = OwnersRegistry(file_path=str(tmp_path / "nonexistent.json"))
    assert registry.get_email("0xabc") is None
