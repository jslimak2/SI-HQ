# manage_strategies.py
"""
This module contains the business logic for managing betting strategies.
It handles creating, deleting, and updating strategy data.
"""
from app import load_json, save_json, strategies_filepath

def get_strategies():
    """Retrieves all betting strategies."""
    return load_json(strategies_filepath, [])

def create_strategy(form_data):
    """Creates a new betting strategy and saves it."""
    strategies_list = get_strategies()
    new_strategy_id = max([s['id'] for s in strategies_list], default=0) + 1
    linked_strategy_id = form_data.get('linked_strategy_id')
    if linked_strategy_id:
        linked_strategy_id = int(linked_strategy_id)
    
    new_strategy = {
        'id': new_strategy_id,
        'name': form_data['name'],
        'type': form_data['type'],
        'linked_strategy_id': linked_strategy_id
    }
    strategies_list.append(new_strategy)
    return save_json(strategies_filepath, strategies_list)

def delete_strategy(strategy_id):
    """Deletes a strategy by its ID."""
    strategies_list = get_strategies()
    updated_list = [s for s in strategies_list if s['id'] != strategy_id]
    return save_json(strategies_filepath, updated_list)
