"""
Interface web para geração e cadastro de assinatura/carimbo médico digital.
Execute com: streamlit run app.py
"""

import io
import streamlit as st
from PIL import Image
from gerar_assinatura import gerar_em_memoria

st.set_page_config(
    page_title="Assinatura Médica Digital",
    page_icon="🏥",
    layout="centered",
)

st.title("Assinatura Médica Digital")

# ---------------------------------------------------------------------------
# Inicializa estado da sessão
# ---------------------------------------------------------------------------
for key in ("img_bytes", "prestador", "cd_prestador", "assinatura_atual"):
    if key not in st.session_state:
        st.session_state[key] = None

# ---------------------------------------------------------------------------
# ETAPA 1 — Upload da assinatura
# ---------------------------------------------------------------------------
st.subheader("1. Assinatura")
arquivo = st.file_uploader("Selecione a imagem da assinatura (PNG ou JPG)", type=["png", "jpg", "jpeg"])

# ---------------------------------------------------------------------------
# ETAPA 2 — Dados do médico
# ---------------------------------------------------------------------------
st.subheader("2. Dados do médico")

col1, col2 = st.columns([3, 1])
nome = col1.text_input("Nome completo", placeholder="Dra. Juliana Santiago")

col3, col4, col5 = st.columns([2, 1, 1])
especialidade = col3.text_input("Especialidade", placeholder="Ginecologista e Obstetra")
crm_estado    = col4.text_input("Estado CRM", placeholder="PA", max_chars=2).upper()
crm_numero    = col5.text_input("Número CRM", placeholder="15696")

rqe = st.text_input("RQE (opcional)", placeholder="124150")

# ---------------------------------------------------------------------------
# ETAPA 3 — Gerar carimbo
# ---------------------------------------------------------------------------
st.subheader("3. Gerar carimbo")

campos_ok = bool(arquivo and nome and especialidade and crm_estado and crm_numero)

if st.button("Gerar PNG", type="primary", disabled=not campos_ok):
    with st.spinner("Gerando..."):
        st.session_state.img_bytes = gerar_em_memoria(
            img_upload=arquivo,
            nome=nome,
            especialidade=especialidade,
            crm_estado=crm_estado,
            crm_numero=crm_numero,
            rqe=rqe.strip() or None,
        )
    st.session_state.prestador       = None
    st.session_state.cd_prestador    = None
    st.session_state.assinatura_atual = None

if st.session_state.img_bytes:
    st.image(st.session_state.img_bytes, caption="Pré-visualização", width="content")
    nome_arquivo = nome.lower().replace(" ", "_").replace(".", "") + ".png"
    st.download_button("⬇ Baixar PNG", st.session_state.img_bytes,
                       file_name=nome_arquivo, mime="image/png")

elif not arquivo:
    st.info("Faça o upload da assinatura para continuar.")
elif not campos_ok:
    st.warning("Preencha todos os campos obrigatórios.")

# ---------------------------------------------------------------------------
# ETAPA 4 — Salvar no banco Oracle
# ---------------------------------------------------------------------------
if st.session_state.img_bytes:
    st.divider()
    st.subheader("4. Salvar no banco Oracle (MV)")

    cd_input = st.text_input("Código do prestador (CD_PRESTADOR)", placeholder="574")

    if st.button("Pesquisar prestador", disabled=not cd_input.strip()):
        try:
            from db import buscar_prestador, buscar_assinatura_atual
            cd = int(cd_input.strip())
            with st.spinner("Consultando..."):
                prestador = buscar_prestador(cd)

            if prestador is None:
                st.error(f"Prestador {cd} não encontrado na tabela PRESTADOR.")
            else:
                st.session_state.cd_prestador    = cd
                st.session_state.prestador       = prestador
                st.session_state.assinatura_atual = buscar_assinatura_atual(cd)

        except ValueError:
            st.error("CD_PRESTADOR deve ser numérico.")
        except Exception as e:
            st.error(f"Erro ao conectar ao banco: {e}")

    # Exibe resultado da pesquisa
    if st.session_state.prestador:
        p = st.session_state.prestador
        st.success(f"**{p['nm_prestador']}** — CRM: {p['ds_codigo_conselho']}")

        if st.session_state.assinatura_atual:
            st.warning("Este prestador já possui assinatura cadastrada:")
            st.image(st.session_state.assinatura_atual,
                     caption="Assinatura atual", width="content")
            acao   = "Atualizar"
            alerta = "⚠ Confirma a **substituição** da assinatura existente?"
        else:
            acao   = "Inserir"
            alerta = f"Confirma o cadastro da assinatura para **{p['nm_prestador']}**?"

        st.info(alerta)

        col_sim, col_nao = st.columns(2)

        if col_sim.button(f"✅ Sim, {acao}", type="primary"):
            try:
                from db import salvar_assinatura
                with st.spinner("Salvando..."):
                    op = salvar_assinatura(st.session_state.cd_prestador,
                                          st.session_state.img_bytes)
                st.success(f"{op} realizado com sucesso para **{p['nm_prestador']}**!")
                # Limpa estado após salvar
                for key in ("prestador", "cd_prestador", "assinatura_atual"):
                    st.session_state[key] = None
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

        if col_nao.button("❌ Cancelar"):
            for key in ("prestador", "cd_prestador", "assinatura_atual"):
                st.session_state[key] = None
            st.rerun()
