import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import os
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
import time

# =========================================
# 🚀 CONFIGURAÇÃO PARA RENDER - POSTGRESQL
# =========================================

def get_connection():
    """Estabelece conexão com PostgreSQL usando a URL do Render"""
    try:
        # URL do PostgreSQL fornecida pelo Render
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            st.error("❌ DATABASE_URL não encontrada. Configure a variável de ambiente no Render.")
            return None
        
        # Corrigir a URL se começar com postgres://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        # Conectar ao PostgreSQL
        conn = psycopg2.connect(
            database_url,
            cursor_factory=RealDictCursor,
            sslmode='require'
        )
        return conn
        
    except Exception as e:
        st.error(f"❌ Erro de conexão com o banco: {str(e)}")
        return None

def init_db():
    """Inicializa o banco PostgreSQL"""
    conn = get_connection()
    if not conn:
        st.error("Não foi possível conectar ao banco de dados")
        return
    
    try:
        cur = conn.cursor()
        
        # Tabela de usuários
        cur.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                nome_completo VARCHAR(100),
                tipo VARCHAR(20) DEFAULT 'vendedor',
                ativo BOOLEAN DEFAULT TRUE,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de escolas
        cur.execute('''
            CREATE TABLE IF NOT EXISTS escolas (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) UNIQUE NOT NULL
            )
        ''')
        
        # Tabela de clientes
        cur.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                telefone VARCHAR(20),
                email VARCHAR(100),
                data_cadastro DATE DEFAULT CURRENT_DATE
            )
        ''')
        
        # Tabela de produtos
        cur.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                categoria VARCHAR(50),
                tamanho VARCHAR(10),
                cor VARCHAR(50),
                preco DECIMAL(10,2),
                estoque INTEGER DEFAULT 0,
                descricao TEXT,
                escola_id INTEGER REFERENCES escolas(id),
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(nome, tamanho, cor, escola_id)
            )
        ''')
        
        # Tabela de pedidos
        cur.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id SERIAL PRIMARY KEY,
                cliente_id INTEGER REFERENCES clientes(id),
                escola_id INTEGER REFERENCES escolas(id),
                status VARCHAR(50) DEFAULT 'Pendente',
                data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_entrega_prevista DATE,
                data_entrega_real DATE,
                forma_pagamento VARCHAR(50) DEFAULT 'Dinheiro',
                quantidade_total INTEGER,
                valor_total DECIMAL(10,2),
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
                preco_unitario DECIMAL(10,2),
                subtotal DECIMAL(10,2)
            )
        ''')
        
        # Inserir usuários padrão
        usuarios_padrao = [
            ('admin', make_hashes('admin123'), 'Administrador', 'admin'),
            ('vendedor', make_hashes('vendedor123'), 'Vendedor', 'vendedor')
        ]
        
        for username, password_hash, nome, tipo in usuarios_padrao:
            try:
                cur.execute('''
                    INSERT INTO usuarios (username, password_hash, nome_completo, tipo) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                ''', (username, password_hash, nome, tipo))
            except Exception as e:
                print(f"Erro ao inserir usuário {username}: {e}")
        
        # Inserir escolas padrão
        escolas_padrao = ['Municipal', 'Desperta', 'São Tadeu']
        for escola in escolas_padrao:
            try:
                cur.execute('INSERT INTO escolas (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING', (escola,))
            except Exception as e:
                print(f"Erro ao inserir escola {escola}: {e}")
        
        conn.commit()
        
    except Exception as e:
        st.error(f"Erro ao inicializar banco: {str(e)}")
        conn.rollback()
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
        cur.execute('SELECT password_hash, nome_completo, tipo FROM usuarios WHERE username = %s AND ativo = true', (username,))
        resultado = cur.fetchone()
        
        if resultado and check_hashes(password, resultado['password_hash']):
            return True, resultado['nome_completo'], resultado['tipo']
        else:
            return False, "Credenciais inválidas", None
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        conn.close()

# =========================================
# 🔐 SISTEMA DE LOGIN
# =========================================

def login():
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type='password')
    
    if st.sidebar.button("Entrar"):
        if username and password:
            sucesso, mensagem, tipo_usuario = verificar_login(username, password)
            if sucesso:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.nome_usuario = mensagem
                st.session_state.tipo_usuario = tipo_usuario
                st.sidebar.success(f"Bem-vindo, {mensagem}!")
                st.rerun()
            else:
                st.sidebar.error(mensagem)
        else:
            st.sidebar.error("Preencha todos os campos")

# =========================================
# 🚀 SISTEMA PRINCIPAL
# =========================================

# Configuração da página
st.set_page_config(
    page_title="Sistema de Fardamentos",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialização do banco
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# CONFIGURAÇÕES
tamanhos_infantil = ["2", "4", "6", "8", "10", "12"]
tamanhos_adulto = ["PP", "P", "M", "G", "GG"]
todos_tamanhos = tamanhos_infantil + tamanhos_adulto
categorias_produtos = ["Camisetas", "Calças/Shorts", "Agasalhos", "Acessórios", "Outros"]

# =========================================
# 🔧 FUNÇÕES DO BANCO DE DADOS - POSTGRESQL
# =========================================

def formatar_data_brasil(data_str):
    """Converte data para formato brasileiro"""
    if not data_str:
        return ""
    try:
        if isinstance(data_str, str):
            data_obj = datetime.strptime(data_str, "%Y-%m-%d")
            return data_obj.strftime("%d/%m/%Y")
        elif isinstance(data_str, datetime):
            return data_str.strftime("%d/%m/%Y")
        else:
            return str(data_str)
    except:
        return data_str

def listar_escolas():
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM escolas ORDER BY nome")
        escolas = cur.fetchall()
        return [dict(escola) for escola in escolas]
    except Exception as e:
        st.error(f"Erro ao listar escolas: {e}")
        return []
    finally:
        conn.close()

def listar_clientes():
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM clientes ORDER BY nome')
        clientes = cur.fetchall()
        return [dict(cliente) for cliente in clientes]
    except Exception as e:
        st.error(f"Erro ao listar clientes: {e}")
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
        return True, "Cliente cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
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
        produtos = cur.fetchall()
        return [dict(produto) for produto in produtos]
    except Exception as e:
        st.error(f"Erro ao listar produtos: {e}")
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

def atualizar_estoque(produto_id, nova_quantidade):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    try:
        cur = conn.cursor()
        cur.execute("UPDATE produtos SET estoque = %s WHERE id = %s", (nova_quantidade, produto_id))
        conn.commit()
        return True, "Estoque atualizado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
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
        
        # Verificar estoque (apenas alerta, não bloqueia)
        alertas_estoque = []
        for item in itens:
            cur.execute("SELECT estoque, nome FROM produtos WHERE id = %s", (item['produto_id'],))
            produto = cur.fetchone()
            if produto and produto['estoque'] < item['quantidade']:
                alertas_estoque.append(f"{produto['nome']} - Estoque: {produto['estoque']}, Pedido: {item['quantidade']}")
        
        # Criar pedido
        cur.execute('''
            INSERT INTO pedidos (cliente_id, escola_id, data_entrega_prevista, forma_pagamento, quantidade_total, valor_total, observacoes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (cliente_id, escola_id, data_entrega, forma_pagamento, quantidade_total, valor_total, observacoes))
        
        pedido_id = cur.fetchone()['id']
        
        # Inserir itens do pedido
        for item in itens:
            cur.execute('''
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            ''', (pedido_id, item['produto_id'], item['quantidade'], item['preco_unitario'], item['subtotal']))
        
        conn.commit()
        
        mensagem = f"✅ Pedido #{pedido_id} criado com sucesso!"
        if alertas_estoque:
            mensagem += f" ⚠️ Alertas de estoque: {', '.join(alertas_estoque)}"
            
        return True, mensagem
        
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
        pedidos = cur.fetchall()
        return [dict(pedido) for pedido in pedidos]
    except Exception as e:
        st.error(f"Erro ao listar pedidos: {e}")
        return []
    finally:
        conn.close()

def atualizar_status_pedido(pedido_id, novo_status):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        if novo_status == 'Entregue':
            data_entrega = datetime.now().strftime("%Y-%m-%d")
            cur.execute('UPDATE pedidos SET status = %s, data_entrega_real = %s WHERE id = %s', (novo_status, data_entrega, pedido_id))
        else:
            cur.execute('UPDATE pedidos SET status = %s WHERE id = %s', (novo_status, pedido_id))
            
        conn.commit()
        return True, "✅ Status do pedido atualizado com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def excluir_pedido(pedido_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM pedidos WHERE id = %s", (pedido_id,))
        conn.commit()
        return True, "Pedido excluído com sucesso"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def baixar_estoque_pedido(pedido_id):
    """Baixa o estoque quando o pedido é marcado como entregue"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Buscar itens do pedido
        cur.execute('''
            SELECT pi.produto_id, pi.quantidade 
            FROM pedido_itens pi 
            WHERE pi.pedido_id = %s
        ''', (pedido_id,))
        itens = cur.fetchall()
        
        # Baixar estoque
        for item in itens:
            produto_id, quantidade = item['produto_id'], item['quantidade']
            cur.execute("UPDATE produtos SET estoque = estoque - %s WHERE id = %s", (quantidade, produto_id))
        
        conn.commit()
        return True, "✅ Estoque baixado com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao baixar estoque: {str(e)}"
    finally:
        conn.close()

def gerar_relatorio_vendas_por_escola(escola_id=None):
    """Gera relatório de vendas por período e escola"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        
        if escola_id:
            cur.execute('''
                SELECT 
                    DATE(p.data_pedido) as data,
                    COUNT(*) as total_pedidos,
                    SUM(p.quantidade_total) as total_itens,
                    SUM(p.valor_total) as total_vendas
                FROM pedidos p
                WHERE p.escola_id = %s AND p.status != 'Cancelado'
                GROUP BY DATE(p.data_pedido)
                ORDER BY data DESC
            ''', (escola_id,))
        else:
            cur.execute('''
                SELECT 
                    DATE(p.data_pedido) as data,
                    e.nome as escola,
                    COUNT(*) as total_pedidos,
                    SUM(p.quantidade_total) as total_itens,
                    SUM(p.valor_total) as total_vendas
                FROM pedidos p
                JOIN escolas e ON p.escola_id = e.id
                WHERE p.status != 'Cancelado'
                GROUP BY DATE(p.data_pedido), e.nome
                ORDER BY data DESC
            ''')
            
        dados = cur.fetchall()
        
        if dados:
            if escola_id:
                df = pd.DataFrame(dados, columns=['Data', 'Total Pedidos', 'Total Itens', 'Total Vendas (R$)'])
            else:
                df = pd.DataFrame(dados, columns=['Data', 'Escola', 'Total Pedidos', 'Total Itens', 'Total Vendas (R$)'])
            
            # Formatar data no padrão brasileiro
            df['Data'] = df['Data'].apply(formatar_data_brasil)
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def gerar_relatorio_produtos_por_escola(escola_id=None):
    """Gera relatório de produtos mais vendidos por escola"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        
        if escola_id:
            cur.execute('''
                SELECT 
                    pr.nome as produto,
                    pr.categoria,
                    pr.tamanho,
                    pr.cor,
                    SUM(pi.quantidade) as total_vendido,
                    SUM(pi.subtotal) as total_faturado
                FROM pedido_itens pi
                JOIN produtos pr ON pi.produto_id = pr.id
                JOIN pedidos p ON pi.pedido_id = p.id
                WHERE p.escola_id = %s AND p.status != 'Cancelado'
                GROUP BY pr.id, pr.nome, pr.categoria, pr.tamanho, pr.cor
                ORDER BY total_vendido DESC
            ''', (escola_id,))
        else:
            cur.execute('''
                SELECT 
                    pr.nome as produto,
                    pr.categoria,
                    pr.tamanho,
                    pr.cor,
                    e.nome as escola,
                    SUM(pi.quantidade) as total_vendido,
                    SUM(pi.subtotal) as total_faturado
                FROM pedido_itens pi
                JOIN produtos pr ON pi.produto_id = pr.id
                JOIN pedidos p ON pi.pedido_id = p.id
                JOIN escolas e ON p.escola_id = e.id
                WHERE p.status != 'Cancelado'
                GROUP BY pr.id, pr.nome, pr.categoria, pr.tamanho, pr.cor, e.nome
                ORDER BY total_vendido DESC
            ''')
            
        dados = cur.fetchall()
        
        if dados:
            if escola_id:
                df = pd.DataFrame(dados, columns=['Produto', 'Categoria', 'Tamanho', 'Cor', 'Total Vendido', 'Total Faturado (R$)'])
            else:
                df = pd.DataFrame(dados, columns=['Produto', 'Categoria', 'Tamanho', 'Cor', 'Escola', 'Total Vendido', 'Total Faturado (R$)'])
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# =========================================
# 🎨 INTERFACE PRINCIPAL
# =========================================

# Sidebar - Informações do usuário
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **Usuário:** {st.session_state.nome_usuario}")
st.sidebar.write(f"🎯 **Tipo:** {st.session_state.tipo_usuario}")

# Botão de logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Menu principal
st.sidebar.title("👕 Sistema de Fardamentos")
menu_options = ["📊 Dashboard", "📦 Pedidos", "👥 Clientes", "👕 Produtos", "📦 Estoque", "📈 Relatórios"]
menu = st.sidebar.radio("Navegação", menu_options)

# Header dinâmico
st.title(f"{menu} - Sistema de Fardamentos")
st.markdown("---")

# =========================================
# 📱 PÁGINAS DO SISTEMA
# =========================================

if menu == "📊 Dashboard":
    st.header("🎯 Dashboard - Visão Geral")
    
    escolas = listar_escolas()
    clientes = listar_clientes()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Escolas", len(escolas))
    
    with col2:
        st.metric("Total de Clientes", len(clientes))
    
    with col3:
        total_produtos = 0
        for escola in escolas:
            produtos = listar_produtos_por_escola(escola['id'])
            total_produtos += len(produtos)
        st.metric("Total de Produtos", total_produtos)
    
    with col4:
        produtos_baixo_estoque = 0
        for escola in escolas:
            produtos = listar_produtos_por_escola(escola['id'])
            produtos_baixo_estoque += len([p for p in produtos if p.get('estoque', 0) < 5])
        st.metric("Alertas de Estoque", produtos_baixo_estoque)
    
    st.success("🚀 Sistema funcionando com PostgreSQL - Dados persistentes!")

elif menu == "👥 Clientes":
    tab1, tab2 = st.tabs(["➕ Cadastrar Cliente", "📋 Listar Clientes"])
    
    with tab1:
        st.header("➕ Novo Cliente")
        
        with st.form("form_cliente"):
            nome = st.text_input("👤 Nome completo*")
            telefone = st.text_input("📞 Telefone")
            email = st.text_input("📧 Email")
            
            if st.form_submit_button("✅ Cadastrar Cliente", type="primary"):
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
        st.header("📋 Clientes Cadastrados")
        clientes = listar_clientes()
        
        if clientes:
            dados = []
            for cliente in clientes:
                dados.append({
                    'ID': cliente['id'],
                    'Nome': cliente['nome'],
                    'Telefone': cliente['telefone'] or 'N/A',
                    'Email': cliente['email'] or 'N/A',
                    'Data Cadastro': formatar_data_brasil(cliente['data_cadastro'])
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
        else:
            st.info("👥 Nenhum cliente cadastrado")

elif menu == "👕 Produtos":
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada. O sistema precisa de escolas para cadastrar produtos.")
        st.stop()
    
    # Seleção da escola
    escola_selecionada_nome = st.selectbox(
        "🏫 Selecione a Escola:",
        [e['nome'] for e in escolas],
        key="produtos_escola"
    )
    escola_id = next(e['id'] for e in escolas if e['nome'] == escola_selecionada_nome)
    
    st.header(f"👕 Produtos - {escola_selecionada_nome}")
    
    tab1, tab2 = st.tabs(["➕ Cadastrar Novo", "📋 Lista de Produtos"])
    
    with tab1:
        st.subheader("➕ Cadastrar Novo Produto")
        
        with st.form("novo_produto_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("📝 Nome do Produto*", placeholder="Ex: Camiseta Polo")
                categoria = st.selectbox("📂 Categoria*", categorias_produtos)
                tamanho = st.selectbox("📏 Tamanho*", todos_tamanhos)
            with col2:
                cor = st.text_input("🎨 Cor*", placeholder="Ex: Branco")
                preco = st.number_input("💰 Preço (R$)*", min_value=0.0, value=29.90, step=0.01)
                estoque = st.number_input("📦 Estoque Inicial*", min_value=0, value=10)
            
            descricao = st.text_area("📄 Descrição (opcional)", placeholder="Detalhes do produto...")
            
            if st.form_submit_button("✅ Cadastrar Produto", type="primary"):
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
        st.subheader("📋 Lista de Produtos")
        produtos = listar_produtos_por_escola(escola_id)
        
        if produtos:
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                filtro_categoria = st.selectbox("Filtrar por categoria:", ["Todas"] + categorias_produtos)
            with col2:
                busca_nome = st.text_input("Buscar por nome:")
            
            # Aplicar filtros
            produtos_filtrados = produtos
            if filtro_categoria != "Todas":
                produtos_filtrados = [p for p in produtos_filtrados if p['categoria'] == filtro_categoria]
            if busca_nome:
                produtos_filtrados = [p for p in produtos_filtrados if busca_nome.lower() in p['nome'].lower()]
            
            # Exibir produtos
            for produto in produtos_filtrados:
                status_estoque = "✅" if produto['estoque'] >= 10 else "⚠️" if produto['estoque'] >= 5 else "❌"
                
                with st.expander(f"{status_estoque} {produto['nome']} - {produto['tamanho']} - {produto['cor']}"):
                    col1, col2 = st.columns([3,1])
                    with col1:
                        st.write(f"**Categoria:** {produto['categoria']}")
                        st.write(f"**Preço:** R$ {produto['preco']:.2f}")
                        st.write(f"**Estoque:** {produto['estoque']} unidades")
                        st.write(f"**Descrição:** {produto['descricao'] or 'Sem descrição'}")
                    with col2:
                        # Edição de estoque
                        novo_estoque = st.number_input("Estoque:", value=produto['estoque'], min_value=0, key=f"estoque_{produto['id']}")
                        if st.button("💾 Atualizar", key=f"btn_{produto['id']}"):
                            if novo_estoque != produto['estoque']:
                                sucesso, msg = atualizar_estoque(produto['id'], novo_estoque)
                                if sucesso:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
        else:
            st.info("📭 Nenhum produto cadastrado para esta escola")

# ... (CONTINUA COM AS OUTRAS PÁGINAS IGUAL AO CÓDIGO ANTERIOR)

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("👕 Sistema de Fardamentos v3.0\n\n🗄️ **PostgreSQL** - Dados persistentes!")

# Botão para recarregar
if st.sidebar.button("🔄 Recarregar Dados"):
    st.rerun()
