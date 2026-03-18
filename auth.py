"""
Autenticação simples com usuários em arquivo JSON.
Senhas armazenadas como SHA-256.
"""

import hashlib
import json
import os
from pathlib import Path

USERS_FILE = Path(os.environ.get("USERS_FILE", "users.json"))


def _hash(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()


def _carregar() -> dict:
    if not USERS_FILE.exists():
        # Cria arquivo com usuário padrão na primeira execução
        usuarios = {
            "admin": {
                "senha": _hash("admin123"),
                "nome":  "Administrador",
            }
        }
        USERS_FILE.write_text(json.dumps(usuarios, indent=2, ensure_ascii=False))
    return json.loads(USERS_FILE.read_text(encoding="utf-8"))


def autenticar(usuario: str, senha: str) -> dict | None:
    """
    Verifica credenciais. Retorna dict com dados do usuário ou None se inválido.
    """
    usuarios = _carregar()
    dados = usuarios.get(usuario.strip().lower())
    if dados and dados["senha"] == _hash(senha):
        return {"usuario": usuario.strip().lower(), "nome": dados["nome"]}
    return None


def listar_usuarios() -> list[dict]:
    return [
        {"usuario": u, "nome": d["nome"]}
        for u, d in _carregar().items()
    ]


def adicionar_usuario(usuario: str, senha: str, nome: str) -> None:
    usuarios = _carregar()
    usuarios[usuario.strip().lower()] = {
        "senha": _hash(senha),
        "nome":  nome,
    }
    USERS_FILE.write_text(json.dumps(usuarios, indent=2, ensure_ascii=False))


def remover_usuario(usuario: str) -> None:
    usuarios = _carregar()
    usuarios.pop(usuario.strip().lower(), None)
    USERS_FILE.write_text(json.dumps(usuarios, indent=2, ensure_ascii=False))


def alterar_senha(usuario: str, nova_senha: str) -> None:
    usuarios = _carregar()
    if usuario in usuarios:
        usuarios[usuario]["senha"] = _hash(nova_senha)
        USERS_FILE.write_text(json.dumps(usuarios, indent=2, ensure_ascii=False))
