import streamlit as st
import random
import json
import os
import paramiko
import io
import base64
from datetime import datetime
from PIL import Image
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração da página
st.set_page_config(
    page_title="Real vs IA - Jogo",
    page_icon="🎮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Estilos CSS personalizados
st.markdown("""
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: bold;
        border: none;
        transition: all 0.3s;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #45a049;
        transform: scale(1.05);
    }
    .title {
        text-align: center;
        color: #1f77b4;
        font-size: 3em;
        margin-bottom: 0.5em;
    }
    .subtitle {
        text-align: center;
        color: #333;
        font-size: 1.5em;
        margin-bottom: 1em;
    }
    .score-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        text-align: center;
    }
    .leaderboard {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .leaderboard-item {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #4CAF50;
    }
    .leaderboard-item.first {
        border-left: 4px solid #FFD700;
        background-color: #fff9e6;
    }
    .leaderboard-item.second {
        border-left: 4px solid #C0C0C0;
        background-color: #f0f0f0;
    }
    .leaderboard-item.third {
        border-left: 4px solid #CD7F32;
        background-color: #f7e9d9;
    }
    .image-container {
        display: flex;
        justify-content: space-around;
        flex-wrap: wrap;
        gap: 20px;
        margin: 20px 0;
    }
    .image-option {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transition: transform 0.3s;
        cursor: pointer;
        width: 45%;
    }
    .image-option:hover {
        transform: scale(1.03);
    }
    .selected {
        border: 4px solid #4CAF50;
    }
    .playground {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 30px;
        margin-top: 30px;
    }
    .playground-title {
        color: white !important;
        text-align: center;
        margin-bottom: 20px;
    }
    .playground-text {
        color: white !important;
        text-align: center;
        margin-bottom: 20px;
    }
    .generated-image {
        border-radius: 10px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        margin-top: 20px;
    }
    .ssh-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        color: #856404;
    }
    .ssh-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        color: #155724;
    }
    .config-help {
        background-color: #e9ecef;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        font-family: monospace;
        font-size: 0.9em;
    }
    </style>
""", unsafe_allow_html=True)

# Dados do jogo
image_data = [
    {
        "real": "https://images.unsplash.com/photo-1501854140801-50d01698950b?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=900&q=80",
        "ai": "https://images.unsplash.com/photo-1502082553048-f009c37129b9?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=900&q=80",
        "answer": "right"
    },
    {
        "real": "https://images.unsplash.com/photo-1504870712357-65ea720d6078?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=900&q=80",
        "ai": "https://images.unsplash.com/photo-1506260408121-e353d10b87c7?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=900&q=80",
        "answer": "left"
    },
    {
        "real": "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=900&q=80",
        "ai": "https://images.unsplash.com/photo-1465146344425-f00d5f5c8f07?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=900&q=80",
        "answer": "right"
    }
]

# Configurações SSH
def get_ssh_config():
    """Obtém configurações SSH de forma segura"""
    config = {
        'hostname': os.environ.get('SSH_HOST'),
        'username': os.environ.get('SSH_USER'),
        'password': os.environ.get('SSH_PASSWORD'),
        'port': int(os.environ.get('SSH_PORT', 22)),
        'private_key_path': os.environ.get('SSH_PRIVATE_KEY_PATH'),
        'remote_path': os.environ.get('SSH_REMOTE_PATH', ''),
        'venv_name': os.environ.get('SSH_VENV_NAME', ''),
        'model_path': 'stabilityai/stable-diffusion-xl-base-1.0'
    }
    
    if not config['hostname'] or not config['username']:
        return None
    
    has_password = bool(config['password'])
    has_private_key = bool(config['private_key_path'])
    
    if not has_password and not has_private_key:
        return None
    
    return config

# Função para testar conexão SSH
def test_ssh_connection():
    """Testa a conexão SSH com as configurações atuais"""
    ssh_config = get_ssh_config()
    if not ssh_config:
        return False, "Configuração SSH não encontrada"
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Conexão com chave privada
        if ssh_config['private_key_path']:
            private_key_path = os.path.expanduser(ssh_config['private_key_path'])
            if os.path.exists(private_key_path):
                try:
                    private_key = paramiko.RSAKey.from_private_key_file(private_key_path)
                    ssh.connect(
                        hostname=ssh_config['hostname'],
                        username=ssh_config['username'],
                        pkey=private_key,
                        port=ssh_config['port'],
                        timeout=15
                    )
                except paramiko.PasswordRequiredException:
                    if ssh_config['password']:
                        ssh.connect(
                            hostname=ssh_config['hostname'],
                            username=ssh_config['username'],
                            password=ssh_config['password'],
                            port=ssh_config['port'],
                            timeout=15
                        )
                    else:
                        return False, "Chave privada exige senha"
        
        # Conexão com senha
        elif ssh_config['password']:
            ssh.connect(
                hostname=ssh_config['hostname'],
                username=ssh_config['username'],
                password=ssh_config['password'],
                port=ssh_config['port'],
                timeout=15
            )
        else:
            return False, "Nenhum método de autenticação"
        
        # Testar comandos básicos
        stdin, stdout, stderr = ssh.exec_command('echo "Teste de conexão bem-sucedido" && python3 --version')
        output = stdout.read().decode().strip()
        error = stderr.read().decode()
        
        ssh.close()
        
        if error:
            return False, f"Erro no teste: {error}"
        
        return True, f"Conexão SSH OK. {output}"
        
    except Exception as e:
        return False, f"Erro de conexão: {str(e)}"

# Função para gerar imagem via SSH (SIMPLIFICADA)
def generate_image_via_ssh(prompt):
    """Conecta via SSH e gera imagem de forma mais robusta"""
    ssh_config = get_ssh_config()
    if not ssh_config:
        return None, "Configuração SSH não encontrada. Verifique o arquivo .env"
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Conexão
        if ssh_config['private_key_path']:
            private_key_path = os.path.expanduser(ssh_config['private_key_path'])
            if os.path.exists(private_key_path):
                private_key = paramiko.RSAKey.from_private_key_file(private_key_path)
                ssh.connect(
                    hostname=ssh_config['hostname'],
                    username=ssh_config['username'],
                    pkey=private_key,
                    port=ssh_config['port'],
                    timeout=30
                )
        elif ssh_config['password']:
            ssh.connect(
                hostname=ssh_config['hostname'],
                username=ssh_config['username'],
                password=ssh_config['password'],
                port=ssh_config['port'],
                timeout=30
            )
        else:
            return None, "Nenhum método de autenticação SSH configurado"
        
        # Criar script Python temporário
        safe_prompt = prompt.replace('"', '\\"').replace("'", "\\'")
        python_script = f'''
import torch
from diffusers import StableDiffusionXLPipeline
import base64
from io import BytesIO

try:
    pipe = StableDiffusionXLPipeline.from_pretrained(
        "{ssh_config['model_path']}", 
        torch_dtype=torch.float16, 
        use_safetensors=True, 
        variant="fp16"
    )
    pipe = pipe.to("cuda")
    
    image = pipe(prompt="{safe_prompt}", num_inference_steps=20).images[0]
    
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    print("SUCCESS:" + img_str)
    
except Exception as e:
    print("ERROR: Falha na geração da imagem")
'''
        
        # Salvar script localmente
        script_filename = "/tmp/generate_image.py"
        with open(script_filename, "w") as f:
            f.write(python_script)
        
        # Comando para executar no servidor
        command_parts = []
        
        if ssh_config["remote_path"]:
            command_parts.append(f"cd {ssh_config['remote_path']}")
        
        if ssh_config["venv_name"]:
            command_parts.append(f"source {ssh_config['venv_name']}/bin/activate")
        
        # Transferir script para o servidor
        sftp = ssh.open_sftp()
        remote_script_path = "/tmp/generate_image.py"
        sftp.put(script_filename, remote_script_path)
        sftp.close()
        
        command_parts.append(f"python3 {remote_script_path}")
        command = " && ".join(command_parts)
        
        # Executar comando
        stdin, stdout, stderr = ssh.exec_command(command, timeout=300)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        ssh.close()
        
        if "SUCCESS:" in output:
            success_line = [line for line in output.split('\n') if line.startswith('SUCCESS:')][0]
            image_data_b64 = success_line[8:]
            try:
                image_data = base64.b64decode(image_data_b64)
                image = Image.open(io.BytesIO(image_data))
                return image, None
            except Exception:
                return None, "Erro ao processar imagem gerada"
        else:
            return None, "Falha na geração da imagem. Verifique se o servidor está configurado corretamente."
            
    except Exception as e:
        return None, f"Erro de conexão: {str(e)}"

# Funções para gerenciar dados
def load_leaderboard():
    if os.path.exists("leaderboard.json"):
        with open("leaderboard.json", "r") as f:
            return json.load(f)
    return []

def save_leaderboard(leaderboard):
    with open("leaderboard.json", "w") as f:
        json.dump(leaderboard, f)

def add_to_leaderboard(name, score):
    leaderboard = load_leaderboard()
    
    # Verificar se o jogador já existe no leaderboard
    player_exists = any(entry["name"] == name for entry in leaderboard)
    
    if not player_exists:
        # Adicionar novo jogador
        leaderboard.append({
            "name": name,
            "score": score,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
    else:
        # Atualizar score se for maior
        for entry in leaderboard:
            if entry["name"] == name and score > entry["score"]:
                entry["score"] = score
                entry["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Ordenar e manter apenas os top 10
    leaderboard.sort(key=lambda x: x["score"], reverse=True)
    leaderboard = leaderboard[:10]
    
    save_leaderboard(leaderboard)
    return leaderboard

def reset_game():
    for key in list(st.session_state.keys()):
        if key not in ['game_state', 'player_name', 'ssh_configured', 'score_added_to_leaderboard']:
            del st.session_state[key]
    st.session_state.game_state = "start"

# Inicialização do estado da sessão
if 'game_state' not in st.session_state:
    st.session_state.game_state = "start"
if 'player_name' not in st.session_state:
    st.session_state.player_name = ""
if 'current_round' not in st.session_state:
    st.session_state.current_round = 0
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'selected_option' not in st.session_state:
    st.session_state.selected_option = None
if 'answer_revealed' not in st.session_state:
    st.session_state.answer_revealed = False
if 'ssh_configured' not in st.session_state:
    st.session_state.ssh_configured = get_ssh_config() is not None
if 'generated_image' not in st.session_state:
    st.session_state.generated_image = None
if 'generating' not in st.session_state:
    st.session_state.generating = False
if 'last_prompt' not in st.session_state:
    st.session_state.last_prompt = ""
if 'ssh_tested' not in st.session_state:
    st.session_state.ssh_tested = False
if 'score_added_to_leaderboard' not in st.session_state:
    st.session_state.score_added_to_leaderboard = False

# Tela inicial
if st.session_state.game_state == "start":
    st.markdown('<h1 class="title">Real vs IA</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Você consegue distinguir imagens reais das geradas por inteligência artificial?</p>', unsafe_allow_html=True)
    
    # Verificação de configuração SSH
    ssh_config = get_ssh_config()
    
    if ssh_config:
        st.markdown('<div class="ssh-success">'
                   '<h4>✅ SSH Configurado</h4>'
                   f'<p>Servidor: {ssh_config["hostname"]} | Usuário: {ssh_config["username"]}</p>'
                   '</div>', unsafe_allow_html=True)
        
        if st.button("🔍 Testar Conexão SSH"):
            success, message = test_ssh_connection()
            if success:
                st.success(f"✅ {message}")
            else:
                st.error(f"❌ {message}")
            st.session_state.ssh_tested = True
    else:
        st.markdown('<div class="ssh-warning">'
                   '<h4>⚠️ Configuração SSH Necessária</h4>'
                   '<p>Para usar o playground de geração de imagens, configure o arquivo .env</p>'
                   '</div>', unsafe_allow_html=True)
    
    with st.form("player_form"):
        player_name = st.text_input("Digite seu nome:", max_chars=20, value=st.session_state.player_name)
        submitted = st.form_submit_button("Iniciar Jogo")
        
        if submitted:
            if player_name.strip():
                st.session_state.player_name = player_name
                st.session_state.game_state = "playing"
                st.session_state.current_round = 0
                st.session_state.score = 0
                st.session_state.selected_option = None
                st.session_state.answer_revealed = False
                st.session_state.score_added_to_leaderboard = False
                st.rerun()
            else:
                st.warning("Por favor, digite seu nome para começar.")

# Tela de jogo
elif st.session_state.game_state == "playing":
    if st.session_state.current_round < len(image_data):
        st.markdown(f'<h2 class="subtitle">Rodada {st.session_state.current_round + 1} de {len(image_data)}</h2>', unsafe_allow_html=True)
        
        round_data = image_data[st.session_state.current_round]
        st.info("Clique na imagem que você acredita ser REAL (não gerada por IA).")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.image(round_data["real"], use_container_width=True, caption="Imagem A")
            if st.session_state.selected_option is None:
                if st.button("Selecionar A", key="btn_left"):
                    st.session_state.selected_option = "left"
                    st.session_state.answer_revealed = True
                    st.rerun()
        
        with col2:
            st.image(round_data["ai"], use_container_width=True, caption="Imagem B")
            if st.session_state.selected_option is None:
                if st.button("Selecionar B", key="btn_right"):
                    st.session_state.selected_option = "right"
                    st.session_state.answer_revealed = True
                    st.rerun()
        
        if st.session_state.selected_option is not None:
            if st.session_state.selected_option == round_data["answer"]:
                st.success("✅ Correto! Você identificou a imagem real.")
            else:
                st.error("❌ Incorreto. Tente novamente na próxima rodada.")
            
            if round_data["answer"] == "left":
                st.info("💡 A imagem REAL era a A (esquerda)")
            else:
                st.info("💡 A imagem REAL era a B (direita)")
            
            if st.button("Próxima Rodada →"):
                if st.session_state.selected_option == round_data["answer"]:
                    st.session_state.score += 1
                st.session_state.current_round += 1
                st.session_state.selected_option = None
                st.session_state.answer_revealed = False
                st.rerun()
    
    else:
        st.session_state.game_state = "end"
        st.rerun()

# Tela final + Playground
elif st.session_state.game_state == "end":
    st.markdown('<h1 class="title">Fim de Jogo!</h1>', unsafe_allow_html=True)
    
    # Mostrar pontuação
    st.markdown(f'<div class="score-card"><h2>Pontuação Final: {st.session_state.score}/{len(image_data)}</h2></div>', unsafe_allow_html=True)
    
    # Adicionar ao leaderboard apenas uma vez
    if not st.session_state.score_added_to_leaderboard:
        leaderboard = add_to_leaderboard(st.session_state.player_name, st.session_state.score)
        st.session_state.score_added_to_leaderboard = True
    else:
        leaderboard = load_leaderboard()
    
    # Mostrar leaderboard
    st.markdown('<div class="leaderboard"><h2>🏆 Leaderboard</h2>', unsafe_allow_html=True)
    
    for i, entry in enumerate(leaderboard):
        emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "🏅"
        position_class = "first" if i == 0 else "second" if i == 1 else "third" if i == 2 else ""
        
        st.markdown(f"""
            <div class="leaderboard-item {position_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 1.2em; font-weight: bold;">
                        {emoji} {entry['name']}
                    </div>
                    <div style="font-size: 1.1em;">
                        {entry['score']} pontos
                    </div>
                </div>
                <div style="color: #666; font-size: 0.9em; margin-top: 5px;">
                    {entry['date']}
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Playground de geração de imagens
    ssh_config = get_ssh_config()
    
    st.markdown('<div class="playground">', unsafe_allow_html=True)
    st.markdown('<h2 class="playground-title">🎨 Playground de Geração de Imagens</h2>', unsafe_allow_html=True)
    
    if not ssh_config:
        st.markdown("""
        <div class="ssh-warning">
            <h4>⚠️ Configuração SSH Necessária</h4>
            <p>Para usar o playground, configure as variáveis de ambiente no arquivo .env</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<p class="playground-text">Agora é sua vez! Gere uma imagem usando IA com a poderosa RTX 4090</p>', unsafe_allow_html=True)
        
        with st.form("generation_form"):
            prompt = st.text_input("Digite o prompt para gerar uma imagem:", 
                                  placeholder="Ex: um gato astronauta no espaço, estilo digital art",
                                  value="Gato de botas")
            generate = st.form_submit_button("🚀 Gerar Imagem")
            
            if generate:
                if prompt.strip():
                    st.session_state.generating = True
                    st.session_state.last_prompt = prompt
                    with st.spinner("⏳ Conectando ao servidor remoto e gerando imagem... (isso pode levar 2-5 minutos)"):
                        generated_image, error_message = generate_image_via_ssh(prompt)
                        if generated_image:
                            st.session_state.generated_image = generated_image
                            st.success("✅ Imagem gerada com sucesso!")
                        else:
                            st.error(f"❌ {error_message}")
                    st.session_state.generating = False
                    st.rerun()
                else:
                    st.warning("Por favor, digite um prompt para gerar a imagem.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Mostrar imagem gerada
    if st.session_state.generated_image:
        st.markdown("---")
        st.markdown(f"### 🖼️ Imagem gerada para: \"{st.session_state.last_prompt}\"")
        st.image(st.session_state.generated_image, use_container_width=True, caption="Imagem gerada por IA - Stable Diffusion XL")
        
        # Botão para salvar a imagem
        buf = io.BytesIO()
        st.session_state.generated_image.save(buf, format="PNG")
        byte_im = buf.getvalue()
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="💾 Baixar Imagem",
                data=byte_im,
                file_name="imagem_gerada_ia.png",
                mime="image/png",
                use_container_width=True
            )
        with col2:
            if st.button("🔄 Gerar Outra", use_container_width=True):
                st.session_state.generated_image = None
                st.rerun()
    
    # Botões de ação
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Jogar Novamente", use_container_width=True):
            reset_game()
            st.rerun()
    with col2:
        if st.button("🏠 Voltar ao Início", use_container_width=True):
            st.session_state.game_state = "start"
            st.rerun()

# Rodapé com informações
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "🎮 Jogo Real vs IA | 🤖 Geração por Stable Diffusion XL | 🖥️ RTX 4090 Remota"
    "</div>",
    unsafe_allow_html=True
)