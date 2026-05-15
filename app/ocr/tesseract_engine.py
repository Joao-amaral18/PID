"""OCR local usando Tesseract via pytesseract."""
import io
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
import pytesseract
from PIL import Image


def run(filepath: str) -> tuple[str, float]:
    """Executa OCR no arquivo. Retorna (texto, confidence 0-1)."""
    ext = Path(filepath).suffix.lower()
    if ext == ".pdf":
        images = _pdf_to_images(filepath)
    elif ext in (".png", ".jpg", ".jpeg"):
        raw = cv2.imread(filepath)
        if raw is None:
            return "", 0.0
        images = [raw]
    else:
        return "", 0.0

    all_text: list[str] = []
    all_conf: list[float] = []
    for img in images:
        preprocessed = _preprocess(img)
        text, conf = _tesseract(preprocessed)
        all_text.append(text)
        all_conf.append(conf)

    combined = "\n\n".join(t for t in all_text if t)
    mean_conf = sum(all_conf) / len(all_conf) if all_conf else 0.0
    return combined, mean_conf


def _pdf_to_images(filepath: str) -> list[np.ndarray]:
    """Renderiza cada página do PDF a 300 DPI como array numpy RGB."""
    try:
        doc = fitz.open(filepath)
    except fitz.FileDataError:
        return []
    images = []
    mat = fitz.Matrix(300 / 72, 300 / 72)
    for page in doc:
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.h, pix.w, 3
        )
        images.append(arr)
    doc.close()
    return images


def _preprocess(img: np.ndarray) -> np.ndarray:
    """Grayscale → CLAHE → Gaussian blur → threshold Otsu."""
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
    _, binary = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return binary


def _tesseract(img: np.ndarray) -> tuple[str, float]:
    """Executa Tesseract com dicionário português."""
    pil_img = Image.fromarray(img)
    try:
        data = pytesseract.image_to_data(
            pil_img,
            lang="por",
            config="--oem 3 --psm 6",
            output_type=pytesseract.Output.DICT,
        )
    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "Tesseract não encontrado. Instale: sudo apt-get install tesseract-ocr tesseract-ocr-por"
        )

    words = [
        w
        for w, c in zip(data["text"], data["conf"])
        if int(c) > 0 and w.strip()
    ]
    confs = [int(c) for c in data["conf"] if int(c) > 0]
    text = " ".join(words)
    avg_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
    return text, avg_conf


def pdf_page_count(filepath: str) -> int:
    """Retorna o número de páginas de um PDF."""
    try:
        doc = fitz.open(filepath)
        n = doc.page_count
        doc.close()
        return n
    except Exception:
        return 1


def pdf_pages_as_png_bytes(filepath: str) -> list[bytes]:
    """Renderiza cada página do PDF como PNG em memória (para Textract)."""
    try:
        doc = fitz.open(filepath)
    except fitz.FileDataError:
        return []
    pages_bytes: list[bytes] = []
    mat = fitz.Matrix(300 / 72, 300 / 72)
    for page in doc:
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        buf = io.BytesIO()
        Image.frombytes("RGB", [pix.w, pix.h], pix.samples).save(buf, format="PNG")
        pages_bytes.append(buf.getvalue())
    doc.close()
    return pages_bytes


def image_as_png_bytes(filepath: str) -> list[bytes]:
    """Lê uma imagem e retorna como PNG em memória (para Textract)."""
    raw = cv2.imread(filepath)
    if raw is None:
        return []
    pil = Image.fromarray(cv2.cvtColor(raw, cv2.COLOR_BGR2RGB))
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return [buf.getvalue()]
