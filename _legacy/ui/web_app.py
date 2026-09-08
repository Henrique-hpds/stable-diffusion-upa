import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from game.mechanics import Game, load_prompts
from PIL import Image
import os
import sys

# Inicializa sessão
if "game" not in st.session_state:
    prompts = load_prompts()
    st.session_state.game = Game(prompts, max_attempts=6)
    st.session_state.step = 0

game = st.session_state.game

st.title("🧩 IA Wordle - Descubra a palavra!")

# Função para desenhar grid estilo Wordle
def render_grid(history, word_length, max_attempts, answer):
    for attempt in history:
        guess, _ = attempt
        row = ""
        for i, letter in enumerate(guess.ljust(word_length)):
            if i < len(answer) and letter.lower() == answer[i].lower():
                color = "🟩"
            elif letter.lower() in answer.lower():
                color = "🟨"
            else:
                color = "⬛"
            row += f"{letter.upper()} {color} "
        st.write(row)
    # linhas vazias
    for _ in range(len(history), max_attempts):
        st.write("⬜ " * word_length)

# Mostra imagem parcial (dummy sequence)
seq_path = f"data/sequences/{game.answer_key}"
steps = sorted(os.listdir(seq_path))
current_step = steps[st.session_state.step]
img = Image.open(os.path.join(seq_path, current_step))
st.image(img, caption=f"Etapa {st.session_state.step+1}/{len(steps)}")

# Campo de entrada de palavra
guess = st.text_input("Digite sua palavra:", max_chars=len(game.answer_value))

if st.button("Enviar"):
    if len(guess) == len(game.answer_value):
        correct = game.guess(guess)
        if correct:
            st.success("🎉 Acertou!")
        else:
            st.error("❌ Não foi dessa vez.")
            st.session_state.step = min(st.session_state.step + 1, len(steps)-1)

# Renderiza grid estilo Wordle
render_grid(game.history, len(game.answer_value), game.attempts_left+len(game.history), game.answer_value)

# Mensagem de fim
if game.attempts_left <= 0 and not any(c for _, c in game.history):
    st.warning(f"Fim de jogo! A resposta era: **{game.answer_value}**")
