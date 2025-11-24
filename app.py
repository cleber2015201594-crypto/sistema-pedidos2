import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date
import os

# =========================================
# 🎯 CONFIGURAÇÃO
# =========================================

st.set_page_config(
    page_title="Sistema Fardamentos",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Mobile
st.markdown("""
<style>
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem;
        }
        .stButton button {
            width: 100%;
            padding: 0.75rem;
        }
        .stTextInput input, .stSelectbox select, .stNumberInput input {
            font-size: 16px;
            padding: 0.75rem;
        }
    }
    .success-box {
        background: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
    }
    .warning-box {
        background: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #ffeaa7;
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🔐 AUTENTICAÇÃO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def get_connection():
    """Conexão com SQLite"""
    try:
        conn = sqlite3.connect('sistema_fardamentos.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"Erro de conexão: {str(e)}")
        return None

def init_db():
    """Inicializa banco de dados SQLite"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nome_completo TEXT,
                tipo TEXT DEFAULT 'vendedor'
            )
        ''')
        
        # Tabela de escolas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS escolas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL
            )
        ''')
        
        # Tabela de clientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT,
                email TEXT,
                data_cadastro DATE DEFAULT CURRENT_DATE
            )
        ''')
        
        # Tabela de produtos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                categoria TEXT,
                tamanho TEXT,
                cor TEXT,
                preco REAL,
                estoque INTEGER DEFAULT 0,
                escola_id INTEGER,
                FOREIGN KEY (escola_id) REFERENCES escolas (id)
            )
        ''')
        
        # Tabela de pedidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER,
                status TEXT DEFAULT 'Pendente',
                data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_entrega_prevista DATE,
                valor_total REAL,
                observacoes TEXT,
                FOREIGN KEY (cliente_id) REFERENCES clientes (id)
            )
        ''')
        
        # Tabela de itens do pedido
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedido_itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER,
                produto_id INTEGER,
                quantidade INTEGER,
                preco_unitario REAL,
                FOREIGN KEY (pedido_id) REFERENCES pedidos (id),
                FOREIGN KEY (produto_id) REFERENCES produtos (id)
            )
        ''')
        
        # Usuários padrão
        usuarios_padrao = [
            ('admin', make_hashes('admin123'), 'Administrador', 'admin'),
            ('vendedor', make_hashes('vendedor123'), 'Vendedor', 'vendedor')
        ]
        
        for username, password_hash, nome, tipo in usuarios_padrao:
            cursor.execute('''
                INSERT OR IGNORE INTO usuarios (username, password_hash, nome_completo, tipo) 
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, nome, tipo))
        
        # Escolas padrão
        escolas_padrao = ['Municipal', 'Desperta', 'São Tadeu']
        for escola in escolas_padrao:
            cursor.execute('INSERT OR IGNORE INTO escolas (nome) VALUES (?)', (escola,))
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Erro ao inicializar banco: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def verificar_login(username, password):
    """Verifica credenciais"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT password_hash, nome_completo, tipo FROM usuarios WHERE username = ?', (username,))
        resultado = cursor.fetchone()
        
        if resultado and check_hashes(password, resultado[0]):
            return True, resultado[1], resultado[2]
        else:
            return False, "Credenciais inválidas", None
            
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        if conn:
            conn.close()

# =========================================
# 📊 FUNÇÕES DO SISTEMA
# =========================================

def adicionar_cliente(nome, telefone, email):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO clientes (nome, telefone, email) VALUES (?, ?, ?)",
            (nome, telefone, email)
        )
        conn.commit()
        return True, "✅ Cliente cadastrado com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_clientes():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clientes ORDER BY nome')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar clientes: {e}")
        return []
    finally:
        if conn:
            conn.close()

def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, escola_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (nome, categoria, tamanho, cor, preco, estoque, escola_id))
        conn.commit()
        return True, "✅ Produto cadastrado com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_produtos():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, e.nome as escola_nome 
            FROM produtos p 
            LEFT JOIN escolas e ON p.escola_id = e.id 
            ORDER BY p.nome
        ''')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar produtos: {e}")
        return []
    finally:
        if conn:
            conn.close()

def listar_escolas():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM escolas ORDER BY nome")
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar escolas: {e}")
        return []
    finally:
        if conn:
            conn.close()

def atualizar_estoque(produto_id, nova_quantidade):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE produtos SET estoque = ? WHERE id = ?", (nova_quantidade, produto_id))
        conn.commit()
        return True, "✅ Estoque atualizado com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def adicionar_pedido(cliente_id, itens, data_entrega, observacoes):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        valor_total = sum(item['subtotal'] for item in itens)
        
        # Inserir pedido
        cursor.execute('''
            INSERT INTO pedidos (cliente_id, data_entrega_prevista, valor_total, observacoes)
            VALUES (?, ?, ?, ?)
        ''', (cliente_id, data_entrega, valor_total, observacoes))
        
        pedido_id = cursor.lastrowid
        
        # Inserir itens do pedido
        for item in itens:
            cursor.execute('''
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario)
                VALUES (?, ?, ?, ?)
            ''', (pedido_id, item['produto_id'], item['quantidade'], item['preco_unitario']))
            
            # Atualizar estoque
            cursor.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", 
                         (item['quantidade'], item['produto_id']))
        
        conn.commit()
        return True, pedido_id
        
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_pedidos():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, c.nome as cliente_nome
            FROM pedidos p
            JOIN clientes c ON p.cliente_id = c.id
            ORDER BY p.data_pedido DESC
        ''')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar pedidos: {e}")
        return []
    finally:
        if conn:
            conn.close()

# =========================================
# 🚀 APP PRINCIPAL
# =========================================

# Inicialização
if 'db_initialized' not in st.session_state:
    if init_db():
        st.session_state.db_initialized = True
        st.success("✅ Banco de dados inicializado com sucesso!")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Página de Login
if not st.session_state.logged_in:
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h1>👕 Sistema de Fardamentos</h1>
        <p>Faça login para continuar</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
        password = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
        
        submitted = st.form_submit_button("🚀 Entrar", use_container_width=True)
        
        if submitted:
            if username and password:
                with st.spinner("Verificando credenciais..."):
                    sucesso, mensagem, tipo_usuario = verificar_login(username, password)
                    if sucesso:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.nome_usuario = mensagem
                        st.session_state.tipo_usuario = tipo_usuario
                        st.success(f"👋 Bem-vindo, {mensagem}!")
                        st.rerun()
                    else:
                        st.error(mensagem)
            else:
                st.error("Por favor, preencha todos os campos")
    st.stop()

# =========================================
# 📱 INTERFACE PRINCIPAL
# =========================================

# Sidebar
st.sidebar.markdown(f"**👤 {st.session_state.nome_usuario}**")
st.sidebar.markdown(f"**🎯 {st.session_state.tipo_usuario}**")

# Menu principal
menu_options = ["📊 Dashboard", "👥 Clientes", "👕 Produtos", "📦 Pedidos", "📦 Estoque"]
menu = st.sidebar.radio("Navegação", menu_options)

# Header
st.title(menu)
st.markdown("---")

# Páginas do sistema
if menu == "📊 Dashboard":
    st.header("🎯 Visão Geral do Sistema")
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        clientes = listar_clientes()
        st.metric("👥 Clientes", len(clientes))
    
    with col2:
        produtos = listar_produtos()
        st.metric("👕 Produtos", len(produtos))
    
    with col3:
        pedidos = listar_pedidos()
        st.metric("📦 Pedidos", len(pedidos))
    
    with col4:
        produtos_baixo_estoque = len([p for p in produtos if p[6] < 5])
        st.metric("⚠️ Alertas", produtos_baixo_estoque)
    
    # Status do sistema
    st.success("🟢 Sistema funcionando perfeitamente!")
    
    # Ações Rápidas
    st.header("⚡ Ações Rápidas")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("👥 Cadastrar Cliente", use_container_width=True):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col2:
        if st.button("👕 Cadastrar Produto", use_container_width=True):
            st.session_state.menu = "👕 Produtos"
            st.rerun()
    
    with col3:
        if st.button("📦 Novo Pedido", use_container_width=True):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()

elif menu == "👥 Clientes":
    tab1, tab2 = st.tabs(["➕ Cadastrar Cliente", "📋 Listar Clientes"])
    
    with tab1:
        st.header("➕ Novo Cliente")
        
        with st.form("form_cliente"):
            nome = st.text_input("👤 Nome completo*")
            telefone = st.text_input("📞 Telefone")
            email = st.text_input("📧 Email")
            
            submitted = st.form_submit_button("✅ Cadastrar Cliente", use_container_width=True)
            
            if submitted:
                if nome:
                    sucesso, msg = adicionar_cliente(nome, telefone, email)
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ O nome é obrigatório!")
    
    with tab2:
        st.header("📋 Clientes Cadastrados")
        clientes = listar_clientes()
        
        if clientes:
            for cliente in clientes:
                with st.expander(f"👤 {cliente[1]}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**📞 Telefone:** {cliente[2] or 'Não informado'}")
                    with col2:
                        st.write(f"**📧 Email:** {cliente[3] or 'Não informado'}")
                    st.write(f"**📅 Data de Cadastro:** {cliente[4]}")
        else:
            st.info("👥 Nenhum cliente cadastrado no momento.")

elif menu == "👕 Produtos":
    tab1, tab2 = st.tabs(["➕ Cadastrar Produto", "📋 Listar Produtos"])
    
    with tab1:
        st.header("➕ Novo Produto")
        
        with st.form("form_produto"):
            nome = st.text_input("👕 Nome do produto*")
            categoria = st.selectbox("📦 Categoria", ["Camisetas", "Calças/Shorts", "Agasalhos", "Acessórios"])
            tamanho = st.selectbox("📏 Tamanho", ["PP", "P", "M", "G", "GG", "2", "4", "6", "8", "10", "12"])
            cor = st.text_input("🎨 Cor", value="Branco")
            preco = st.number_input("💰 Preço (R$)", min_value=0.0, value=29.90, step=0.01)
            estoque = st.number_input("📦 Estoque inicial", min_value=0, value=10)
            
            escolas = listar_escolas()
            escola_selecionada = st.selectbox("🏫 Escola*", [f"{e[0]} - {e[1]}" for e in escolas])
            escola_id = int(escola_selecionada.split(" - ")[0])
            
            submitted = st.form_submit_button("✅ Cadastrar Produto", use_container_width=True)
            
            if submitted:
                if nome:
                    sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id)
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome do produto é obrigatório!")
    
    with tab2:
        st.header("📋 Produtos Cadastrados")
        produtos = listar_produtos()
        
        if produtos:
            for produto in produtos:
                with st.expander(f"👕 {produto[1]} - {produto[3]} - {produto[4]}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**📦 Categoria:** {produto[2]}")
                        st.write(f"**💰 Preço:** R$ {produto[5]:.2f}")
                    with col2:
                        st.write(f"**📦 Estoque:** {produto[6]} unidades")
                        st.write(f"**🏫 Escola:** {produto[8]}")
                    
                    # Ação rápida: ajustar estoque
                    novo_estoque = st.number_input(
                        "Ajustar estoque:",
                        min_value=0,
                        value=produto[6],
                        key=f"estoque_{produto[0]}"
                    )
                    
                    if novo_estoque != produto[6]:
                        if st.button("💾 Atualizar", key=f"btn_{produto[0]}", use_container_width=True):
                            sucesso, msg = atualizar_estoque(produto[0], novo_estoque)
                            if sucesso:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
        else:
            st.info("👕 Nenhum produto cadastrado no momento.")

elif menu == "📦 Pedidos":
    tab1, tab2 = st.tabs(["➕ Novo Pedido", "📋 Listar Pedidos"])
    
    with tab1:
        st.header("➕ Novo Pedido")
        
        # Selecionar cliente
        clientes = listar_clientes()
        if clientes:
            cliente_selecionado = st.selectbox(
                "👤 Selecione o cliente:",
                [f"{c[0]} - {c[1]}" for c in clientes]
            )
            cliente_id = int(cliente_selecionado.split(" - ")[0])
            
            # Selecionar produtos
            produtos = listar_produtos()
            if produtos:
                st.subheader("🛒 Adicionar Itens ao Pedido")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    produto_selecionado = st.selectbox(
                        "Produto:",
                        [f"{p[0]} - {p[1]} (Estoque: {p[6]}) - R$ {p[5]:.2f}" for p in produtos]
                    )
                with col2:
                    quantidade = st.number_input("Quantidade", min_value=1, value=1)
                with col3:
                    if st.button("➕ Adicionar Item", use_container_width=True):
                        if 'itens_pedido' not in st.session_state:
                            st.session_state.itens_pedido = []
                        
                        produto_id = int(produto_selecionado.split(" - ")[0])
                        produto = next(p for p in produtos if p[0] == produto_id)
                        
                        if quantidade > produto[6]:
                            st.error("❌ Quantidade maior que estoque disponível!")
                        else:
                            item = {
                                'produto_id': produto_id,
                                'nome': produto[1],
                                'quantidade': quantidade,
                                'preco_unitario': produto[5],
                                'subtotal': produto[5] * quantidade
                            }
                            st.session_state.itens_pedido.append(item)
                            st.success("✅ Item adicionado ao pedido!")
                            st.rerun()
                
                # Mostrar itens do pedido
                if 'itens_pedido' in st.session_state and st.session_state.itens_pedido:
                    st.subheader("📋 Itens do Pedido")
                    total_pedido = sum(item['subtotal'] for item in st.session_state.itens_pedido)
                    
                    for i, item in enumerate(st.session_state.itens_pedido):
                        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                        with col1:
                            st.write(f"**{item['nome']}**")
                        with col2:
                            st.write(f"Qtd: {item['quantidade']}")
                        with col3:
                            st.write(f"R$ {item['preco_unitario']:.2f}")
                        with col4:
                            st.write(f"R$ {item['subtotal']:.2f}")
                            if st.button("❌", key=f"del_{i}"):
                                st.session_state.itens_pedido.pop(i)
                                st.rerun()
                    
                    st.write(f"**💰 Total do Pedido: R$ {total_pedido:.2f}**")
                    
                    # Finalizar pedido
                    data_entrega = st.date_input("📅 Data de Entrega Prevista", min_value=date.today())
                    observacoes = st.text_area("Observações")
                    
                    if st.button("✅ Finalizar Pedido", type="primary", use_container_width=True):
                        if st.session_state.itens_pedido:
                            sucesso, resultado = adicionar_pedido(
                                cliente_id, 
                                st.session_state.itens_pedido, 
                                data_entrega, 
                                observacoes
                            )
                            if sucesso:
                                st.success(f"✅ Pedido #{resultado} criado com sucesso!")
                                st.balloons()
                                del st.session_state.itens_pedido
                                st.rerun()
                            else:
                                st.error(f"❌ Erro ao criar pedido: {resultado}")
                        else:
                            st.error("❌ Adicione itens ao pedido antes de finalizar!")
                else:
                    st.info("🛒 Adicione itens ao pedido usando o botão acima")
            else:
                st.error("❌ Nenhum produto cadastrado. Cadastre produtos primeiro.")
        else:
            st.error("❌ Nenhum cliente cadastrado. Cadastre clientes primeiro.")
    
    with tab2:
        st.header("📋 Pedidos Realizados")
        pedidos = listar_pedidos()
        
        if pedidos:
            for pedido in pedidos:
                status_cor = {
                    'Pendente': '🟡',
                    'Em produção': '🟠', 
                    'Pronto para entrega': '🔵',
                    'Entregue': '🟢',
                    'Cancelado': '🔴'
                }.get(pedido[2], '⚪')
                
                with st.expander(f"{status_cor} Pedido #{pedido[0]} - {pedido[7]}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Status:** {pedido[2]}")
                        st.write(f"**Data do Pedido:** {pedido[3]}")
                        st.write(f"**Cliente:** {pedido[7]}")
                    with col2:
                        st.write(f"**Valor Total:** R$ {pedido[5]:.2f}")
                        st.write(f"**Entrega Prevista:** {pedido[4]}")
                        st.write(f"**Observações:** {pedido[6] or 'Nenhuma'}")
        else:
            st.info("📦 Nenhum pedido realizado.")

elif menu == "📦 Estoque":
    st.header("📊 Controle de Estoque")
    
    produtos = listar_produtos()
    
    if produtos:
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            categorias = list(set([p[2] for p in produtos]))
            categoria_filtro = st.selectbox("Filtrar por categoria:", ["Todas"] + categorias)
        
        with col2:
            escolas = list(set([p[8] for p in produtos if p[8]]))
            escola_filtro = st.selectbox("Filtrar por escola:", ["Todas"] + escolas)
        
        # Aplicar filtros
        produtos_filtrados = produtos
        if categoria_filtro != "Todas":
            produtos_filtrados = [p for p in produtos_filtrados if p[2] == categoria_filtro]
        if escola_filtro != "Todas":
            produtos_filtrados = [p for p in produtos_filtrados if p[8] == escola_filtro]
        
        # Exibir produtos
        for produto in produtos_filtrados:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.write(f"**{produto[1]}**")
                st.write(f"{produto[2]} - {produto[3]} - {produto[4]}")
                st.write(f"Escola: {produto[8]}")
            
            with col2:
                st.write(f"**Estoque:**")
                if produto[6] < 5:
                    st.error(f"❌ {produto[6]}")
                elif produto[6] < 10:
                    st.warning(f"⚠️ {produto[6]}")
                else:
                    st.success(f"✅ {produto[6]}")
            
            with col3:
                st.write(f"**Preço:**")
                st.write(f"R$ {produto[5]:.2f}")
            
            with col4:
                novo_estoque = st.number_input(
                    "Novo valor:",
                    min_value=0,
                    value=produto[6],
                    key=f"estoque_main_{produto[0]}"
                )
                
                if novo_estoque != produto[6]:
                    if st.button("💾", key=f"save_{produto[0]}"):
                        sucesso, msg = atualizar_estoque(produto[0], novo_estoque)
                        if sucesso:
                            st.success("✅ Estoque atualizado!")
                            st.rerun()
                        else:
                            st.error(msg)
            
            st.markdown("---")
        
        # Resumo
        st.subheader("📈 Resumo do Estoque")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_produtos = len(produtos_filtrados)
            st.metric("Total de Produtos", total_produtos)
        
        with col2:
            baixo_estoque = len([p for p in produtos_filtrados if p[6] < 5])
            st.metric("Produtos com Estoque Baixo", baixo_estoque)
        
        with col3:
            estoque_total = sum(p[6] for p in produtos_filtrados)
            st.metric("Estoque Total", estoque_total)
            
    else:
        st.info("👕 Nenhum produto cadastrado para exibir controle de estoque.")

# Logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Rodapé
st.sidebar.markdown("---")
st.sidebar.markdown("👕 **Sistema de Fardamentos v5.0**")
st.sidebar.markdown("🗄️ **SQLite** | 📱 **Mobile** | 🚀 **Render**")
