import random

def player(prev_play, opponent_history=[]):
    
    if prev_play != "":
        opponent_history.append(prev_play)

    # counter moves
    beat = {"R": "P", "P": "S", "S": "R"}

    # first few moves: random
    if len(opponent_history) < 5:
        return random.choice(["R", "P", "S"])

    # Look for repeating patterns in last 4 moves
    pattern = "".join(opponent_history[-4:])
    counts = {"R": 0, "P": 0, "S": 0}

    for i in range(len(opponent_history) - 4):
        if "".join(opponent_history[i:i+4]) == pattern:
            next_move = opponent_history[i+4]
            counts[next_move] += 1

    # predict most frequent next move
    predicted = max(counts, key=counts.get)

    if counts[predicted] > 0:
        return beat[predicted]

    # fallback strategy: counter most common move overall
    common = max(set(opponent_history), key=opponent_history.count)
    return beat[common]