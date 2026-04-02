"""
Interface web para geração e cadastro de assinatura/carimbo médico digital.
Execute com: streamlit run app.py
"""

import streamlit as st
from gerar_assinatura import gerar_em_memoria


TIPOS_CONSELHO = {
    "Medico": "CRM",
    "Psicologo": "CRP",
    "Bucomaxilofacial": "CRO",
    "Nutricionista": "CRN",
    "Fonoaudiologia": "CRFA",
}

CONSELHOS_POR_PROFISSAO = {
    "Medico": ["CRM", "CFM"],
}

REGISTROS_PRINCIPAIS = ["Nenhum", "RQE", "SBOT", "SBOP"]
TITULOS_OPCIONAIS = ["Nenhum", "TEOT", "TEOP"]

CRFA_REGIOES = {
    "RJ": "1",
    "SP": "2",
    "PR": "3",
    "SC": "3",
    "AL": "4",
    "BA": "4",
    "PB": "4",
    "PE": "4",
    "SE": "4",
    "DF": "5",
    "GO": "5",
    "MS": "5",
    "MT": "5",
    "TO": "5",
    "MG": "6",
    "ES": "6",
    "RS": "7",
    "CE": "8",
    "MA": "8",
    "PI": "8",
    "RN": "8",
    "AC": "9",
    "AP": "9",
    "AM": "9",
    "PA": "9",
    "RO": "9",
    "RR": "9",
}


def codigo_conselho_exibicao(tipo_prestador: str, sigla_conselho: str, uf: str, numero: str) -> str:
    uf = (uf or "").strip().upper()
    numero = (numero or "").strip()

    if tipo_prestador == "Fonoaudiologia":
        regiao = CRFA_REGIOES.get(uf)
        prefixo = f"{sigla_conselho}-{regiao}" if regiao else sigla_conselho
    else:
        prefixo = f"{sigla_conselho}/{uf}" if uf else sigla_conselho

    return f"{prefixo} {numero}".strip()

st.set_page_config(
    page_title="Assinatura Digital",
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
if "ambiente" not in st.session_state:
    st.session_state.ambiente = "HML"


def tela_login():
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.image("logo.jpg", use_container_width=True)
        st.markdown("<h2 style='text-align:center'>Assinatura Digital</h2>",
                    unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:gray'>Acesso ao sistema</p>",
                    unsafe_allow_html=True)
        st.write("")

        with st.form("login"):
            usuario  = st.text_input("Usuário")
            senha    = st.text_input("Senha", type="password")
            ambiente = st.selectbox("Ambiente", ["HML", "PRD"],
                                    help="HML = Homologação · PRD = Produção")
            entrar   = st.form_submit_button("Entrar", type="primary", use_container_width=True)

        if entrar:
            from auth import autenticar
            dados = autenticar(usuario, senha)
            if dados:
                st.session_state.usuario      = dados["usuario"]
                st.session_state.nome_usuario = dados["nome"]
                st.session_state.ambiente     = ambiente
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
    st.image("logo.jpg", use_container_width=True)
    st.divider()
    st.markdown(f"**{st.session_state.nome_usuario}**")
    st.caption(f"@{st.session_state.usuario}")
    amb = st.session_state.ambiente
    cor = "🟢" if amb == "PRD" else "🟡"
    st.caption(f"{cor} Banco: **{amb}**")
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
abas = ["Cadastro de Assinatura", "Assinaturas Cadastradas", "Log de Auditoria"]
if st.session_state.usuario == "admin":
    abas.append("Gerenciar Usuários")

tabs = st.tabs(abas)
aba_cadastro   = tabs[0]
aba_lista      = tabs[1]
aba_auditoria  = tabs[2]
aba_usuarios   = tabs[3] if len(tabs) > 3 else None

# ===========================================================================
# ABA CADASTRO
# ===========================================================================
with aba_cadastro:
    st.title("Assinatura Digital")

    # -----------------------------------------------------------------------
    # ETAPA 1 — Upload da assinatura
    # -----------------------------------------------------------------------
    st.subheader("1. Assinatura")
    arquivo = st.file_uploader("Selecione a imagem da assinatura (PNG ou JPG)",
                               type=["png", "jpg", "jpeg"])

    # -----------------------------------------------------------------------
    # ETAPA 2 — Dados do prestador
    # -----------------------------------------------------------------------
    st.subheader("2. Dados do prestador")

    col1, col2 = st.columns([3, 1])
    nome = col1.text_input("Nome completo", placeholder="Dra. Juliana Santiago")
    tipo_prestador = col2.selectbox("Profissao", list(TIPOS_CONSELHO))
    opcoes_conselho = CONSELHOS_POR_PROFISSAO.get(tipo_prestador, [TIPOS_CONSELHO[tipo_prestador]])
    sigla_conselho = opcoes_conselho[0]

    if len(opcoes_conselho) > 1:
        sigla_conselho = st.selectbox("Conselho", opcoes_conselho)

    col3, col4, col5 = st.columns([2, 1, 1])
    especialidade = col3.text_area(
        "Especialidade",
        placeholder="Ginecologista e Obstetra",
        height=80,
        help="Use Enter para forcar a quebra de linha no carimbo.",
    )
    if sigla_conselho == "CFM":
        crm_estado = ""
        col4.text_input("UF do conselho", value="", max_chars=2, disabled=True)
    else:
        crm_estado = col4.text_input("UF do conselho", value="PA", max_chars=2).upper()
    crm_numero    = col5.text_input(f"Numero {sigla_conselho}", placeholder="15696")

    regiao_crfa = CRFA_REGIOES.get(crm_estado) if tipo_prestador == "Fonoaudiologia" else None
    if tipo_prestador == "Fonoaudiologia":
        if regiao_crfa:
            st.caption(f"Formato do conselho: `{codigo_conselho_exibicao(tipo_prestador, sigla_conselho, crm_estado, crm_numero or '12345')}`")
        elif crm_estado:
            st.warning("UF sem regiao CRFa mapeada. Verifique o estado informado.")

    col6, col7 = st.columns([1, 2])
    registro_tipo = col6.selectbox("Registro opcional", REGISTROS_PRINCIPAIS)
    registro_numero = col7.text_input("Numero do registro", placeholder="124150")

    col8, col9 = st.columns([1, 2])
    titulo_tipo = col8.selectbox("Titulo opcional", TITULOS_OPCIONAIS)
    titulo_numero = col9.text_input("Numero do titulo", placeholder="12345")

    # -----------------------------------------------------------------------
    # ETAPA 3 — Gerar carimbo
    # -----------------------------------------------------------------------
    st.subheader("3. Gerar carimbo")

    campos_ok = bool(
        arquivo
        and nome
        and especialidade
        and (sigla_conselho == "CFM" or crm_estado)
        and crm_numero
        and (tipo_prestador != "Fonoaudiologia" or regiao_crfa)
    )

    if st.button("Gerar PNG", type="primary", disabled=not campos_ok):
        with st.spinner("Gerando..."):
            st.session_state.img_bytes = gerar_em_memoria(
                img_upload=arquivo,
                nome=nome,
                especialidade=especialidade,
                conselho_sigla=sigla_conselho,
                crm_estado=regiao_crfa if tipo_prestador == "Fonoaudiologia" else crm_estado,
                crm_numero=crm_numero,
                registro_tipo=registro_tipo,
                registro_numero=registro_numero.strip() or None,
                titulo_tipo=titulo_tipo,
                titulo_numero=titulo_numero.strip() or None,
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
                cd  = int(cd_input.strip())
                amb = st.session_state.ambiente
                with st.spinner("Consultando..."):
                    prestador = buscar_prestador(cd, amb)

                if prestador is None:
                    st.error(f"Prestador {cd} não encontrado.")
                else:
                    st.session_state.cd_prestador     = cd
                    st.session_state.prestador        = prestador
                    st.session_state.assinatura_atual = buscar_assinatura_atual(cd, amb)

            except ValueError:
                st.error("CD_PRESTADOR deve ser numérico.")
            except Exception as e:
                st.error(f"Erro ao conectar ao banco: {e}")

        if st.session_state.prestador:
            p   = st.session_state.prestador
            ass = st.session_state.assinatura_atual or {}
            st.success(f"**{p['nm_prestador']}** — Conselho: {p['ds_codigo_conselho']}")

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
                                               st.session_state.img_bytes,
                                               st.session_state.ambiente)
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
# ABA LISTA DE ASSINATURAS
# ===========================================================================
with aba_lista:
    st.title("Assinaturas Cadastradas")

    from db import listar_assinaturas, excluir_assinatura

    # Inicializa estados da aba
    for key in ("ver_cd", "del_cd", "del_nome", "edit_cd"):
        if key not in st.session_state:
            st.session_state[key] = None

    filtro = st.text_input("Buscar por nome ou código", placeholder="Ex: Juliana ou 574")

    try:
        registros = listar_assinaturas(filtro.strip(), st.session_state.ambiente)
    except Exception as e:
        st.error(f"Erro ao carregar lista: {e}")
        registros = []

    if not registros:
        st.info("Nenhuma assinatura encontrada.")
    else:
        st.caption(f"{len(registros)} prestador(es) encontrado(s)")

        # Cabeçalho
        h = st.columns([1, 3, 2, 1, 1, 1])
        for col, titulo in zip(h, ["Código", "Nome", "CRM", "Ver", "Editar", "Excluir"]):
            col.markdown(f"**{titulo}**")
        st.divider()

        for r in registros:
            cd   = r["cd_prestador"]
            nome = r["nm_prestador"]
            crm  = r["crm"] or "—"

            c1, c2, c3, c4, c5, c6 = st.columns([1, 3, 2, 1, 1, 1])
            c1.write(cd)
            c2.write(nome)
            c3.write(crm)

            if c4.button("👁", key=f"ver_{cd}", help="Visualizar assinatura"):
                st.session_state.ver_cd = cd if st.session_state.ver_cd != cd else None
                st.session_state.del_cd = None

            if c5.button("✏️", key=f"edit_{cd}", help="Alterar assinatura"):
                st.session_state.edit_cd = cd
                st.toast(f"Vá para a aba **Cadastro** e pesquise o código **{cd}** para substituir a assinatura.")

            if c6.button("🗑️", key=f"del_{cd}", help="Excluir assinatura"):
                st.session_state.del_cd   = cd
                st.session_state.del_nome = nome
                st.session_state.ver_cd   = None

            # Painel de visualização inline
            if st.session_state.ver_cd == cd:
                with st.container(border=True):
                    try:
                        from db import buscar_assinatura_atual
                        ass = buscar_assinatura_atual(cd, st.session_state.ambiente)
                        if ass.get("imagem"):
                            st.image(ass["imagem"], caption=nome, width="content")
                        else:
                            st.caption("Assinatura cadastrada, mas o formato não pode ser pré-visualizado.")
                    except Exception as e:
                        st.error(f"Erro ao carregar imagem: {e}")

            # Confirmação de exclusão inline
            if st.session_state.del_cd == cd:
                with st.container(border=True):
                    st.warning(f"Confirma a exclusão da assinatura de **{st.session_state.del_nome}**?")
                    ca, cb = st.columns(2)
                    if ca.button("✅ Sim, excluir", key=f"conf_del_{cd}", type="primary"):
                        try:
                            from audit import registrar
                            excluir_assinatura(cd, st.session_state.ambiente)
                            registrar(
                                operador=st.session_state.nome_usuario,
                                cd_prestador=cd,
                                nm_prestador=nome,
                                operacao="DELETE",
                            )
                            st.success(f"Assinatura de **{nome}** excluída.")
                            st.session_state.del_cd   = None
                            st.session_state.del_nome = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir: {e}")
                    if cb.button("❌ Cancelar", key=f"canc_del_{cd}"):
                        st.session_state.del_cd   = None
                        st.session_state.del_nome = None
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
