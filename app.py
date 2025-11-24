import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date, timedelta

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
    .admin-card { border-left: 4px solid #dc3545; }
    .gestor-card { border-left: 4px solid #ffc107; }
    .vendedor-card { border-left: 4px solid #28a745; }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🇧🇷 FUNÇÕES DE FORMATAÇÃO BRASILEIRA
# =========================================

def formatar_data_brasil(data_string):
    """Converte data do banco (YYYY-MM-DD) para formato brasileiro (DD/MM/YYYY)"""
    if not data_string:
        return "N/A"
    
    try:
        # Se já estiver no formato brasileiro, retorna como está
        if '/' in str(data_string):
            return str(data_string)
            
        # Converte do formato do banco para brasileiro
        if isinstance(data_string, str) and len(data_string) >= 10:
            partes = data_string.split('-')
            if len(partes) >= 3:
                return f"{partes[2]}/{partes[1]}/{partes[0]}"
        
        return str(data_string)
    except:
        return str(data_string)

def formatar_datahora_brasil(datahora_string):
    """Converte data/hora para formato brasileiro"""
    if not datahora_string:
        return "N/A"
    
    try:
        # Para datetime completo
        if ' ' in str(datahora_string):
            data_part, hora_part = str(datahora_string).split(' ', 1)
            data_brasil = formatar_data_brasil(data_part)
            # Formatar hora (remove segundos se necessário)
            hora_part = hora_part[:5]  # Mantém apenas HH:MM
            return f"{data_brasil} {hora_part}"
        else:
            return formatar_data_brasil(datahora_string)
    except:
        return str(datahora_string)

def data_atual_brasil():
    """Retorna data atual no formato brasileiro"""
    return datetime.now().strftime("%d/%m/%Y")

def hora_atual_brasil():
    """Retorna hora atual no formato brasileiro"""
    return datetime.now().strftime("%H:%M")

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO
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
    """Inicializa banco de dados"""
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
                tipo TEXT DEFAULT 'vendedor',
                ativo INTEGER DEFAULT 1
            )
        ''')
        
        # Tabela de escolas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS escolas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                endereco TEXT,
                telefone TEXT
            )
        ''')
        
        # Tabela de clientes (SEM VÍNCULO COM ESCOLA)
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
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(nome, tamanho, cor, escola_id),
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
                data_entrega_real DATE,
                valor_total REAL DEFAULT 0,
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
                subtotal REAL,
                FOREIGN KEY (pedido_id) REFERENCES pedidos (id),
                FOREIGN KEY (produto_id) REFERENCES produtos (id)
            )
        ''')
        
        # Usuários padrão
        usuarios_padrao = [
            ('admin', make_hashes('admin123'), 'Administrador Sistema', 'admin'),
            ('gestor', make_hashes('gestor123'), 'Gestor Comercial', 'gestor'),
            ('vendedor', make_hashes('vendedor123'), 'Vendedor Principal', 'vendedor')
        ]
        
        for username, password_hash, nome, tipo in usuarios_padrao:
            cursor.execute('''
                INSERT OR IGNORE INTO usuarios (username, password_hash, nome_completo, tipo) 
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, nome, tipo))
        
        # Escolas padrão
        escolas_padrao = [
            ('Escola Municipal', 'Rua Principal, 123', '(11) 9999-8888'),
            ('Colégio Desperta', 'Av. Central, 456', '(11) 7777-6666'),
            ('Instituto São Tadeu', 'Praça da Matriz, 789', '(11) 5555-4444')
        ]
        
        for nome, endereco, telefone in escolas_padrao:
            cursor.execute('INSERT OR IGNORE INTO escolas (nome, endereco, telefone) VALUES (?, ?, ?)', 
                         (nome, endereco, telefone))
        
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
        cursor.execute('''
            SELECT password_hash, nome_completo, tipo 
            FROM usuarios 
            WHERE username = ? AND ativo = 1
        ''', (username,))
        
        resultado = cursor.fetchone()
        
        if resultado and check_hashes(password, resultado['password_hash']):
            return True, resultado['nome_completo'], resultado['tipo']
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

def listar_usuarios():
    """Lista todos os usuários"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, nome_completo, tipo, ativo FROM usuarios ORDER BY username')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar usuários: {e}")
        return []
    finally:
        if conn:
            conn.close()

def criar_usuario(username, password, nome_completo, tipo):
    """Cria novo usuário"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        password_hash = make_hashes(password)
        
        cursor.execute('''
            INSERT INTO usuarios (username, password_hash, nome_completo, tipo)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, nome_completo, tipo))
        
        conn.commit()
        return True, "✅ Usuário criado com sucesso!"
        
    except sqlite3.IntegrityError:
        return False, "❌ Username já existe"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def alterar_senha_usuario(username, nova_senha):
    """Altera senha do usuário"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        nova_senha_hash = make_hashes(nova_senha)
        
        cursor.execute('''
            UPDATE usuarios SET password_hash = ? WHERE username = ?
        ''', (nova_senha_hash, username))
        
        conn.commit()
        return True, "✅ Senha alterada com sucesso!"
        
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def adicionar_escola(nome, endereco, telefone):
    """Adiciona nova escola"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO escolas (nome, endereco, telefone)
            VALUES (?, ?, ?)
        ''', (nome, endereco, telefone))
        
        conn.commit()
        return True, "✅ Escola cadastrada com sucesso!"
    except sqlite3.IntegrityError:
        return False, "❌ Escola já existe"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def editar_escola(escola_id, nome, endereco, telefone):
    """Edita escola existente"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE escolas 
            SET nome = ?, endereco = ?, telefone = ?
            WHERE id = ?
        ''', (nome, endereco, telefone, escola_id))
        
        conn.commit()
        return True, "✅ Escola atualizada com sucesso!"
    except sqlite3.IntegrityError:
        return False, "❌ Nome da escola já existe"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def excluir_escola(escola_id):
    """Exclui escola"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        
        # Verificar se há produtos vinculados
        cursor.execute("SELECT COUNT(*) FROM produtos WHERE escola_id = ?", (escola_id,))
        if cursor.fetchone()[0] > 0:
            return False, "❌ Escola possui produtos vinculados"
        
        cursor.execute("DELETE FROM escolas WHERE id = ?", (escola_id,))
        conn.commit()
        return True, "✅ Escola excluída com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def adicionar_cliente(nome, telefone, email):
    """Adiciona cliente SEM vínculo com escola"""
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
    """Lista todos os clientes"""
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

def excluir_cliente(cliente_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        
        # Verificar se cliente tem pedidos
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE cliente_id = ?", (cliente_id,))
        if cursor.fetchone()[0] > 0:
            return False, "❌ Cliente possui pedidos e não pode ser excluído"
        
        cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        conn.commit()
        return True, "✅ Cliente excluído com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def editar_cliente(cliente_id, nome, telefone, email):
    """Edita cliente existente"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE clientes 
            SET nome = ?, telefone = ?, email = ?
            WHERE id = ?
        ''', (nome, telefone, email, cliente_id))
        
        conn.commit()
        return True, "✅ Cliente atualizado com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def produto_existe(nome, tamanho, cor, escola_id):
    """Verifica se produto já existe"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM produtos 
            WHERE nome = ? AND tamanho = ? AND cor = ? AND escola_id = ?
        ''', (nome, tamanho, cor, escola_id))
        return cursor.fetchone() is not None
    finally:
        if conn:
            conn.close()

def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        # Verificar se produto já existe
        if produto_existe(nome, tamanho, cor, escola_id):
            return False, "❌ Produto já existe para esta escola"
        
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

def listar_produtos(escola_id=None):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        if escola_id:
            cursor.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                WHERE p.escola_id = ?
                ORDER BY p.nome
            ''', (escola_id,))
        else:
            cursor.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                ORDER BY p.escola_id, p.nome
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
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
            ''', (pedido_id, item['produto_id'], item['quantidade'], item['preco_unitario'], item['subtotal']))
            
            # Atualizar estoque
            cursor.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", 
                         (item['quantidade'], item['produto_id']))
        
        conn.commit()
        return True, pedido_id
        
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_pedidos(usuario_tipo):
    """Lista pedidos - cliente NÃO tem mais escola"""
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

def atualizar_status_pedido(pedido_id, novo_status, data_entrega_real=None):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        
        if novo_status == 'Entregue' and data_entrega_real:
            cursor.execute('''
                UPDATE pedidos 
                SET status = ?, data_entrega_real = ? 
                WHERE id = ?
            ''', (novo_status, data_entrega_real, pedido_id))
        else:
            cursor.execute('''
                UPDATE pedidos 
                SET status = ? 
                WHERE id = ?
            ''', (novo_status, pedido_id))
        
        conn.commit()
        return True, "✅ Status do pedido atualizado com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def excluir_pedido(pedido_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        
        # Restaurar estoque dos itens
        cursor.execute('SELECT produto_id, quantidade FROM pedido_itens WHERE pedido_id = ?', (pedido_id,))
        itens = cursor.fetchall()
        
        for item in itens:
            cursor.execute("UPDATE produtos SET estoque = estoque + ? WHERE id = ?", 
                         (item['quantidade'], item['produto_id']))
        
        # Excluir itens do pedido
        cursor.execute("DELETE FROM pedido_itens WHERE pedido_id = ?", (pedido_id,))
        
        # Excluir pedido
        cursor.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        
        conn.commit()
        return True, "✅ Pedido excluído com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

# =========================================
# 🚀 INTERFACES POR TIPO DE USUÁRIO
# =========================================

def interface_admin():
    """Interface para Administrador"""
    st.header("👑 Painel do Administrador")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Dashboard", "👥 Clientes", "👕 Produtos", "📦 Pedidos", "🏫 Escolas", "👤 Usuários"
    ])
    
    with tab1:
        st.subheader("📊 Visão Geral do Sistema")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            clientes = listar_clientes()
            st.metric("Total Clientes", len(clientes))
        
        with col2:
            produtos = listar_produtos()
            st.metric("Total Produtos", len(produtos))
        
        with col3:
            pedidos = listar_pedidos('admin')
            st.metric("Total Pedidos", len(pedidos))
        
        with col4:
            estoque_baixo = len([p for p in produtos if p['estoque'] < 5])
            st.metric("Alerta Estoque", estoque_baixo)
        
        # Data e hora atual
        st.write(f"**📅 Data atual:** {data_atual_brasil()}")
        st.write(f"**🕒 Hora atual:** {hora_atual_brasil()}")
    
    with tab2:
        st.subheader("👥 Gestão de Clientes")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("➕ Novo Cliente")
            with st.form("novo_cliente_admin", clear_on_submit=True):
                nome = st.text_input("Nome completo*")
                telefone = st.text_input("Telefone*")
                email = st.text_input("Email")
                
                if st.form_submit_button("✅ Cadastrar Cliente"):
                    if nome and telefone:
                        sucesso, msg = adicionar_cliente(nome, telefone, email)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Nome e telefone são obrigatórios!")
        
        with col2:
            st.write("📋 Clientes Cadastrados")
            clientes = listar_clientes()
            
            for cliente in clientes:
                with st.expander(f"👤 {cliente['nome']}", expanded=False):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Telefone:** {cliente['telefone'] or 'N/A'}")
                        st.write(f"**Email:** {cliente['email'] or 'N/A'}")
                    with col_b:
                        st.write(f"**Data Cadastro:** {formatar_data_brasil(cliente['data_cadastro'])}")
                    
                    col_c, col_d = st.columns(2)
                    with col_c:
                        if st.button("🗑️ Excluir", key=f"del_cli_{cliente['id']}"):
                            sucesso, msg = excluir_cliente(cliente['id'])
                            if sucesso:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
    
    with tab3:
        st.subheader("👕 Gestão de Produtos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("➕ Novo Produto")
            with st.form("novo_produto_admin", clear_on_submit=True):
                nome = st.text_input("Nome do produto*")
                categoria = st.selectbox("Categoria", ["Camiseta", "Calça", "Short", "Agasalho", "Acessório"])
                tamanho = st.selectbox("Tamanho", ["PP", "P", "M", "G", "GG", "2", "4", "6", "8", "10", "12"])
                cor = st.text_input("Cor*", value="Branco")
                preco = st.number_input("Preço R$*", min_value=0.0, value=29.90)
                estoque = st.number_input("Estoque*", min_value=0, value=10)
                
                escolas = listar_escolas()
                escola_id = st.selectbox("Escola*", 
                                       options=[e['id'] for e in escolas],
                                       format_func=lambda x: next(e['nome'] for e in escolas if e['id'] == x))
                
                if st.form_submit_button("✅ Cadastrar Produto"):
                    if nome and cor and escola_id:
                        sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Nome, cor e escola são obrigatórios!")
        
        with col2:
            st.write("📋 Produtos por Escola")
            
            escolas = listar_escolas()
            for escola in escolas:
                with st.expander(f"🏫 {escola['nome']}"):
                    produtos_escola = listar_produtos(escola['id'])
                    
                    for produto in produtos_escola:
                        st.write(f"👕 **{produto['nome']}** - {produto['tamanho']} - {produto['cor']}")
                        st.write(f"   Estoque: {produto['estoque']} | Preço: R$ {produto['preco']:.2f}")
    
    with tab4:
        interface_pedidos('admin')
    
    with tab5:
        st.subheader("🏫 Gestão de Escolas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("➕ Nova Escola")
            with st.form("nova_escola", clear_on_submit=True):
                nome = st.text_input("Nome da Escola*")
                endereco = st.text_input("Endereço")
                telefone = st.text_input("Telefone")
                
                if st.form_submit_button("✅ Cadastrar Escola"):
                    if nome:
                        sucesso, msg = adicionar_escola(nome, endereco, telefone)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Nome da escola é obrigatório")
        
        with col2:
            st.write("📋 Escolas Cadastradas")
            escolas = listar_escolas()
            
            for escola in escolas:
                with st.expander(f"🏫 {escola['nome']}"):
                    st.write(f"**Endereço:** {escola['endereco']}")
                    st.write(f"**Telefone:** {escola['telefone']}")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("✏️ Editar", key=f"edit_esc_{escola['id']}"):
                            st.session_state.editando_escola = escola['id']
                    with col_b:
                        if st.button("🗑️ Excluir", key=f"del_esc_{escola['id']}"):
                            sucesso, msg = excluir_escola(escola['id'])
                            if sucesso:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    
                    # Formulário de edição
                    if st.session_state.get('editando_escola') == escola['id']:
                        with st.form(f"editar_escola_{escola['id']}", clear_on_submit=True):
                            novo_nome = st.text_input("Nome", value=escola['nome'])
                            novo_endereco = st.text_input("Endereço", value=escola['endereco'] or "")
                            novo_telefone = st.text_input("Telefone", value=escola['telefone'] or "")
                            
                            col_c, col_d = st.columns(2)
                            with col_c:
                                if st.form_submit_button("💾 Salvar"):
                                    sucesso, msg = editar_escola(escola['id'], novo_nome, novo_endereco, novo_telefone)
                                    if sucesso:
                                        st.success(msg)
                                        del st.session_state.editando_escola
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            with col_d:
                                if st.form_submit_button("❌ Cancelar"):
                                    del st.session_state.editando_escola
                                    st.rerun()
    
    with tab6:
        st.subheader("👤 Gestão de Usuários")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("➕ Novo Usuário")
            with st.form("novo_usuario", clear_on_submit=True):
                username = st.text_input("Username*")
                password = st.text_input("Senha*", type="password")
                nome_completo = st.text_input("Nome Completo*")
                tipo = st.selectbox("Tipo", ["admin", "gestor", "vendedor"])
                
                if st.form_submit_button("✅ Criar Usuário"):
                    if username and password and nome_completo:
                        sucesso, msg = criar_usuario(username, password, nome_completo, tipo)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Todos os campos são obrigatórios")
        
        with col2:
            st.write("📋 Usuários do Sistema")
            usuarios = listar_usuarios()
            
            for usuario in usuarios:
                with st.expander(f"👤 {usuario['username']} - {usuario['tipo']}"):
                    st.write(f"**Nome:** {usuario['nome_completo']}")
                    st.write(f"**Status:** {'✅ Ativo' if usuario['ativo'] else '❌ Inativo'}")
                    
                    # Alterar senha
                    with st.form(f"alterar_senha_{usuario['id']}", clear_on_submit=True):
                        nova_senha = st.text_input("Nova Senha", type="password", key=f"pwd_{usuario['id']}")
                        if st.form_submit_button("🔐 Alterar Senha"):
                            if nova_senha:
                                sucesso, msg = alterar_senha_usuario(usuario['username'], nova_senha)
                                if sucesso:
                                    st.success(msg)
                                else:
                                    st.error(msg)
                            else:
                                st.error("❌ Digite uma nova senha")

def interface_gestor():
    """Interface para Gestor"""
    st.header("📈 Painel do Gestor")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard", "👥 Clientes", "👕 Produtos", "📦 Pedidos"
    ])
    
    with tab1:
        st.subheader("📊 Métricas Comerciais")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            clientes = listar_clientes()
            st.metric("Clientes Ativos", len(clientes))
        
        with col2:
            pedidos = listar_pedidos('gestor')
            pedidos_hoje = len([p for p in pedidos if p['data_pedido'][:10] == str(date.today())])
            st.metric("Pedidos Hoje", pedidos_hoje)
        
        with col3:
            produtos = listar_produtos()
            estoque_total = sum(p['estoque'] for p in produtos)
            st.metric("Estoque Total", estoque_total)
        
        # Data e hora atual
        st.write(f"**📅 Data atual:** {data_atual_brasil()}")
        st.write(f"**🕒 Hora atual:** {hora_atual_brasil()}")
    
    with tab2:
        st.subheader("👥 Clientes")
        
        clientes = listar_clientes()
        for cliente in clientes:
            with st.expander(f"👤 {cliente['nome']}"):
                st.write(f"**Contato:** {cliente['telefone']} | {cliente['email']}")
                st.write(f"**Cadastro:** {formatar_data_brasil(cliente['data_cadastro'])}")
    
    with tab3:
        st.subheader("👕 Produtos e Estoque")
        
        escolas = listar_escolas()
        for escola in escolas:
            with st.expander(f"🏫 {escola['nome']}"):
                produtos_escola = listar_produtos(escola['id'])
                
                for produto in produtos_escola:
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"**{produto['nome']}** - {produto['tamanho']} - {produto['cor']}")
                    with col2:
                        st.write(f"Estoque: {produto['estoque']}")
                    with col3:
                        st.write(f"R$ {produto['preco']:.2f}")
    
    with tab4:
        interface_pedidos('gestor')

def interface_vendedor():
    """Interface para Vendedor"""
    st.header("👔 Painel do Vendedor")
    
    tab1, tab2, tab3 = st.tabs(["📦 Pedidos", "👥 Clientes", "📦 Estoque"])
    
    with tab1:
        interface_pedidos('vendedor')
    
    with tab2:
        st.subheader("👥 Clientes")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("➕ Novo Cliente")
            with st.form("novo_cliente_vendedor", clear_on_submit=True):
                nome = st.text_input("Nome completo*")
                telefone = st.text_input("Telefone*")
                email = st.text_input("Email")
                
                if st.form_submit_button("✅ Cadastrar Cliente"):
                    if nome and telefone:
                        sucesso, msg = adicionar_cliente(nome, telefone, email)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Nome e telefone são obrigatórios!")
        
        with col2:
            clientes = listar_clientes()
            for cliente in clientes:
                with st.expander(f"👤 {cliente['nome']}"):
                    st.write(f"**Telefone:** {cliente['telefone']}")
                    st.write(f"**Email:** {cliente['email'] or 'N/A'}")
                    st.write(f"**Cadastro:** {formatar_data_brasil(cliente['data_cadastro'])}")
    
    with tab3:
        st.subheader("📦 Estoque de Todas as Escolas")
        
        escolas = listar_escolas()
        for escola in escolas:
            with st.expander(f"🏫 {escola['nome']}"):
                produtos = listar_produtos(escola['id'])
                for produto in produtos:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**{produto['nome']}** - {produto['tamanho']} - {produto['cor']}")
                    with col2:
                        if produto['estoque'] < 5:
                            st.error(f"Estoque: {produto['estoque']}")
                        elif produto['estoque'] < 10:
                            st.warning(f"Estoque: {produto['estoque']}")
                        else:
                            st.success(f"Estoque: {produto['estoque']}")
                    with col3:
                        st.write(f"R$ {produto['preco']:.2f}")

def interface_pedidos(tipo_usuario):
    """Interface de pedidos compartilhada"""
    st.subheader("📦 Gestão de Pedidos")
    
    tab1, tab2 = st.tabs(["➕ Novo Pedido", "📋 Meus Pedidos"])
    
    with tab1:
        # Selecionar cliente
        clientes = listar_clientes()
        
        if not clientes:
            st.error("❌ Nenhum cliente cadastrado. Cadastre clientes primeiro.")
            return
        
        cliente_selecionado = st.selectbox(
            "👤 Selecione o cliente:",
            options=[c['id'] for c in clientes],
            format_func=lambda x: f"{next(c['nome'] for c in clientes if c['id'] == x)}"
        )
        
        # Mostrar TODOS os produtos de TODAS as escolas
        st.subheader("🛒 Adicionar Itens ao Pedido")
        st.info("🎯 O cliente pode escolher produtos de qualquer escola")
        
        # Agrupar produtos por escola para melhor organização
        escolas = listar_escolas()
        
        for escola in escolas:
            with st.expander(f"🏫 {escola['nome']}", expanded=True):
                produtos_escola = listar_produtos(escola['id'])
                
                if produtos_escola:
                    for produto in produtos_escola:
                        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                        with col1:
                            st.write(f"**{produto['nome']}**")
                            st.write(f"Tamanho: {produto['tamanho']} | Cor: {produto['cor']}")
                        with col2:
                            st.write(f"Estoque: {produto['estoque']}")
                        with col3:
                            st.write(f"R$ {produto['preco']:.2f}")
                        with col4:
                            # Botão para adicionar este produto específico
                            if st.button("➕ Adicionar", key=f"add_{produto['id']}"):
                                if 'itens_pedido' not in st.session_state:
                                    st.session_state.itens_pedido = []
                                
                                # Verificar se produto já está no pedido
                                produto_ja_adicionado = any(item['produto_id'] == produto['id'] for item in st.session_state.itens_pedido)
                                
                                if produto_ja_adicionado:
                                    st.error("❌ Produto já adicionado ao pedido")
                                elif produto['estoque'] <= 0:
                                    st.error("❌ Produto sem estoque")
                                else:
                                    item = {
                                        'produto_id': produto['id'],
                                        'nome': produto['nome'],
                                        'escola': produto['escola_nome'],
                                        'quantidade': 1,
                                        'preco_unitario': produto['preco'],
                                        'subtotal': produto['preco'] * 1
                                    }
                                    st.session_state.itens_pedido.append(item)
                                    st.success(f"✅ {produto['nome']} adicionado!")
                                    st.rerun()
                else:
                    st.write("📭 Nenhum produto cadastrado para esta escola")
        
        # Itens do pedido
        if 'itens_pedido' in st.session_state and st.session_state.itens_pedido:
            st.subheader("📋 Itens do Pedido")
            total_pedido = sum(item['subtotal'] for item in st.session_state.itens_pedido)
            
            for i, item in enumerate(st.session_state.itens_pedido):
                col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 1])
                with col1:
                    st.write(f"**{item['nome']}**")
                    st.write(f"Escola: {item['escola']}")
                with col2:
                    # Permitir alterar quantidade
                    nova_quantidade = st.number_input(
                        "Qtd", 
                        min_value=1, 
                        value=item['quantidade'],
                        key=f"qtd_{i}"
                    )
                    if nova_quantidade != item['quantidade']:
                        item['quantidade'] = nova_quantidade
                        item['subtotal'] = item['preco_unitario'] * nova_quantidade
                        st.rerun()
                with col3:
                    st.write(f"R$ {item['preco_unitario']:.2f}")
                with col4:
                    st.write(f"R$ {item['subtotal']:.2f}")
                with col5:
                    if st.button("❌", key=f"del_{i}"):
                        st.session_state.itens_pedido.pop(i)
                        st.rerun()
            
            # Recalcular total
            total_pedido = sum(item['subtotal'] for item in st.session_state.itens_pedido)
            st.write(f"**💰 Total do Pedido: R$ {total_pedido:.2f}**")
            
            # Finalizar pedido
            st.subheader("✅ Finalizar Pedido")
            data_entrega = st.date_input("📅 Data de Entrega Prevista", min_value=date.today())
            observacoes = st.text_area("Observações")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("✅ Finalizar Pedido", type="primary", use_container_width=True):
                    if st.session_state.itens_pedido:
                        # Verificar estoque para todos os itens
                        estoque_insuficiente = False
                        for item in st.session_state.itens_pedido:
                            produto = next((p for p in listar_produtos() if p['id'] == item['produto_id']), None)
                            if produto and item['quantidade'] > produto['estoque']:
                                st.error(f"❌ Estoque insuficiente para {produto['nome']} (estoque: {produto['estoque']})")
                                estoque_insuficiente = True
                                break
                        
                        if not estoque_insuficiente:
                            sucesso, resultado = adicionar_pedido(
                                cliente_selecionado, 
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
            
            with col_btn2:
                if st.button("🗑️ Limpar Pedido", use_container_width=True):
                    if 'itens_pedido' in st.session_state:
                        del st.session_state.itens_pedido
                    st.rerun()
        else:
            st.info("🛒 Adicione itens ao pedido usando os botões 'Adicionar' acima")
    
    with tab2:
        pedidos = listar_pedidos(tipo_usuario)
        
        if pedidos:
            for pedido in pedidos:
                status_info = {
                    'Pendente': '🟡 Pendente',
                    'Em produção': '🟠 Em produção', 
                    'Pronto para entrega': '🔵 Pronto',
                    'Entregue': '🟢 Entregue',
                    'Cancelado': '🔴 Cancelado'
                }.get(pedido['status'], f'⚪ {pedido["status"]}')
                
                with st.expander(f"{status_info} Pedido #{pedido['id']} - {pedido['cliente_nome']}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Cliente:** {pedido['cliente_nome']}")
                        st.write(f"**Status:** {pedido['status']}")
                        st.write(f"**Data Pedido:** {formatar_datahora_brasil(pedido['data_pedido'])}")
                    with col2:
                        st.write(f"**Valor Total:** R$ {pedido['valor_total']:.2f}")
                        st.write(f"**Entrega Prevista:** {formatar_data_brasil(pedido['data_entrega_prevista'])}")
                        if pedido['data_entrega_real']:
                            st.write(f"**Entregue em:** {formatar_data_brasil(pedido['data_entrega_real'])}")
                    
                    # Ações do pedido
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        novo_status = st.selectbox(
                            "Alterar status:",
                            ["Pendente", "Em produção", "Pronto para entrega", "Entregue", "Cancelado"],
                            key=f"status_{pedido['id']}"
                        )
                        
                        if st.button("🔄 Atualizar", key=f"upd_{pedido['id']}"):
                            data_entrega = date.today() if novo_status == 'Entregue' else None
                            sucesso, msg = atualizar_status_pedido(pedido['id'], novo_status, data_entrega)
                            if sucesso:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    
                    # Admin e gestor podem excluir pedidos
                    if tipo_usuario in ['admin', 'gestor']:
                        with col2:
                            if st.button("🗑️ Excluir Pedido", key=f"del_ped_{pedido['id']}"):
                                sucesso, msg = excluir_pedido(pedido['id'])
                                if sucesso:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
        else:
            st.info("📦 Nenhum pedido encontrado.")

# =========================================
# 🚀 APP PRINCIPAL
# =========================================

def main():
    # Inicialização
    if 'db_initialized' not in st.session_state:
        if init_db():
            st.session_state.db_initialized = True

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
                            st.success(f"Bem-vindo, {mensagem}!")
                            st.rerun()
                        else:
                            st.error(mensagem)
                else:
                    st.error("Por favor, preencha todos os campos")
        st.stop()

    # Interface baseada no tipo de usuário
    st.sidebar.markdown(f"**👤 {st.session_state.nome_usuario}**")
    st.sidebar.markdown(f"**🎯 {st.session_state.tipo_usuario.upper()}**")
    
    # Data e hora atual
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**📅 {data_atual_brasil()}**")
    st.sidebar.markdown(f"**🕒 {hora_atual_brasil()}**")
    
    # Alterar própria senha
    with st.sidebar.expander("🔐 Alterar Minha Senha"):
        with st.form("alterar_minha_senha", clear_on_submit=True):
            nova_senha = st.text_input("Nova Senha", type="password")
            confirmar_senha = st.text_input("Confirmar Senha", type="password")
            
            if st.form_submit_button("💾 Alterar Senha"):
                if nova_senha and confirmar_senha:
                    if nova_senha == confirmar_senha:
                        sucesso, msg = alterar_senha_usuario(st.session_state.username, nova_senha)
                        if sucesso:
                            st.success(msg)
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Senhas não coincidem")
                else:
                    st.error("❌ Preencha todos os campos")
    
    # Logout
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # Redirecionar para interface correta
    if st.session_state.tipo_usuario == 'admin':
        interface_admin()
    elif st.session_state.tipo_usuario == 'gestor':
        interface_gestor()
    elif st.session_state.tipo_usuario == 'vendedor':
        interface_vendedor()
    else:
        st.error("Tipo de usuário não reconhecido")

if __name__ == "__main__":
    main()