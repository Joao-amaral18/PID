"""Classifica documentos por palavras-chave no texto OCR."""
import unicodedata

KEYWORDS: dict[str, list[str]] = {
    "identificacao": [
        "cpf", "registro geral", "carteira de identidade", "rg", "cnh",
        "carteira nacional de habilitação", "passaporte", "filiação",
        "naturalidade", "nacionalidade", "data de nascimento",
        "documento de identidade",
    ],
    "residencia": [
        "conta de luz", "energia elétrica", "conta de água", "saneamento",
        "conta de gás", "comprovante de residência", "iptu",
        "correspondencia", "logradouro", "município", "cep",
        "declaracao de residencia",
    ],
    "bancario": [
        "banco", "agência", "conta corrente", "conta poupança",
        "extrato bancário", "comprovante bancário", "pix",
        "bradesco", "itaú", "caixa econômica", "banco do brasil",
        "santander", "nubank", "inter", "c6 bank",
        "iban", "número da conta",
    ],
    "procuracao": [
        "procuração", "outorgante", "outorgado", "procurador",
        "poderes", "substabelecimento", "mandato", "mandante",
        "outorgado os poderes", "por seus direitos",
    ],
    "termo": [
        "termo de ciência", "termo de adesao", "declaração",
        "declaro para os devidos fins", "concordo", "assinatura do declarante",
        "termo de compromisso",
    ],
}


def classify_document(ocr_text: str) -> tuple[str, float]:
    """
    Classifica o documento. Retorna (tipo, score_0_1).
    Tipos: identificacao | residencia | bancario | procuracao | termo | outros
    """
    norm = _normalize(ocr_text)
    scores: dict[str, float] = {}

    for doc_type, keywords in KEYWORDS.items():
        score = 0.0
        for kw in keywords:
            if _normalize(kw) in norm:
                score += len(kw.split())
        scores[doc_type] = score

    best_type = max(scores, key=lambda k: scores[k])
    total = sum(scores.values())

    if scores[best_type] == 0:
        return "outros", 0.0

    confidence = min(1.0, scores[best_type] / total) if total > 0 else 0.0
    return best_type, confidence


def _normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))
