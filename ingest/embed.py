# ingest/embed.py
from nomic import embed
import numpy as np
from PIL import Image
import clip
import torch

# Text embedding
def embed_text(text: str):
    return embed.text(text, model="nomic-embed-text-v1.5")[0]["embedding"]

# Image embedding (CLIP)
device = "cuda" if torch.cuda.is_available() else "cpu"
clip_model, preprocess = clip.load("ViT-B/32", device=device)

def embed_image(img: Image.Image):
    img = preprocess(img).unsqueeze(0).to(device)
    with torch.no_grad():
        vec = clip_model.encode_image(img).cpu().numpy()[0]
    return vec.tolist()
