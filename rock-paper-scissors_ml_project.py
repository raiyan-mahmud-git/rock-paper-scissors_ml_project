import random

def player(prev_play, opponent_history=None):
    if opponent_history is None:
        opponent_history = []
    
    if prev_play != "":
        opponent_history.append(prev_play)

    beat = {"R": "P", "P": "S", "S": "R"}

    if len(opponent_history) < 5:
        return random.choice(["R", "P", "S"])

    pattern = "".join(opponent_history[-4:])
    counts = {"R": 0, "P": 0, "S": 0}

    for i in range(len(opponent_history) - 4):
        if i + 4 < len(opponent_history) and "".join(opponent_history[i:i+4]) == pattern:
            next_move = opponent_history[i+4]
            counts[next_move] += 1

    predicted = max(counts, key=counts.get)

    if counts[predicted] > 0:
        return beat[predicted]

    if opponent_history:  # Check if not empty
        common = max(set(opponent_history), key=opponent_history.count)
        return beat[common]
    
    return random.choice(["R", "P", "S"])
