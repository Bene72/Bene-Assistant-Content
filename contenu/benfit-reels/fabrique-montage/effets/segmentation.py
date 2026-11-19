"""Détourage de Bene (masque de la personne) pour les effets « texte derrière » et « contour découpé ».
Modèle u2net_human_seg (rembg, licence MIT) : ~/.u2net/u2net_human_seg.onnx, à télécharger une fois :
  curl -L -o ~/.u2net/u2net_human_seg.onnx https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx
Prérequis : pip install onnxruntime. Environ 1 s par image sur CPU.
"""
import numpy as np, onnxruntime as ort, os
from PIL import Image, ImageFilter
_S = None
def _sess():
    global _S
    if _S is None:
        p = os.path.expanduser("~/.u2net/u2net_human_seg.onnx")
        _S = ort.InferenceSession(p, providers=["CPUExecutionProvider"])
    return _S
MEAN = np.array([0.485, 0.456, 0.406], np.float32); STD = np.array([0.229, 0.224, 0.225], np.float32)
def mask(frame):
    """frame uint8 HxWx3 -> masque float32 HxW (1 = personne)."""
    h, w = frame.shape[:2]
    im = Image.fromarray(frame).resize((320, 320), Image.BILINEAR)
    x = (np.asarray(im).astype(np.float32) / 255 - MEAN) / STD
    x = x.transpose(2, 0, 1)[None]
    s = _sess()
    o = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
    o = (o - o.min()) / (o.max() - o.min() + 1e-6)
    m = Image.fromarray((o * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.5))
    m = np.asarray(m).astype(np.float32) / 255
    return np.clip((m - 0.35) / 0.3, 0, 1)
