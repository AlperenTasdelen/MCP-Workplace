import json
import os
import uuid
from typing import List, Dict, Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
INVENTORY_FILE = os.path.join(DATA_DIR, "user_inventory.json")

def _ensure_file():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(INVENTORY_FILE):
        with open(INVENTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)

def read_inventory() -> List[Dict[str, Any]]:
    _ensure_file()
    try:
        with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def write_inventory(data: List[Dict[str, Any]]) -> None:
    _ensure_file()
    with open(INVENTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def add_item(name: str, category: str, color: str = "", season: str = "", extra_notes: str = "") -> str:
    """Adds a new clothing item to the user's local inventory via JSON. Returns the item ID."""
    inventory = read_inventory()
    item_id = str(uuid.uuid4())[:8]  # Short ID for simplicity
    new_item = {
        "id": item_id,
        "name": name,
        "category": category,
        "color": color,
        "season": season,
        "extra_notes": extra_notes
    }
    inventory.append(new_item)
    write_inventory(inventory)
    return item_id

def get_items() -> List[Dict[str, Any]]:
    """Returns the full list of items in the user's inventory."""
    return read_inventory()

def remove_item(item_id: str) -> bool:
    """Removes an item by ID. Returns True if removed, False if not found."""
    inventory = read_inventory()
    filtered_inv = [item for item in inventory if item.get("id") != item_id]
    if len(filtered_inv) == len(inventory):
        return False
    
    write_inventory(filtered_inv)
    return True
