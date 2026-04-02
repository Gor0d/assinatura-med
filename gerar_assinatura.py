"""
Gerador de assinatura/carimbo médico digital.
Combina a imagem da assinatura com os dados do médico ao lado direito.

Funcionalidades:
- Auto-crop de margens em branco
- Normalização de altura (todas as assinaturas ficam no mesmo tamanho)
- Fontes proporcionais à altura da assinatura
"""

import argparse
import io
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


# Altura padrão (px) para normalizar todas as assinaturas
# 300 DPI × 4 cm ≈ 472 px — tamanho adequado para documentos médicos
TARGET_HEIGHT = 472

# DPI para salvar o PNG (300 = qualidade para impressão/documentos)
TARGET_DPI = 300

# Proporções em relação à altura da assinatura normalizada
FONT_NOME_RATIO   = 0.18   # tamanho da fonte do nome
FONT_INFO_RATIO   = 0.15   # tamanho da fonte dos demais campos
SPACING_RATIO     = 0.04   # espaço entre linhas
PADDING_RATIO     = 0.18   # padding externo
GAP_RATIO         = 0.18   # espaço entre assinatura e texto

# Cor
BG_COLOR   = (255, 255, 255)
TEXT_COLOR = (0, 0, 0)

# Fontes — prioriza a pasta local (funciona em qualquer SO)
_BASE = Path(__file__).parent / "fonts"
FONT_PATHS_REGULAR = [
    str(_BASE / "DejaVuSans.ttf"),
    "C:/Windows/Fonts/calibri.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
FONT_PATHS_BOLD = [
    str(_BASE / "DejaVuSans-Bold.ttf"),
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


# ---------------------------------------------------------------------------
# Utilitários de imagem
# ---------------------------------------------------------------------------

def carregar_fonte(tamanho: int, negrito: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    paths = FONT_PATHS_BOLD if negrito else FONT_PATHS_REGULAR
    for path in paths:
        try:
            return ImageFont.truetype(path, tamanho)
        except (IOError, OSError):
            continue
    if negrito:
        return carregar_fonte(tamanho, negrito=False)
    return ImageFont.load_default()


def fundo_branco(img: Image.Image) -> Image.Image:
    """Garante fundo branco em imagens com transparência."""
    rgba = img.convert("RGBA")
    fundo = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    fundo.paste(rgba, mask=rgba.split()[3])
    return fundo.convert("RGB")


def recortar_whitespace(img: Image.Image, threshold: int = 240, margem: int = 4) -> Image.Image:
    """
    Remove margens em branco ao redor da assinatura.
    Pixels com luminosidade >= threshold são tratados como fundo.
    """
    gray = img.convert("L")
    mask = gray.point(lambda p: 255 if p < threshold else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return img  # imagem toda branca — devolve sem modificar

    w, h = img.size
    x0 = max(0, bbox[0] - margem)
    y0 = max(0, bbox[1] - margem)
    x1 = min(w, bbox[2] + margem)
    y1 = min(h, bbox[3] + margem)
    return img.crop((x0, y0, x1, y1))


def normalizar_altura(img: Image.Image, altura_alvo: int = TARGET_HEIGHT) -> Image.Image:
    """Redimensiona mantendo proporção para a altura alvo."""
    w, h = img.size
    if h == altura_alvo:
        return img
    novo_w = max(1, int(w * altura_alvo / h))
    return img.resize((novo_w, altura_alvo), Image.LANCZOS)


def preparar_assinatura_de_arquivo(img_path: str) -> Image.Image:
    img = Image.open(img_path)
    return _preparar(img)


def preparar_assinatura_de_upload(img_upload) -> Image.Image:
    img = Image.open(img_upload)
    return _preparar(img)


def _preparar(img: Image.Image) -> Image.Image:
    img = fundo_branco(img)
    img = recortar_whitespace(img)
    img = normalizar_altura(img)
    return img


# ---------------------------------------------------------------------------
# Composição do carimbo
# ---------------------------------------------------------------------------

def _tamanhos(sig_h: int) -> tuple[int, int, int, int, int]:
    """Retorna (font_nome, font_info, spacing, padding, gap) proporcional à altura."""
    return (
        max(12, int(sig_h * FONT_NOME_RATIO)),
        max(10, int(sig_h * FONT_INFO_RATIO)),
        max(3,  int(sig_h * SPACING_RATIO)),
        max(10, int(sig_h * PADDING_RATIO)),
        max(10, int(sig_h * GAP_RATIO)),
    )


def _linha_opcional(tipo: str | None, numero: str | None) -> str | None:
    if not tipo or tipo == "Nenhum" or not numero:
        return None
    return f"{tipo} {numero}"


def _formatar_conselho(conselho_sigla: str, crm_estado: str, crm_numero: str) -> str:
    if conselho_sigla.upper() == "CRFA" and crm_estado.isdigit():
        return f"{conselho_sigla}-{crm_estado} {crm_numero}"
    return f"{conselho_sigla}/{crm_estado} {crm_numero}"


def _medir_texto(texto: str, tamanho: int, negrito: bool = False) -> tuple[int, int]:
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    fonte = carregar_fonte(tamanho, negrito=negrito)
    bbox = draw.textbbox((0, 0), texto, font=fonte)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _tokenizar_texto(texto: str) -> list[str]:
    tokens: list[str] = []
    atual = []
    for char in texto:
        if char in "/&":
            if atual:
                tokens.append("".join(atual).strip())
                atual = []
            tokens.append(char)
        elif char.isspace():
            if atual:
                tokens.append("".join(atual).strip())
                atual = []
        else:
            atual.append(char)
    if atual:
        tokens.append("".join(atual).strip())
    return [token for token in tokens if token]


def _juntar_tokens(tokens: list[str]) -> str:
    texto = ""
    for token in tokens:
        if token in "/&":
            texto = f"{texto} {token}" if texto else token
        else:
            texto = f"{texto} {token}" if texto else token
    return texto.strip()


def _quebrar_texto_inteligente(texto: str, tamanho: int, largura_max: int) -> list[str]:
    if not texto:
        return []

    largura_texto, _ = _medir_texto(texto, tamanho)
    if largura_texto <= largura_max:
        return [texto]

    tokens = _tokenizar_texto(texto)
    if len(tokens) <= 1:
        return [texto]

    linhas: list[str] = []
    atual: list[str] = []

    for token in tokens:
        candidato = _juntar_tokens(atual + [token])
        largura_candidata, _ = _medir_texto(candidato, tamanho)

        if atual and largura_candidata > largura_max:
            if atual[-1] in "/&" and len(atual) > 1:
                ultimo_separador = atual.pop()
                linhas.append(_juntar_tokens(atual))
                atual = [ultimo_separador, token]
            else:
                linhas.append(_juntar_tokens(atual))
                atual = [token]
        else:
            atual.append(token)

    if atual:
        linhas.append(_juntar_tokens(atual))

    return linhas


def _linhas_especialidade(especialidade: str, tamanho: int, largura_max: int) -> list[str]:
    blocos = [linha.strip() for linha in especialidade.splitlines() if linha.strip()]
    if not blocos:
        return []

    linhas: list[str] = []
    for bloco in blocos:
        linhas.extend(_quebrar_texto_inteligente(bloco, tamanho, largura_max))
    return linhas


def _montar_linhas(nome: str, especialidade: str, conselho_sigla: str,
                   crm_estado: str, crm_numero: str,
                   registro_tipo: str | None, registro_numero: str | None,
                   titulo_tipo: str | None, titulo_numero: str | None,
                   font_nome: int, font_info: int,
                   largura_max_especialidade: int) -> list[tuple[str, int, bool]]:
    linhas = [(nome, font_nome, True)]
    for linha_especialidade in _linhas_especialidade(especialidade, font_info, largura_max_especialidade):
        linhas.append((linha_especialidade, font_info, False))
    linhas.append((_formatar_conselho(conselho_sigla, crm_estado, crm_numero), font_info, False))
    for linha in (
        _linha_opcional(registro_tipo, registro_numero),
        _linha_opcional(titulo_tipo, titulo_numero),
    ):
        if linha:
            linhas.append((linha, font_info, False))
    return linhas


def _calcular_bloco(linhas: list[tuple[str, int, bool]],
                    spacing: int) -> tuple[int, int, list]:
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    renderizadas = []
    max_w = total_h = 0

    for texto, tamanho, negrito in linhas:
        fonte = carregar_fonte(tamanho, negrito=negrito)
        bbox = draw.textbbox((0, 0), texto, font=fonte)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        renderizadas.append((texto, fonte, w, h))
        max_w = max(max_w, w)
        total_h += h + spacing

    total_h -= spacing
    return max_w, total_h, renderizadas


def _compor_canvas(assinatura: Image.Image, nome: str, especialidade: str,
                   conselho_sigla: str, crm_estado: str, crm_numero: str,
                   registro_tipo: str | None, registro_numero: str | None,
                   titulo_tipo: str | None, titulo_numero: str | None) -> Image.Image:
    sig_w, sig_h = assinatura.size
    font_nome, font_info, spacing, padding, gap = _tamanhos(sig_h)
    largura_max_especialidade = max(int(sig_w * 1.55), int(sig_h * 1.8))

    linhas = _montar_linhas(
        nome,
        especialidade,
        conselho_sigla,
        crm_estado,
        crm_numero,
        registro_tipo,
        registro_numero,
        titulo_tipo,
        titulo_numero,
        font_nome,
        font_info,
        largura_max_especialidade,
    )
    texto_w, texto_h, renderizadas = _calcular_bloco(linhas, spacing)

    altura  = max(sig_h, texto_h) + padding * 2
    largura = padding + sig_w + gap + texto_w + padding

    canvas = Image.new("RGB", (largura, altura), BG_COLOR)

    # Assinatura centralizada verticalmente
    y_sig = (altura - sig_h) // 2
    canvas.paste(assinatura, (padding, y_sig))

    # Texto centralizado verticalmente
    draw = ImageDraw.Draw(canvas)
    x_texto = padding + sig_w + gap
    y_texto = (altura - texto_h) // 2

    for texto, fonte, w, h in renderizadas:
        x = x_texto + (texto_w - w) // 2
        draw.text((x, y_texto), texto, font=fonte, fill=TEXT_COLOR)
        y_texto += h + spacing

    return canvas


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def gerar(img_assinatura: str, nome: str, especialidade: str,
          conselho_sigla: str, crm_estado: str, crm_numero: str,
          registro_tipo: str | None, registro_numero: str | None,
          titulo_tipo: str | None, titulo_numero: str | None,
          saida: str) -> None:
    """Gera o PNG a partir de um arquivo em disco."""
    assinatura = preparar_assinatura_de_arquivo(img_assinatura)
    canvas = _compor_canvas(
        assinatura,
        nome,
        especialidade,
        conselho_sigla,
        crm_estado,
        crm_numero,
        registro_tipo,
        registro_numero,
        titulo_tipo,
        titulo_numero,
    )
    canvas.save(saida, "PNG", dpi=(TARGET_DPI, TARGET_DPI))
    print(f"Assinatura gerada: {saida}")


def gerar_em_memoria(img_upload, nome: str, especialidade: str,
                     conselho_sigla: str, crm_estado: str, crm_numero: str,
                     registro_tipo: str | None, registro_numero: str | None,
                     titulo_tipo: str | None, titulo_numero: str | None) -> bytes:
    """Gera o PNG a partir de um upload (file-like object) e retorna bytes."""
    assinatura = preparar_assinatura_de_upload(img_upload)
    canvas = _compor_canvas(
        assinatura,
        nome,
        especialidade,
        conselho_sigla,
        crm_estado,
        crm_numero,
        registro_tipo,
        registro_numero,
        titulo_tipo,
        titulo_numero,
    )
    buf = io.BytesIO()
    canvas.save(buf, "PNG", dpi=(TARGET_DPI, TARGET_DPI))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera assinatura/carimbo médico digital em PNG."
    )
    parser.add_argument("assinatura", help="Caminho da imagem da assinatura (PNG/JPG)")
    parser.add_argument("--nome",          required=True, help='Ex: "Dra. Juliana Santiago"')
    parser.add_argument("--especialidade", required=True, help='Ex: "Ginecologista e Obstetra"')
    parser.add_argument("--conselho-sigla", default="CRM", help="Sigla do conselho. Ex: CRM, CRP, CRO")
    parser.add_argument("--crm-estado",    required=True, help='Estado do CRM. Ex: PA, SP, RJ')
    parser.add_argument("--crm-numero",    required=True, help='Número do CRM. Ex: 15696')
    parser.add_argument("--registro-tipo",   default=None, help="Registro opcional. Ex: RQE, SBOT, SBOP")
    parser.add_argument("--registro-numero", default=None, help="NÃºmero do registro opcional")
    parser.add_argument("--titulo-tipo",     default=None, help="Titulo opcional. Ex: TEOT, TEOP")
    parser.add_argument("--titulo-numero",   default=None, help="NÃºmero do titulo opcional")
    parser.add_argument("--saida",         default=None,  help="Arquivo de saída PNG")
    parser.add_argument("--altura",        type=int, default=TARGET_HEIGHT,
                        help=f"Altura alvo da assinatura em px (padrão: {TARGET_HEIGHT})")

    args = parser.parse_args()

    if not Path(args.assinatura).exists():
        print(f"Erro: arquivo não encontrado: {args.assinatura}", file=sys.stderr)
        sys.exit(1)

    # Permite sobrescrever a altura alvo via CLI
    import gerar_assinatura as _self
    _self.TARGET_HEIGHT = args.altura

    saida = args.saida or (
        args.nome.lower().replace(" ", "_").replace(".", "") + ".png"
    )

    gerar(
        img_assinatura=args.assinatura,
        nome=args.nome,
        especialidade=args.especialidade,
        conselho_sigla=args.conselho_sigla.upper(),
        crm_estado=args.crm_estado.upper(),
        crm_numero=args.crm_numero,
        registro_tipo=args.registro_tipo,
        registro_numero=args.registro_numero,
        titulo_tipo=args.titulo_tipo,
        titulo_numero=args.titulo_numero,
        saida=saida,
    )


if __name__ == "__main__":
    main()
