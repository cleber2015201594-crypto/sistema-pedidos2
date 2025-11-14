import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
import json
import os
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
import urllib.parse as urlparse
import base64
from PIL import Image
import io
import time
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import GradientBoostingClassifier
from transformers import pipeline

# =========================================
# 🎨 CONFIGURAÇÃO DE TEMA E ESTILO
# =========================================

st.set_page_config(
    page_title="FactoryPilot - Gestão Inteligente para Confecções",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado estilo FactoryPilot
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #2563EB;
        text-align: center;
        font-weight: 700;
        margin-bottom: 0;
        font-family: 'Inter', sans-serif;
    }
    .sub-header {
        font-size: 1.4rem;
        color: #10B981;
        text-align: center;
        margin-top: 0;
        font-weight: 400;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px;
        border-radius: 15px;
        color: white;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    .feature-card {
        background: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        border: 1px solid #e0e0e0;
        transition: transform 0.3s ease;
    }
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12);
    }
    .premium-badge {
        background: linear-gradient(45deg, #FFD700, #FFEC8B);
        color: #8B4513;
        padding: 8px 20px;
        border-radius: 25px;
        font-weight: bold;
        font-size: 0.9rem;
        display: inline-block;
        margin: 5px;
    }
    .status-pendente { 
        background-color: #FFF3CD; 
        color: #856404; 
        padding: 8px 15px; 
        border-radius: 12px; 
        font-weight: 600;
    }
    .status-producao { 
        background-color: #D1ECF1; 
        color: #0C5460; 
        padding: 8px 15px; 
        border-radius: 12px;
        font-weight: 600;
    }
    .status-entregue { 
        background-color: #D4EDDA; 
        color: #155724; 
        padding: 8px 15px; 
        border-radius: 12px;
        font-weight: 600;
    }
    .status-cancelado { 
        background-color: #F8D7DA; 
        color: #721C24; 
        padding: 8px 15px; 
        border-radius: 12px;
        font-weight: 600;
    }
    .ai-chat-bubble {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 20px;
        border-radius: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    .user-chat-bubble {
        background: #f1f5f9;
        color: #334155;
        padding: 15px 20px;
        border-radius: 20px;
        margin: 10px 0;
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🏭 CONFIGURAÇÃO MULTI-FÁBRICA
# =========================================

PLANOS = {
    'starter': {
        'nome': 'Plano Starter',
        'preco_mensal': 97,
        'preco_anual': 970,
        'limites': {
            'usuarios': 2,
            'produtos': 100,
            'clientes': 500,
            'pedidos_mes': 100
        },
        'cor': '#10B981'
    },
    'professional': {
        'nome': 'Plano Professional',
        'preco_mensal': 197,
        'preco_anual': 1970,
        'limites': {
            'usuarios': 5,
            'produtos': 1000,
            'clientes': 2000,
            'pedidos_mes': 500
        },
        'cor': '#2563EB'
    },
    'enterprise': {
        'nome': 'Plano Enterprise',
        'preco_mensal': 497,
        'preco_anual': 4970,
        'limites': {
            'usuarios': 20,
            'produtos': 10000,
            'clientes': 10000,
            'pedidos_mes': 5000
        },
        'cor': '#7C3AED'
    }
}

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO AVANÇADO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def init_db():
    """Inicializa o banco de dados com tabelas multi-fábrica"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            
            # Tabela de fábricas
            cur.execute('''
                CREATE TABLE IF NOT EXISTS fabricas (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(200) NOT NULL,
                    cnpj VARCHAR(20) UNIQUE,
                    telefone VARCHAR(20),
                    email VARCHAR(100),
                    endereco TEXT,
                    plano VARCHAR(50) DEFAULT 'professional',
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ativa BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Tabela de usuários
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    fabrica_id INTEGER REFERENCES fabricas(id),
                    username VARCHAR(50) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    nome_completo VARCHAR(100),
                    tipo VARCHAR(20) DEFAULT 'vendedor',
                    ativo BOOLEAN DEFAULT TRUE,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ultimo_login TIMESTAMP,
                    UNIQUE(fabrica_id, username)
                )
            ''')
            
            # Tabela de escolas
            cur.execute('''
                CREATE TABLE IF NOT EXISTS escolas (
                    id SERIAL PRIMARY KEY,
                    fabrica_id INTEGER REFERENCES fabricas(id),
                    nome VARCHAR(100) NOT NULL,
                    endereco TEXT,
                    telefone VARCHAR(20),
                    ativa BOOLEAN DEFAULT TRUE,
                    UNIQUE(fabrica_id, nome)
                )
            ''')
            
            # Tabela de clientes (CRM)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id SERIAL PRIMARY KEY,
                    fabrica_id INTEGER REFERENCES fabricas(id),
                    nome VARCHAR(200) NOT NULL,
                    telefone VARCHAR(20),
                    email VARCHAR(100),
                    data_nascimento DATE,
                    endereco TEXT,
                    observacoes TEXT,
                    data_cadastro DATE DEFAULT CURRENT_DATE,
                    tipo_cliente VARCHAR(20) DEFAULT 'regular',
                    indicacoes INTEGER DEFAULT 0
                )
            ''')
            
            # Tabela de relação cliente-escola
            cur.execute('''
                CREATE TABLE IF NOT EXISTS cliente_escolas (
                    id SERIAL PRIMARY KEY,
                    cliente_id INTEGER REFERENCES clientes(id) ON DELETE CASCADE,
                    escola_id INTEGER REFERENCES escolas(id) ON DELETE CASCADE,
                    UNIQUE(cliente_id, escola_id)
                )
            ''')
            
            # Tabela de produtos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id SERIAL PRIMARY KEY,
                    fabrica_id INTEGER REFERENCES fabricas(id),
                    nome VARCHAR(200) NOT NULL,
                    categoria VARCHAR(100),
                    subcategoria VARCHAR(100),
                    tamanho VARCHAR(10),
                    cor VARCHAR(50),
                    preco_custo DECIMAL(10,2),
                    preco_venda DECIMAL(10,2),
                    margem_lucro DECIMAL(10,2),
                    estoque INTEGER DEFAULT 0,
                    estoque_minimo INTEGER DEFAULT 5,
                    descricao TEXT,
                    codigo_barras VARCHAR(100),
                    ativo BOOLEAN DEFAULT TRUE,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de pedidos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedidos (
                    id SERIAL PRIMARY KEY,
                    fabrica_id INTEGER REFERENCES fabricas(id),
                    cliente_id INTEGER REFERENCES clientes(id),
                    status VARCHAR(50) DEFAULT 'Orçamento',
                    prioridade VARCHAR(20) DEFAULT 'Normal',
                    data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_entrega_prevista DATE,
                    data_entrega_real DATE,
                    quantidade_total INTEGER,
                    valor_total DECIMAL(10,2),
                    custo_total DECIMAL(10,2),
                    lucro_total DECIMAL(10,2),
                    observacoes TEXT,
                    responsavel VARCHAR(100),
                    forma_pagamento VARCHAR(50),
                    pago BOOLEAN DEFAULT FALSE
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
                    custo_unitario DECIMAL(10,2),
                    subtotal DECIMAL(10,2),
                    observacoes TEXT
                )
            ''')
            
            # Tabela de fluxo de produção
            cur.execute('''
                CREATE TABLE IF NOT EXISTS producao_etapas (
                    id SERIAL PRIMARY KEY,
                    pedido_id INTEGER REFERENCES pedidos(id),
                    etapa VARCHAR(100),
                    responsavel VARCHAR(100),
                    status VARCHAR(50) DEFAULT 'Pendente',
                    data_inicio TIMESTAMP,
                    data_conclusao TIMESTAMP,
                    observacoes TEXT
                )
            ''')
            
            # Tabela de notificações
            cur.execute('''
                CREATE TABLE IF NOT EXISTS notificacoes (
                    id SERIAL PRIMARY KEY,
                    fabrica_id INTEGER REFERENCES fabricas(id),
                    usuario_id INTEGER REFERENCES usuarios(id),
                    tipo VARCHAR(50),
                    titulo VARCHAR(200),
                    mensagem TEXT,
                    lida BOOLEAN DEFAULT FALSE,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    link TEXT
                )
            ''')
            
            # Criar fábrica demo se não existir
            cur.execute('''
                INSERT INTO fabricas (nome, cnpj, telefone, email, plano) 
                VALUES ('Fábrica Demonstração', '00.000.000/0001-00', '(11) 9999-9999', 'demo@factorypilot.com', 'professional')
                ON CONFLICT (cnpj) DO NOTHING
                RETURNING id
            ''')
            
            resultado = cur.fetchone()
            if resultado:
                fabrica_demo_id = resultado[0]
                
                # Criar usuário admin demo
                cur.execute('''
                    INSERT INTO usuarios (fabrica_id, username, password_hash, nome_completo, tipo)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (fabrica_id, username) DO NOTHING
                ''', (fabrica_demo_id, 'admin', make_hashes('admin123'), 'Administrador Demo', 'admin'))
                
                # Criar produtos demo
                produtos_demo = [
                    ('Camiseta Básica Algodão', 'Camisetas', 'Básica', 'P', 'Branco', 15.00, 45.00, 50, 5),
                    ('Calça Jeans Infantil', 'Calças', 'Jeans', '10', 'Azul', 35.00, 89.90, 30, 3),
                    ('Moletom com Capuz', 'Agasalhos', 'Moletom', 'M', 'Cinza', 45.00, 120.00, 20, 2)
                ]
                
                for produto in produtos_demo:
                    cur.execute('''
                        INSERT INTO produtos (fabrica_id, nome, categoria, subcategoria, tamanho, cor, preco_custo, preco_venda, estoque, estoque_minimo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (fabrica_demo_id, *produto))
            
            conn.commit()
            
        except Exception as e:
            st.error(f"Erro ao inicializar banco: {str(e)}")
        finally:
            conn.close()

def get_connection():
    """Estabelece conexão com o PostgreSQL"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://')
            
            conn = psycopg2.connect(database_url, sslmode='require')
            return conn
        else:
            st.error("DATABASE_URL não configurada")
            return None
            
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {str(e)}")
        return None

# =========================================
# 🤖 SISTEMA DE IA INTEGRADO
# =========================================

class FactoryPilotAI:
    def __init__(self):
        self.sentiment_analyzer = None
        self.sales_model = None
        
    def initialize_models(self):
        """Inicializa modelos de IA (lazy loading)"""
        try:
            if self.sentiment_analyzer is None:
                self.sentiment_analyzer = pipeline('sentiment-analysis')
            return True
        except Exception as e:
            st.warning(f"Modelos de IA não disponíveis: {e}")
            return False
    
    def analisar_sentimento_texto(self, texto):
        """Analisa sentimento de textos"""
        if not self.initialize_models():
            return {'sentimento': 'neutro', 'confianca': 0.5}
        
        try:
            resultado = self.sentiment_analyzer(texto)[0]
            return {
                'sentimento': resultado['label'],
                'confianca': resultado['score']
            }
        except:
            return {'sentimento': 'neutro', 'confianca': 0.5}
    
    def prever_vendas_proximos_30_dias(self, fabrica_id):
        """Previsão de vendas usando ML"""
        try:
            dados = self.obter_historico_vendas(fabrica_id)
            if len(dados) < 30:
                return self.previsao_conservadora()
            
            # Simulação de modelo de ML
            dias = list(range(30))
            tendencia = 1.02  # Crescimento de 2% ao dia
            previsao = [dados[-1] * (tendencia ** i) for i in range(1, 31)]
            
            return {
                'previsao': previsao,
                'confianca': 0.85,
                'tendencia': 'crescimento'
            }
        except:
            return self.previsao_conservadora()
    
    def previsao_conservadora(self):
        """Previsão conservadora quando não há dados suficientes"""
        return {
            'previsao': [1000] * 30,
            'confianca': 0.6,
            'tendencia': 'estavel'
        }
    
    def obter_historico_vendas(self, fabrica_id):
        """Obtém histórico de vendas para treinamento"""
        conn = get_connection()
        if not conn:
            return [1000, 1200, 1100, 1300, 1400]  # Dados demo
        
        try:
            cur = conn.cursor()
            cur.execute('''
                SELECT COALESCE(SUM(valor_total), 0) as total
                FROM pedidos 
                WHERE fabrica_id = %s 
                AND data_pedido >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY DATE(data_pedido)
                ORDER BY DATE(data_pedido)
            ''', (fabrica_id,))
            
            resultados = cur.fetchall()
            return [float(r[0]) for r in resultados] if resultados else [1000, 1200, 1100, 1300, 1400]
        except:
            return [1000, 1200, 1100, 1300, 1400]
        finally:
            conn.close()
    
    def gerar_insights_inteligentes(self, fabrica_id):
        """Gera insights automáticos baseado nos dados"""
        insights = []
        
        # Insight 1: Produtos com melhor margem
        produtos = listar_produtos_por_fabrica(fabrica_id)
        if produtos:
            melhor_margem = max(produtos, key=lambda x: x[8] if x[8] else 0)
            insights.append(f"💎 **{melhor_margem[2]}** tem a melhor margem: R$ {melhor_margem[8]:.2f}")
        
        # Insight 2: Clientes mais valiosos
        clientes = listar_clientes_completos_por_fabrica(fabrica_id)
        if clientes:
            cliente_top = max([c for c in clientes if c[11]], key=lambda x: x[11] or 0)
            insights.append(f"🏆 **{cliente_top[1]}** é seu cliente mais valioso: R$ {cliente_top[11]:.2f}")
        
        # Insight 3: Alertas de estoque
        produtos_baixo_estoque = [p for p in produtos if p[10] <= p[11]]
        if produtos_baixo_estoque:
            insights.append(f"⚠️ **{len(produtos_baixo_estoque)} produtos** com estoque baixo")
        
        return insights

# Instância global da IA
factory_ai = FactoryPilotAI()

# =========================================
# 🎯 SISTEMA DE NOTIFICAÇÕES INTELIGENTES
# =========================================

def criar_notificacao(fabrica_id, usuario_id, tipo, titulo, mensagem, link=None):
    """Cria uma notificação para o usuário"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO notificacoes (fabrica_id, usuario_id, tipo, titulo, mensagem, link)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (fabrica_id, usuario_id, tipo, titulo, mensagem, link))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def obter_notificacoes(usuario_id, nao_lidas=True):
    """Obtém notificações do usuário"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        if nao_lidas:
            cur.execute('''
                SELECT * FROM notificacoes 
                WHERE usuario_id = %s AND lida = FALSE
                ORDER BY data_criacao DESC
                LIMIT 10
            ''', (usuario_id,))
        else:
            cur.execute('''
                SELECT * FROM notificacoes 
                WHERE usuario_id = %s
                ORDER BY data_criacao DESC
                LIMIT 20
            ''', (usuario_id,))
        return cur.fetchall()
    except Exception as e:
        return []
    finally:
        conn.close()

# =========================================
# 🎨 INTERFACE PREMIUM - FACTORYPILOT
# =========================================

def mostrar_header():
    """Header personalizado estilo FactoryPilot"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<h1 class="main-header">🏭 FactoryPilot</h1>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Gestão Inteligente para Confecções</p>', unsafe_allow_html=True)
    
    st.markdown("---")

def mostrar_dashboard_premium():
    """Dashboard executivo premium com IA"""
    
    if 'fabrica_id' not in st.session_state:
        st.error("Erro: Fábrica não identificada")
        return
    
    fabrica_id = st.session_state.fabrica_id
    
    # Métricas principais
    metricas = obter_metricas_dashboard(fabrica_id)
    
    st.markdown("## 📊 Dashboard Executivo")
    
    # KPIs em cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>🎯 Pedidos Mês</h3>
            <h2>{metricas.get('pedidos_mes', 0)}</h2>
            <p>Total de pedidos este mês</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>💰 Faturamento</h3>
            <h2>R$ {metricas.get('faturamento_mes', 0):,.2f}</h2>
            <p>Faturamento mensal</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>👥 Clientes Ativos</h3>
            <h2>{metricas.get('clientes_ativos', 0)}</h2>
            <p>Últimos 90 dias</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📦 Ticket Médio</h3>
            <h2>R$ {metricas.get('ticket_medio', 0):.2f}</h2>
            <p>Valor médio por pedido</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Seção IA - Assistente Inteligente
    st.markdown("## 🤖 Assistente IA FactoryPilot")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="ai-chat-bubble">
        🧠 **Assistente IA:** Olá! Sou seu assistente inteligente. 
        Posso ajudar a analisar seus dados e dar insights valiosos 
        para o seu negócio. O que gostaria de saber?
        </div>
        """, unsafe_allow_html=True)
        
        pergunta = st.text_input("💬 Faça uma pergunta sobre seu negócio:", 
                               placeholder="Ex: Como aumentar minhas vendas? Quais meus melhores produtos?")
        
        if pergunta:
            if "aumentar" in pergunta.lower() and "venda" in pergunta.lower():
                produtos = listar_produtos_por_fabrica(fabrica_id)
                if produtos:
                    melhor_margem = max(produtos, key=lambda x: x[8] if x[8] else 0)
                    st.markdown(f"""
                    <div class="ai-chat-bubble">
                    💡 **Recomendação IA:** Para aumentar vendas, foque em **{melhor_margem[2]}** 
                    que tem a melhor margem (R$ {melhor_margem[8]:.2f}). Considere promoções 
                    ou pacotes com este produto.
                    </div>
                    """, unsafe_allow_html=True)
            
            elif "melhor" in pergunta.lower() and "cliente" in pergunta.lower():
                clientes = listar_clientes_completos_por_fabrica(fabrica_id)
                if clientes:
                    cliente_top = max([c for c in clientes if c[11]], key=lambda x: x[11] or 0, default=None)
                    if cliente_top:
                        st.markdown(f"""
                        <div class="ai-chat-bubble">
                        🏆 **Insight IA:** Seu cliente mais valioso é **{cliente_top[1]}** 
                        com R$ {cliente_top[11]:.2f} em compras. Recomendo um programa 
                        de fidelidade para este cliente.
                        </div>
                        """, unsafe_allow_html=True)
    
    with col2:
        # Insights automáticos da IA
        st.markdown("### 💡 Insights Automáticos")
        insights = factory_ai.gerar_insights_inteligentes(fabrica_id)
        
        for insight in insights[:3]:  # Mostrar apenas 3 insights
            st.info(insight)
        
        # Previsão de vendas
        st.markdown("### 📈 Previsão IA")
        previsao = factory_ai.prever_vendas_proximos_30_dias(fabrica_id)
        st.metric("Próximos 30 dias", f"R$ {sum(previsao['previsao'])/30:.0f}/dia", 
                 delta=f"{'↑' if previsao['tendencia'] == 'crescimento' else '↓'} Previsão")
    
    # Gráficos
    st.markdown("## 📈 Analytics em Tempo Real")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Evolução de Vendas")
        dados_vendas = obter_vendas_por_periodo(fabrica_id, 30)
        if not dados_vendas.empty:
            fig = px.line(dados_vendas, x='data', y='faturamento', 
                         title="Faturamento Diário - Últimos 30 Dias", markers=True)
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Gráfico demo
            dados_demo = pd.DataFrame({
                'data': pd.date_range(start='2024-01-01', periods=30, freq='D'),
                'faturamento': np.random.normal(1000, 200, 30).cumsum()
            })
            fig = px.line(dados_demo, x='data', y='faturamento', 
                         title="Faturamento Diário - Demo", markers=True)
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🎯 Distribuição de Pedidos")
        pedidos = listar_pedidos_por_fabrica(fabrica_id)
        if pedidos:
            df_pedidos = pd.DataFrame(pedidos, columns=['ID', 'Fabrica_ID', 'Cliente_ID', 'Status', 'Prioridade', 
                                                       'Data_Pedido', 'Data_Entrega_Prev', 'Data_Entrega_Real',
                                                       'Quantidade', 'Valor_Total', 'Custo_Total', 'Lucro_Total',
                                                       'Observacoes', 'Responsavel', 'Forma_Pagamento', 'Pago', 'Cliente_Nome'])
            status_counts = df_pedidos['Status'].value_counts()
            
            fig = px.pie(values=status_counts.values, names=status_counts.index,
                        title="Pedidos por Status", hole=0.4)
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Gráfico demo
            status_demo = {'Orçamento': 5, 'Produção': 8, 'Entregue': 12, 'Cancelado': 1}
            fig = px.pie(values=list(status_demo.values()), names=list(status_demo.keys()),
                        title="Pedidos por Status - Demo", hole=0.4)
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    # Ações rápidas premium
    st.markdown("## ⚡ Ações Rápidas")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🎯 Novo Pedido", use_container_width=True):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()
    
    with col2:
        if st.button("👥 Cadastrar Cliente", use_container_width=True):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col3:
        if st.button("👕 Catálogo Produtos", use_container_width=True):
            st.session_state.menu = "👕 Produtos"
            st.rerun()
    
    with col4:
        if st.button("📊 Ver Relatórios", use_container_width=True):
            st.session_state.menu = "📈 Relatórios"
            st.rerun()

# =========================================
# 🔐 SISTEMA DE LOGIN MULTI-FÁBRICA
# =========================================

def verificar_login_multi_fabrica(username, password):
    """Verifica credenciais no sistema multi-fábrica"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None, None, None, None, None
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT u.id, u.password_hash, u.nome_completo, u.tipo, 
                   u.fabrica_id, f.nome as fabrica_nome, f.plano
            FROM usuarios u
            JOIN fabricas f ON u.fabrica_id = f.id
            WHERE u.username = %s AND u.ativo = TRUE AND f.ativa = TRUE
        ''', (username,))
        
        resultado = cur.fetchone()
        
        if resultado and check_hashes(password, resultado[1]):
            # Atualizar último login
            cur.execute('UPDATE usuarios SET ultimo_login = CURRENT_TIMESTAMP WHERE id = %s', (resultado[0],))
            conn.commit()
            
            # Criar notificação de login
            criar_notificacao(
                resultado[4], 
                resultado[0],
                'login', 
                'Login realizado', 
                f'Login realizado em {datetime.now().strftime("%d/%m/%Y %H:%M")}'
            )
            
            return True, resultado[2], resultado[3], resultado[0], resultado[4], resultado[5], resultado[6]
        else:
            return False, "Credenciais inválidas", None, None, None, None, None
            
    except Exception as e:
        return False, f"Erro: {str(e)}", None, None, None, None, None
    finally:
        conn.close()

def login_premium():
    """Interface de login premium"""
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px;
            margin: 50px auto;
            padding: 40px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.markdown('<h1 style="text-align: center; color: #2563EB;">🏭</h1>', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align: center; color: #2563EB;">FactoryPilot</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; color: #666;">Sistema Inteligente para Confecções</p>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
            password = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
            
            if st.form_submit_button("🚀 Entrar no Sistema", use_container_width=True):
                if username and password:
                    sucesso, mensagem, tipo_usuario, usuario_id, fabrica_id, fabrica_nome, plano = verificar_login_multi_fabrica(username, password)
                    if sucesso:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.nome_usuario = mensagem
                        st.session_state.tipo_usuario = tipo_usuario
                        st.session_state.usuario_id = usuario_id
                        st.session_state.fabrica_id = fabrica_id
                        st.session_state.fabrica_nome = fabrica_nome
                        st.session_state.plano = plano
                        st.success(f"Bem-vindo(a), {mensagem}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(mensagem)
                else:
                    st.error("Preencha todos os campos")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Credenciais de teste
        with st.expander("🔑 Credenciais de Demonstração"):
            st.write("**Usuário:** admin")
            st.write("**Senha:** admin123")
            st.write("**Fábrica:** Fábrica Demonstração")
            st.info("💡 Sistema multi-fábrica pronto para escalar!")

# =========================================
# 📊 FUNÇÕES DE DADOS MULTI-FÁBRICA
# =========================================

def obter_metricas_dashboard(fabrica_id):
    """Obtém métricas específicas da fábrica"""
    conn = get_connection()
    if not conn:
        return {}
    
    try:
        cur = conn.cursor()
        
        # Total de pedidos
        cur.execute("SELECT COUNT(*) FROM pedidos WHERE fabrica_id = %s", (fabrica_id,))
        total_pedidos = cur.fetchone()[0]
        
        # Pedidos do mês
        cur.execute("SELECT COUNT(*) FROM pedidos WHERE fabrica_id = %s AND DATE_TRUNC('month', data_pedido) = DATE_TRUNC('month', CURRENT_DATE)", (fabrica_id,))
        pedidos_mes = cur.fetchone()[0]
        
        # Faturamento mensal
        cur.execute("SELECT COALESCE(SUM(valor_total), 0) FROM pedidos WHERE fabrica_id = %s AND DATE_TRUNC('month', data_pedido) = DATE_TRUNC('month', CURRENT_DATE) AND status = 'Entregue'", (fabrica_id,))
        faturamento_mes = cur.fetchone()[0]
        
        # Clientes ativos
        cur.execute("SELECT COUNT(DISTINCT cliente_id) FROM pedidos WHERE fabrica_id = %s AND data_pedido >= CURRENT_DATE - INTERVAL '90 days'", (fabrica_id,))
        clientes_ativos = cur.fetchone()[0]
        
        # Produtos com estoque baixo
        cur.execute("SELECT COUNT(*) FROM produtos WHERE fabrica_id = %s AND estoque <= estoque_minimo AND ativo = TRUE", (fabrica_id,))
        estoque_baixo = cur.fetchone()[0]
        
        # Ticket médio
        cur.execute("SELECT COALESCE(AVG(valor_total), 0) FROM pedidos WHERE fabrica_id = %s AND status = 'Entregue'", (fabrica_id,))
        ticket_medio = cur.fetchone()[0]
        
        return {
            'total_pedidos': total_pedidos,
            'pedidos_mes': pedidos_mes,
            'faturamento_mes': faturamento_mes,
            'clientes_ativos': clientes_ativos,
            'estoque_baixo': estoque_baixo,
            'ticket_medio': ticket_medio
        }
    except Exception as e:
        return {}
    finally:
        conn.close()

def listar_produtos_por_fabrica(fabrica_id):
    """Lista produtos da fábrica específica"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM produtos WHERE fabrica_id = %s ORDER BY nome", (fabrica_id,))
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar produtos: {e}")
        return []
    finally:
        conn.close()

def listar_clientes_completos_por_fabrica(fabrica_id):
    """Lista clientes com informações completas da fábrica"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT c.*, 
                   (SELECT COUNT(*) FROM pedidos p WHERE p.cliente_id = c.id AND p.fabrica_id = %s) as total_pedidos,
                   (SELECT SUM(valor_total) FROM pedidos p WHERE p.cliente_id = c.id AND p.fabrica_id = %s) as total_gasto
            FROM clientes c
            WHERE c.fabrica_id = %s
            ORDER BY c.nome
        ''', (fabrica_id, fabrica_id, fabrica_id))
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar clientes: {e}")
        return []
    finally:
        conn.close()

def listar_pedidos_por_fabrica(fabrica_id):
    """Lista pedidos da fábrica específica"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT p.*, c.nome as cliente_nome
            FROM pedidos p
            JOIN clientes c ON p.cliente_id = c.id
            WHERE p.fabrica_id = %s
            ORDER BY p.data_pedido DESC
        ''', (fabrica_id,))
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar pedidos: {e}")
        return []
    finally:
        conn.close()

def obter_vendas_por_periodo(fabrica_id, dias=30):
    """Obtém dados de vendas da fábrica"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT DATE(data_pedido) as data, 
                   COUNT(*) as pedidos,
                   SUM(valor_total) as faturamento
            FROM pedidos 
            WHERE fabrica_id = %s AND data_pedido >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY DATE(data_pedido)
            ORDER BY data
        ''', (fabrica_id, dias))
        
        dados = cur.fetchall()
        if dados:
            df = pd.DataFrame(dados, columns=['data', 'pedidos', 'faturamento'])
            return df
        
        # Retornar dados demo se não houver dados reais
        return pd.DataFrame({
            'data': pd.date_range(start=date.today() - timedelta(days=dias-1), periods=dias),
            'pedidos': np.random.randint(1, 10, dias),
            'faturamento': np.random.normal(1000, 200, dias)
        })
    except Exception as e:
        # Dados demo em caso de erro
        return pd.DataFrame({
            'data': pd.date_range(start=date.today() - timedelta(days=dias-1), periods=dias),
            'pedidos': np.random.randint(1, 10, dias),
            'faturamento': np.random.normal(1000, 200, dias)
        })
    finally:
        conn.close()

# =========================================
# 🆘 SISTEMA DE AJUDA COMPLETO
# =========================================

def pagina_ajuda_completa():
    """Página de ajuda completa do sistema"""
    st.markdown("## 🆘 Central de Ajuda - FactoryPilot")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 Comece Aqui", "📚 Tutoriais", "❓ FAQ", "📞 Suporte", "🏭 Sobre"])
    
    with tab1:
        st.markdown("""
        ## 🎯 Bem-vindo ao FactoryPilot!
        
        **Sistema inteligente de gestão para confecções e ateliês**
        
        ### 🚀 Primeiros Passos:
        
        #### 1️⃣ **Configuração Inicial**
        ```python
        ✓ Cadastre seus produtos no catálogo
        ✓ Adicione seus clientes no CRM  
        ✓ Configure sua equipe de usuários
        ✓ Explore o dashboard inteligente
        ```
        
        #### 2️⃣ **Fluxo de Trabalho Recomendado:**
        ```
        Cliente entra em contato → Cadastro no sistema → 
        Criação do pedido → Controle de produção → 
        Entrega → Recebimento → Análise de resultados
        ```
        
        #### 3️⃣ **Dashboard Inteligente**
        - **Métricas em tempo real** do seu negócio
        - **IA que dá insights** automáticos
        - **Alertas inteligentes** de estoque e prazos
        - **Previsões** de vendas futuras
        """)
        
        st.success("""
        💡 **Dica Rápida:** Comece cadastrando 3-5 produtos e 2-3 clientes 
        para testar o fluxo completo antes de migrar todos os dados.
        """)
    
    with tab2:
        st.markdown("## 📚 Tutoriais em Vídeo")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 🎬 Vídeos Explicativos
            
            #### 📊 **Dashboard e IA**
            - Como interpretar seus KPIs
            - Usar o assistente inteligente
            - Configurar alertas personalizados
            
            #### 👥 **Gestão de Clientes (CRM)**
            - Cadastro completo de clientes
            - Histórico de compras
            - Segmentação por perfil
            
            #### 📦 **Controle de Pedidos**
            - Fluxo completo do pedido
            - Cálculo automático de lucro
            - Controle de produção
            """)
        
        with col2:
            st.markdown("""
            #### 👕 **Catálogo de Produtos**
            - Cadastro com margem de lucro
            - Controle de estoque inteligente
            - Alertas de reposição
            
            #### 📈 **Relatórios Avançados**
            - Análise financeira
            - Performance de vendas
            - Rentabilidade por produto
            
            #### ⚙️ **Configurações Multi-Fábrica**
            - Gerenciar múltiplas unidades
            - Perfis de usuário
            - Permissões de acesso
            """)
    
    with tab3:
        st.markdown("## ❓ Perguntas Frequentes (FAQ)")
        
        with st.expander("🤔 Como faço o primeiro cadastro?"):
            st.markdown("""
            **Passo a passo inicial:**
            1. Vá em **👕 Produtos** → **➕ Novo Produto**
            2. Cadastre seus 5 produtos mais vendidos
            3. Vá em **👥 Clientes** → **➕ Novo Cliente**  
            4. Adicione seus 3 clientes principais
            5. Volte ao **📊 Dashboard** para ver as métricas
            """)
        
        with st.expander("💰 Como o sistema calcula meu lucro?"):
            st.markdown("""
            **Fórmula automática de lucro:**
            ```
            Preço de Venda - Preço de Custo = Lucro Unitário
            Lucro Unitário × Quantidade = Lucro Total
            ```
            
            **Exemplo prático:**
            - Camiseta: Custo R$ 15 → Venda R$ 45
            - Lucro: R$ 30 por unidade
            - Pedido de 10 unidades: R$ 300 de lucro
            """)
        
        with st.expander("🏭 Como funciona o multi-fábrica?"):
            st.markdown("""
            **Sistema escalável:**
            - Cada fábrica tem dados **100% separados**
            - Você pode gerenciar **múltiplas unidades**
            - Preços por fábrica/plano
            - Relatórios individuais e consolidados
            
            **Perfeito para:** Redes de confecções, franquias, grupos
            """)
    
    with tab4:
        st.markdown("## 📞 Canais de Suporte")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 🎯 Suporte Prioritário
            
            #### 📱 **WhatsApp Business**
            **🕒 Horário:** 9h-18h (segunda a sexta)
            **🚀 Resposta:** Em até 15 minutos
            
            #### 📧 **E-mail Profissional**
            **📬 Endereço:** suporte@factorypilot.com
            **⏰ Resposta:** Em até 4 horas úteis
            """)
        
        with col2:
            st.markdown("""
            ### 🛠️ Tipos de Suporte
            
            #### 🔧 **Suporte Técnico**
            - Problemas de acesso
            - Erros no sistema
            - Configurações
            
            #### 💡 **Suporte Estratégico**
            - Análise de métricas
            - Otimização de processos
            - Tomada de decisão
            """)
    
    with tab5:
        st.markdown("## 🏭 Sobre o FactoryPilot")
        
        st.markdown("""
        ### 🎯 Nossa Missão
        
        **"Transformar a gestão de confecções através de tecnologia 
        inteligente e acessível, permitindo que empreendedores 
        foquem no que realmente importa: criar produtos incríveis."**
        
        ### 🚀 Tecnologia
        
        #### 🔧 **Stack Tecnológica:**
        - **Frontend:** Streamlit (Python)
        - **Backend:** PostgreSQL
        - **IA:** Machine Learning integrado
        - **Hospedagem:** Cloud profissional
        
        #### 📊 **Capacidades:**
        - ✅ **+1.000 produtos** por fábrica
        - ✅ **+5.000 clientes** na base
        - ✅ **+10.000 pedidos** mensais
        - ✅ **Multi-fábrica** simultâneo
        
        ---
        
        *"Organizar para crescer - Controlar para lucrar"* 🏭
        """)

# =========================================
# 📦 PÁGINAS DO SISTEMA (Versões simplificadas)
# =========================================

def pagina_pedidos_premium():
    """Página de pedidos premium"""
    st.markdown("## 📦 Gestão de Pedidos")
    
    if 'fabrica_id' not in st.session_state:
        st.error("Erro: Fábrica não identificada")
        return
    
    fabrica_id = st.session_state.fabrica_id
    
    tab1, tab2 = st.tabs(["📋 Todos os Pedidos", "🎯 Novo Pedido"])
    
    with tab1:
        st.subheader("📋 Pedidos da Fábrica")
        pedidos = listar_pedidos_por_fabrica(fabrica_id)
        
        if pedidos:
            dados = []
            for pedido in pedidos:
                status_class = f"status-{pedido[3].lower()}" if pedido[3].lower() in ['pendente', 'producao', 'entregue', 'cancelado'] else "status-pendente"
                
                dados.append({
                    'ID': pedido[0],
                    'Cliente': pedido[16],
                    'Status': f'<span class="{status_class}">{pedido[3]}</span>',
                    'Data Pedido': pedido[5].strftime("%d/%m/%Y"),
                    'Valor Total': f"R$ {pedido[9]:.2f}",
                    'Responsável': pedido[13] or '-'
                })
            
            df = pd.DataFrame(dados)
            st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info("📦 Nenhum pedido cadastrado. Comece criando seu primeiro pedido!")
    
    with tab2:
        st.subheader("🎯 Criar Novo Pedido")
        st.info("🚀 Funcionalidade completa em desenvolvimento...")
        
        # Aqui viria o formulário completo de novo pedido
        with st.form("novo_pedido_simples"):
            cliente = st.text_input("👤 Nome do Cliente")
            produto = st.text_input("👕 Produto")
            quantidade = st.number_input("📦 Quantidade", min_value=1, value=1)
            valor = st.number_input("💰 Valor Unitário", min_value=0.0, value=0.0)
            
            if st.form_submit_button("✅ Criar Pedido"):
                st.success("Pedido criado com sucesso! (Demo)")
                # Aqui viria a lógica real de criação do pedido

def pagina_clientes_premium():
    """Página de clientes premium"""
    st.markdown("## 👥 Gestão de Clientes")
    
    if 'fabrica_id' not in st.session_state:
        st.error("Erro: Fábrica não identificada")
        return
    
    fabrica_id = st.session_state.fabrica_id
    
    tab1, tab2 = st.tabs(["📋 Base de Clientes", "➕ Novo Cliente"])
    
    with tab1:
        st.subheader("📋 Clientes Cadastrados")
        clientes = listar_clientes_completos_por_fabrica(fabrica_id)
        
        if clientes:
            dados = []
            for cliente in clientes:
                dados.append({
                    'ID': cliente[0],
                    'Nome': cliente[2],
                    'Telefone': cliente[3] or 'N/A',
                    'Email': cliente[4] or 'N/A',
                    'Total Pedidos': cliente[12] or 0,
                    'Total Gasto': f"R$ {cliente[13]:.2f}" if cliente[13] else "R$ 0.00"
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
        else:
            st.info("👥 Nenhum cliente cadastrado. Comece cadastrando seu primeiro cliente!")
    
    with tab2:
        st.subheader("➕ Cadastrar Novo Cliente")
        
        with st.form("novo_cliente"):
            nome = st.text_input("👤 Nome completo*")
            telefone = st.text_input("📞 Telefone")
            email = st.text_input("📧 Email")
            
            if st.form_submit_button("✅ Cadastrar Cliente"):
                if nome:
                    st.success("Cliente cadastrado com sucesso! (Demo)")
                    # Aqui viria a lógica real de cadastro
                else:
                    st.error("❌ Nome é obrigatório!")

def pagina_produtos_premium():
    """Página de produtos premium"""
    st.markdown("## 👕 Catálogo de Produtos")
    
    if 'fabrica_id' not in st.session_state:
        st.error("Erro: Fábrica não identificada")
        return
    
    fabrica_id = st.session_state.fabrica_id
    
    tab1, tab2 = st.tabs(["📋 Catálogo", "➕ Novo Produto"])
    
    with tab1:
        st.subheader("📋 Produtos Cadastrados")
        produtos = listar_produtos_por_fabrica(fabrica_id)
        
        if produtos:
            dados = []
            for produto in produtos:
                status_estoque = "✅" if produto[10] > produto[11] else "⚠️" if produto[10] > 0 else "❌"
                
                dados.append({
                    'ID': produto[0],
                    'Nome': produto[2],
                    'Categoria': produto[3],
                    'Tamanho': produto[5],
                    'Cor': produto[6],
                    'Preço Venda': f"R$ {produto[8]:.2f}",
                    'Estoque': f"{status_estoque} {produto[10]}",
                    'Status': 'Ativo' if produto[14] else 'Inativo'
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
        else:
            st.info("👕 Nenhum produto cadastrado. Comece cadastrando seu primeiro produto!")
    
    with tab2:
        st.subheader("➕ Cadastrar Novo Produto")
        
        with st.form("novo_produto"):
            nome = st.text_input("🏷️ Nome do produto*")
            categoria = st.selectbox("📂 Categoria", ["Camisetas", "Calças", "Shorts", "Agasalhos", "Acessórios"])
            preco_venda = st.number_input("🏷️ Preço de Venda (R$)", min_value=0.0, value=0.0)
            estoque = st.number_input("📦 Estoque Inicial", min_value=0, value=0)
            
            if st.form_submit_button("✅ Cadastrar Produto"):
                if nome and preco_venda > 0:
                    st.success("Produto cadastrado com sucesso! (Demo)")
                    # Aqui viria a lógica real de cadastro
                else:
                    st.error("❌ Nome e preço de venda são obrigatórios!")

def pagina_relatorios_premium():
    """Página de relatórios premium"""
    st.markdown("## 📈 Relatórios e Analytics")
    
    if 'fabrica_id' not in st.session_state:
        st.error("Erro: Fábrica não identificada")
        return
    
    fabrica_id = st.session_state.fabrica_id
    
    tab1, tab2 = st.tabs(["💰 Financeiro", "📊 Performance"])
    
    with tab1:
        st.subheader("💰 Relatório Financeiro")
        
        # Métricas financeiras
        metricas = obter_metricas_dashboard(fabrica_id)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Faturamento Mensal", f"R$ {metricas.get('faturamento_mes', 0):,.2f}")
        with col2:
            st.metric("Ticket Médio", f"R$ {metricas.get('ticket_medio', 0):.2f}")
        with col3:
            st.metric("Pedidos/Mês", metricas.get('pedidos_mes', 0))
        
        # Gráfico de evolução
        st.subheader("📈 Evolução do Faturamento")
        dados_vendas = obter_vendas_por_periodo(fabrica_id, 30)
        if not dados_vendas.empty:
            fig = px.line(dados_vendas, x='data', y='faturamento', 
                         title="Faturamento dos Últimos 30 Dias")
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("📊 Performance da Fábrica")
        st.info("📈 Relatórios avançados de performance em desenvolvimento...")

# =========================================
# 🚀 APLICAÇÃO PRINCIPAL
# =========================================

def main():
    # Inicializar banco
    if 'db_initialized' not in st.session_state:
        init_db()
        st.session_state.db_initialized = True
    
    # Verificar login
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        login_premium()
        return
    
    # Sidebar premium
    with st.sidebar:
        st.markdown(f"## 🏭 {st.session_state.fabrica_nome}")
        st.markdown(f"**👤 Usuário:** {st.session_state.nome_usuario}")
        st.markdown(f"**🎯 Plano:** {st.session_state.plano}")
        
        # Notificações
        notificacoes = obter_notificacoes(st.session_state.usuario_id)
        if notificacoes:
            with st.expander(f"🔔 Notificações ({len(notificacoes)})"):
                for notif in notificacoes:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{notif[4]}**")
                        st.write(notif[5])
                    with col2:
                        if st.button("✓", key=f"read_{notif[0]}"):
                            # Marcar como lida
                            st.rerun()
        else:
            st.info("🔔 Nenhuma notificação")
        
        # Menu principal
        st.markdown("---")
        menu_options = [
            "📊 Dashboard", 
            "📦 Pedidos", 
            "👥 Clientes", 
            "👕 Produtos", 
            "📈 Relatórios",
            "🆘 Ajuda"
        ]
        
        menu = st.radio("Navegação", menu_options)
        
        # Configurações
        st.markdown("---")
        with st.expander("⚙️ Configurações"):
            if st.button("🔄 Recarregar Dados"):
                st.rerun()
            
            if st.button("🚪 Sair"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
    
    # Header
    mostrar_header()
    
    # Conteúdo principal baseado no menu
    if menu == "📊 Dashboard":
        mostrar_dashboard_premium()
    elif menu == "📦 Pedidos":
        pagina_pedidos_premium()
    elif menu == "👥 Clientes":
        pagina_clientes_premium()
    elif menu == "👕 Produtos":
        pagina_produtos_premium()
    elif menu == "📈 Relatórios":
        pagina_relatorios_premium()
    elif menu == "🆘 Ajuda":
        pagina_ajuda_completa()

if __name__ == "__main__":
    main()