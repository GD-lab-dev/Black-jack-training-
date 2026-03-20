import random
import sys
from dataclasses import dataclass
from pathlib import Path

import pygame


# =========================================================
# CONFIG
# =========================================================
WIDTH, HEIGHT = 1400, 900
FPS = 60
IMG_DIR = Path("img")

TABLE_COLOR = (18, 102, 56)
PANEL_COLOR = (20, 20, 20)
TEXT_COLOR = (245, 245, 245)
BUTTON_COLOR = (45, 45, 45)
BUTTON_HOVER = (75, 75, 75)
BORDER_COLOR = (190, 190, 190)

GREEN = (90, 220, 120)
RED = (230, 90, 90)
YELLOW = (235, 210, 90)
BLUE = (120, 170, 255)

SUITS = ["clubs", "diamonds", "hearts", "spades"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

BLACKJACK_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10, "A": 11
}

COUNT_VALUES = {
    "2": 1, "3": 1, "4": 1, "5": 1, "6": 1,
    "7": 0, "8": 0, "9": 0,
    "10": -1, "J": -1, "Q": -1, "K": -1, "A": -1
}


# =========================================================
# CARD / SHOE LOGIC
# =========================================================
@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    @property
    def blackjack_value(self) -> int:
        return BLACKJACK_VALUES[self.rank]

    @property
    def count_value(self) -> int:
        return COUNT_VALUES[self.rank]

    def image_name(self) -> str:
        rank_map = {
            "A": "ace",
            "J": "jack",
            "Q": "queen",
            "K": "king",
        }
        image_rank = rank_map.get(self.rank, self.rank)

        normal = IMG_DIR / f"{image_rank}_of_{self.suit}.png"
        if normal.exists():
            return normal.name

        # Handles your ace_of_spades2.png case
        if self.rank == "A" and self.suit == "spades":
            odd = IMG_DIR / "ace_of_spades2.png"
            if odd.exists():
                return odd.name

        return normal.name


class Shoe:
    def __init__(self, num_decks: int = 6, penetration: float = 0.75):
        self.num_decks = num_decks
        self.penetration = penetration
        self.cards: list[Card] = []
        self.running_count = 0
        self.initial_size = 52 * num_decks
        self.shuffle()

    def build_shoe(self) -> list[Card]:
        cards = []
        for _ in range(self.num_decks):
            for suit in SUITS:
                for rank in RANKS:
                    cards.append(Card(rank, suit))
        return cards

    def shuffle(self) -> None:
        self.cards = self.build_shoe()
        random.shuffle(self.cards)
        self.running_count = 0
        self.initial_size = len(self.cards)

    def draw(self) -> Card:
        if not self.cards:
            self.shuffle()

        card = self.cards.pop()
        self.running_count += card.count_value
        return card

    def decks_remaining(self) -> float:
        return max(len(self.cards) / 52, 0.25)

    def true_count(self) -> float:
        return self.running_count / self.decks_remaining()

    def rounded_true_count(self) -> int:
        return round(self.true_count())

    def needs_reshuffle(self) -> bool:
        used = self.initial_size - len(self.cards)
        return (used / self.initial_size) >= self.penetration


def hand_value(hand: list[Card]) -> int:
    total = sum(card.blackjack_value for card in hand)
    aces = sum(1 for card in hand if card.rank == "A")

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    return total


def is_blackjack(hand: list[Card]) -> bool:
    return len(hand) == 2 and hand_value(hand) == 21


def can_split(hand: list[Card]) -> bool:
    return len(hand) == 2 and hand[0].rank == hand[1].rank


def is_soft_hand(hand: list[Card]) -> bool:
    total = sum(card.blackjack_value for card in hand)
    aces = sum(1 for card in hand if card.rank == "A")

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    return any(card.rank == "A" for card in hand) and total != sum(card.blackjack_value for card in hand)


# =========================================================
# UI HELPERS
# =========================================================
class Button:
    def __init__(self, text: str, rect: pygame.Rect):
        self.text = text
        self.rect = rect

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, mouse_pos, active: bool = False):
        hovered = self.rect.collidepoint(mouse_pos)
        color = BLUE if active else (BUTTON_HOVER if hovered else BUTTON_COLOR)
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        pygame.draw.rect(surface, BORDER_COLOR, self.rect, width=2, border_radius=12)

        label = font.render(self.text, True, TEXT_COLOR)
        label_rect = label.get_rect(center=self.rect.center)
        surface.blit(label, label_rect)

    def draw_disabled(self, surface: pygame.Surface, font: pygame.font.Font):
        pygame.draw.rect(surface, (70, 70, 70), self.rect, border_radius=12)
        pygame.draw.rect(surface, (110, 110, 110), self.rect, width=2, border_radius=12)
        label = font.render(self.text, True, (160, 160, 160))
        surface.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, event: pygame.event.Event) -> bool:
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


class InputOverlay:
    def __init__(self):
        self.active = False
        self.prompt = ""
        self.user_text = ""
        self.answer_type = ""
        self.feedback = ""
        self.feedback_color = TEXT_COLOR

    def open(self, prompt: str, answer_type: str):
        self.active = True
        self.prompt = prompt
        self.user_text = ""
        self.answer_type = answer_type
        self.feedback = ""
        self.feedback_color = TEXT_COLOR

    def close(self):
        self.active = False
        self.prompt = ""
        self.user_text = ""
        self.answer_type = ""
        self.feedback = ""

    def handle_event(self, event: pygame.event.Event):
        if not self.active:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                text = self.user_text.strip()
                if text in {"q", "quit", "exit"}:
                    self.close()
                    return "cancel"
                try:
                    return int(text)
                except ValueError:
                    self.feedback = "Enter a whole number."
                    self.feedback_color = RED

            elif event.key == pygame.K_BACKSPACE:
                self.user_text = self.user_text[:-1]

            elif event.unicode in "-0123456789":
                self.user_text += event.unicode

        return None

    def draw(self, surface: pygame.Surface, fonts: dict, size: tuple[int, int]):
        if not self.active:
            return

        w, h = size
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        box_w = min(640, w - 80)
        box_h = 220
        box = pygame.Rect((w - box_w) // 2, (h - box_h) // 2, box_w, box_h)

        pygame.draw.rect(surface, PANEL_COLOR, box, border_radius=16)
        pygame.draw.rect(surface, BORDER_COLOR, box, width=2, border_radius=16)

        prompt = fonts["large"].render(self.prompt, True, TEXT_COLOR)
        surface.blit(prompt, (box.x + 24, box.y + 24))

        input_rect = pygame.Rect(box.x + 24, box.y + 92, box.w - 48, 52)
        pygame.draw.rect(surface, (35, 35, 35), input_rect, border_radius=10)
        pygame.draw.rect(surface, (160, 160, 160), input_rect, width=2, border_radius=10)

        entered = fonts["large"].render(self.user_text or "|", True, YELLOW)
        surface.blit(entered, (input_rect.x + 14, input_rect.y + 9))

        help_text = fonts["small"].render("Press Enter to submit", True, TEXT_COLOR)
        surface.blit(help_text, (box.x + 24, box.y + 156))

        if self.feedback:
            fb = fonts["small"].render(self.feedback, True, self.feedback_color)
            surface.blit(fb, (box.x + 24, box.y + 184))


def load_card_images(card_w: int, card_h: int) -> dict[str, pygame.Surface]:
    images = {}
    if not IMG_DIR.exists():
        return images

    for path in IMG_DIR.glob("*.png"):
        try:
            img = pygame.image.load(str(path)).convert_alpha()
            img = pygame.transform.smoothscale(img, (card_w, card_h))
            images[path.name] = img
        except pygame.error:
            pass
    return images


# =========================================================
# GAME
# =========================================================
class BlackjackTrainerGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Blackjack Card Counting Trainer")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()

        # Home-page settings
        self.selected_decks = 6
        self.selected_dealer_rule = "H17"  # "H17" or "S17"

        # Active session settings
        self.strategy_mode = self.selected_dealer_rule
        self.shoe = Shoe(num_decks=self.selected_decks, penetration=0.75)

        self.player_hands: list[list[Card]] = []
        self.active_hand_index = 0
        self.dealer_hand: list[Card] = []

        self.message = "Click Next Hand to begin."
        self.message_color = TEXT_COLOR

        self.hands_played = 0
        self.checks_correct = 0
        self.checks_total = 0
        self.last_check = "None"

        self.basic_strategy_correct = 0
        self.basic_strategy_total = 0
        self.last_strategy_result = "None"

        self.visible_counts = False
        self.show_strategy_chart = False

        self.hand_over = True
        self.awaiting_new_hand = True

        self.quiz_overlay = InputOverlay()
        self.pending_quiz_answer = None
        self.cards_until_quiz = random.randint(4, 9)

        self.game_state = "home"

        self.card_size = (110, 160)
        self.images = load_card_images(*self.card_size)

        self.strategy_images = {}
        self.load_strategy_images()

        self.fonts = self.make_fonts()
        self.buttons = {}
        self.home_buttons = {}
        self.update_layout(*self.screen.get_size())

    # -------------------------
    # Loading / Layout
    # -------------------------
    def make_fonts(self):
        return {
            "small": pygame.font.SysFont("arial", 16),
            "medium": pygame.font.SysFont("arial", 24),
            "large": pygame.font.SysFont("arial", 34),
            "title": pygame.font.SysFont("arial", 48, bold=True),
        }

    def load_strategy_images(self):
        self.strategy_images = {}
        for name in ["H17-Basic-Strategy.png", "S17-Basic-Strategy.png"]:
            path = IMG_DIR / name
            if path.exists():
                try:
                    img = pygame.image.load(str(path)).convert_alpha()
                    self.strategy_images[name] = img
                except pygame.error:
                    pass

    def current_strategy_chart_name(self) -> str:
        return "H17-Basic-Strategy.png" if self.strategy_mode == "H17" else "S17-Basic-Strategy.png"

    def update_layout(self, w: int, h: int):
        panel_h = max(200, h // 4)
        button_y = h - panel_h - 68
        button_w = 130
        button_h = 48
        gap = 14
        total_w = button_w * 6 + gap * 5
        start_x = max(20, (w - total_w) // 2)

        self.buttons = {
            "hit": Button("Hit", pygame.Rect(start_x, button_y, button_w, button_h)),
            "stand": Button("Stand", pygame.Rect(start_x + (button_w + gap), button_y, button_w, button_h)),
            "split": Button("Split", pygame.Rect(start_x + 2 * (button_w + gap), button_y, button_w, button_h)),
            "next": Button("Next Hand", pygame.Rect(start_x + 3 * (button_w + gap), button_y, button_w, button_h)),
            "toggle_count": Button("Count", pygame.Rect(start_x + 4 * (button_w + gap), button_y, button_w, button_h)),
            "toggle_chart": Button("Chart", pygame.Rect(start_x + 5 * (button_w + gap), button_y, button_w, button_h)),
        }

        home_button_w = 220
        home_button_h = 60
        small_button_w = 100
        small_button_h = 50
        center_x = w // 2

        self.home_buttons = {
            "start": Button("Start Trainer", pygame.Rect(center_x - 110, h // 2 + 140, home_button_w, home_button_h)),
            "quit": Button("Quit", pygame.Rect(center_x - 110, h // 2 + 215, home_button_w, home_button_h)),
            "deck_4": Button("4 Deck", pygame.Rect(center_x - 170, h // 2 - 20, small_button_w, small_button_h)),
            "deck_6": Button("6 Deck", pygame.Rect(center_x - 50, h // 2 - 20, small_button_w, small_button_h)),
            "deck_8": Button("8 Deck", pygame.Rect(center_x + 70, h // 2 - 20, small_button_w, small_button_h)),
            "rule_h17": Button("Dealer Hits Soft 17", pygame.Rect(center_x - 210, h // 2 + 50, 200, 50)),
            "rule_s17": Button("Dealer Stands Soft 17", pygame.Rect(center_x + 10, h // 2 + 50, 210, 50)),
        }

        card_w = max(72, min(132, w // 11))
        card_h = int(card_w * 1.45)
        if (card_w, card_h) != self.card_size:
            self.card_size = (card_w, card_h)
            self.images = load_card_images(card_w, card_h)

    def get_table_area(self, w: int, h: int) -> pygame.Rect:
        panel_h = max(200, h // 4)
        strategy_w = min(420, max(260, w // 3)) if self.show_strategy_chart else 0
        margin = 24
        return pygame.Rect(
            margin,
            margin,
            w - strategy_w - margin * 2,
            h - panel_h - margin * 2
        )

    # -------------------------
    # Drawing
    # -------------------------
    def draw_card_surface(self, card: Card | None, hidden=False) -> pygame.Surface:
        filename = "back_of_card.png" if hidden else (card.image_name() if card else "")
        img = self.images.get(filename)

        if img:
            return img

        surf = pygame.Surface(self.card_size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (245, 245, 245), surf.get_rect(), border_radius=10)
        pygame.draw.rect(surf, (50, 50, 50), surf.get_rect(), width=2, border_radius=10)

        label_text = "BACK" if hidden else (f"{card.rank} {card.suit[0].upper()}" if card else "?")
        label = self.fonts["medium"].render(label_text, True, (30, 30, 30))
        label_rect = label.get_rect(center=surf.get_rect().center)
        surf.blit(label, label_rect)
        return surf

    def draw_hand(self, hand: list[Card], x: int, y: int, hide_second=False):
        spacing = int(self.card_size[0] * 0.42)
        for i, card in enumerate(hand):
            hidden = hide_second and i == 1
            img = self.draw_card_surface(card, hidden=hidden)
            self.screen.blit(img, (x + i * spacing, y))

    def draw_strategy_chart(self, w: int, h: int):
        if not self.show_strategy_chart:
            return

        name = self.current_strategy_chart_name()
        img = self.strategy_images.get(name)
        if not img:
            return

        panel_h = max(200, h // 4)
        chart_w = min(420, max(260, w // 3))
        chart_x = w - chart_w - 20
        chart_y = 20
        chart_h = h - panel_h - 40

        panel_rect = pygame.Rect(chart_x, chart_y, chart_w, chart_h)
        pygame.draw.rect(self.screen, PANEL_COLOR, panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, BORDER_COLOR, panel_rect, width=2, border_radius=12)

        title = self.fonts["small"].render(f"Basic Strategy ({self.strategy_mode})", True, TEXT_COLOR)
        self.screen.blit(title, (chart_x + 12, chart_y + 10))

        available_w = chart_w - 24
        available_h = chart_h - 48

        img_w, img_h = img.get_size()
        scale = min(available_w / img_w, available_h / img_h)
        new_size = (max(1, int(img_w * scale)), max(1, int(img_h * scale)))
        scaled = pygame.transform.smoothscale(img, new_size)

        img_x = chart_x + (chart_w - scaled.get_width()) // 2
        img_y = chart_y + 38
        self.screen.blit(scaled, (img_x, img_y))

    def draw_home(self):
        w, h = self.screen.get_size()
        self.screen.fill(TABLE_COLOR)

        title = self.fonts["title"].render("Blackjack Trainer", True, TEXT_COLOR)
        subtitle = self.fonts["medium"].render("Choose your rules, then start", True, TEXT_COLOR)

        self.screen.blit(title, title.get_rect(center=(w // 2, h // 4)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(w // 2, h // 4 + 50)))

        deck_label = self.fonts["medium"].render("Shoe Size", True, TEXT_COLOR)
        rule_label = self.fonts["medium"].render("Dealer Rule", True, TEXT_COLOR)

        self.screen.blit(deck_label, deck_label.get_rect(center=(w // 2, h // 2 - 55)))
        self.screen.blit(rule_label, rule_label.get_rect(center=(w // 2, h // 2 + 15)))

        mouse_pos = pygame.mouse.get_pos()

        for key, button in self.home_buttons.items():
            selected = (
                (key == "deck_4" and self.selected_decks == 4) or
                (key == "deck_6" and self.selected_decks == 6) or
                (key == "deck_8" and self.selected_decks == 8) or
                (key == "rule_h17" and self.selected_dealer_rule == "H17") or
                (key == "rule_s17" and self.selected_dealer_rule == "S17")
            )
            button.draw(self.screen, self.fonts["small"], mouse_pos, active=selected)

        info_lines = [
            f"Selected shoe: {self.selected_decks} decks",
            f"Selected rule: {self.selected_dealer_rule}",
            "These rules stay active until you return here and change them.",
            "Press Enter or click Start Trainer to begin.",
        ]

        for i, line in enumerate(info_lines):
            txt = self.fonts["small"].render(line, True, TEXT_COLOR)
            self.screen.blit(txt, txt.get_rect(center=(w // 2, h // 2 + 315 + i * 24)))

        pygame.display.flip()

    def draw_game(self):
        w, h = self.screen.get_size()
        self.screen.fill(TABLE_COLOR)

        table_area = self.get_table_area(w, h)
        panel_h = max(200, h // 4)

        title = self.fonts["title"].render("Blackjack Trainer", True, TEXT_COLOR)
        self.screen.blit(title, (table_area.x, table_area.y))

        dealer_label_y = table_area.y + 76
        dealer_cards_y = dealer_label_y + 48

        dealer_text = f"Dealer  Total: {hand_value(self.dealer_hand)}" if self.hand_over and self.dealer_hand else "Dealer"
        dealer_label = self.fonts["large"].render(dealer_text, True, TEXT_COLOR)
        self.screen.blit(dealer_label, (table_area.x, dealer_label_y))
        self.draw_hand(self.dealer_hand, table_area.x, dealer_cards_y, hide_second=not self.hand_over)

        player_block_y = dealer_cards_y + self.card_size[1] + 58
        hand_gap_y = self.card_size[1] + 90

        for idx, hand in enumerate(self.player_hands):
            label_y = player_block_y + idx * hand_gap_y
            cards_y = label_y + 42

            total = hand_value(hand) if hand else 0
            prefix = ">> " if idx == self.active_hand_index and not self.hand_over else ""
            hand_label = self.fonts["large"].render(
                f"{prefix}Player Hand {idx + 1}  Total: {total}",
                True,
                YELLOW if idx == self.active_hand_index and not self.hand_over else TEXT_COLOR
            )
            self.screen.blit(hand_label, (table_area.x, label_y))
            self.draw_hand(hand, table_area.x, cards_y)

        if self.player_hands:
            last_hand_y = player_block_y + (len(self.player_hands) - 1) * hand_gap_y
            msg_y = last_hand_y + self.card_size[1] + 68
        else:
            msg_y = player_block_y + 40

        msg = self.fonts["medium"].render(self.message, True, self.message_color)
        self.screen.blit(msg, (table_area.x, msg_y))

        mouse_pos = pygame.mouse.get_pos()
        split_allowed = (
            not self.hand_over
            and len(self.player_hands) == 1
            and can_split(self.player_hands[0])
        )

        for key, button in self.buttons.items():
            if key == "split" and not split_allowed:
                button.draw_disabled(self.screen, self.fonts["small"])
            else:
                button.draw(self.screen, self.fonts["small"], mouse_pos)

        panel_rect = pygame.Rect(0, h - panel_h, w, panel_h)
        pygame.draw.rect(self.screen, PANEL_COLOR, panel_rect)
        pygame.draw.line(self.screen, BORDER_COLOR, (0, panel_rect.y), (w, panel_rect.y), 2)

        count_accuracy = (self.checks_correct / self.checks_total * 100) if self.checks_total else 0.0
        strategy_accuracy = (
            (self.basic_strategy_correct / self.basic_strategy_total) * 100
            if self.basic_strategy_total else 0.0
        )

        lines = [
            f"Hands Played: {self.hands_played}",
            f"Count Checks: {self.checks_correct}/{self.checks_total} ({count_accuracy:.1f}%)",
            f"Last Count Check: {self.last_check}",
            f"Basic Strategy: {self.basic_strategy_correct}/{self.basic_strategy_total} ({strategy_accuracy:.1f}%)",
            f"Last Strategy Result: {self.last_strategy_result}",
            f"Decks Remaining: {self.shoe.decks_remaining():.2f}",
            f"Rules: {self.selected_decks} Decks / {self.selected_dealer_rule}",
        ]

        if self.visible_counts:
            lines.append(f"Running Count: {self.shoe.running_count}")
            lines.append(f"True Count: {self.shoe.true_count():.2f}")
        else:
            lines.append("Running Count: hidden")
            lines.append("True Count: hidden")

        left_x = 24
        top_y = panel_rect.y + 18
        line_gap = 22
        for i, line in enumerate(lines):
            txt = self.fonts["small"].render(line, True, TEXT_COLOR)
            self.screen.blit(txt, (left_x, top_y + i * line_gap))

        help_text = self.fonts["small"].render(
            "Hotkeys: H=Hit  S=Stand  P=Split  N=New Hand  C=Count  B=Chart  ESC=Home",
            True,
            TEXT_COLOR,
        )
        self.screen.blit(help_text, (w - help_text.get_width() - 24, top_y))

        self.draw_strategy_chart(w, h)
        self.quiz_overlay.draw(self.screen, self.fonts, (w, h))
        pygame.display.flip()

    def draw(self):
        if self.game_state == "home":
            self.draw_home()
        else:
            self.draw_game()

    # -------------------------
    # Session setup
    # -------------------------
    def start_game_from_home(self):
        self.shoe = Shoe(num_decks=self.selected_decks, penetration=0.75)
        self.strategy_mode = self.selected_dealer_rule

        self.player_hands = []
        self.active_hand_index = 0
        self.dealer_hand = []

        self.message = "Click Next Hand to begin."
        self.message_color = TEXT_COLOR

        self.hand_over = True
        self.awaiting_new_hand = True
        self.quiz_overlay.close()

        self.game_state = "playing"

    # -------------------------
    # Trainer Logic
    # -------------------------
    def maybe_open_quiz(self):
        self.cards_until_quiz -= 1
        if self.cards_until_quiz > 0 or self.quiz_overlay.active:
            return

        quiz_type = random.choice(["running", "true"])
        if quiz_type == "running":
            self.pending_quiz_answer = self.shoe.running_count
            self.quiz_overlay.open("What is the running count?", "running")
        else:
            self.pending_quiz_answer = self.shoe.rounded_true_count()
            self.quiz_overlay.open("What is the rounded true count?", "true")

        self.cards_until_quiz = random.randint(4, 9)

    def record_quiz_result(self, guess: int):
        correct = guess == self.pending_quiz_answer
        self.checks_total += 1

        if correct:
            self.checks_correct += 1
            self.last_check = "Correct"
            self.quiz_overlay.feedback = "Correct"
            self.quiz_overlay.feedback_color = GREEN
        else:
            self.last_check = "Incorrect"
            if self.quiz_overlay.answer_type == "true":
                exact = self.shoe.true_count()
                self.quiz_overlay.feedback = (
                    f"Incorrect. Rounded: {self.pending_quiz_answer}  Exact: {exact:.2f}"
                )
            else:
                self.quiz_overlay.feedback = f"Incorrect. Answer: {self.pending_quiz_answer}"
            self.quiz_overlay.feedback_color = RED

    # -------------------------
    # Strategy Tracking
    # -------------------------
    def dealer_upcard_value(self) -> int:
        if not self.dealer_hand:
            return 0
        up = self.dealer_hand[0].rank
        if up == "A":
            return 11
        if up in {"J", "Q", "K"}:
            return 10
        return int(up)

    def record_strategy(self, action: str):
        if self.hand_over or not self.player_hands:
            return

        hand = self.player_hands[self.active_hand_index]
        dealer_up = self.dealer_upcard_value()
        correct_moves = self.recommended_moves(hand, dealer_up, self.selected_dealer_rule == "H17")

        self.basic_strategy_total += 1
        if action in correct_moves:
            self.basic_strategy_correct += 1
            self.last_strategy_result = f"Correct ({action})"
        else:
            expected = "/".join(sorted(correct_moves))
            self.last_strategy_result = f"Wrong ({action}, should be {expected})"

    def recommended_moves(self, hand: list[Card], dealer_up: int, h17: bool = True) -> set[str]:
        if len(hand) == 2 and hand[0].rank == hand[1].rank:
            rank = hand[0].rank

            if rank == "A" or rank == "8":
                return {"split"}
            if rank == "10":
                return {"stand"}
            if rank == "9":
                return {"split"} if dealer_up in {2, 3, 4, 5, 6, 8, 9} else {"stand"}
            if rank == "7":
                return {"split"} if 2 <= dealer_up <= 7 else {"hit"}
            if rank == "6":
                return {"split"} if 2 <= dealer_up <= 6 else {"hit"}
            if rank == "5":
                return {"hit"}  # double normally, but app doesn't support it yet
            if rank == "4":
                return {"split"} if dealer_up in {5, 6} else {"hit"}
            if rank in {"2", "3"}:
                return {"split"} if 2 <= dealer_up <= 7 else {"hit"}

        total = hand_value(hand)
        soft = is_soft_hand(hand)

        if soft:
            if total >= 19:
                return {"stand"}
            if total == 18:
                return {"stand"} if dealer_up in {2, 7, 8} else {"hit"}
            return {"hit"}

        if total >= 17:
            return {"stand"}
        if 13 <= total <= 16:
            return {"stand"} if 2 <= dealer_up <= 6 else {"hit"}
        if total == 12:
            return {"stand"} if 4 <= dealer_up <= 6 else {"hit"}
        return {"hit"}

    # -------------------------
    # Dealer rules
    # -------------------------
    def is_soft_17(self, hand: list[Card]) -> bool:
        return hand_value(hand) == 17 and is_soft_hand(hand)

    # -------------------------
    # Hand Flow
    # -------------------------
    def new_round(self):
        if self.shoe.needs_reshuffle():
            self.shoe.shuffle()
            self.message = "Shoe reshuffled."
            self.message_color = YELLOW
        else:
            self.message = "New hand dealt."
            self.message_color = TEXT_COLOR

        first_hand = [self.shoe.draw(), self.shoe.draw()]
        self.player_hands = [first_hand]
        self.active_hand_index = 0
        self.dealer_hand = [self.shoe.draw(), self.shoe.draw()]

        self.hands_played += 1
        self.hand_over = False
        self.awaiting_new_hand = False

        self.maybe_open_quiz()

        if is_blackjack(first_hand) or is_blackjack(self.dealer_hand):
            self.finish_naturals()

    def finish_naturals(self):
        self.hand_over = True
        self.awaiting_new_hand = True

        player_bj = len(self.player_hands) == 1 and is_blackjack(self.player_hands[0])
        dealer_bj = is_blackjack(self.dealer_hand)

        if player_bj and dealer_bj:
            self.message = "Push. Both have blackjack."
            self.message_color = YELLOW
        elif player_bj:
            self.message = "Blackjack! You win."
            self.message_color = GREEN
        else:
            self.message = "Dealer blackjack. You lose."
            self.message_color = RED

    def move_to_next_player_hand(self):
        for idx in range(self.active_hand_index + 1, len(self.player_hands)):
            hand = self.player_hands[idx]
            if hand_value(hand) < 21:
                self.active_hand_index = idx
                return True
        return False

    def current_hand(self) -> list[Card] | None:
        if not self.player_hands:
            return None
        return self.player_hands[self.active_hand_index]

    def hit(self):
        if self.hand_over or self.quiz_overlay.active:
            return

        hand = self.current_hand()
        if not hand:
            return

        self.record_strategy("hit")
        hand.append(self.shoe.draw())
        self.maybe_open_quiz()

        if hand_value(hand) > 21:
            if not self.move_to_next_player_hand():
                self.finish_dealer_and_resolve()
            else:
                self.message = f"Hand {self.active_hand_index} busted. Moving to next hand."
                self.message_color = RED

    def stand(self):
        if self.hand_over or self.quiz_overlay.active:
            return

        self.record_strategy("stand")

        if not self.move_to_next_player_hand():
            self.finish_dealer_and_resolve()
        else:
            self.message = f"Standing on hand {self.active_hand_index}. Next hand active."
            self.message_color = BLUE

    def split(self):
        if self.hand_over or self.quiz_overlay.active:
            return
        if len(self.player_hands) != 1:
            return

        hand = self.player_hands[0]
        if not can_split(hand):
            return

        self.record_strategy("split")

        card1, card2 = hand[0], hand[1]
        new_hand_1 = [card1, self.shoe.draw()]
        new_hand_2 = [card2, self.shoe.draw()]

        self.player_hands = [new_hand_1, new_hand_2]
        self.active_hand_index = 0

        self.maybe_open_quiz()
        self.message = "Hand split into two hands."
        self.message_color = BLUE

    def finish_dealer_and_resolve(self):
        if self.quiz_overlay.active:
            return

        while True:
            total = hand_value(self.dealer_hand)

            if total < 17:
                self.dealer_hand.append(self.shoe.draw())
                self.maybe_open_quiz()
                if self.quiz_overlay.active:
                    return
            elif (
                total == 17
                and self.selected_dealer_rule == "H17"
                and self.is_soft_17(self.dealer_hand)
            ):
                self.dealer_hand.append(self.shoe.draw())
                self.maybe_open_quiz()
                if self.quiz_overlay.active:
                    return
            else:
                break

        self.resolve_all_hands()

    def resolve_all_hands(self):
        self.hand_over = True
        self.awaiting_new_hand = True

        dealer_total = hand_value(self.dealer_hand)
        results = []

        for i, hand in enumerate(self.player_hands, start=1):
            total = hand_value(hand)

            if total > 21:
                results.append(f"H{i}: Lose")
            elif dealer_total > 21:
                results.append(f"H{i}: Win")
            elif total > dealer_total:
                results.append(f"H{i}: Win")
            elif dealer_total > total:
                results.append(f"H{i}: Lose")
            else:
                results.append(f"H{i}: Push")

        self.message = " | ".join(results)
        if all("Win" in r for r in results):
            self.message_color = GREEN
        elif all("Lose" in r for r in results):
            self.message_color = RED
        else:
            self.message_color = YELLOW

    # -------------------------
    # Input Handling
    # -------------------------
    def handle_home_clicks(self, event):
        if self.home_buttons["deck_4"].clicked(event):
            self.selected_decks = 4
        elif self.home_buttons["deck_6"].clicked(event):
            self.selected_decks = 6
        elif self.home_buttons["deck_8"].clicked(event):
            self.selected_decks = 8
        elif self.home_buttons["rule_h17"].clicked(event):
            self.selected_dealer_rule = "H17"
        elif self.home_buttons["rule_s17"].clicked(event):
            self.selected_dealer_rule = "S17"
        elif self.home_buttons["start"].clicked(event):
            self.start_game_from_home()
        elif self.home_buttons["quit"].clicked(event):
            pygame.quit()
            sys.exit()

    def handle_button_clicks(self, event):
        if self.buttons["hit"].clicked(event):
            self.hit()
        elif self.buttons["stand"].clicked(event):
            self.stand()
        elif self.buttons["split"].clicked(event):
            if not self.hand_over and len(self.player_hands) == 1 and can_split(self.player_hands[0]):
                self.split()
        elif self.buttons["next"].clicked(event):
            self.new_round()
        elif self.buttons["toggle_count"].clicked(event):
            self.visible_counts = not self.visible_counts
        elif self.buttons["toggle_chart"].clicked(event):
            self.show_strategy_chart = not self.show_strategy_chart

    def run(self):
        while True:
            self.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                    self.update_layout(*event.size)

                if self.game_state == "home":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_RETURN:
                            self.start_game_from_home()
                        elif event.key == pygame.K_ESCAPE:
                            pygame.quit()
                            sys.exit()
                    self.handle_home_clicks(event)
                    continue

                if self.quiz_overlay.active:
                    result = self.quiz_overlay.handle_event(event)
                    if result == "cancel":
                        pass
                    elif isinstance(result, int):
                        self.record_quiz_result(result)
                    continue

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_h:
                        self.hit()
                    elif event.key == pygame.K_s:
                        self.stand()
                    elif event.key == pygame.K_p:
                        self.split()
                    elif event.key == pygame.K_n:
                        self.new_round()
                    elif event.key == pygame.K_c:
                        self.visible_counts = not self.visible_counts
                    elif event.key == pygame.K_b:
                        self.show_strategy_chart = not self.show_strategy_chart
                    elif event.key == pygame.K_ESCAPE:
                        self.game_state = "home"

                self.handle_button_clicks(event)

            if self.game_state == "playing" and self.quiz_overlay.active and self.quiz_overlay.feedback:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_RETURN]:
                    self.quiz_overlay.close()
                    if not self.hand_over and self.active_hand_index >= len(self.player_hands) - 1:
                        self.finish_dealer_and_resolve()

            self.draw()


if __name__ == "__main__":
    BlackjackTrainerGame().run()