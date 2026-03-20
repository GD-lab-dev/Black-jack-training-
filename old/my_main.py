import os
import sys
import random
from dataclasses import dataclass
import pygame

class Deck:
    def __init__(self):
        self.cards = []
        for suit in ['Hearts', 'Diamonds', 'Clubs', 'Spades']:
            for rank in ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King', 'Ace']:
                self.cards.append(f'{rank} of {suit}')
        random.shuffle(self.cards)

class Shoe:
    def __init__(self, num_decks=6):
        self.cards = []
        for _ in range(num_decks):
            self.cards.extend(Deck().cards)
        random.shuffle(self.cards)
    def draw_card(self):
        return self.cards.pop()

def main():
    shoe = Shoe()
    print("Welcome to the Blackjack Card Counting Trainer!")
    print("Type 'exit' to quit.")
    while True:
        card = shoe.draw_card()
        print(f"Card drawn: {card}")
        user_input = input("Enter the current count (or 'exit' to quit): ")
        if user_input.lower() == 'exit':
            break
        # Here you would implement logic to check the user's input against the actual count
        # For simplicity, this example does not include the counting logic
        
