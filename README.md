# Stable Diffusion Game for UPA2025

An interactive game where you try to distinguish real photographs from AI-generated images (Stable Diffusion XL). Each round shows 4 images — one is real, three are AI-generated — and you must pick the real one.

Built for the "Unicamp Portas Abertas 2025" demonstration (FEEC-UNICAMP).

## Repository Structure

- **`src/app.py`** — Main Streamlit app with the game, leaderboard, and an image generation playground via SSH
- **`src/requirements.txt`** — Python dependencies
- **`data/`** — Images organized in rounds (`rodada1` through `rodada10`), each containing `real.png` and three AI-generated images (`ia01.png`, `ia02.png`, `ia03.png`)
- **`_legacy/`** — Previous versions (Wordle and early game prototype), kept for reference only

## Dependencies / Requirements

- Python 3.10+
- SSH access to a server with an NVIDIA GPU (for the image generation playground)
- Remote server must have `stable-diffusion-xl-base-1.0` and the `diffusers` library installed

## Installation / Usage

```bash
# Clone the repository
git clone https://github.com/Henrique-hpds/stable-diffusion-upa.git
cd stable-diffusion-upa

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r src/requirements.txt

# Configure SSH credentials (create a .env file at the project root):
# SSH_HOST=your.server
# SSH_USER=username
# SSH_PASSWORD=password
# SSH_PORT=22
# SSH_PRIVATE_KEY_PATH=~/.ssh/id_rsa
# SSH_REMOTE_PATH=/remote/path
# SSH_VENV_NAME=venv

# Run the game
streamlit run src/app.py
```

### How to Play

1. Enter your name and click **Start Game**
2. Each round shows 4 images — click the one you believe is **real**
3. After all rounds, check your score on the leaderboard
4. In the **Playground**, type a prompt to generate an image via Stable Diffusion over SSH

## Authors

- (2026-) [Henrique Parede de Souza](https://github.com/Henrique-hpds): Computer Engineering student, FEEC-UNICAMP