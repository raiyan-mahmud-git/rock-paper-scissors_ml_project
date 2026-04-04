## Rock Paper Scissors AI – freeCodeCamp Project Overview 

This project implements an AI player for the Rock–Paper–Scissors game. The goal is to create a function that competes against several predefined bots and achieves a win rate of at least 60% against each of them.

The AI analyzes the opponent’s previous moves, identifies patterns, predicts the next move, and plays the counter move to increase its chance of winning.

## Project Objective 

# Create a function called player() that:

Receives the opponent’s previous move ("R", "P", or "S"). Returns the next move for the AI ("R", "P", or "S"). Learns from the opponent’s history to improve its predictions. 

The AI must defeat four bots provided by the project:

Quincy Abbey Kris Mrugesh 

The solution must win at least 60% of matches against each bot over a large number of games.

Game Rules 

# Rock–Paper–Scissors follows these rules:

Rock (R) beats Scissors (S) Scissors (S) beats Paper (P) Paper (P) beats Rock (R) How the AI Works 1. Opponent History Tracking 

The program stores the opponent’s previous moves in a list called opponent_history. This allows the AI to analyze patterns in the opponent's behavior.

2. Pattern Detection 

After at least five rounds, the AI examines the last four moves played by the opponent and searches the history for the same sequence.

Example pattern:

Last moves: R P S R 

If this pattern appeared earlier in the game, the program checks what move the opponent played next after that pattern.

3. Prediction 

The program counts how often "R", "P", or "S" followed the detected pattern and predicts the most likely next move.

4. Counter Strategy 

Once a move is predicted, the AI returns the move that beats it.

Example:

Predicted: R AI plays: P 5. Fallback Strategy 

If no pattern is detected, the AI counters the opponent’s most frequently played move.

If there is not enough data, the AI chooses a move randomly.

# Through this project you will learn:

How to store and analyze historical data Pattern recognition techniques Designing simple AI strategies Implementing decision-making algorithms in Python Author 

# Student project completed as part of the freeCodeCamp Machine Learning with Python Certification.

