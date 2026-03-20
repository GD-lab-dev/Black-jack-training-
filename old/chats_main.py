import os
import sys
import random
from dataclasses import dataclass

import pygame

# ---------- Paths / constants ----------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "img")  # card PNGs live in ./img


# ---------- Game logic (no GUI) ----------

@dataclass
class Card:
    rank: str   # "2".."10", "J", "Q", "K", "A"
    suit: str   # "hearts", "diamonds", "clubs", "spades"

    @property
    def value(self) -> int:
        if self.rank in ("J", "Q", "K"):
            return 10
        if self.rank == "A":
            return 11
        return int(self.rank)


class Deck:
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    suits = ["hearts", "diamonds", "clubs", "spades"]

    def __init__(self, num_decks: int = 6):
        self.num_decks = num_decks
        self._build()

    def _build(self):
        self.cards = [
            Card(rank, suit)
            for _ in range(self.num_decks)
            for suit in self.suits
            for rank in self.ranks
        ]
        random.shuffle(self.cards)

    def deal(self) -> Card:
        if not self.cards:
            self._build()
        return self.cards.pop()


class Hand:
    def __init__(self, owner: str):
        self.owner = owner
        self.cards: list[Card] = []

    def add_card(self, card: Card):
        self.cards.append(card)

    @property
    def value(self) -> int:
        total = sum(c.value for c in self.cards)
        aces = sum(1 for c in self.cards if c.rank == "A")
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return total

    def is_bust(self) -> bool:
        return self.value > 21


class BlackjackGame:
    def __init__(self, num_decks: int = 6):
        self.num_decks = num_decks
        self.deck = Deck(num_decks)
        self.player = Hand("Player")
        self.dealer = Hand("Dealer")

    def start_round(self):
        self.player = Hand("Player")
        self.dealer = Hand("Dealer")
        if len(self.deck.cards) < 15:
            self.deck = Deck(self.num_decks)

        # Standard dealing order:
        # Player card, Dealer upcard, Player card, Dealer hole card
        self.player.add_card(self.deck.deal())
        self.dealer.add_card(self.deck.deal())   # upcard
        self.player.add_card(self.deck.deal())
        self.dealer.add_card(self.deck.deal())   # hole card

    def player_hit(self, hand: Hand):
        hand.add_card(self.deck.deal())

    def dealer_play(self):
        while self.dealer.value < 17:
            self.dealer.add_card(self.deck.deal())

    def hand_outcome(self, hand: Hand) -> str:
        """Outcome of ONE hand vs dealer."""
        if hand.is_bust():
            return "Bust"
        if self.dealer.is_bust():
            return "Win"
        if hand.value > self.dealer.value:
            return "Win"
        if hand.value < self.dealer.value:
            return "Lose"
        return "Push"


# ---------- Basic strategy helper functions ----------

def dealer_upcard_value(card: Card) -> int:
    if card.rank == "A":
        return 11
    if card.rank in ("J", "Q", "K"):
        return 10
    return int(card.rank)


def is_pair(hand: Hand) -> bool:
    return len(hand.cards) == 2 and hand.cards[0].rank == hand.cards[1].rank


def is_soft(hand: Hand) -> bool:
    """Soft hand = at least one Ace counted as 11 in current total."""
    total = sum(c.value for c in hand.cards)
    aces = sum(1 for c in hand.cards if c.rank == "A")
    return aces > 0 and total <= 21


def basic_strategy_advice(hand: Hand, dealer_card: Card) -> str:
    """
    Basic strategy (multi-deck, dealer stands on soft 17, no surrender).
    Returns a text hint (Hit/Stand/Double/Split suggestions).
    """
    up = dealer_upcard_value(dealer_card)
    total = hand.value

    # --- Pairs ---
    if is_pair(hand) and len(hand.cards) == 2:
        r = hand.cards[0].rank
        pair_val = 10 if r in ("10", "J", "Q", "K") else (11 if r == "A" else int(r))

        if pair_val == 11:           # A,A
            return "Split Aces (otherwise Hit)."
        if pair_val == 10:           # 10,10
            return "Stand (never split 10s)."
        if pair_val == 9:
            if up in (7, 10, 11):
                return "Stand (don't split 9s vs 7, 10, A)."
            return "Split 9s (otherwise Stand)."
        if pair_val == 8:
            return "Always split 8s."
        if pair_val == 7:
            if 2 <= up <= 7:
                return "Split 7s (otherwise Hit)."
            return "Hit."
        if pair_val == 6:
            if 2 <= up <= 6:
                return "Split 6s (otherwise Hit)."
            return "Hit."
        if pair_val in (2, 3):
            if 2 <= up <= 7:
                return "Split 2s/3s vs 2–7 (otherwise Hit)."
            return "Hit."
        if pair_val == 4:
            if up in (5, 6):
                return "Split 4s vs 5–6 (otherwise Hit)."
            return "Hit."
        # 5,5 is treated as hard 10 below

    # --- Soft totals ---
    if is_soft(hand):
        if total in (13, 14):  # A2–A3
            if up in (5, 6):
                return "Double (otherwise Hit) with A2–A3."
            return "Hit."
        if total in (15, 16):  # A4–A5
            if 4 <= up <= 6:
                return "Double (otherwise Hit) with A4–A5."
            return "Hit."
        if total == 17:        # A6
            if 3 <= up <= 6:
                return "Double (otherwise Hit) with A6."
            return "Hit."
        if total == 18:        # A7
            if 3 <= up <= 6:
                return "Double (otherwise Stand) with A7."
            if up in (2, 7, 8):
                return "Stand with A7."
            return "Hit with A7 vs 9, 10, A."
        # Soft 19+
        return "Stand (soft 19+)."

    # --- Hard totals ---
    if total <= 8:
        return "Hit (8 or less)."
    if total == 9:
        if 3 <= up <= 6:
            return "Double (otherwise Hit) on 9."
        return "Hit on 9."
    if total == 10:
        if 2 <= up <= 9:
            return "Double (otherwise Hit) on 10."
        return "Hit vs 10 or A with 10."
    if total == 11:
        if up != 11:
            return "Double (otherwise Hit) on 11."
        return "Hit vs Ace with 11."
    if total == 12:
        if 4 <= up <= 6:
            return "Stand on 12 vs 4–6."
        return "Hit on 12 vs 2,3,7+."
    if 13 <= total <= 16:
        if 2 <= up <= 6:
            return f"Stand on {total} vs 2–6."
        return f"Hit on {total} vs 7+."
    # 17+
    return "Stand (17 or more)."


# ---------- Image loading / drawing ----------

def load_card_images() -> dict:
    """
    Load card PNGs from ./img into a dict keyed by (rank, suit),
    plus "BACK" for back_of_card.png and "STRAT" for basic_strategy.png.
    """
    images: dict[tuple[str, str] | str, pygame.Surface] = {}

    rank_from_name = {
        "jack": "J",
        "queen": "Q",
        "king": "K",
        "ace": "A",
    }

    print("Loading images from:", IMAGE_DIR)
    try:
        files = os.listdir(IMAGE_DIR)
    except FileNotFoundError:
        print("ERROR: img folder not found at", IMAGE_DIR)
        return images

    for fname in files:
        if not fname.lower().endswith(".png"):
            continue

        base = fname[:-4]  # strip ".png"

        if base in ("back_of_card", "basic_strategy"):
            # handled separately below
            continue

        if "joker" in base.lower():
            continue

        # handle e.g. "king_of_spades2" -> "king_of_spades"
        stripped_base = base[:-1] if base.endswith("2") else base

        if "_of_" not in stripped_base:
            continue

        rank_part, suit_part = stripped_base.split("_of_", 1)
        rank = rank_from_name.get(rank_part, rank_part)  # "jack" -> "J"
        suit = suit_part  # hearts/diamonds/clubs/spades

        path = os.path.join(IMAGE_DIR, fname)
        try:
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, (80, 120))
        except Exception as e:
            print("Failed to load", path, "->", e)
            continue

        images[(rank, suit)] = img

    # back of card
    back_path = os.path.join(IMAGE_DIR, "back_of_card.png")
    if os.path.exists(back_path):
        try:
            back_img = pygame.image.load(back_path).convert_alpha()
            back_img = pygame.transform.smoothscale(back_img, (80, 120))
            images["BACK"] = back_img
        except Exception as e:
            print("Failed to load back_of_card.png:", e)
    else:
        print("back_of_card.png not found.")

    # basic strategy chart
    strat_path = os.path.join(IMAGE_DIR, "basic_strategy.png")
    if os.path.exists(strat_path):
        try:
            strat_img = pygame.image.load(strat_path).convert_alpha()
            strat_img = pygame.transform.smoothscale(strat_img, (350, 350))
            images["STRAT"] = strat_img
        except Exception as e:
            print("Failed to load basic_strategy.png:", e)
    else:
        print("basic_strategy.png not found.")

    print(f"Loaded {len(images)} images (including BACK/STRAT if present).")
    return images


def draw_hand(
    screen: pygame.Surface,
    images: dict,
    hand: Hand,
    x: int,
    y: int,
    hide_hole: bool = False,
):
    """
    Draws cards horizontally with spacing.
    If hide_hole=True, the *second* card (index 1) is drawn as back-of-card,
    so card[0] remains the visible upcard used for strategy.
    """
    spacing = 30

    for i, card in enumerate(hand.cards):
        pos = (x + i * spacing, y)

        # hide the hole card (second card)
        if hide_hole and i == 1:
            back = images.get("BACK")
            if back:
                screen.blit(back, pos)
            else:
                pygame.draw.rect(screen, (0, 0, 80), (*pos, 80, 120))
                pygame.draw.rect(screen, (255, 255, 255), (*pos, 80, 120), 2)
            continue

        img = images.get((card.rank, card.suit))
        if img is not None:
            screen.blit(img, pos)
        else:
            pygame.draw.rect(screen, (255, 255, 255), (*pos, 80, 120))
            pygame.draw.rect(screen, (0, 0, 0), (*pos, 80, 120), 2)


# ---------- Utility: ask for decks ----------

def ask_num_decks() -> int:
    try:
        raw = input("How many decks do you want to use? (1–8, default 6): ").strip()
        if not raw:
            return 6
        n = int(raw)
        if n < 1:
            n = 1
        if n > 8:
            n = 8
        return n
    except Exception:
        return 6


# ---------- Pygame main loop ----------

def main():
    # get number of decks before pygame grabs the terminal
    num_decks = ask_num_decks()
    print(f"Using {num_decks} deck(s).")

    pygame.init()
    WIDTH, HEIGHT = 900, 720

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Blackjack Trainer")

    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 32)
    small_font = pygame.font.SysFont(None, 24)

    card_images = load_card_images()

    game = BlackjackGame(num_decks)
    game.start_round()

    # multiple hands state
    player_hands: list[Hand] = [game.player]   # first hand is game.player
    hand_done: list[bool] = [False]
    hand_doubled: list[bool] = [False]
    hand_results: list[str] = [""]

    current_hand_idx = 0
    player_turn = True
    dealer_done = False
    round_over = False

    status_message = "H=Hit, S=Stand, D=Double, P=Split, I=Insurance (if offered)"
    strategy_message = ""
    insurance_message = ""

    # insurance state
    insurance_offered = game.dealer.cards[0].rank == "A"
    insurance_taken = False
    insurance_resolved = False

    running = True
    while running:
        # --- events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                # Only accept action keys while player_turn and not round_over
                if player_turn and not round_over:
                    active_hand = player_hands[current_hand_idx]

                    # Hit
                    if event.key == pygame.K_h:
                        game.player_hit(active_hand)
                        # if bust, mark this hand done and go to next / dealer
                        if active_hand.is_bust():
                            hand_done[current_hand_idx] = True

                            # move to next unfinished hand if any
                            moved = False
                            for i in range(current_hand_idx + 1, len(player_hands)):
                                if not hand_done[i]:
                                    current_hand_idx = i
                                    moved = True
                                    break

                            if not moved:
                                # all hands done -> dealer plays regardless of busts
                                player_turn = False
                                if not dealer_done:
                                    game.dealer_play()
                                    dealer_done = True
                                round_over = True
                                status_message = "Round complete. SPACE = new round."
                                strategy_message = ""

                                # resolve insurance
                                if insurance_offered and not insurance_resolved and len(game.dealer.cards) >= 2:
                                    tmp = Hand("tmp")
                                    tmp.add_card(game.dealer.cards[0])
                                    tmp.add_card(game.dealer.cards[1])
                                    if tmp.value == 21:
                                        if insurance_taken:
                                            insurance_message = "Insurance would WIN here."
                                        else:
                                            insurance_message = "Insurance would win here (but still -EV overall)."
                                    else:
                                        if insurance_taken:
                                            insurance_message = "Insurance would LOSE here. (Basic strategy says skip.)"
                                        else:
                                            insurance_message = "Insurance would lose here. (Correct to skip.)"
                                    insurance_resolved = True

                    # Stand
                    elif event.key == pygame.K_s:
                        hand_done[current_hand_idx] = True

                        # move to next unfinished hand
                        moved = False
                        for i in range(current_hand_idx + 1, len(player_hands)):
                            if not hand_done[i]:
                                current_hand_idx = i
                                moved = True
                                break

                        if not moved:
                            # all hands done -> dealer plays
                            player_turn = False
                            if not dealer_done:
                                game.dealer_play()
                                dealer_done = True
                            round_over = True
                            status_message = "Round complete. SPACE = new round."
                            strategy_message = ""

                            # resolve insurance
                            if insurance_offered and not insurance_resolved and len(game.dealer.cards) >= 2:
                                tmp = Hand("tmp")
                                tmp.add_card(game.dealer.cards[0])
                                tmp.add_card(game.dealer.cards[1])
                                if tmp.value == 21:
                                    if insurance_taken:
                                        insurance_message = "Insurance would WIN here."
                                    else:
                                        insurance_message = "Insurance would win here (but still -EV overall)."
                                else:
                                    if insurance_taken:
                                        insurance_message = "Insurance would LOSE here. (Basic strategy says skip.)"
                                    else:
                                        insurance_message = "Insurance would lose here. (Correct to skip.)"
                                insurance_resolved = True

                    # Double (only if exactly 2 cards)
                    elif event.key == pygame.K_d:
                        if len(active_hand.cards) == 2 and not hand_doubled[current_hand_idx]:
                            game.player_hit(active_hand)  # exactly one card
                            hand_doubled[current_hand_idx] = True
                            hand_done[current_hand_idx] = True

                            # move to next unfinished hand
                            moved = False
                            for i in range(current_hand_idx + 1, len(player_hands)):
                                if not hand_done[i]:
                                    current_hand_idx = i
                                    moved = True
                                    break

                            if not moved:
                                # all hands done -> dealer plays
                                player_turn = False
                                if not dealer_done:
                                    game.dealer_play()
                                    dealer_done = True
                                round_over = True
                                status_message = "You doubled. Round complete. SPACE = new round."
                                strategy_message = ""

                                # resolve insurance
                                if insurance_offered and not insurance_resolved and len(game.dealer.cards) >= 2:
                                    tmp = Hand("tmp")
                                    tmp.add_card(game.dealer.cards[0])
                                    tmp.add_card(game.dealer.cards[1])
                                    if tmp.value == 21:
                                        if insurance_taken:
                                            insurance_message = "Insurance would WIN here."
                                        else:
                                            insurance_message = "Insurance would win here (but still -EV overall)."
                                    else:
                                        if insurance_taken:
                                            insurance_message = "Insurance would LOSE here. (Basic strategy says skip.)"
                                        else:
                                            insurance_message = "Insurance would lose here. (Correct to skip.)"
                                    insurance_resolved = True

                    # Split (only once, only if pair, only if we have 1 hand)
                    elif event.key == pygame.K_p:
                        if (
                            len(player_hands) < 2
                            and len(active_hand.cards) == 2
                            and active_hand.cards[0].rank == active_hand.cards[1].rank
                        ):
                            # perform split: original hand keeps first card; new hand gets second card
                            first_card = active_hand.cards[0]
                            second_card = active_hand.cards[1]
                            active_hand.cards = [first_card]
                            new_hand = Hand("Player (split)")
                            new_hand.add_card(second_card)

                            # deal one card to each from the deck
                            game.player_hit(active_hand)
                            game.player_hit(new_hand)

                            player_hands.append(new_hand)
                            hand_done.append(False)
                            hand_doubled.append(False)
                            hand_results.append("")

                            status_message = "Split performed. H/S/D to play each hand. SPACE = new round after dealer."

                    # Insurance (if offered)
                    elif event.key == pygame.K_i:
                        if insurance_offered and not insurance_taken:
                            insurance_taken = True
                            insurance_message = "Insurance taken (trainer: basic strategy says DON'T)."

                # New round
                if event.key == pygame.K_SPACE and round_over:
                    game.start_round()
                    player_hands = [game.player]
                    hand_done = [False]
                    hand_doubled = [False]
                    hand_results = [""]
                    current_hand_idx = 0

                    player_turn = True
                    dealer_done = False
                    round_over = False

                    status_message = "H=Hit, S=Stand, D=Double, P=Split, I=Insurance (if offered)"
                    strategy_message = ""
                    insurance_message = ""
                    insurance_offered = game.dealer.cards[0].rank == "A"
                    insurance_taken = False
                    insurance_resolved = False

        # --- after round over, compute per-hand results if dealer is done ---
        if round_over and dealer_done:
            for i, h in enumerate(player_hands):
                hand_results[i] = game.hand_outcome(h)

        # --- update basic strategy hint (for active hand only) ---
        if player_turn and not round_over and len(game.dealer.cards) >= 1:
            active_hand = player_hands[current_hand_idx]
            if len(active_hand.cards) >= 2:
                advice = basic_strategy_advice(active_hand, game.dealer.cards[0])
                strategy_message = f"Basic strategy (Hand {current_hand_idx+1}): {advice}"

        # --- drawing ---
        screen.fill((0, 100, 0))  # green felt

        # Dealer hand (hide hole card while player's turn)
        hide_dealer = player_turn and not round_over
        draw_hand(screen, card_images, game.dealer, x=150, y=80, hide_hole=hide_dealer)

        # Dealer label
        dealer_label = "Dealer"
        if not hide_dealer:
            dealer_label += f" ({game.dealer.value})"
        dealer_text = font.render(dealer_label, True, (255, 255, 255))
        screen.blit(dealer_text, (50, 40))

        # Player hands
        for i, h in enumerate(player_hands):
            y = 310 + i * 140
            draw_hand(screen, card_images, h, x=150, y=y, hide_hole=False)

            label = f"Hand {i+1} ({h.value})"
            if round_over and dealer_done:
                label += f" - {hand_results[i]}"
            elif h.is_bust():
                label += " - Bust"

            color = (255, 255, 0) if (i == current_hand_idx and player_turn and not round_over) else (255, 255, 255)
            label_text = font.render(label, True, color)
            screen.blit(label_text, (50, y - 25))

        # Status and info
        status_text = font.render(status_message, True, (255, 255, 0))
        strategy_text = small_font.render(strategy_message, True, (0, 255, 255))
        insurance_text = small_font.render(insurance_message, True, (255, 200, 200))
        decks_text = small_font.render(f"Decks: {num_decks}", True, (255, 255, 255))

        screen.blit(status_text, (50, 560))
        screen.blit(strategy_text, (50, 590))
        screen.blit(insurance_text, (50, 620))
        screen.blit(decks_text, (WIDTH - decks_text.get_width() - 10, 10))

        # Draw strategy chart if available
        strat_img = card_images.get("STRAT")
        if strat_img:
            screen.blit(strat_img, (525, 125))  # adjust position if you want

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
