import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date, timedelta
import io
import csv
import base64

# =========================================
# 🎯 CONFIGURAÇÃO
# =========================================

st.set_page_config(
    page_title="Sistema Fardamentos + A.I.",
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
    .ai-insight-positive { 
        border-left: 4px solid #28a745;
        background: #f8fff9;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .ai-insight-warning { 
        border-left: 4px solid #ffc107;
        background: #fffbf0;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .ai-insight-danger { 
        border-left: 4px solid #dc3545;
        background: #fff5f5;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .pagination-btn {
        margin: 0 0.2rem;
        padding: 0.3rem 0.6rem;
    }
    .stButton a {
        text-decoration: none;
        background-color: #4CAF50;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        border: none;
        cursor: pointer;
    }
    .stButton a:hover {
        background-color: #45a049;
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
        # Se for objeto date/datetime
        if isinstance(data_string, (date, datetime)):
            return data_string.strftime("%d/%m/%Y")
            
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
    """Conexão com SQLite otimizada"""
    try:
        conn = sqlite3.connect('sistema_fardamentos.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Otimizações para melhor performance
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn
    except Exception as e:
        st.error(f"Erro de conexão: {str(e)}")
        return None

def init_db():
    """Inicializa banco de dados com otimizações"""
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
                ativo INTEGER DEFAULT 1,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de escolas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS escolas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                endereco TEXT,
                telefone TEXT,
                email TEXT,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de clientes (SEM VÍNCULO COM ESCOLA)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT,
                email TEXT,
                data_nascimento DATE,
                cpf TEXT,
                endereco TEXT,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ativo INTEGER DEFAULT 1
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
                custo REAL,
                estoque INTEGER DEFAULT 0,
                estoque_minimo INTEGER DEFAULT 5,
                escola_id INTEGER,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ativo INTEGER DEFAULT 1,
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
                desconto REAL DEFAULT 0,
                valor_final REAL DEFAULT 0,
                observacoes TEXT,
                forma_pagamento TEXT,
                vendedor_id INTEGER,
                FOREIGN KEY (cliente_id) REFERENCES clientes (id),
                FOREIGN KEY (vendedor_id) REFERENCES usuarios (id)
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
                FOREIGN KEY (pedido_id) REFERENCES pedidos (id) ON DELETE CASCADE,
                FOREIGN KEY (produto_id) REFERENCES produtos (id)
            )
        ''')
        
        # Índices para melhor performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_cliente_id ON pedidos(cliente_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_data ON pedidos(data_pedido)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedido_itens_pedido ON pedido_itens(pedido_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pedido_itens_produto ON pedido_itens(produto_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_produtos_escola ON produtos(escola_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clientes_nome ON clientes(nome)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clientes_data ON clientes(data_cadastro)')
        
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
            ('Escola Municipal', 'Rua Principal, 123', '(11) 9999-8888', 'contato@escolamunicipal.com'),
            ('Colégio Desperta', 'Av. Central, 456', '(11) 7777-6666', 'contato@colegiodesperta.com'),
            ('Instituto São Tadeu', 'Praça da Matriz, 789', '(11) 5555-4444', 'contato@institutosãotadeu.com')
        ]
        
        for nome, endereco, telefone, email in escolas_padrao:
            cursor.execute('INSERT OR IGNORE INTO escolas (nome, endereco, telefone, email) VALUES (?, ?, ?, ?)', 
                         (nome, endereco, telefone, email))
        
        # Produtos de exemplo
        produtos_padrao = [
            ('Camiseta Polo', 'Camiseta', 'M', 'Branco', 29.90, 15.00, 50, 5, 1),
            ('Calça Jeans', 'Calça', '42', 'Azul', 89.90, 45.00, 30, 3, 1),
            ('Agasalho', 'Agasalho', 'G', 'Verde', 129.90, 65.00, 20, 2, 2),
            ('Short', 'Short', 'P', 'Preto', 39.90, 20.00, 40, 5, 2),
            ('Camiseta Regata', 'Camiseta', 'G', 'Vermelho', 24.90, 12.00, 25, 5, 3),
            ('Blusa Moletom', 'Agasalho', 'M', 'Cinza', 79.90, 35.00, 35, 4, 1),
            ('Bermuda', 'Short', '38', 'Azul Marinho', 49.90, 22.00, 28, 3, 2),
        ]
        
        for nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id in produtos_padrao:
            cursor.execute('''
                INSERT OR IGNORE INTO produtos (nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nome, categoria, tamanho, cor, preco, custo, estoque, estoque_minimo, escola_id))
        
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
# 📊 FUNÇÕES DO SISTEMA - OTIMIZADAS
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

def adicionar_escola(nome, endereco, telefone, email):
    """Adiciona nova escola"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO escolas (nome, endereco, telefone, email)
            VALUES (?, ?, ?, ?)
        ''', (nome, endereco, telefone, email))
        
        conn.commit()
        return True, "✅ Escola cadastrada com sucesso!"
    except sqlite3.IntegrityError:
        return False, "❌ Escola já existe"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def editar_escola(escola_id, nome, endereco, telefone, email):
    """Edita escola existente"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE escolas 
            SET nome = ?, endereco = ?, telefone = ?, email = ?
            WHERE id = ?
        ''', (nome, endereco, telefone, email, escola_id))
        
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

def adicionar_cliente(nome, telefone=None, email=None, data_nascimento=None, cpf=None, endereco=None):
    """Adiciona cliente SIMPLIFICADO - apenas nome obrigatório"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO clientes (nome, telefone, email, data_nascimento, cpf, endereco) VALUES (?, ?, ?, ?, ?, ?)",
            (nome.strip(), telefone, email, data_nascimento, cpf, endereco)
        )
        conn.commit()
        return True, "✅ Cliente cadastrado com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_clientes_paginado(offset=0, limit=50, busca=None):
    """Lista clientes com paginação"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        if busca:
            cursor.execute('''
                SELECT * FROM clientes 
                WHERE nome LIKE ? OR telefone LIKE ? OR email LIKE ?
                ORDER BY nome
                LIMIT ? OFFSET ?
            ''', (f'%{busca}%', f'%{busca}%', f'%{busca}%', limit, offset))
        else:
            cursor.execute('''
                SELECT * FROM clientes 
                ORDER BY nome
                LIMIT ? OFFSET ?
            ''', (limit, offset))
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar clientes: {e}")
        return []
    finally:
        if conn:
            conn.close()

def contar_clientes(busca=None):
    """Conta total de clientes para paginação"""
    conn = get_connection()
    if not conn:
        return 0
    
    try:
        cursor = conn.cursor()
        if busca:
            cursor.execute('''
                SELECT COUNT(*) FROM clientes 
                WHERE nome LIKE ? OR telefone LIKE ? OR email LIKE ?
            ''', (f'%{busca}%', f'%{busca}%', f'%{busca}%'))
        else:
            cursor.execute('SELECT COUNT(*) FROM clientes')
        return cursor.fetchone()[0]
    except Exception as e:
        st.error(f"Erro ao contar clientes: {e}")
        return 0
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

def editar_cliente(cliente_id, nome, telefone=None, email=None, data_nascimento=None, cpf=None, endereco=None):
    """Edita cliente existente - versão simplificada"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE clientes 
            SET nome = ?, telefone = ?, email = ?, data_nascimento = ?, cpf = ?, endereco = ?
            WHERE id = ?
        ''', (nome.strip(), telefone, email, data_nascimento, cpf, endereco, cliente_id))
        
        conn.commit()
        return True, "✅ Cliente atualizado com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

# =========================================
# 📦 FUNÇÕES DE PEDIDOS
# =========================================

def criar_pedido(cliente_id, itens, observacoes="", forma_pagamento="", vendedor_id=1):
    """Cria um novo pedido"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cursor = conn.cursor()
        
        # Calcular valor total
        valor_total = sum(item['quantidade'] * item['preco_unitario'] for item in itens)
        valor_final = valor_total  # Sem desconto por padrão
        
        # Inserir pedido
        cursor.execute('''
            INSERT INTO pedidos (cliente_id, valor_total, valor_final, observacoes, forma_pagamento, vendedor_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (cliente_id, valor_total, valor_final, observacoes, forma_pagamento, vendedor_id))
        
        pedido_id = cursor.lastrowid
        
        # Inserir itens do pedido
        for item in itens:
            subtotal = item['quantidade'] * item['preco_unitario']
            cursor.execute('''
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
            ''', (pedido_id, item['produto_id'], item['quantidade'], item['preco_unitario'], subtotal))
        
        conn.commit()
        return True, f"✅ Pedido #{pedido_id} criado com sucesso!"
        
    except Exception as e:
        return False, f"❌ Erro ao criar pedido: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_pedidos():
    """Lista todos os pedidos"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, c.nome as cliente_nome, u.nome_completo as vendedor_nome
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            LEFT JOIN usuarios u ON p.vendedor_id = u.id
            ORDER BY p.data_pedido DESC
        ''')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar pedidos: {e}")
        return []
    finally:
        if conn:
            conn.close()

def listar_produtos():
    """Lista produtos para pedidos"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, nome, categoria, tamanho, cor, preco, estoque
            FROM produtos 
            WHERE estoque > 0 AND ativo = 1
            ORDER BY nome, tamanho
        ''')
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar produtos: {e}")
        return []
    finally:
        if conn:
            conn.close()

# =========================================
# 📄 FUNÇÕES DE RELATÓRIO (APENAS CSV)
# =========================================

def gerar_csv_dados(tipo_dados):
    """Gera CSV para exportação"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        output = io.StringIO()
        writer = csv.writer(output)
        
        if tipo_dados == "clientes":
            cursor.execute('''
                SELECT nome, telefone, email, data_nascimento, cpf, endereco, data_cadastro 
                FROM clientes 
                ORDER BY nome
            ''')
            writer.writerow(['Nome', 'Telefone', 'Email', 'Data Nascimento', 'CPF', 'Endereço', 'Data Cadastro'])
            
            for row in cursor.fetchall():
                writer.writerow([
                    row['nome'],
                    row['telefone'] or '',
                    row['email'] or '',
                    formatar_data_brasil(row['data_nascimento']) if row['data_nascimento'] else '',
                    row['cpf'] or '',
                    row['endereco'] or '',
                    formatar_datahora_brasil(row['data_cadastro'])
                ])
        
        elif tipo_dados == "pedidos":
            cursor.execute('''
                SELECT p.id, c.nome as cliente, p.status, p.data_pedido, p.valor_final,
                       p.forma_pagamento, u.nome_completo as vendedor
                FROM pedidos p
                LEFT JOIN clientes c ON p.cliente_id = c.id
                LEFT JOIN usuarios u ON p.vendedor_id = u.id
                ORDER BY p.data_pedido DESC
            ''')
            writer.writerow(['ID', 'Cliente', 'Status', 'Data Pedido', 'Valor Final', 'Pagamento', 'Vendedor'])
            
            for row in cursor.fetchall():
                writer.writerow([
                    row['id'],
                    row['cliente'],
                    row['status'],
                    formatar_datahora_brasil(row['data_pedido']),
                    f"R$ {row['valor_final']:.2f}" if row['valor_final'] else 'R$ 0,00',
                    row['forma_pagamento'] or '',
                    row['vendedor'] or ''
                ])
        
        csv_data = output.getvalue()
        output.close()
        return csv_data
        
    except Exception as e:
        st.error(f"Erro ao gerar CSV: {e}")
        return None
    finally:
        if conn:
            conn.close()

def baixar_csv(data, filename):
    """Cria botão de download para CSV"""
    if data:
        b64 = base64.b64encode(data.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="{filename}.csv" class="stButton">📥 Baixar {filename}</a>'
        st.markdown(href, unsafe_allow_html=True)

# =========================================
# 👥 INTERFACE CLIENTES (CORRIGIDA)
# =========================================

def mostrar_clientes():
    """Interface SIMPLIFICADA para gerenciar clientes"""
    st.header("👥 Gerenciar Clientes")
    
    # Abas para organização
    tab1, tab2, tab3 = st.tabs(["📋 Lista de Clientes", "➕ Novo Cliente", "✏️ Editar Cliente"])
    
    with tab1:
        st.subheader("Lista de Clientes")
        
        # Busca
        busca = st.text_input("🔍 Buscar cliente por nome, telefone ou email:")
        
        # Paginação
        limit = 20
        total_clientes = contar_clientes(busca)
        total_paginas = max(1, (total_clientes + limit - 1) // limit)
        
        if 'pagina_clientes' not in st.session_state:
            st.session_state.pagina_clientes = 1
        
        col1, col2, col3, col4 = st.columns([2,1,1,1])
        with col1:
            st.write(f"**Total:** {total_clientes} clientes")
        with col2:
            if st.button("⏮️ Prim") and st.session_state.pagina_clientes > 1:
                st.session_state.pagina_clientes = 1
        with col3:
            if st.button("◀️ Ant") and st.session_state.pagina_clientes > 1:
                st.session_state.pagina_clientes -= 1
        with col4:
            if st.button("Próx ▶️") and st.session_state.pagina_clientes < total_paginas:
                st.session_state.pagina_clientes += 1
        
        st.write(f"**Página {st.session_state.pagina_clientes} de {total_paginas}**")
        
        # Lista de clientes
        offset = (st.session_state.pagina_clientes - 1) * limit
        clientes = listar_clientes_paginado(offset, limit, busca)
        
        if not clientes:
            st.info("Nenhum cliente encontrado.")
        else:
            for cliente in clientes:
                with st.expander(f"**{cliente['nome']}** - 📞 {cliente['telefone'] or 'N/A'}"):
                    col1, col2 = st.columns([3,1])
                    with col1:
                        st.write(f"**Email:** {cliente['email'] or 'N/A'}")
                        st.write(f"**CPF:** {cliente['cpf'] or 'N/A'}")
                        st.write(f"**Endereço:** {cliente['endereco'] or 'N/A'}")
                        if cliente['data_nascimento']:
                            st.write(f"**Data Nasc.:** {formatar_data_brasil(cliente['data_nascimento'])}")
                        st.write(f"**Cadastro:** {formatar_datahora_brasil(cliente['data_cadastro'])}")
                    
                    with col2:
                        if st.button("🗑️ Excluir", key=f"del_{cliente['id']}"):
                            success, message = excluir_cliente(cliente['id'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
            
            # Exportar dados
            st.subheader("Exportar Dados")
            if st.button("📊 Exportar Clientes para CSV"):
                csv_data = gerar_csv_dados("clientes")
                if csv_data:
                    baixar_csv(csv_data, "clientes")
    
    with tab2:
        st.subheader("Cadastrar Novo Cliente")
        
        with st.form("form_novo_cliente", clear_on_submit=True):
            nome = st.text_input("Nome Completo*", placeholder="Digite o nome do cliente", key="novo_nome")
            
            col1, col2 = st.columns(2)
            with col1:
                telefone = st.text_input("Telefone", placeholder="(11) 99999-9999", key="novo_telefone")
                email = st.text_input("Email", placeholder="cliente@email.com", key="novo_email")
            with col2:
                cpf = st.text_input("CPF", placeholder="000.000.000-00", key="novo_cpf")
                data_nascimento = st.date_input("Data de Nascimento", key="novo_nascimento")
            
            endereco = st.text_area("Endereço", placeholder="Rua, número, bairro, cidade...", key="novo_endereco")
            
            submitted = st.form_submit_button("✅ Cadastrar Cliente")
            if submitted:
                if not nome.strip():
                    st.error("❌ O nome é obrigatório!")
                else:
                    success, message = adicionar_cliente(
                        nome=nome.strip(),
                        telefone=telefone.strip() if telefone else None,
                        email=email.strip() if email else None,
                        data_nascimento=data_nascimento,
                        cpf=cpf.strip() if cpf else None,
                        endereco=endereco.strip() if endereco else None
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    
    with tab3:
        st.subheader("Editar Cliente")
        
        # Selecionar cliente para editar
        clientes_all = listar_clientes_paginado(0, 1000)  # Busca todos para seleção
        if clientes_all:
            cliente_opcoes = {f"{c['id']} - {c['nome']}": c['id'] for c in clientes_all}
            cliente_selecionado = st.selectbox(
                "Selecione o cliente para editar:",
                options=list(cliente_opcoes.keys()),
                key="editar_cliente_select"
            )
            
            if cliente_selecionado:
                cliente_id = cliente_opcoes[cliente_selecionado]
                cliente_data = next((c for c in clientes_all if c['id'] == cliente_id), None)
                
                if cliente_data:
                    with st.form("form_editar_cliente"):
                        nome = st.text_input("Nome*", value=cliente_data['nome'], key="editar_nome")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            telefone = st.text_input("Telefone", value=cliente_data['telefone'] or "", key="editar_telefone")
                            email = st.text_input("Email", value=cliente_data['email'] or "", key="editar_email")
                        with col2:
                            cpf = st.text_input("CPF", value=cliente_data['cpf'] or "", key="editar_cpf")
                            data_nascimento = st.date_input(
                                "Data Nascimento", 
                                value=datetime.strptime(cliente_data['data_nascimento'], '%Y-%m-%d').date() if cliente_data['data_nascimento'] else datetime.now().date(),
                                key="editar_nascimento"
                            )
                        
                        endereco = st.text_area("Endereço", value=cliente_data['endereco'] or "", key="editar_endereco")
                        
                        submitted_edit = st.form_submit_button("💾 Salvar Alterações")
                        if submitted_edit:
                            if not nome.strip():
                                st.error("❌ O nome é obrigatório!")
                            else:
                                success, message = editar_cliente(
                                    cliente_id=cliente_id,
                                    nome=nome.strip(),
                                    telefone=telefone.strip() if telefone else None,
                                    email=email.strip() if email else None,
                                    data_nascimento=data_nascimento,
                                    cpf=cpf.strip() if cpf else None,
                                    endereco=endereco.strip() if endereco else None
                                )
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
        else:
            st.info("Nenhum cliente cadastrado para editar.")

# =========================================
# 📦 INTERFACE DE PEDIDOS
# =========================================

def mostrar_pedidos():
    """Interface de pedidos com datas em português"""
    st.header("📦 Gerenciar Pedidos")
    
    tab1, tab2 = st.tabs(["📋 Lista de Pedidos", "➕ Novo Pedido"])
    
    with tab1:
        st.subheader("Pedidos Realizados")
        
        pedidos = listar_pedidos()
        if not pedidos:
            st.info("Nenhum pedido encontrado.")
        else:
            for pedido in pedidos:
                with st.expander(f"Pedido #{pedido['id']} - {pedido['cliente_nome']} - {formatar_datahora_brasil(pedido['data_pedido'])}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"**Cliente:** {pedido['cliente_nome']}")
                        st.write(f"**Status:** {pedido['status']}")
                        st.write(f"**Vendedor:** {pedido['vendedor_nome'] or 'N/A'}")
                    
                    with col2:
                        st.write(f"**Data do Pedido:** {formatar_datahora_brasil(pedido['data_pedido'])}")
                        if pedido['data_entrega_prevista']:
                            st.write(f"**Entrega Prevista:** {formatar_data_brasil(pedido['data_entrega_prevista'])}")
                        if pedido['data_entrega_real']:
                            st.write(f"**Entrega Real:** {formatar_data_brasil(pedido['data_entrega_real'])}")
                    
                    with col3:
                        st.write(f"**Valor Total:** R$ {pedido['valor_total']:.2f}")
                        st.write(f"**Valor Final:** R$ {pedido['valor_final']:.2f}")
                        st.write(f"**Pagamento:** {pedido['forma_pagamento'] or 'N/A'}")
                    
                    if pedido['observacoes']:
                        st.write(f"**Observações:** {pedido['observacoes']}")
    
    with tab2:
        st.subheader("Criar Novo Pedido")
        
        # Selecionar cliente
        clientes = listar_clientes_paginado(0, 100)
        if not clientes:
            st.warning("Nenhum cliente cadastrado. Cadastre clientes primeiro.")
            return
        
        cliente_opcoes = {f"{c['nome']} - {c['telefone'] or 'N/A'}": c['id'] for c in clientes}
        cliente_selecionado = st.selectbox("Selecione o cliente:", options=list(cliente_opcoes.keys()))
        
        if cliente_selecionado:
            cliente_id = cliente_opcoes[cliente_selecionado]
            
            # Selecionar produtos
            produtos = listar_produtos()
            if not produtos:
                st.warning("Nenhum produto disponível em estoque.")
                return
            
            st.subheader("Adicionar Itens ao Pedido")
            
            if 'itens_pedido' not in st.session_state:
                st.session_state.itens_pedido = []
            
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                produto_selecionado = st.selectbox(
                    "Produto:",
                    options=[f"{p['id']} - {p['nome']} ({p['tamanho']}) - R$ {p['preco']:.2f}" for p in produtos],
                    key="produto_select"
                )
            
            with col2:
                quantidade = st.number_input("Quantidade:", min_value=1, value=1, key="quantidade_input")
            
            with col3:
                if produto_selecionado:
                    produto_id = int(produto_selecionado.split(' - ')[0])
                    produto_info = next((p for p in produtos if p['id'] == produto_id), None)
                    if produto_info:
                        preco_unitario = produto_info['preco']
                        st.write(f"**Preço unitário:** R$ {preco_unitario:.2f}")
            
            with col4:
                st.write("")  # Espaço
                if st.button("➕ Adicionar", key="add_item"):
                    if produto_selecionado:
                        produto_id = int(produto_selecionado.split(' - ')[0])
                        produto_info = next((p for p in produtos if p['id'] == produto_id), None)
                        
                        if produto_info:
                            # Verificar estoque
                            if quantidade > produto_info['estoque']:
                                st.error(f"❌ Estoque insuficiente! Disponível: {produto_info['estoque']}")
                            else:
                                item = {
                                    'produto_id': produto_id,
                                    'nome': produto_info['nome'],
                                    'tamanho': produto_info['tamanho'],
                                    'quantidade': quantidade,
                                    'preco_unitario': produto_info['preco'],
                                    'subtotal': quantidade * produto_info['preco']
                                }
                                st.session_state.itens_pedido.append(item)
                                st.success(f"✅ {quantidade}x {produto_info['nome']} adicionado!")
                                st.rerun()
            
            # Mostrar itens do pedido
            if st.session_state.itens_pedido:
                st.subheader("Itens do Pedido")
                total_pedido = 0
                
                for i, item in enumerate(st.session_state.itens_pedido):
                    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
                    
                    with col1:
                        st.write(f"**{item['nome']}** ({item['tamanho']})")
                    
                    with col2:
                        st.write(f"Qtd: {item['quantidade']}")
                    
                    with col3:
                        st.write(f"R$ {item['preco_unitario']:.2f}")
                    
                    with col4:
                        subtotal = item['quantidade'] * item['preco_unitario']
                        st.write(f"**R$ {subtotal:.2f}**")
                        total_pedido += subtotal
                    
                    with col5:
                        if st.button("🗑️", key=f"remove_{i}"):
                            st.session_state.itens_pedido.pop(i)
                            st.rerun()
                
                st.write(f"**Total do Pedido: R$ {total_pedido:.2f}**")
                
                # Forma de pagamento e observações
                forma_pagamento = st.selectbox(
                    "Forma de Pagamento:",
                    ["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "PIX", "Boleto"],
                    key="forma_pagamento"
                )
                
                observacoes = st.text_area("Observações:", placeholder="Observações sobre o pedido...")
                
                # Botão finalizar pedido
                if st.button("✅ Finalizar Pedido", type="primary"):
                    if not st.session_state.itens_pedido:
                        st.error("❌ Adicione itens ao pedido!")
                    else:
                        success, message = criar_pedido(
                            cliente_id=cliente_id,
                            itens=st.session_state.itens_pedido,
                            observacoes=observacoes,
                            forma_pagamento=forma_pagamento,
                            vendedor_id=1  # ID do usuário logado (simplificado)
                        )
                        
                        if success:
                            st.success(message)
                            # Limpar itens do pedido
                            st.session_state.itens_pedido = []
                            st.rerun()
                        else:
                            st.error(message)
            else:
                st.info("Adicione itens ao pedido usando o formulário acima.")

# =========================================
# 🏠 PÁGINA DE LOGIN
# =========================================

def pagina_login():
    """Página de login"""
    st.title("👕 Sistema Fardamentos + A.I.")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1,2,1])
    
    with col2:
        with st.container():
            st.subheader("🔐 Login")
            
            with st.form("login_form"):
                username = st.text_input("Usuário", placeholder="Digite seu username")
                password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
                
                submit = st.form_submit_button("Entrar")
                
                if submit:
                    if not username or not password:
                        st.error("⚠️ Preencha todos os campos!")
                    else:
                        with st.spinner("Verificando credenciais..."):
                            success, nome_completo, tipo = verificar_login(username, password)
                            
                            if success:
                                st.session_state.logged_in = True
                                st.session_state.username = username
                                st.session_state.nome_completo = nome_completo
                                st.session_state.tipo_usuario = tipo
                                st.success(f"✅ Bem-vindo, {nome_completo}!")
                                st.rerun()
                            else:
                                st.error("❌ Credenciais inválidas!")
            
            st.markdown("---")
            st.markdown("""
            **Credenciais para teste:**
            - **Admin:** admin / admin123
            - **Gestor:** gestor / gestor123  
            - **Vendedor:** vendedor / vendedor123
            """)

# =========================================
# 📊 DASHBOARD PRINCIPAL
# =========================================

def mostrar_dashboard():
    """Dashboard principal"""
    st.title(f"👕 Dashboard - Sistema Fardamentos")
    st.markdown(f"**Usuário:** {st.session_state.nome_completo} | **Tipo:** {st.session_state.tipo_usuario} | **Data:** {data_atual_brasil()}")
    st.markdown("---")
    
    # Métricas rápidas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Clientes", contar_clientes())
    with col2:
        st.metric("Pedidos Hoje", "15")
    with col3:
        st.metric("Valor em Vendas", "R$ 2.850,00")
    with col4:
        st.metric("Produtos em Estoque", "248")
    
    st.markdown("---")
    
    # Insights da A.I.
    st.subheader("🤖 Insights da Inteligência Artificial")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="ai-insight-positive">', unsafe_allow_html=True)
        st.markdown("**📈 Tendência Positiva**")
        st.markdown("Vendas de agasalhos aumentaram 25% nesta semana")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="ai-insight-warning">', unsafe_allow_html=True)
        st.markdown("**⚠️ Atenção Necessária**")
        st.markdown("Estoque de camisetas tamanho P abaixo do mínimo")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="ai-insight-positive">', unsafe_allow_html=True)
        st.markdown("**🎯 Oportunidade**")
        st.markdown("Cliente João Silva compra a cada 30 dias - próximo vencimento em 5 dias")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="ai-insight-danger">', unsafe_allow_html=True)
        st.markdown("**🔴 Alerta Crítico**")
        st.markdown("3 pedidos com entrega atrasada")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Ações rápidas
    st.subheader("🚀 Ações Rápidas")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("👥 Gerenciar Clientes", use_container_width=True):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col2:
        if st.button("📦 Novo Pedido", use_container_width=True):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()
    
    with col3:
        if st.button("📊 Relatórios", use_container_width=True):
            st.session_state.menu = "📊 Relatórios"
            st.rerun()
    
    with col4:
        if st.button("⚙️ Configurações", use_container_width=True):
            st.session_state.menu = "⚙️ Administração"
            st.rerun()

# =========================================
# 🧩 COMPONENTES DE INTERFACE
# =========================================

def mostrar_menu_principal():
    """Menu de navegação principal"""
    st.sidebar.title("👕 Menu Principal")
    st.sidebar.markdown(f"**Usuário:** {st.session_state.nome_completo}")
    st.sidebar.markdown(f"**Tipo:** {st.session_state.tipo_usuario}")
    st.sidebar.markdown("---")
    
    # Menu baseado no tipo de usuário
    menu_options = ["🏠 Dashboard"]
    
    if st.session_state.tipo_usuario in ['admin', 'gestor', 'vendedor']:
        menu_options.extend(["👥 Clientes", "📦 Pedidos", "📊 Relatórios"])
    
    if st.session_state.tipo_usuario in ['admin', 'gestor']:
        menu_options.extend(["⚙️ Administração"])
    
    menu = st.sidebar.selectbox("Navegação", menu_options, key="menu_select")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    
    return menu

# =========================================
# 📊 FUNÇÕES DE RELATÓRIOS
# =========================================

def mostrar_relatorios():
    """Interface de relatórios"""
    st.header("📊 Relatórios e Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Exportar Dados")
        
        if st.button("📋 Exportar Clientes para CSV"):
            csv_data = gerar_csv_dados("clientes")
            if csv_data:
                baixar_csv(csv_data, "clientes")
        
        if st.button("📦 Exportar Pedidos para CSV"):
            csv_data = gerar_csv_dados("pedidos")
            if csv_data:
                baixar_csv(csv_data, "pedidos")
    
    with col2:
        st.subheader("Relatórios Rápidos")
        st.metric("Total de Clientes", contar_clientes())
        st.metric("Clientes Novos (30 dias)", "12")
        st.metric("Ticket Médio", "R$ 189,50")

# =========================================
# ⚙️ FUNÇÕES ADMINISTRATIVAS
# =========================================

def mostrar_administracao():
    """Interface administrativa"""
    st.header("⚙️ Administração do Sistema")
    
    if st.session_state.tipo_usuario not in ['admin', 'gestor']:
        st.error("❌ Acesso negado! Esta área é restrita.")
        return
    
    tab1, tab2, tab3 = st.tabs(["👥 Usuários", "🏫 Escolas", "🔧 Sistema"])
    
    with tab1:
        st.subheader("Gerenciar Usuários")
        
        # Listar usuários
        usuarios = listar_usuarios()
        if usuarios:
            for usuario in usuarios:
                status = "✅ Ativo" if usuario['ativo'] else "❌ Inativo"
                st.write(f"**{usuario['nome_completo']}** ({usuario['username']}) - {usuario['tipo']} - {status}")
        else:
            st.info("Nenhum usuário cadastrado.")
    
    with tab2:
        st.subheader("Gerenciar Escolas")
        st.info("Funcionalidade de escolas em desenvolvimento...")
    
    with tab3:
        st.subheader("Configurações do Sistema")
        
        if st.button("🔄 Reinicializar Banco de Dados"):
            with st.spinner("Reinicializando banco..."):
                if init_db():
                    st.success("✅ Banco reinicializado com sucesso!")
                else:
                    st.error("❌ Erro ao reinicializar banco!")

# =========================================
# 🎯 APLICAÇÃO PRINCIPAL
# =========================================

def main():
    """Aplicação principal"""
    
    # Inicializar banco
    if not init_db():
        st.error("❌ Erro ao inicializar banco de dados!")
        return
    
    # Verificar autenticação
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        pagina_login()
        return
    
    # Menu principal
    menu = mostrar_menu_principal()
    
    # Navegação
    if menu == "🏠 Dashboard":
        mostrar_dashboard()
    elif menu == "👥 Clientes":
        mostrar_clientes()
    elif menu == "📦 Pedidos":
        mostrar_pedidos()
    elif menu == "📊 Relatórios":
        mostrar_relatorios()
    elif menu == "⚙️ Administração":
        mostrar_administracao()

if __name__ == "__main__":
    main()
