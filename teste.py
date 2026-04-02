"""Cria uma assinatura de teste sintética e chama o gerador."""
from PIL import Image, ImageDraw
from gerar_assinatura import gerar

# Cria uma imagem simulando uma assinatura (fundo branco + traço preto)
sig = Image.new("RGB", (300, 150), (255, 255, 255))
draw = ImageDraw.Draw(sig)
# Traços simulando uma assinatura
pontos = [
    (20, 100), (40, 60), (60, 110), (80, 50), (110, 90),
    (140, 40), (160, 100), (200, 70), (240, 90), (280, 60)
]
draw.line(pontos, fill=(0, 0, 0), width=3)
draw.line([(20, 110), (120, 130)], fill=(0, 0, 0), width=2)
sig.save("assinatura_teste.png")

# Gera com RQE
gerar(
    img_assinatura="assinatura_teste.png",
    nome="Dra. Juliana Santiago",
    especialidade="Ginecologista e Obstetra",
    crm_estado="PA",
    crm_numero="15696",
    rqe="124150",
    saida="resultado_com_rqe.png",
)

# Gera sem RQE
gerar(
    img_assinatura="assinatura_teste.png",
    nome="Dr. Carlos Mendes",
    especialidade="Clínico Geral",
    crm_estado="SP",
    crm_numero="98765",
    rqe=None,
    saida="resultado_sem_rqe.png",
)

print("Testes concluídos.")
