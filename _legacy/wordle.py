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
    New behavior: always return a list of 4 target words and an optional allowed set.
    If JSON contains "answers" (list), sample 4 words from it (without replacement if possible).
    If only "answer" is present, repeat it 4 times.

    Returns: (words_list_of_4, allowed_set_or_None)
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo JSON não encontrado: {path}")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    words = []
    # Prefer 'answers' as pool to sample from
    if "answers" in data and isinstance(data["answers"], list) and data["answers"]:
        pool = [str(w).strip().upper() for w in data["answers"] if isinstance(w, str) and len(str(w).strip()) == 5 and str(w).strip().isalpha()]
        if not pool:
            raise ValueError("O campo 'answers' deve conter palavras de 5 letras A-Z.")
        if len(pool) >= 4:
            words = random.sample(pool, 4)
        else:
            # if fewer than 4 available, sample with repetition
            words = random.choices(pool, k=4)
    elif "answer" in data and isinstance(data["answer"], str):
        a = data["answer"].strip().upper()
        if len(a) != 5 or not a.isalpha():
            raise ValueError("A resposta no JSON deve ser uma string com 5 letras A-Z.")
        words = [a] * 4
    else:
        raise ValueError("O JSON deve conter 'answers' (lista) ou 'answer' (string).")

    allowed = None
    if "allowed" in data and isinstance(data["allowed"], list):
        allowed = set([str(w).strip().upper() for w in data["allowed"] if isinstance(w, (str,)) and len(str(w).strip()) == 5])

    return words, allowed

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
        # If the label is the backspace symbol and the font doesn't render it, draw a simple arrow icon
        if label == BKSP_KEY:
            # draw a left-pointing arrow centered in the key
            left = self.rect.left + 10
            right = self.rect.right - 10
            top = self.rect.top + 12
            bottom = self.rect.bottom - 12
            cx, cy = self.rect.center
            # arrow triangle
            points = [(right, top), (left, cy), (right, bottom)]
            pygame.draw.polygon(surf, KEY_TEXT, points)
            # small notch to resemble a backspace body
            notch = pygame.Rect(self.rect.left + 8, cy - 8, 8, 16)
            pygame.draw.rect(surf, KEY_TEXT, notch)
            # dark border for icon
            pygame.draw.polygon(surf, (20,20,20), points, width=1)
        else:
            txt = font_small.render(label, True, KEY_TEXT)
            txt_rect = txt.get_rect(center=self.rect.center)
            surf.blit(txt, txt_rect)


class Game:
    def __init__(self, words, allowed=None, num_boards=4):
        # words: list of target words (will be uppercased)
        self.num_boards = num_boards
        self.words = [w.upper() for w in (words if isinstance(words, (list,tuple)) else [words])]
        # If fewer words provided, repeat the first
        if len(self.words) < self.num_boards:
            self.words = (self.words * self.num_boards)[:self.num_boards]
        self.allowed = allowed  # set or None

        pygame.init()
        pygame.display.set_caption("Wordle (clone)")
        # start windowed
        self.windowed_size = (SCREEN_W, SCREEN_H)
        self.fullscreen = False
        self.screen = pygame.display.set_mode(self.windowed_size)
        self.clock = pygame.time.Clock()

        self.font = pygame.font.Font(FONT_NAME, 36)
        self.font_small = pygame.font.Font(FONT_NAME, 22)
        self.font_tiny = pygame.font.Font(FONT_NAME, 18)
        self.title_font = pygame.font.Font(FONT_NAME, 40)

        # Tiles: list per board (board -> rows -> cols)
        self.tiles = [[] for _ in range(self.num_boards)]

        # Game state (shared guess across boards, like Quordle)
        self.cur_row = 0
        self.cur_col = 0
        # grid_letters[board][row][col]
        self.grid_letters = [[[""] * COLS for _ in range(ROWS)] for _ in range(self.num_boards)]
        self.grid_states = [[["empty"] * COLS for _ in range(ROWS)] for _ in range(self.num_boards)]
        # per-board finished/win
        self.finished = [False] * self.num_boards
        self.win = [False] * self.num_boards

        self.animating = False
        self.reveal_start = 0
        self.shake_start = None
        self.message = ""
        self.message_time = 0

        # Keyboard
        self.keyboard = []

        # layout based on current screen size
        self.relayout()

    def build_keyboard(self):
        # Build keyboard same as before but using self.screen_w and self.keyboard_margin_top
        key_w, key_h = 38, 52
        gap = 6

        y = self.keyboard_margin_top
        kbd = []

        def make_row(keystr, extra_padding_left=0):
            row_keys = []
            total_w = len(keystr) * key_w + (len(keystr)-1)*gap
            x = (self.screen_w - total_w) // 2 + extra_padding_left
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
        # ENTER
        enter_rect = pygame.Rect(16, y, 72, key_h)
        kbd.append(KeyboardKey(ENTER_KEY, enter_rect))
        # letters
        total_letters = len(KEY_ROWS[2])
        total_w = total_letters * key_w + (total_letters-1)*gap
        xletters = (self.screen_w - total_w) // 2
        x = xletters
        for ch in KEY_ROWS[2]:
            rect = pygame.Rect(x, y, key_w, key_h)
            kbd.append(KeyboardKey(ch, rect))
            x += key_w + gap
        # backspace
        bk_rect = pygame.Rect(self.screen_w - 16 - 72, y, 72, key_h)
        kbd.append(KeyboardKey(BKSP_KEY, bk_rect))

        return kbd

    def toggle_fullscreen(self):
        """Toggle fullscreen/windowed mode and relayout UI."""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(self.windowed_size)
        self.relayout()

    def relayout(self):
        """Compute layout for num_boards arranged in a single row and (re)create tiles/keyboard.
        Boards are vertically centered and the keyboard is placed near the bottom of the window.
        """
        self.screen_w, self.screen_h = self.screen.get_size()
        # single row arrangement
        cols_boards = self.num_boards
        rows_boards = 1
        board_gap = 30

        # board (grid) size is fixed by TILE_SIZE/TILE_GAP
        board_w = COLS * TILE_SIZE + (COLS - 1) * TILE_GAP
        board_h = ROWS * TILE_SIZE + (ROWS - 1) * TILE_GAP

        total_w = cols_boards * board_w + (cols_boards - 1) * board_gap
        start_x = (self.screen_w - total_w) // 2
        # center boards vertically
        start_y = max(10, (self.screen_h - board_h) // 2)

        # compute per-board grid_x, grid_y and create tiles
        new_tiles = [[] for _ in range(self.num_boards)]
        # ensure board_pos exists
        self.board_pos = [None] * self.num_boards
        for b in range(self.num_boards):
            bc = b  # column index in single row
            br = 0
            grid_x = start_x + bc * (board_w + board_gap)
            grid_y = start_y + br * (board_h + 0)
            self.board_pos[b] = (grid_x, grid_y, board_w, board_h)

            row_tiles = []
            for r in range(ROWS):
                row = []
                for c in range(COLS):
                    x = grid_x + c * (TILE_SIZE + TILE_GAP)
                    y = grid_y + r * (TILE_SIZE + TILE_GAP)
                    # reuse existing tile if present
                    if len(self.tiles) > b and len(self.tiles[b]) > r and len(self.tiles[b][r]) > c:
                        tile = self.tiles[b][r][c]
                        tile.x = x
                        tile.y = y
                        tile.size = TILE_SIZE
                    else:
                        tile = Tile(x, y, TILE_SIZE)
                    row.append(tile)
                row_tiles.append(row)
            new_tiles[b] = row_tiles

        self.tiles = new_tiles

        # keyboard placed near bottom
        # key height used by build_keyboard is 52; reserve 20px padding from bottom
        key_h = 52
        self.grid_y = start_y
        self.grid_h = rows_boards * board_h + (rows_boards - 1) * 0
        # place keyboard either just below the boards or near the bottom, whichever keeps it visible
        self.keyboard_margin_top = min(self.grid_y + self.grid_h + 20, self.screen_h - key_h - 20)
        self.keyboard = self.build_keyboard()

    def set_message(self, msg, duration=1400):
         self.message = msg
         self.message_time = pygame.time.get_ticks() + duration

    def current_guess(self):
        # build guess from first board (they are kept synchronized)
        return "".join(self.grid_letters[0][self.cur_row]).upper()

    def submit_guess(self):
        guess = self.current_guess()
        if len(guess) != 5 or not guess.isalpha():
            self.shake_start = pygame.time.get_ticks()
            self.set_message("Precisam ser 5 letras")
            return

        # Lock current row as filled for all boards
        for b in range(self.num_boards):
            if self.finished[b]:
                continue
            for c in range(COLS):
                self.grid_states[b][self.cur_row][c] = "filled"
                self.tiles[b][self.cur_row][c].state = "filled"

        # Start flip animation for each board (stagger within each board)
        self.animating = True
        base = pygame.time.get_ticks()
        self.pending_patterns = []
        for b in range(self.num_boards):
            if self.finished[b]:
                self.pending_patterns.append(None)
                continue
            pattern = evaluate_guess(guess, self.words[b])
            self.pending_patterns.append(pattern)
            for c in range(COLS):
                target_state = pattern[c]
                # add small offset per board so flips don't perfectly align
                board_offset = b * 30
                self.tiles[b][self.cur_row][c].start_flip(base + board_offset + c*FLIP_DELAY, target_state)

        self.reveal_start = base

    def update_keyboard(self):
        # Combine pending patterns from all boards and update keyboard with highest-priority state
        if not hasattr(self, 'pending_patterns') or not self.pending_patterns:
            return
        priority = {"neutral":0,"absent":1,"present":2,"correct":3}
        # For each letter in guess, compute best state across boards
        guess = self.current_guess()
        combined = {ch: "neutral" for ch in string.ascii_uppercase}
        for pattern in self.pending_patterns:
            if not pattern:
                continue
            for ch, st in zip(guess, pattern):
                cur = combined.get(ch, "neutral")
                new_state = "correct" if st=="correct" else ("present" if st=="present" else "absent")
                if priority[new_state] > priority[cur]:
                    combined[ch] = new_state

        for key in self.keyboard:
            if key.label in (ENTER_KEY, BKSP_KEY):
                continue
            if key.label in combined:
                key.state = combined[key.label]

        # clear pending
        self.pending_patterns = []

    def handle_key(self, key):
        # allow fullscreen toggle anytime
        if key == pygame.K_F11 or key == pygame.K_f:
            self.toggle_fullscreen()
            return

        if self.animating:
            return
        if all(self.finished):
            return

        if key == pygame.K_RETURN:
            if self.cur_col == COLS:
                self.submit_guess()
            else:
                self.set_message("Completa a palavra")
        elif key == pygame.K_BACKSPACE:
            if self.cur_col > 0:
                self.cur_col -= 1
                for b in range(self.num_boards):
                    self.grid_letters[b][self.cur_row][self.cur_col] = ""
                    self.tiles[b][self.cur_row][self.cur_col].letter = ""
                    self.grid_states[b][self.cur_row][self.cur_col] = "empty"
        else:
            ch = None
            if pygame.K_a <= key <= pygame.K_z:
                ch = chr(key).upper()
            if ch and self.cur_col < COLS:
                for b in range(self.num_boards):
                    # allow typing even on finished boards (keeps synced but won't be evaluated)
                    self.grid_letters[b][self.cur_row][self.cur_col] = ch
                    self.tiles[b][self.cur_row][self.cur_col].letter = ch
                    self.grid_states[b][self.cur_row][self.cur_col] = "filled"
                self.cur_col += 1

    def handle_mouse(self, pos):
        if self.animating or all(self.finished):
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
                        for b in range(self.num_boards):
                            self.grid_letters[b][self.cur_row][self.cur_col] = ""
                            self.tiles[b][self.cur_row][self.cur_col].letter = ""
                            self.grid_states[b][self.cur_row][self.cur_col] = "empty"
                elif label in string.ascii_uppercase and len(label) == 1:
                    if self.cur_col < COLS:
                        for b in range(self.num_boards):
                            self.grid_letters[b][self.cur_row][self.cur_col] = label
                            self.tiles[b][self.cur_row][self.cur_col].letter = label
                            self.grid_states[b][self.cur_row][self.cur_col] = "filled"
                        self.cur_col += 1
                break

    def draw_title(self, surf):
        title = self.title_font.render("WORDLE 4x (Quordle)", True, TEXT)
        rect = title.get_rect(center=(self.screen_w//2, 40))
        surf.blit(title, rect)

    def draw_message(self, surf):
        if hasattr(self, 'message') and self.message and hasattr(self, 'message_time') and pygame.time.get_ticks() < self.message_time:
            txt = self.font_small.render(self.message, True, KEY_TEXT)
            rect = txt.get_rect()
            # place message above the boards (use grid_y if available), but ensure it is above the keyboard
            base_y = getattr(self, 'grid_y', TOP_MARGIN)
            preferred_y = base_y - 20
            # don't overlap keyboard; put message at least 40px above keyboard margin
            kb_top = getattr(self, 'keyboard_margin_top', self.screen_h - 80)
            y = min(preferred_y, kb_top - 40)
            # also clamp to at least 20px from top
            y = max(20, y)
            rect.center = (self.screen_w//2, y)
             # background bubble
            pad = 10
            bubble = pygame.Rect(rect.left - pad, rect.top - pad, rect.width + 2*pad, rect.height + 2*pad)
            pygame.draw.rect(surf, MESSAGE_BG, bubble, border_radius=12)
            pygame.draw.rect(surf, (50,50,50), bubble, width=2, border_radius=12)
            surf.blit(txt, rect)

    def update(self):
        now = pygame.time.get_ticks()

        # Update tile flips across all boards
        if self.animating:
            any_flipping = False
            for b in range(self.num_boards):
                for c in range(COLS):
                    self.tiles[b][self.cur_row][c].update(now)
                    if self.tiles[b][self.cur_row][c].flipping:
                        any_flipping = True
            if not any_flipping:
                # Done revealing this row for all boards
                self.animating = False
                guess = self.current_guess()
                # collect patterns and update per-board finished state
                for b in range(self.num_boards):
                    if self.finished[b]:
                        continue
                    pattern = evaluate_guess(guess, self.words[b])
                    # update per-board tiles states already set in flip end
                    if guess == self.words[b]:
                        self.finished[b] = True
                        self.win[b] = True
                    else:
                        if self.cur_row == ROWS - 1:
                            self.finished[b] = True
                            self.win[b] = False

                # update keyboard from the prior pending_patterns (if any)
                self.update_keyboard()

                # advance shared row if any board still active
                if not all(self.finished):
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

        for b in range(self.num_boards):
            grid_x, grid_y, board_w, board_h = self.board_pos[b]
            # draw board background (optional)
            board_bg = pygame.Rect(grid_x-10, grid_y-10, board_w+20, board_h+20)
            pygame.draw.rect(surf, (12,12,13), board_bg, border_radius=8)
            for r in range(ROWS):
                for c in range(COLS):
                    tile = self.tiles[b][r][c]
                    ox = offset_x if r == self.cur_row and not self.finished[b] else 0
                    original_x = tile.x
                    tile.x = original_x + ox
                    tile.draw(surf, self.font)
                    tile.x = original_x
            # draw small status under each board
            status = "✅" if self.win[b] else ("❌" if self.finished[b] and not self.win[b] else "")
            # draw small status indicator (colored dot) to avoid emoji/glyph issues
            if self.finished[b]:
                color = CORRECT if self.win[b] else (200, 60, 60)
                center = (grid_x + board_w - 20, grid_y - 20)
                pygame.draw.circle(surf, color, center, 10)
                pygame.draw.circle(surf, (20,20,20), center, 10, width=2)

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
        words, allowed = load_words_json("words.json")
    except Exception as e:
        print("Erro ao carregar words.json:", e)
        print("Crie um arquivo words.json com um campo 'answers' (lista de palavras de 5 letras) ")
        print("ou um campo 'answer' (string de 5 letras).")
        sys.exit(1)

    Game(words, allowed).mainloop()


if __name__ == "__main__":
    main()
