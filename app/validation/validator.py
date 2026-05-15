"""Regras de validação de campos extraídos."""
import re
from typing import Optional


VALIDATION_RULES: dict[str, callable] = {}


def validate_field(field_name: str, value: str) -> tuple[bool, str]:
    """
    Valida um campo. Retorna (ok, mensagem_de_erro).
    Se ok=True, mensagem_de_erro é string vazia.
    """
    if not value.strip():
        return False, "Valor vazio"
    fn = VALIDATION_RULES.get(field_name)
    if fn:
        return fn(value)
    return True, ""


# ── Implementações por campo ───────────────────────────────────────────────

def _validate_cpf(value: str) -> tuple[bool, str]:
    digits = re.sub(r'\D', '', value)
    if len(digits) != 11:
        return False, "CPF deve ter 11 dígitos"
    if len(set(digits)) == 1:
        return False, "CPF inválido (todos dígitos iguais)"

    def _check(d: str, n: int) -> bool:
        total = sum(int(d[i]) * (n - i) for i in range(n - 1))
        rem = (total * 10) % 11
        rem = 0 if rem == 10 else rem
        return rem == int(d[n - 1])

    if not (_check(digits, 10) and _check(digits, 11)):
        return False, "CPF inválido (dígitos verificadores)"
    return True, ""


def _validate_cep(value: str) -> tuple[bool, str]:
    digits = re.sub(r'\D', '', value)
    if len(digits) != 8:
        return False, "CEP deve ter 8 dígitos"
    return True, ""


def _validate_data_nascimento(value: str) -> tuple[bool, str]:
    m = re.match(r'(\d{2})[/\-\.](\d{2})[/\-\.](\d{4})', value)
    if not m:
        return False, "Formato esperado: DD/MM/AAAA"
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2025):
        return False, "Data fora do intervalo válido"
    return True, ""


def _validate_agencia(value: str) -> tuple[bool, str]:
    digits = re.sub(r'\D', '', value)
    if len(digits) < 3 or len(digits) > 6:
        return False, "Agência deve ter entre 3 e 6 dígitos"
    return True, ""


def _validate_conta(value: str) -> tuple[bool, str]:
    digits = re.sub(r'\D', '', value)
    if len(digits) < 4:
        return False, "Número de conta muito curto"
    return True, ""


# Registro das regras
VALIDATION_RULES.update({
    "cpf": _validate_cpf,
    "cep": _validate_cep,
    "data_nascimento": _validate_data_nascimento,
    "agencia": _validate_agencia,
    "conta": _validate_conta,
})
