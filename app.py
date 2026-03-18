"""
Interface web para geração e cadastro de assinatura/carimbo médico digital.
Execute com: streamlit run app.py
"""

import streamlit as st
from gerar_assinatura import gerar_em_memoria

st.set_page_config(
    page_title="Assinatura Médica Digital",
    page_icon="🏥",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------
if "usuario" not in st.session_state:
    st.session_state.usuario = None
if "nome_usuario" not in st.session_state:
    st.session_state.nome_usuario = None


def tela_login():
    st.title("Assinatura Médica Digital")
    st.subheader("Acesso ao sistema")

    with st.form("login"):
        usuario = st.text_input("Usuário")
        senha   = st.text_input("Senha", type="password")
        entrar  = st.form_submit_button("Entrar", type="primary", use_container_width=True)

    if entrar:
        from auth import autenticar
        dados = autenticar(usuario, senha)
        if dados:
            st.session_state.usuario      = dados["usuario"]
            st.session_state.nome_usuario = dados["nome"]
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos.")


if not st.session_state.usuario:
    tela_login()
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar — usuário logado + logout
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"**{st.session_state.nome_usuario}**")
    st.caption(f"@{st.session_state.usuario}")
    if st.button("Sair", use_container_width=True):
        st.session_state.usuario      = None
        st.session_state.nome_usuario = None
        st.rerun()

# ---------------------------------------------------------------------------
# Inicializa estado da sessão
# ---------------------------------------------------------------------------
for key in ("img_bytes", "prestador", "cd_prestador", "assinatura_atual"):
    if key not in st.session_state:
        st.session_state[key] = None

# ---------------------------------------------------------------------------
# Abas: Cadastro | Auditoria | Usuários
# ---------------------------------------------------------------------------
abas = ["Cadastro de Assinatura", "Log de Auditoria"]
if st.session_state.usuario == "admin":
    abas.append("Gerenciar Usuários")

tabs = st.tabs(abas)
aba_cadastro  = tabs[0]
aba_auditoria = tabs[1]
aba_usuarios  = tabs[2] if len(tabs) > 2 else None

# ===========================================================================
# ABA CADASTRO
# ===========================================================================
with aba_cadastro:
    st.title("Assinatura Médica Digital")

    # -----------------------------------------------------------------------
    # ETAPA 1 — Upload da assinatura
    # -----------------------------------------------------------------------
    st.subheader("1. Assinatura")
    arquivo = st.file_uploader("Selecione a imagem da assinatura (PNG ou JPG)",
                               type=["png", "jpg", "jpeg"])

    # -----------------------------------------------------------------------
    # ETAPA 2 — Dados do médico
    # -----------------------------------------------------------------------
    st.subheader("2. Dados do médico")

    col1, col2 = st.columns([3, 1])
    nome = col1.text_input("Nome completo", placeholder="Dra. Juliana Santiago")

    col3, col4, col5 = st.columns([2, 1, 1])
    especialidade = col3.text_input("Especialidade", placeholder="Ginecologista e Obstetra")
    crm_estado    = col4.text_input("Estado CRM", placeholder="PA", max_chars=2).upper()
    crm_numero    = col5.text_input("Número CRM", placeholder="15696")

    rqe = st.text_input("RQE (opcional)", placeholder="124150")

    # -----------------------------------------------------------------------
    # ETAPA 3 — Gerar carimbo
    # -----------------------------------------------------------------------
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
        st.session_state.prestador        = None
        st.session_state.cd_prestador     = None
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

    # -----------------------------------------------------------------------
    # ETAPA 4 — Salvar no banco Oracle
    # -----------------------------------------------------------------------
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
                    st.error(f"Prestador {cd} não encontrado.")
                else:
                    st.session_state.cd_prestador     = cd
                    st.session_state.prestador        = prestador
                    st.session_state.assinatura_atual = buscar_assinatura_atual(cd)

            except ValueError:
                st.error("CD_PRESTADOR deve ser numérico.")
            except Exception as e:
                st.error(f"Erro ao conectar ao banco: {e}")

        if st.session_state.prestador:
            p   = st.session_state.prestador
            ass = st.session_state.assinatura_atual or {}
            st.success(f"**{p['nm_prestador']}** — CRM: {p['ds_codigo_conselho']}")

            if ass.get("existe"):
                st.warning("Este prestador já possui assinatura cadastrada.")
                if ass.get("imagem"):
                    st.image(ass["imagem"], caption="Assinatura atual", width="content")
                else:
                    st.caption("(formato atual não pode ser pré-visualizado)")
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
                    from audit import registrar
                    with st.spinner("Salvando..."):
                        op = salvar_assinatura(st.session_state.cd_prestador,
                                               st.session_state.img_bytes)
                    registrar(
                        operador=st.session_state.nome_usuario,
                        cd_prestador=st.session_state.cd_prestador,
                        nm_prestador=p["nm_prestador"],
                        operacao=op,
                    )
                    st.success(f"{op} realizado com sucesso para **{p['nm_prestador']}**!")
                    for key in ("prestador", "cd_prestador", "assinatura_atual"):
                        st.session_state[key] = None
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

            if col_nao.button("❌ Cancelar"):
                for key in ("prestador", "cd_prestador", "assinatura_atual"):
                    st.session_state[key] = None
                st.rerun()

# ===========================================================================
# ABA AUDITORIA
# ===========================================================================
with aba_auditoria:
    st.title("Log de Auditoria")

    from audit import carregar_logs
    import pandas as pd

    logs = carregar_logs()

    if not logs:
        st.info("Nenhuma operação registrada ainda.")
    else:
        df = pd.DataFrame(logs, columns=["dt_operacao", "operador", "cd_prestador",
                                         "nm_prestador", "operacao", "obs"])
        df.columns = ["Data/Hora", "Operador", "Cód. Prestador", "Prestador", "Operação", "Obs"]

        col_f1, col_f2 = st.columns(2)
        filtro_op  = col_f1.text_input("Filtrar por operador")
        filtro_pre = col_f2.text_input("Filtrar por prestador")

        if filtro_op:
            df = df[df["Operador"].str.contains(filtro_op, case=False, na=False)]
        if filtro_pre:
            df = df[df["Prestador"].str.contains(filtro_pre, case=False, na=False)]

        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"{len(df)} registro(s)")

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇ Exportar CSV", csv, "auditoria.csv", "text/csv")

# ===========================================================================
# ABA USUÁRIOS (somente admin)
# ===========================================================================
if aba_usuarios:
    with aba_usuarios:
        st.title("Gerenciar Usuários")
        from auth import listar_usuarios, adicionar_usuario, remover_usuario, alterar_senha

        # Lista atual
        usuarios = listar_usuarios()
        st.dataframe(
            {"Usuário": [u["usuario"] for u in usuarios],
             "Nome":    [u["nome"]    for u in usuarios]},
            use_container_width=True, hide_index=True,
        )

        st.divider()

        col_a, col_b = st.columns(2)

        # Adicionar usuário
        with col_a:
            st.subheader("Adicionar usuário")
            with st.form("add_user"):
                nu = st.text_input("Usuário (login)")
                nn = st.text_input("Nome completo")
                ns = st.text_input("Senha", type="password")
                if st.form_submit_button("Adicionar", use_container_width=True):
                    if nu and nn and ns:
                        adicionar_usuario(nu, ns, nn)
                        st.success(f"Usuário **{nu}** criado.")
                        st.rerun()
                    else:
                        st.warning("Preencha todos os campos.")

        # Remover / alterar senha
        with col_b:
            st.subheader("Remover usuário")
            logins = [u["usuario"] for u in usuarios if u["usuario"] != "admin"]
            with st.form("rem_user"):
                ru = st.selectbox("Usuário", logins if logins else ["—"])
                if st.form_submit_button("Remover", use_container_width=True):
                    if ru and ru != "—":
                        remover_usuario(ru)
                        st.success(f"Usuário **{ru}** removido.")
                        st.rerun()

            st.subheader("Alterar senha")
            with st.form("alt_senha"):
                au = st.selectbox("Usuário ", [u["usuario"] for u in usuarios])
                ns2 = st.text_input("Nova senha", type="password")
                if st.form_submit_button("Alterar", use_container_width=True):
                    if au and ns2:
                        alterar_senha(au, ns2)
                        st.success("Senha alterada.")
