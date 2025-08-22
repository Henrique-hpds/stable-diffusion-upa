import json
import random

def load_prompts(path="data/prompts.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

class Game:
    def __init__(self, prompts, max_attempts=5):
        self.prompts = prompts
        self.answer_key, self.answer_value = random.choice(list(prompts.items()))
        self.attempts_left = max_attempts
        self.history = []

    def guess(self, word):
        correct = word.strip().lower() == self.answer_value.lower()
        self.history.append((word, correct))
        self.attempts_left -= 1
        return correct
