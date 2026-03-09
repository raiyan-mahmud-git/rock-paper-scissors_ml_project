class RockPaperScissors:
    def __init__(self):
        self.player_score = 0
        self.computer_score = 0

    def play_round(self, player_choice):
        import random
        choices = ['rock', 'paper', 'scissors']
        computer_choice = random.choice(choices)
        print(f"Computer chose: {computer_choice}")

        if player_choice == computer_choice:
            print("It's a tie!")
        elif (player_choice == 'rock' and computer_choice == 'scissors') or \
             (player_choice == 'paper' and computer_choice == 'rock') or \
             (player_choice == 'scissors' and computer_choice == 'paper'):
            print("You win!")
            self.player_score += 1
        else:
            print("You lose!")
            self.computer_score += 1

    def show_scores(self):
        print(f"Player Score: {self.player_score}, Computer Score: {self.computer_score}")


if __name__ == '__main__':
    game = RockPaperScissors()
    while True:
        player_choice = input("Enter rock, paper, or scissors (or 'quit' to stop): ").lower()
        if player_choice == 'quit':
            break
        elif player_choice not in ['rock', 'paper', 'scissors']:
            print("Invalid choice, try again.")
            continue
        game.play_round(player_choice)
        game.show_scores()
