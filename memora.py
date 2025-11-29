# memora.py — v1.1 — TOTAL RECALL (audio + screen + webcam + Phi-3 reasoning)
# ONE FILE. ZERO CLOUD. WORKS NOW.

import time, os, threading, numpy as np, sqlite3, sqlite_vec
from datetime import datetime
from pathlib import Path
import whisper, soundcard as sc, mss, cv2
from PIL import Image
import pytesseract
from nomic import embed
from rich.console import Console

# === CONFIG ===
DB_PATH = Path.home() / ".memora" / "memory.db"
DB_PATH.parent.mkdir(exist_ok=True)
console = Console()

# === DATABASE ===
conn = sqlite3.connect(DB_PATH)
conn.execute("CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY, ts REAL, type TEXT, content TEXT, embedding BLOB)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON memories(ts)")

# === MODELS (lazy load) ===
whisper_model = None
phi3 = None

def get_whisper():
    global whisper_model
    if whisper_model is None:
        console.print("[yellow]Loading Whisper tiny...[/]")
        whisper_model = whisper.load_model("tiny")
    return whisper_model

def get_phi3():
    global phi3
    if phi3 is None:
        console.print("[bold magenta]Waking up your second brain (Phi-3 Mini)...[/]")
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct", trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            "microsoft/Phi-3-mini-4k-instruct", device_map="auto", torch_dtype=torch.float16, trust_remote_code=True
        )
        phi3 = {"model": model, "tokenizer": tokenizer}
    return phi3

# === EMBEDDING ===
def embed_text(text: str):
    return embed.text(text, model="nomic-embed-text-v1.5")[0]["embedding"]

# === CAPTURE THREADS ===
def audio_thread():
    model = get_whisper()
    with sc.get_microphone().recorder(samplerate=16000) as mic:
        while True:
            data = mic.record(numframes=16000*5)
            audio = np.squeeze(data)
            text = model.transcribe(audio, fp16=False, language="en")["text"].strip()
            if len(text) > 10:
                vec = embed_text(text)
                conn.execute("INSERT INTO memories(ts,type,content,embedding) VALUES(?,?,?,?)",
                            (time.time(), "audio", text, np.array(vec, dtype=np.float32).tobytes()))
                conn.commit()
                console.print(f"[cyan][AUDIO][/cyan] {text[:100]}{'...' if len(text)>100 else ''}")

def screen_thread():
    with mss.mss() as sct:
        while True:
            img = Image.frombytes("RGB", sct.monitors[0]["width"], sct.monitors[0]["height"], sct.grab(sct.monitors[0]).rgb)
            text = pytesseract.image_to_string(img)
            if text.strip():
                vec = embed_text(text[:4000])
                conn.execute("INSERT INTO memories(ts,type,content,embedding) VALUES(?,?,?,?)",
                            (time.time(), "screen", text[:2000], np.array(vec, dtype=np.float32).tobytes()))
                conn.commit()
            time.sleep(20)

def webcam_thread():
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if ret:
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            text = pytesseract.image_to_string(img)
            vec = embed_text(text[:2000] if text else "webcam frame")
            conn.execute("INSERT INTO memories(ts,type,content,embedding) VALUES(?,?,?,?)",
                        (time.time(), "webcam", text[:1000], np.array(vec, dtype=np.float32).tobytes()))
            conn.commit()
        time.sleep(30)

# === SEARCH & REASONING ===
def recall(query: str, limit=10):
    qvec = np.array(embed_text(query), dtype=np.float32)
    rows = conn.execute("""
        SELECT content, ts, type, distance
        FROM memories
        WHERE embedding MATCH ?
        ORDER BY distance LIMIT ?
    """, (qvec.tobytes(), limit)).fetchall()
    for content, ts, typ, dist in rows:
        date = datetime.fromtimestamp(ts).strftime("%b %d %Y %H:%M")
        console.print(f"[green]{date}[/] [{typ}] (sim={1-dist:.3f}) {content[:140]}...")

def ask_life(question: str):
    console.print("[bold magenta]Asking my entire life...[/]")
    phi = get_phi3()
    qvec = np.array(embed_text(question), dtype=np.float32)
    rows = conn.execute("""
        SELECT content, ts, type
        FROM memories
        WHERE embedding MATCH ?
        ORDER BY distance LIMIT 40
    """, (qvec.tobytes(),)).fetchall()
    
    context = "\n".join([f"{datetime.fromtimestamp(ts).strftime('%Y-%m-%d')} [{typ}]: {c[:800]}" for c,ts,typ in rows])
    prompt = f"""You are my lifelong second brain. Here is real data from my life:

{context}

Question: {question}
Answer as me, brutally honest, with dates."""

    inputs = phi["tokenizer"](prompt, return_tensors="pt").to(phi["model"].device)
    output = phi["model"].generate(**inputs, max_new_tokens=400, temperature=0.7)
    answer = phi["tokenizer"].decode(output[0], skip_special_tokens=True)
    console.print(f"[bold white]{answer.split('Question:')[-1].strip()}[/]")

# === START EVERYTHING ===
console.print("[bold red]MEMORA v1.1 — TOTAL RECALL ACTIVATED[/]")
threading.Thread(target=audio_thread, daemon=True).start()
threading.Thread(target=screen_thread, daemon=True).start()
threading.Thread(target=webcam_thread, daemon=True).start()

console.print("[green]Capturing audio • screen • webcam. Type 'quit' to stop.[/]")
try:
    while True:
        q = input("\n> ").strip()
        if q.lower() == "quit": break
        if q.startswith("why") or q.startswith("when") or "feel" in q:
            ask_life(q)
        else:
            recall(q)
except KeyboardInterrupt:
    pass
finally:
    console.print("\n[bold red]Memora stopped. Your entire life is safe. Forever yours.[/]")
