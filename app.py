import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import json
import os
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
import urllib.parse

# =========================================
# 🎨 CONFIGURAÇÃO DE ESTILOS E CORES
# =========================================

st.set_page_config(
    page_title="FashionManager Pro",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para cores e estilo
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #6A0DAD;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .section-header {
        font-size: 1.8rem;
        color: #4B0082;
        border-bottom: 3px solid #9370DB;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
    }
    .success-card {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .warning-card {
        background: linear-gradient(135deg, #f46b45 0%, #eea849 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .info-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    .stButton>button {
        background: linear-gradient(135deg, #6A0DAD 0%, #9370DB 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #5a0a9c 0%, #8367c7 100%);
        color: white;
    }
    .tab-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Cores temáticas
COLORS = {
    'primary': '#6A0DAD',
    'secondary': '#9370DB',
    'success': '#00b09b',
    'warning': '#f46b45',
    'info': '#4facfe',
    'dark': '#4B0082'
}

# =========================================
# 🔧 CONFIGURAÇÃO DO BANCO DE DADOS - POSTGRESQL
# =========================================

def get_connection():
    """Estabelece conexão com PostgreSQL no Render"""
    try:
        # Para Render - usa DATABASE_URL do environment
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            # Parse da URL do Render
            parsed_url = urllib.parse.urlparse(database_url)
            
            conn = psycopg2.connect(
                database=parsed_url.path[1:],
                user=parsed_url.username,
                password=parsed_url.password,
                host=parsed_url.hostname,
                port=parsed_url.port,
                sslmode='require'
            )
        else:
            # Para desenvolvimento local
            conn = psycopg2.connect(
                host="localhost",
                database="fardamentos",
                user="postgres",
                password="password"
            )
        
        return conn
    except Exception as e:
        st.error(f"❌ Erro de conexão com o banco: {str(e)}")
        return None

def init_db():
    """Inicializa o banco PostgreSQL"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            
            # Tabela de usuários
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    nome_completo TEXT,
                    tipo TEXT DEFAULT 'vendedor',
                    ativo BOOLEAN DEFAULT TRUE,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de escolas
            cur.execute('''
                CREATE TABLE IF NOT EXISTS escolas (
                    id SERIAL PRIMARY KEY,
                    nome TEXT UNIQUE NOT NULL
                )
            ''')
            
            # Tabela de clientes
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            # Tabela de produtos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    categoria TEXT,
                    tamanho TEXT,
                    cor TEXT,
                    preco REAL,
                    estoque INTEGER DEFAULT 0,
                    descricao TEXT,
                    escola_id INTEGER REFERENCES escolas(id),
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de pedidos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedidos (
                    id SERIAL PRIMARY KEY,
                    cliente_id INTEGER REFERENCES clientes(id),
                    escola_id INTEGER REFERENCES escolas(id),
                    status TEXT DEFAULT 'Pendente',
                    data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_entrega_prevista DATE,
                    data_entrega_real DATE,
                    forma_pagamento TEXT DEFAULT 'Dinheiro',
                    quantidade_total INTEGER,
                    valor_total REAL,
                    observacoes TEXT
                )
            ''')
            
            # Tabela de itens do pedido
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedido_itens (
                    id SERIAL PRIMARY KEY,
                    pedido_id INTEGER REFERENCES pedidos(id) ON DELETE CASCADE,
                    produto_id INTEGER REFERENCES produtos(id),
                    quantidade INTEGER,
                    preco_unitario REAL,
                    subtotal REAL
                )
            ''')
            
            # Inserir usuários padrão
            usuarios_padrao = [
                ('admin', make_hashes('Admin@2024!'), 'Administrador', 'admin'),
                ('vendedor', make_hashes('Vendas@123'), 'Vendedor', 'vendedor')
            ]
            
            for username, password_hash, nome, tipo in usuarios_padrao:
                try:
                    cur.execute('''
                        INSERT INTO usuarios (username, password_hash, nome_completo, tipo) 
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (username) DO NOTHING
                    ''', (username, password_hash, nome, tipo))
                except Exception as e:
                    pass
            
            # Inserir escolas padrão
            escolas_padrao = ['Escola Municipal', 'Colégio Desperta', 'Instituto São Tadeu']
            for escola in escolas_padrao:
                try:
                    cur.execute('INSERT INTO escolas (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING', (escola,))
                except Exception as e:
                    pass
            
            conn.commit()
            
        except Exception as e:
            st.error(f"❌ Erro ao inicializar banco: {str(e)}")
        finally:
            conn.close()

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def verificar_login(username, password):
    """Verifica credenciais no banco de dados"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT password_hash, nome_completo, tipo 
            FROM usuarios 
            WHERE username = %s AND ativo = TRUE
        ''', (username,))
        
        resultado = cur.fetchone()
        
        if resultado and check_hashes(password, resultado[0]):
            return True, resultado[1], resultado[2]
        else:
            return False, "Credenciais inválidas", None
            
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        conn.close()

# =========================================
# 🗃️ FUNÇÕES DO BANCO DE DADOS
# =========================================

def listar_escolas():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM escolas ORDER BY nome")
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar escolas: {e}")
        return []
    finally:
        conn.close()

def adicionar_cliente(nome, telefone, email):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_cadastro = datetime.now().strftime("%Y-%m-%d")
        
        cur.execute(
            "INSERT INTO clientes (nome, telefone, email, data_cadastro) VALUES (%s, %s, %s, %s)",
            (nome, telefone, email, data_cadastro)
        )
        
        conn.commit()
        return True, "✅ Cliente cadastrado com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def listar_clientes():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM clientes ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar clientes: {e}")
        return []
    finally:
        conn.close()

def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        cur.execute('''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id))
        
        conn.commit()
        return True, "✅ Produto cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def listar_produtos_por_escola(escola_id=None):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        if escola_id:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                WHERE p.escola_id = %s
                ORDER BY p.categoria, p.nome
            ''', (escola_id,))
        else:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                ORDER BY e.nome, p.categoria, p.nome
            ''')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar produtos: {e}")
        return []
    finally:
        conn.close()

def adicionar_pedido(cliente_id, escola_id, itens, data_entrega, forma_pagamento, observacoes):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_pedido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        quantidade_total = sum(item['quantidade'] for item in itens)
        valor_total = sum(item['subtotal'] for item in itens)
        
        cur.execute('''
            INSERT INTO pedidos (cliente_id, escola_id, data_entrega_prevista, forma_pagamento, quantidade_total, valor_total, observacoes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (cliente_id, escola_id, data_entrega, forma_pagamento, quantidade_total, valor_total, observacoes))
        
        pedido_id = cur.lastrowid
        
        for item in itens:
            cur.execute('''
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            ''', (pedido_id, item['produto_id'], item['quantidade'], item['preco_unitario'], item['subtotal']))
            
            # Atualizar estoque
            cur.execute("UPDATE produtos SET estoque = estoque - %s WHERE id = %s", 
                       (item['quantidade'], item['produto_id']))
        
        conn.commit()
        return True, pedido_id
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def listar_pedidos_por_escola(escola_id=None):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        if escola_id:
            cur.execute('''
                SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome
                FROM pedidos p
                JOIN clientes c ON p.cliente_id = c.id
                JOIN escolas e ON p.escola_id = e.id
                WHERE p.escola_id = %s
                ORDER BY p.data_pedido DESC
            ''', (escola_id,))
        else:
            cur.execute('''
                SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome
                FROM pedidos p
                JOIN clientes c ON p.cliente_id = c.id
                JOIN escolas e ON p.escola_id = e.id
                ORDER BY p.data_pedido DESC
            ''')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar pedidos: {e}")
        return []
    finally:
        conn.close()

# =========================================
# 🔐 SISTEMA DE LOGIN
# =========================================

def login():
    st.markdown("<h1 class='main-header'>👕 FashionManager Pro</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    
    with col2:
        st.markdown("<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color: white; text-align: center;'>🔐 Acesso ao Sistema</h2>", unsafe_allow_html=True)
        
        username = st.text_input("👤 **Usuário**", placeholder="Digite seu usuário")
        password = st.text_input("🔒 **Senha**", type='password', placeholder="Digite sua senha")
        
        if st.button("🚀 **Entrar no Sistema**", use_container_width=True):
            if username and password:
                sucesso, mensagem, tipo_usuario = verificar_login(username, password)
                if sucesso:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.nome_usuario = mensagem
                    st.session_state.tipo_usuario = tipo_usuario
                    st.success(f"✅ Bem-vindo, {mensagem}!")
                    st.rerun()
                else:
                    st.error(f"❌ {mensagem}")
            else:
                st.error("⚠️ Preencha todos os campos")
        st.markdown("</div>", unsafe_allow_html=True)

# =========================================
# 🎯 CONFIGURAÇÕES GLOBAIS
# =========================================

# Inicializar banco na primeira execução
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# Configurações específicas
tamanhos_infantil = ["2", "4", "6", "8", "10", "12"]
tamanhos_adulto = ["PP", "P", "M", "G", "GG"]
todos_tamanhos = tamanhos_infantil + tamanhos_adulto

categorias_produtos = ["Camisetas", "Calças/Shorts", "Agasalhos", "Acessórios", "Outros"]

# =========================================
# 🎨 SIDEBAR - MENU PRINCIPAL
# =========================================

with st.sidebar:
    st.markdown("<h1 style='color: white; text-align: center;'>👕 FashionManager Pro</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Informações do usuário
    st.markdown(f"""
    <div style='background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px; margin-bottom: 1rem;'>
        <p style='color: white; margin: 0;'>👤 <strong>{st.session_state.nome_usuario}</strong></p>
        <p style='color: white; margin: 0;'>🎯 {st.session_state.tipo_usuario.title()}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Menu de navegação
    menu_options = ["📊 Dashboard", "🛍️ Vendas", "📦 Pedidos", "👥 Clientes", "👕 Produtos", "📦 Estoque", "📈 Relatórios", "⚙️ Configurações"]
    menu = st.radio("**Navegação**", menu_options, label_visibility="collapsed")
    
    st.markdown("---")
    
    # Botão de logout
    if st.button("🚪 **Sair do Sistema**", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.nome_usuario = None
        st.session_state.tipo_usuario = None
        st.rerun()

# =========================================
# 📊 PÁGINA - DASHBOARD
# =========================================

if menu == "📊 Dashboard":
    st.markdown("<h1 class='main-header'>📊 Dashboard - FashionManager Pro</h1>", unsafe_allow_html=True)
    
    # Métricas em tempo real
    st.markdown("<h2 class='section-header'>🎯 Métricas em Tempo Real</h2>", unsafe_allow_html=True)
    
    escolas = listar_escolas()
    clientes = listar_clientes()
    pedidos = listar_pedidos_por_escola()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_pedidos = len(pedidos)
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Total de Pedidos</div>
            <div class='metric-value'>{total_pedidos}</div>
            <div>📦 Todos os pedidos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        pedidos_pendentes = len([p for p in pedidos if p[3] == 'Pendente'])
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #f46b45 0%, #eea849 100%);'>
            <div class='metric-label'>Pedidos Pendentes</div>
            <div class='metric-value'>{pedidos_pendentes}</div>
            <div>⏳ Aguardando</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);'>
            <div class='metric-label'>Clientes Ativos</div>
            <div class='metric-value'>{len(clientes)}</div>
            <div>👥 Cadastrados</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        produtos_baixo_estoque = 0
        for escola in escolas:
            produtos = listar_produtos_por_escola(escola[0])
            produtos_baixo_estoque += len([p for p in produtos if p[6] < 5])
        
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);'>
            <div class='metric-label'>Alertas de Estoque</div>
            <div class='metric-value'>{produtos_baixo_estoque}</div>
            <div>⚠️ Produtos críticos</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Gráficos e visualizações
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<h3 class='section-header'>📈 Vendas por Escola</h3>", unsafe_allow_html=True)
        
        vendas_por_escola = []
        for escola in escolas:
            pedidos_escola = listar_pedidos_por_escola(escola[0])
            total_vendas = sum(float(p[9]) for p in pedidos_escola)
            vendas_por_escola.append({'Escola': escola[1], 'Vendas': total_vendas})
        
        if vendas_por_escola:
            df_vendas = pd.DataFrame(vendas_por_escola)
            fig = px.pie(df_vendas, values='Vendas', names='Escola', 
                        title='Distribuição de Vendas por Escola',
                        color_discrete_sequence=px.colors.sequential.Viridis)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("<h3 class='section-header'>📦 Status dos Pedidos</h3>", unsafe_allow_html=True)
        
        status_counts = {}
        for pedido in pedidos:
            status = pedido[3]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        if status_counts:
            df_status = pd.DataFrame(list(status_counts.items()), columns=['Status', 'Quantidade'])
            fig = px.bar(df_status, x='Status', y='Quantidade', 
                        title='Pedidos por Status',
                        color='Status',
                        color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig, use_container_width=True)
    
    # Ações Rápidas
    st.markdown("<h2 class='section-header'>⚡ Ações Rápidas</h2>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🛍️ **Nova Venda**", use_container_width=True):
            st.session_state.menu = "🛍️ Vendas"
            st.rerun()
    
    with col2:
        if st.button("👥 **Cadastrar Cliente**", use_container_width=True):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col3:
        if st.button("👕 **Cadastrar Produto**", use_container_width=True):
            st.session_state.menu = "👕 Produtos"
            st.rerun()
    
    with col4:
        if st.button("📦 **Ver Estoque**", use_container_width=True):
            st.session_state.menu = "📦 Estoque"
            st.rerun()

# =========================================
# 🛍️ PÁGINA - VENDAS
# =========================================

elif menu == "🛍️ Vendas":
    st.markdown("<h1 class='main-header'>🛍️ Sistema de Vendas</h1>", unsafe_allow_html=True)
    
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada. Configure as escolas primeiro.")
        st.stop()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("<h2 class='section-header'>🛒 Nova Venda</h2>", unsafe_allow_html=True)
        
        # Seleção da escola
        escola_venda_nome = st.selectbox(
            "🏫 **Escola para Venda:**",
            [e[1] for e in escolas],
            key="venda_escola"
        )
        escola_venda_id = next(e[0] for e in escolas if e[1] == escola_venda_nome)
        
        # Seleção do cliente
        clientes = listar_clientes()
        if not clientes:
            st.error("❌ Nenhum cliente cadastrado. Cadastre clientes primeiro.")
        else:
            cliente_selecionado = st.selectbox(
                "👤 **Selecione o Cliente:**",
                [f"{c[1]} (ID: {c[0]})" for c in clientes]
            )
            
            if cliente_selecionado:
                cliente_id = int(cliente_selecionado.split("(ID: ")[1].replace(")", ""))
                
                # Produtos disponíveis
                produtos = listar_produtos_por_escola(escola_venda_id)
                
                if produtos:
                    st.markdown("#### 🎯 Produtos Disponíveis")
                    
                    col_a, col_b, col_c = st.columns([3, 1, 1])
                    with col_a:
                        produto_selecionado = st.selectbox(
                            "**Produto:**",
                            [f"{p[1]} - Tamanho: {p[3]} - Cor: {p[4]} - Estoque: {p[6]} - R$ {p[5]:.2f}" for p in produtos],
                            key="produto_venda"
                        )
                    with col_b:
                        quantidade = st.number_input("**Quantidade**", min_value=1, value=1, key="qtd_venda")
                    with col_c:
                        if st.button("➕ **Adicionar**", use_container_width=True):
                            if 'itens_venda' not in st.session_state:
                                st.session_state.itens_venda = []
                            
                            produto_id = next(p[0] for p in produtos if f"{p[1]} - Tamanho: {p[3]} - Cor: {p[4]} - Estoque: {p[6]} - R$ {p[5]:.2f}" == produto_selecionado)
                            produto = next(p for p in produtos if p[0] == produto_id)
                            
                            if quantidade > produto[6]:
                                st.error("❌ Quantidade indisponível em estoque!")
                            else:
                                item = {
                                    'produto_id': produto_id,
                                    'nome': produto[1],
                                    'tamanho': produto[3],
                                    'cor': produto[4],
                                    'quantidade': quantidade,
                                    'preco_unitario': float(produto[5]),
                                    'subtotal': float(produto[5]) * quantidade
                                }
                                st.session_state.itens_venda.append(item)
                                st.success("✅ Item adicionado à venda!")
                                st.rerun()
                    
                    # Itens da venda
                    if 'itens_venda' in st.session_state and st.session_state.itens_venda:
                        st.markdown("#### 📋 Itens da Venda")
                        
                        for i, item in enumerate(st.session_state.itens_venda):
                            col1, col2, col3, col4, col5 = st.columns([3,1,1,1,1])
                            with col1:
                                st.write(f"**{item['nome']}**")
                                st.write(f"Tamanho: {item['tamanho']} | Cor: {item['cor']}")
                            with col2:
                                st.write(f"**Qtd:** {item['quantidade']}")
                            with col3:
                                st.write(f"**R$ {item['preco_unitario']:.2f}**")
                            with col4:
                                st.write(f"**R$ {item['subtotal']:.2f}**")
                            with col5:
                                if st.button("❌", key=f"del_venda_{i}"):
                                    st.session_state.itens_venda.pop(i)
                                    st.rerun()
                        
                        total_venda = sum(item['subtotal'] for item in st.session_state.itens_venda)
                        st.markdown(f"<div class='success-card'><h3>💰 Total da Venda: R$ {total_venda:.2f}</h3></div>", unsafe_allow_html=True)
                        
                        # Finalizar venda
                        col1, col2 = st.columns(2)
                        with col1:
                            forma_pagamento = st.selectbox(
                                "💳 **Forma de Pagamento:**",
                                ["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "PIX", "Transferência"]
                            )
                        with col2:
                            observacoes = st.text_area("📝 **Observações:**")
                        
                        if st.button("✅ **Finalizar Venda**", type="primary", use_container_width=True):
                            if st.session_state.itens_venda:
                                sucesso, resultado = adicionar_pedido(
                                    cliente_id, 
                                    escola_venda_id,
                                    st.session_state.itens_venda, 
                                    date.today(), 
                                    forma_pagamento,
                                    observacoes
                                )
                                if sucesso:
                                    st.success(f"✅ Venda #{resultado} realizada com sucesso!")
                                    st.balloons()
                                    del st.session_state.itens_venda
                                    st.rerun()
                                else:
                                    st.error(f"❌ Erro ao realizar venda: {resultado}")
    
    with col2:
        st.markdown("<h3 class='section-header'>📊 Resumo</h3>", unsafe_allow_html=True)
        
        # Métricas rápidas
        total_produtos = len(listar_produtos_por_escola(escola_venda_id))
        st.metric("📦 Produtos Disponíveis", total_produtos)
        
        if 'itens_venda' in st.session_state:
            total_itens = len(st.session_state.itens_venda)
            st.metric("🛒 Itens na Venda", total_itens)
        
        # Cliente selecionado
        if cliente_selecionado:
            st.markdown("<div class='info-card'>", unsafe_allow_html=True)
            st.write("👤 **Cliente Selecionado:**")
            st.write(cliente_selecionado.split("(ID: ")[0])
            st.markdown("</div>", unsafe_allow_html=True)

# =========================================
# 👕 PÁGINA - PRODUTOS
# =========================================

elif menu == "👕 Produtos":
    st.markdown("<h1 class='main-header'>👕 Gestão de Produtos</h1>", unsafe_allow_html=True)
    
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada. Configure as escolas primeiro.")
        st.stop()
    
    tab1, tab2 = st.tabs(["➕ Cadastrar Produto", "📋 Lista de Produtos"])
    
    with tab1:
        st.markdown("<h2 class='section-header'>➕ Cadastrar Novo Produto</h2>", unsafe_allow_html=True)
        
        with st.form("novo_produto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                escola_produto = st.selectbox(
                    "🏫 **Escola:**",
                    [e[1] for e in escolas],
                    key="produto_escola"
                )
                escola_id = next(e[0] for e in escolas if e[1] == escola_produto)
                
                nome = st.text_input("📝 **Nome do Produto***", placeholder="Ex: Camiseta Básica")
                categoria = st.selectbox("📂 **Categoria***", categorias_produtos)
                tamanho = st.selectbox("📏 **Tamanho***", todos_tamanhos)
            
            with col2:
                cor = st.text_input("🎨 **Cor***", value="Branco", placeholder="Ex: Azul Marinho")
                preco = st.number_input("💰 **Preço (R$)***", min_value=0.0, value=29.90, step=0.01)
                estoque = st.number_input("📦 **Estoque Inicial***", min_value=0, value=10)
                descricao = st.text_area("📄 **Descrição**", placeholder="Detalhes do produto...")
            
            if st.form_submit_button("✅ **Cadastrar Produto**", type="primary"):
                if nome and cor:
                    sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id)
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Campos obrigatórios: Nome e Cor")
    
    with tab2:
        st.markdown("<h2 class='section-header'>📋 Produtos Cadastrados</h2>", unsafe_allow_html=True)
        
        # Filtro por escola
        escola_filtro = st.selectbox(
            "🏫 **Filtrar por Escola:**",
            ["Todas as escolas"] + [e[1] for e in escolas],
            key="filtro_produtos"
        )
        
        if escola_filtro == "Todas as escolas":
            produtos = listar_produtos_por_escola()
        else:
            escola_id = next(e[0] for e in escolas if e[1] == escola_filtro)
            produtos = listar_produtos_por_escola(escola_id)
        
        if produtos:
            # Métricas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📦 Total de Produtos", len(produtos))
            with col2:
                total_estoque = sum(p[6] for p in produtos)
                st.metric("🔄 Estoque Total", total_estoque)
            with col3:
                baixo_estoque = len([p for p in produtos if p[6] < 5])
                st.metric("⚠️ Estoque Baixo", baixo_estoque)
            
            # Tabela de produtos
            dados = []
            for produto in produtos:
                status_estoque = "✅" if produto[6] >= 5 else "⚠️" if produto[6] > 0 else "❌"
                
                dados.append({
                    'ID': produto[0],
                    'Produto': produto[1],
                    'Categoria': produto[2],
                    'Tamanho': produto[3],
                    'Cor': produto[4],
                    'Preço': f"R$ {produto[5]:.2f}",
                    'Estoque': f"{status_estoque} {produto[6]}",
                    'Escola': produto[9],
                    'Descrição': produto[7] or 'N/A'
                })
            
            df = pd.DataFrame(dados)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("👕 Nenhum produto cadastrado")

# =========================================
# 👥 PÁGINA - CLIENTES
# =========================================

elif menu == "👥 Clientes":
    st.markdown("<h1 class='main-header'>👥 Gestão de Clientes</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["➕ Cadastrar Cliente", "📋 Lista de Clientes"])
    
    with tab1:
        st.markdown("<h2 class='section-header'>➕ Novo Cliente</h2>", unsafe_allow_html=True)
        
        with st.form("novo_cliente", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("👤 **Nome completo***", placeholder="Digite o nome completo")
                telefone = st.text_input("📞 **Telefone**", placeholder="(11) 99999-9999")
            
            with col2:
                email = st.text_input("📧 **Email**", placeholder="cliente@email.com")
            
            if st.form_submit_button("✅ **Cadastrar Cliente**", type="primary"):
                if nome:
                    sucesso, msg = adicionar_cliente(nome, telefone, email)
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome é obrigatório!")
    
    with tab2:
        st.markdown("<h2 class='section-header'>📋 Clientes Cadastrados</h2>", unsafe_allow_html=True)
        clientes = listar_clientes()
        
        if clientes:
            dados = []
            for cliente in clientes:
                dados.append({
                    'ID': cliente[0],
                    'Nome': cliente[1],
                    'Telefone': cliente[2] or 'N/A',
                    'Email': cliente[3] or 'N/A',
                    'Data Cadastro': cliente[4]
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
            
            # Métricas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("👥 Total Clientes", len(clientes))
            with col2:
                clientes_30_dias = len([c for c in clientes if datetime.strptime(c[4], '%Y-%m-%d').date() >= date.today() - timedelta(days=30)])
                st.metric("🆕 Últimos 30 dias", clientes_30_dias)
        else:
            st.info("👥 Nenhum cliente cadastrado")

# =========================================
# 📦 PÁGINA - ESTOQUE
# =========================================

elif menu == "📦 Estoque":
    st.markdown("<h1 class='main-header'>📦 Controle de Estoque</h1>", unsafe_allow_html=True)
    
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada. Configure as escolas primeiro.")
        st.stop()
    
    # Abas por escola
    tabs = st.tabs([f"🏫 {e[1]}" for e in escolas])
    
    for idx, escola in enumerate(escolas):
        with tabs[idx]:
            st.markdown(f"<h2 class='section-header'>📦 Estoque - {escola[1]}</h2>", unsafe_allow_html=True)
            
            produtos = listar_produtos_por_escola(escola[0])
            
            if produtos:
                # Métricas da escola
                col1, col2, col3, col4 = st.columns(4)
                total_produtos = len(produtos)
                total_estoque = sum(p[6] for p in produtos)
                produtos_baixo_estoque = len([p for p in produtos if p[6] < 5])
                produtos_sem_estoque = len([p for p in produtos if p[6] == 0])
                
                with col1:
                    st.metric("📦 Total Produtos", total_produtos)
                with col2:
                    st.metric("🔄 Estoque Total", total_estoque)
                with col3:
                    st.metric("⚠️ Estoque Baixo", produtos_baixo_estoque)
                with col4:
                    st.metric("❌ Sem Estoque", produtos_sem_estoque)
                
                # Tabela de estoque
                st.markdown("#### 📋 Situação do Estoque")
                dados_estoque = []
                for produto in produtos:
                    status = "✅ Suficiente" if produto[6] >= 5 else "⚠️ Baixo" if produto[6] > 0 else "❌ Esgotado"
                    cor_status = "green" if produto[6] >= 5 else "orange" if produto[6] > 0 else "red"
                    
                    dados_estoque.append({
                        'Produto': produto[1],
                        'Categoria': produto[2],
                        'Tamanho': produto[3],
                        'Cor': produto[4],
                        'Estoque Atual': produto[6],
                        'Status': status
                    })
                
                df_estoque = pd.DataFrame(dados_estoque)
                st.dataframe(df_estoque, use_container_width=True)
                
                # Alertas de estoque baixo
                produtos_alerta = [p for p in produtos if p[6] < 5]
                if produtos_alerta:
                    st.markdown("#### 🚨 Alertas de Estoque")
                    for produto in produtos_alerta:
                        if produto[6] == 0:
                            st.error(f"**{produto[1]} - {produto[3]} - {produto[4]}**: ❌ ESGOTADO")
                        else:
                            st.warning(f"**{produto[1]} - {produto[3]} - {produto[4]}**: ⚠️ Apenas {produto[6]} unidades")
            
            else:
                st.info(f"👕 Nenhum produto cadastrado para {escola[1]}")

# =========================================
# 📈 PÁGINA - RELATÓRIOS
# =========================================

elif menu == "📈 Relatórios":
    st.markdown("<h1 class='main-header'>📈 Relatórios e Analytics</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📊 Vendas", "📦 Produtos", "👥 Clientes"])
    
    with tab1:
        st.markdown("<h2 class='section-header'>📊 Relatório de Vendas</h2>", unsafe_allow_html=True)
        
        pedidos = listar_pedidos_por_escola()
        
        if pedidos:
            # Métricas de vendas
            col1, col2, col3, col4 = st.columns(4)
            total_vendas = sum(float(p[9]) for p in pedidos)
            pedidos_entregues = len([p for p in pedidos if p[3] == 'Entregue'])
            ticket_medio = total_vendas / len(pedidos) if pedidos else 0
            
            with col1:
                st.metric("💰 Total em Vendas", f"R$ {total_vendas:,.2f}")
            with col2:
                st.metric("📦 Total de Pedidos", len(pedidos))
            with col3:
                st.metric("✅ Pedidos Entregues", pedidos_entregues)
            with col4:
                st.metric("📊 Ticket Médio", f"R$ {ticket_medio:.2f}")
            
            # Gráfico de vendas por status
            status_counts = {}
            for pedido in pedidos:
                status = pedido[3]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            if status_counts:
                df_status = pd.DataFrame(list(status_counts.items()), columns=['Status', 'Quantidade'])
                fig = px.pie(df_status, values='Quantidade', names='Status', 
                            title='Distribuição de Pedidos por Status',
                            color_discrete_sequence=px.colors.sequential.Rainbow)
                st.plotly_chart(fig, use_container_width=True)
        
        else:
            st.info("📊 Nenhum dado de venda disponível")
    
    with tab2:
        st.markdown("<h2 class='section-header'>📦 Relatório de Produtos</h2>", unsafe_allow_html=True)
        
        produtos = listar_produtos_por_escola()
        
        if produtos:
            # Análise por categoria
            categorias = {}
            for produto in produtos:
                categoria = produto[2]
                categorias[categoria] = categorias.get(categoria, 0) + 1
            
            if categorias:
                df_categorias = pd.DataFrame(list(categorias.items()), columns=['Categoria', 'Quantidade'])
                fig = px.bar(df_categorias, x='Categoria', y='Quantidade',
                            title='Produtos por Categoria',
                            color='Categoria')
                st.plotly_chart(fig, use_container_width=True)
        
        else:
            st.info("📦 Nenhum produto cadastrado")
    
    with tab3:
        st.markdown("<h2 class='section-header'>👥 Relatório de Clientes</h2>", unsafe_allow_html=True)
        
        clientes = listar_clientes()
        
        if clientes:
            # Evolução de cadastros
            cadastros_por_mes = {}
            for cliente in clientes:
                data_cadastro = datetime.strptime(cliente[4], '%Y-%m-%d')
                mes_ano = data_cadastro.strftime('%Y-%m')
                cadastros_por_mes[mes_ano] = cadastros_por_mes.get(mes_ano, 0) + 1
            
            if cadastros_por_mes:
                df_cadastros = pd.DataFrame(list(cadastros_por_mes.items()), columns=['Mês', 'Novos Clientes'])
                df_cadastros = df_cadastros.sort_values('Mês')
                
                fig = px.line(df_cadastros, x='Mês', y='Novos Clientes',
                            title='Evolução de Cadastros de Clientes',
                            markers=True)
                st.plotly_chart(fig, use_container_width=True)
        
        else:
            st.info("👥 Nenhum cliente cadastrado")

# =========================================
# ⚙️ PÁGINA - CONFIGURAÇÕES
# =========================================

elif menu == "⚙️ Configurações":
    st.markdown("<h1 class='main-header'>⚙️ Configurações do Sistema</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🏫 Escolas", "🔐 Segurança", "💾 Sistema"])
    
    with tab1:
        st.markdown("<h2 class='section-header'>🏫 Gestão de Escolas</h2>", unsafe_allow_html=True)
        
        escolas = listar_escolas()
        
        if escolas:
            st.markdown("#### 📋 Escolas Cadastradas")
            for escola in escolas:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{escola[1]}**")
                with col2:
                    produtos_escola = listar_produtos_por_escola(escola[0])
                    st.write(f"**{len(produtos_escola)}** produtos")
                with col3:
                    if st.button("📊 Ver", key=f"ver_{escola[0]}"):
                        st.session_state.menu = "📦 Estoque"
                        st.rerun()
        
        # Adicionar nova escola
        st.markdown("#### ➕ Adicionar Nova Escola")
        with st.form("nova_escola"):
            nova_escola = st.text_input("Nome da Nova Escola")
            if st.form_submit_button("✅ Adicionar Escola"):
                if nova_escola:
                    conn = get_connection()
                    if conn:
                        try:
                            cur = conn.cursor()
                            cur.execute("INSERT INTO escolas (nome) VALUES (%s)", (nova_escola,))
                            conn.commit()
                            st.success(f"✅ Escola '{nova_escola}' adicionada com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao adicionar escola: {e}")
                        finally:
                            conn.close()
    
    with tab2:
        st.markdown("<h2 class='section-header'>🔐 Segurança e Acesso</h2>", unsafe_allow_html=True)
        
        st.markdown("#### 🔄 Alterar Senha")
        with st.form("alterar_senha"):
            senha_atual = st.text_input("Senha Atual", type='password')
            nova_senha1 = st.text_input("Nova Senha", type='password')
            nova_senha2 = st.text_input("Confirmar Nova Senha", type='password')
            
            if st.form_submit_button("🔄 Alterar Senha"):
                if senha_atual and nova_senha1 and nova_senha2:
                    if nova_senha1 == nova_senha2:
                        conn = get_connection()
                        if conn:
                            try:
                                cur = conn.cursor()
                                cur.execute('SELECT password_hash FROM usuarios WHERE username = %s', (st.session_state.username,))
                                resultado = cur.fetchone()
                                
                                if resultado and check_hashes(senha_atual, resultado[0]):
                                    nova_senha_hash = make_hashes(nova_senha1)
                                    cur.execute(
                                        'UPDATE usuarios SET password_hash = %s WHERE username = %s',
                                        (nova_senha_hash, st.session_state.username)
                                    )
                                    conn.commit()
                                    st.success("✅ Senha alterada com sucesso!")
                                else:
                                    st.error("❌ Senha atual incorreta")
                            except Exception as e:
                                st.error(f"❌ Erro: {str(e)}")
                            finally:
                                conn.close()
                    else:
                        st.error("❌ As novas senhas não coincidem")
                else:
                    st.error("❌ Preencha todos os campos")
    
    with tab3:
        st.markdown("<h2 class='section-header'>💾 Informações do Sistema</h2>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<div class='info-card'>", unsafe_allow_html=True)
            st.write("**📊 Estatísticas do Sistema:**")
            st.write(f"• 👥 Usuários: 2")
            st.write(f"• 🏫 Escolas: {len(listar_escolas())}")
            st.write(f"• 👕 Produtos: {len(listar_produtos_por_escola())}")
            st.write(f"• 📦 Pedidos: {len(listar_pedidos_por_escola())}")
            st.write(f"• 👤 Clientes: {len(listar_clientes())}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='success-card'>", unsafe_allow_html=True)
            st.write("**🔄 Ações do Sistema:**")
            if st.button("🔄 Recarregar Dados", use_container_width=True):
                st.rerun()
            if st.button("🗃️ Reinicializar Banco", use_container_width=True):
                init_db()
                st.success("✅ Banco reinicializado!")
            st.markdown("</div>", unsafe_allow_html=True)

# =========================================
# 🎯 RODAPÉ DO SISTEMA
# =========================================

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style='text-align: center; color: white;'>
    <p><strong>👕 FashionManager Pro v2.0</strong></p>
    <p>🚀 Sistema completo de gestão</p>
    <p>💾 PostgreSQL | ☁️ Render</p>
</div>
""", unsafe_allow_html=True)
