#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wordle clone in Python (Pygame)
- 6 attempts, 5-letter word
- Flip animation on reveal (like the original)
- On-screen keyboard + physical keyboard support
- Shake animation for invalid words
- Reads the target word from a JSON file (words.json)
    * If "answer" is present, uses it.
    * If "answers" (list) is present, picks a daily word based on date.
    * If both are present, "answer" wins.
- Optional "allowed" list for validation. If not provided, accepts any A-Z 5-letter string.

Run:
    python3 wordle.py

Dependencies:
    pip install pygame
"""

import pygame
import sys
import json
import math
import datetime
import random
import string
from pathlib import Path

# ------------------------ Configuration ------------------------ #
SCREEN_W, SCREEN_H = 520, 740
FPS = 60

ROWS, COLS = 6, 5
TILE_SIZE = 64
TILE_GAP = 8

TOP_MARGIN = 80
GRID_W = COLS * TILE_SIZE + (COLS - 1) * TILE_GAP
GRID_H = ROWS * TILE_SIZE + (ROWS - 1) * TILE_GAP
GRID_X = (SCREEN_W - GRID_W) // 2
GRID_Y = TOP_MARGIN

KEYBOARD_MARGIN_TOP = GRID_Y + GRID_H + 40

FONT_NAME = "freesansbold.ttf"

# Colors (close to Wordle)
BG = (18, 18, 19)
TEXT = (215, 218, 220)
BORDER = (58, 58, 60)
EMPTY = (18, 18, 19)
ABSENT = (58, 58, 60)     # gray
PRESENT = (181, 159, 59)   # yellow
CORRECT = (83, 141, 78)    # green
KEY_BG = (129, 131, 132)   # keyboard default gray
KEY_TEXT = (255, 255, 255)

MESSAGE_BG = (30, 30, 30)

FLIP_DURATION = 320  # ms per tile flip
FLIP_DELAY = 120      # ms stagger between tiles
SHAKE_DURATION = 360  # ms
SHAKE_PIXELS = 10

# Keyboard layout (no accents for simplicity)
KEY_ROWS = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]
ENTER_KEY = "ENTER"
BKSP_KEY = "⌫"

# ------------------------ Helpers ------------------------ #
def load_words_json(path="words.json"):
    """
    Expected structures:
    {
      "answer": "CASAS",
      "allowed": ["CASAS","CASAL","CASCO", ...]
    }
    or
    {
      "answers": ["CASAS","NAVIO","CARRO", ...],
      "allowed": ["..."]
    }
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo JSON não encontrado: {path}")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    answer = None
    if "answer" in data and isinstance(data["answer"], str):
        answer = data["answer"].strip().upper()
    elif "answers" in data and isinstance(data["answers"], list) and data["answers"]:
        # pick daily deterministic word
        today = datetime.date.today().toordinal()
        idx = today % len(data["answers"])
        answer = str(data["answers"][idx]).strip().upper()

    if not answer or len(answer) != 5 or not answer.isalpha():
        raise ValueError("A resposta no JSON deve ser uma string com 5 letras A-Z.")

    allowed = None
    if "allowed" in data and isinstance(data["allowed"], list):
        allowed = set([str(w).strip().upper() for w in data["allowed"] if isinstance(w, (str,)) and len(str(w).strip()) == 5])

    return answer, allowed

def evaluate_guess(guess, target):
    """
    Wordle-like evaluation.
    Returns a list of states for each letter: 'correct', 'present', 'absent'
    """
    guess = guess.upper()
    target = target.upper()
    result = ["absent"] * 5

    # mark correct positions first
    target_counts = {}
    for ch in target:
        target_counts[ch] = target_counts.get(ch, 0) + 1

    # first pass: correct
    for i, ch in enumerate(guess):
        if ch == target[i]:
            result[i] = "correct"
            target_counts[ch] -= 1

    # second pass: present (only for remaining counts)
    for i, ch in enumerate(guess):
        if result[i] == "correct":
            continue
        if target_counts.get(ch, 0) > 0:
            result[i] = "present"
            target_counts[ch] -= 1
        else:
            result[i] = "absent"

    return result

def lerp(a, b, t):
    return a + (b - a) * t

# ------------------------ Classes ------------------------ #
class Tile:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size
        self.letter = ""
        self.state = "empty"  # empty, filled, absent, present, correct
        self.flip_t = 0.0
        self.flipping = False
        self.flip_start = 0
        self.flip_target_state = None

    def start_flip(self, now_ms, target_state):
        self.flipping = True
        self.flip_t = 0.0
        self.flip_start = now_ms
        self.flip_target_state = target_state

    def update(self, now_ms):
        if self.flipping:
            elapsed = now_ms - self.flip_start
            self.flip_t = min(1.0, elapsed / FLIP_DURATION)
            if self.flip_t >= 1.0:
                self.flipping = False
                if self.flip_target_state:
                    self.state = self.flip_target_state

    def draw(self, surf, font):
        # Compute flip scale based on flip_t (0..1). We flip "over" the X-axis (vertical flip).
        # At t=0.5 we switch color/state to the target state.
        t = self.flip_t
        is_mid = t >= 0.5
        scale_y = 1.0
        if self.flipping:
            # smooth step
            if t < 0.5:
                # going to 0 height
                scale_y = lerp(1.0, 0.0, t / 0.5)
            else:
                # back to 1 height
                scale_y = lerp(0.0, 1.0, (t - 0.5) / 0.5)

        # Choose color
        draw_state = self.state
        if self.flipping and is_mid and self.flip_target_state:
            draw_state = self.flip_target_state

        if draw_state == "empty":
            bg = EMPTY
            border = BORDER
        elif draw_state == "filled":
            bg = (22, 22, 24)
            border = (86, 87, 88)
        elif draw_state == "absent":
            bg = ABSENT
            border = ABSENT
        elif draw_state == "present":
            bg = PRESENT
            border = PRESENT
        elif draw_state == "correct":
            bg = CORRECT
            border = CORRECT
        else:
            bg = EMPTY
            border = BORDER

        # Draw rect with scale around center
        rect = pygame.Rect(self.x, self.y, self.size, self.size)
        cx, cy = rect.center
        draw_h = max(1, int(self.size * scale_y))
        draw_rect = pygame.Rect(0, 0, self.size, draw_h)
        draw_rect.center = (cx, cy)

        pygame.draw.rect(surf, bg, draw_rect, border_radius=8)
        pygame.draw.rect(surf, border, draw_rect, width=2, border_radius=8)

        # Draw letter only if height is big enough
        if self.letter and draw_h > self.size * 0.2:
            txt = font.render(self.letter, True, KEY_TEXT if draw_state in ("absent","present","correct") else TEXT)
            txt_rect = txt.get_rect(center=(cx, cy))
            surf.blit(txt, txt_rect)


class KeyboardKey:
    def __init__(self, label, rect):
        self.label = label
        self.rect = rect
        self.state = "neutral"  # neutral, absent, present, correct

    def color(self):
        if self.state == "correct":
            return CORRECT
        if self.state == "present":
            return PRESENT
        if self.state == "absent":
            return ABSENT
        return KEY_BG

    def draw(self, surf, font_small):
        pygame.draw.rect(surf, self.color(), self.rect, border_radius=6)
        pygame.draw.rect(surf, (20,20,20), self.rect, width=2, border_radius=6)
        label = self.label
        txt = font_small.render(label, True, KEY_TEXT)
        txt_rect = txt.get_rect(center=self.rect.center)
        surf.blit(txt, txt_rect)


class Game:
    def __init__(self, word, allowed=None):
        self.word = word.upper()
        self.allowed = allowed  # set or None

        pygame.init()
        pygame.display.set_caption("Wordle (clone)")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()

        self.font = pygame.font.Font(FONT_NAME, 36)
        self.font_small = pygame.font.Font(FONT_NAME, 22)
        self.font_tiny = pygame.font.Font(FONT_NAME, 18)
        self.title_font = pygame.font.Font(FONT_NAME, 40)

        # Grid of tiles
        self.tiles = []
        for r in range(ROWS):
            row = []
            for c in range(COLS):
                x = GRID_X + c * (TILE_SIZE + TILE_GAP)
                y = GRID_Y + r * (TILE_SIZE + TILE_GAP)
                row.append(Tile(x, y, TILE_SIZE))
            self.tiles.append(row)

        # Game state
        self.cur_row = 0
        self.cur_col = 0
        self.grid_letters = [[""] * COLS for _ in range(ROWS)]
        self.grid_states = [["empty"] * COLS for _ in range(ROWS)]
        self.animating = False
        self.reveal_start = 0
        self.shake_start = None
        self.message = ""
        self.message_time = 0
        self.finished = False
        self.win = False

        # Keyboard
        self.keyboard = self.build_keyboard()

    def build_keyboard(self):
        # Build 3 rows, centered
        rows = []
        key_w, key_h = 38, 52
        gap = 6

        y = KEYBOARD_MARGIN_TOP
        kbd = []

        def make_row(keystr, extra_padding_left=0):
            row_keys = []
            total_w = len(keystr) * key_w + (len(keystr)-1)*gap
            x = (SCREEN_W - total_w) // 2 + extra_padding_left
            for ch in keystr:
                rect = pygame.Rect(x, y, key_w, key_h)
                row_keys.append(KeyboardKey(ch, rect))
                x += key_w + gap
            return row_keys

        row1 = make_row(KEY_ROWS[0])
        kbd.extend(row1)

        y += key_h + gap
        row2 = make_row(KEY_ROWS[1], extra_padding_left=14)
        kbd.extend(row2)

        y += key_h + gap
        # for row3, add ENTER and BKSP keys wider
        # ENTER
        enter_rect = pygame.Rect(16, y, 72, key_h)
        kbd.append(KeyboardKey(ENTER_KEY, enter_rect))
        # letters
        total_letters = len(KEY_ROWS[2])
        total_w = total_letters * key_w + (total_letters-1)*gap
        xletters = (SCREEN_W - total_w) // 2
        x = xletters
        for ch in KEY_ROWS[2]:
            rect = pygame.Rect(x, y, key_w, key_h)
            kbd.append(KeyboardKey(ch, rect))
            x += key_w + gap
        # backspace
        bk_rect = pygame.Rect(SCREEN_W - 16 - 72, y, 72, key_h)
        kbd.append(KeyboardKey(BKSP_KEY, bk_rect))

        return kbd

    def set_message(self, msg, duration=1400):
        self.message = msg
        self.message_time = pygame.time.get_ticks() + duration

    def current_guess(self):
        return "".join(self.grid_letters[self.cur_row]).upper()

    def submit_guess(self):
        guess = self.current_guess()
        if len(guess) != 5 or not guess.isalpha():
            self.shake_start = pygame.time.get_ticks()
            self.set_message("Precisam ser 5 letras")
            return

        if self.allowed is not None and guess not in self.allowed and guess != self.word:
            self.shake_start = pygame.time.get_ticks()
            self.set_message("Não está na lista")
            return

        # Lock current row as filled
        for c in range(COLS):
            self.grid_states[self.cur_row][c] = "filled"
            self.tiles[self.cur_row][c].state = "filled"

        # Start flip animation with stagger
        self.animating = True
        base = pygame.time.get_ticks()
        pattern = evaluate_guess(guess, self.word)
        for c in range(COLS):
            target_state = pattern[c]
            self.tiles[self.cur_row][c].start_flip(base + c*FLIP_DELAY, target_state)

        self.reveal_start = base
        # Update keyboard colors after full reveal
        self.pending_keyboard_update = (guess, pattern)

    def update_keyboard(self, guess, pattern):
        # States priority: correct > present > absent
        priority = {"neutral":0,"absent":1,"present":2,"correct":3}
        for key in self.keyboard:
            if key.label in (ENTER_KEY, BKSP_KEY):
                continue
            for ch, st in zip(guess, pattern):
                if key.label == ch:
                    new_state = "correct" if st=="correct" else ("present" if st=="present" else "absent")
                    if priority[new_state] > priority[key.state]:
                        key.state = new_state

    def handle_key(self, key):
        if self.animating or self.finished:
            return

        if key == pygame.K_RETURN:
            if self.cur_col == COLS:
                self.submit_guess()
            else:
                self.set_message("Completa a palavra")
        elif key == pygame.K_BACKSPACE:
            if self.cur_col > 0:
                self.cur_col -= 1
                self.grid_letters[self.cur_row][self.cur_col] = ""
                self.tiles[self.cur_row][self.cur_col].letter = ""
                self.grid_states[self.cur_row][self.cur_col] = "empty"
        else:
            ch = None
            if pygame.K_a <= key <= pygame.K_z:
                ch = chr(key).upper()
            if ch and self.cur_col < COLS:
                self.grid_letters[self.cur_row][self.cur_col] = ch
                self.tiles[self.cur_row][self.cur_col].letter = ch
                self.grid_states[self.cur_row][self.cur_col] = "filled"
                self.cur_col += 1

    def handle_mouse(self, pos):
        if self.animating or self.finished:
            return
        for key in self.keyboard:
            if key.rect.collidepoint(pos):
                label = key.label
                if label == ENTER_KEY:
                    if self.cur_col == COLS:
                        self.submit_guess()
                    else:
                        self.set_message("Completa a palavra")
                elif label == BKSP_KEY:
                    if self.cur_col > 0:
                        self.cur_col -= 1
                        self.grid_letters[self.cur_row][self.cur_col] = ""
                        self.tiles[self.cur_row][self.cur_col].letter = ""
                        self.grid_states[self.cur_row][self.cur_col] = "empty"
                elif label in string.ascii_uppercase and len(label) == 1:
                    if self.cur_col < COLS:
                        self.grid_letters[self.cur_row][self.cur_col] = label
                        self.tiles[self.cur_row][self.cur_col].letter = label
                        self.grid_states[self.cur_row][self.cur_col] = "filled"
                        self.cur_col += 1
                break

    def draw_title(self, surf):
        title = self.title_font.render("WORDLE", True, TEXT)
        rect = title.get_rect(center=(SCREEN_W//2, 40))
        surf.blit(title, rect)

    def draw_message(self, surf):
        if self.message and pygame.time.get_ticks() < self.message_time:
            txt = self.font_small.render(self.message, True, KEY_TEXT)
            rect = txt.get_rect()
            rect.center = (SCREEN_W//2, GRID_Y - 20)
            # background bubble
            pad = 10
            bubble = pygame.Rect(rect.left - pad, rect.top - pad, rect.width + 2*pad, rect.height + 2*pad)
            pygame.draw.rect(surf, MESSAGE_BG, bubble, border_radius=12)
            pygame.draw.rect(surf, (50,50,50), bubble, width=2, border_radius=12)
            surf.blit(txt, rect)

    def update(self):
        now = pygame.time.get_ticks()

        # Update tile flips
        if self.animating:
            all_done = True
            for c in range(COLS):
                self.tiles[self.cur_row][c].update(now)
                if self.tiles[self.cur_row][c].flipping:
                    all_done = False
            if all_done:
                # Done revealing this row
                self.animating = False
                guess = self.current_guess()
                pattern = evaluate_guess(guess, self.word)
                self.update_keyboard(guess, pattern)

                if guess == self.word:
                    self.finished = True
                    self.win = True
                    self.set_message(random.choice(["Excelente!","Perfeito!","Você acertou!","Mandou bem!"]), duration=2200)
                else:
                    if self.cur_row == ROWS - 1:
                        self.finished = True
                        self.win = False
                        self.set_message(f"A palavra era {self.word}", duration=2800)
                    else:
                        self.cur_row += 1
                        self.cur_col = 0

        # Update shake timer
        if self.shake_start is not None:
            if now - self.shake_start > SHAKE_DURATION:
                self.shake_start = None

    def draw_grid(self, surf):
        # Compute shake offset for current row if needed
        offset_x = 0
        if self.shake_start is not None:
            t = (pygame.time.get_ticks() - self.shake_start) / SHAKE_DURATION
            offset_x = int(math.sin(t * math.pi * 8) * SHAKE_PIXELS)

        for r in range(ROWS):
            for c in range(COLS):
                tile = self.tiles[r][c]
                ox = offset_x if r == self.cur_row else 0
                # Draw with horizontal shake for current row
                # Temporarily shift and draw
                original_x = tile.x
                tile.x = original_x + ox
                tile.draw(surf, self.font)
                tile.x = original_x

    def draw_keyboard(self, surf):
        for key in self.keyboard:
            key.draw(surf, self.font_tiny)

    def mainloop(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_mouse(event.pos)

            self.update()

            self.screen.fill(BG)
            self.draw_title(self.screen)
            self.draw_grid(self.screen)
            self.draw_keyboard(self.screen)
            self.draw_message(self.screen)

            pygame.display.flip()
            self.clock.tick(FPS)


def main():
    try:
        answer, allowed = load_words_json("words.json")
    except Exception as e:
        print("Erro ao carregar words.json:", e)
        print("Crie um arquivo words.json com um campo 'answer' (string de 5 letras) ")
        print("ou um campo 'answers' (lista de palavras de 5 letras).")
        sys.exit(1)

    Game(answer, allowed).mainloop()


if __name__ == "__main__":
    main()
