from __future__ import annotations


def get_shortened_string(length: int, start: int, string: str) -> str:
    full_length = len(string)
    if full_length <= 100:
        return string

    item_id, _, remaining = string.partition(' - ')
    start_index = len(item_id) + 3
    max_remaining_length = 100 - start_index

    end = start + length
    if start < start_index:
        start = start_index

    # If the match is near the beginning then just extend it to the end
    if end < 100:
        if full_length > 100:
            return string[:99] + '…'
        return string[:100]

    has_end = end < full_length
    excess = (end - start) - max_remaining_length + 1
    if has_end:
        return f"{item_id} - …{string[start + excess + 1:end]}…"
    return f"{item_id} - …{string[start + excess:end]}"


def mention_to_user_id(mention: str):
    user_id = mention.replace("<", "")
    user_id = user_id.replace(">", "")
    user_id = user_id.replace("@", "")
    return int(user_id)
