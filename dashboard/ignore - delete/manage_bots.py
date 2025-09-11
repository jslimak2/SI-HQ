# manage_bots.py
"""
This module contains the business logic for managing betting bots.
It handles creating, deleting, and updating bot data.
"""
from app import load_json, save_json, bots_filepath

def get_bots():
    """Retrieves all betting bots."""
    return load_json(bots_filepath, [])

def create_bot(form_data):
    """Creates a new betting bot and saves it."""
    bots_list = get_bots()
    new_bot_id = max([b['id'] for b in bots_list], default=0) + 1
    new_bot = {
        'id': new_bot_id,
        'name': form_data['name'],
        'starting_bankroll': float(form_data['starting_bankroll']),
        'bet_percentage': float(form_data['bet_percentage']),
        'current_balance': float(form_data['starting_bankroll']),
        'linked_strategy_id': int(form_data['linked_strategy_id']),
        'career_wins': 0,
        'career_losses': 0,
        'current_win_streak': 0,
        'current_loss_streak': 0,
        'bet_history': []
    }
    bots_list.append(new_bot)
    return save_json(bots_filepath, bots_list)

def delete_bot(bot_id):
    """Deletes a bot by its ID."""
    bots_list = get_bots()
    updated_list = [b for b in bots_list if b['id'] != bot_id]
    return save_json(bots_filepath, updated_list)
