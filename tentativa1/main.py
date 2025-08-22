import os
import subprocess

if __name__ == "__main__":
    # Executa a interface web
    subprocess.run(["streamlit", "run", "ui/web_app.py"])
