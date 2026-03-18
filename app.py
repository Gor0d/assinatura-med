"""
Interface web para geração de assinatura/carimbo médico digital.
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
st.markdown("Faça o upload da assinatura e preencha os dados do médico para gerar o carimbo em PNG.")

# --- Upload ---
st.subheader("1. Assinatura")
arquivo = st.file_uploader("Selecione a imagem da assinatura (PNG ou JPG)", type=["png", "jpg", "jpeg"])

# --- Dados do médico ---
st.subheader("2. Dados do médico")

col1, col2 = st.columns([3, 1])
nome = col1.text_input("Nome completo", placeholder="Dra. Juliana Santiago")

col3, col4, col5 = st.columns([2, 1, 1])
especialidade = col3.text_input("Especialidade", placeholder="Ginecologista e Obstetra")
crm_estado = col4.text_input("Estado CRM", placeholder="PA", max_chars=2).upper()
crm_numero = col5.text_input("Número CRM", placeholder="15696")

rqe = st.text_input("RQE (opcional)", placeholder="124150")

# --- Geração ---
st.subheader("3. Gerar carimbo")

if st.button("Gerar PNG", type="primary", disabled=not arquivo or not nome or not especialidade or not crm_estado or not crm_numero):
    with st.spinner("Gerando..."):
        img_bytes = gerar_em_memoria(
            img_upload=arquivo,
            nome=nome,
            especialidade=especialidade,
            crm_estado=crm_estado,
            crm_numero=crm_numero,
            rqe=rqe.strip() or None,
        )

    st.success("Carimbo gerado com sucesso!")
    st.image(img_bytes, caption="Pré-visualização", width="content")

    nome_arquivo = nome.lower().replace(" ", "_").replace(".", "") + ".png"
    st.download_button(
        label="⬇ Baixar PNG",
        data=img_bytes,
        file_name=nome_arquivo,
        mime="image/png",
    )

elif not arquivo:
    st.info("Faça o upload da assinatura para continuar.")
elif not (nome and especialidade and crm_estado and crm_numero):
    st.warning("Preencha todos os campos obrigatórios.")
