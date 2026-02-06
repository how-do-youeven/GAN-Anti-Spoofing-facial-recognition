import os
import time
from pathlib import Path
import tkinter as tk
from tkinter import simpledialog, messagebox

import cv2
import numpy as np
from PIL import Image, ImageTk

import torch
import torch.nn.functional as F
from torchvision import transforms

# Anti-spoof model (your trained model)
from ml.src.predictor.model import AntiSpoofAndIDModel

# Pretrained face recognition embedder
from facenet_pytorch import InceptionResnetV1

# ------------------ CONFIG ------------------
CKPT_PATH = "ml/exports/predictor_best.pt"
GALLERY_PT = "ml/exports/gallery_facenet.pt"
GALLERY_ROOT = "ml/data/gallery"  # stores captured frames per identity

REAL_THRESH_VERIFY = 0.70
REAL_THRESH_ENROLL = 0.20   # much lower so you can capture frames

REAL_THRESH = 0.90   # min P(real) to proceed
SIM_THRESH  = 0.70   # start here; tune 0.70–0.85
GAP_THRESH  = 0.05   # top1 - top2 margin; tune 0.03–0.10

# Registration capture settings
CAPTURE_SECONDS = 3.0
SAMPLE_EVERY_N_FRAMES = 2     # take every 2nd frame
MIN_FRAMES_REQUIRED = 8       # minimum usable face frames to accept registration
# --------------------------------------------


IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def ensure_dir(p: str):
    Path(p).mkdir(parents=True, exist_ok=True)


def detect_face_bgr(frame_bgr, face_cascade):
    """Return (x,y,w,h) for largest detected face, else None."""
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(90, 90))
    if len(faces) == 0:
        return None
    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
    return faces[0]


def crop_face(frame_bgr, box, pad=0.25):
    x, y, w, h = box
    H, W = frame_bgr.shape[:2]
    px = int(w * pad)
    py = int(h * pad)
    x1 = max(0, x - px)
    y1 = max(0, y - py)
    x2 = min(W, x + w + px)
    y2 = min(H, y + h + py)
    return frame_bgr[y1:y2, x1:x2], (x1, y1, x2 - x1, y2 - y1)


def load_antispoof(ckpt_path: str, device: str):
    ckpt = torch.load(ckpt_path, map_location="cpu")

    model = AntiSpoofAndIDModel(num_spoof_classes=2, emb_dim=256, pretrained=False)
    model.load_state_dict(ckpt["model_state"])
    model.to(device).eval()

    tf = transforms.Compose([
        transforms.Resize((ckpt["img_size"], ckpt["img_size"])),
        transforms.ToTensor(),
        transforms.Normalize(ckpt["mean"], ckpt["std"]),
    ])
    return model, tf


def load_facenet(device: str):
    """
    Pretrained face recognition embedder.
    Returns 512-D normalized embeddings.
    """
    fr = InceptionResnetV1(pretrained="vggface2").to(device).eval()
    # Facenet expects 160x160 RGB roughly normalized to [-1, 1]
    fr_tf = transforms.Compose([
        transforms.Resize((160, 160)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])
    return fr, fr_tf


@torch.no_grad()
def antispoof_score(model, tf, device, face_bgr):
    rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    x = tf(pil).unsqueeze(0).to(device)
    logits, _ = model(x)
    probs = torch.softmax(logits, dim=1).squeeze(0).cpu()
    return float(probs[0]), float(probs[1])  # spoof, real


@torch.no_grad()
def facenet_embed(fr_model, fr_tf, device, face_bgr):
    rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    x = fr_tf(pil).unsqueeze(0).to(device)
    emb = fr_model(x).squeeze(0).cpu()
    emb = F.normalize(emb, p=2, dim=0)
    return emb  # [512]


def load_gallery(path: str):
    """
    gallery format:
    {
      "people": {
         name: Tensor[K, 512]  # normalized embeddings
      }
    }
    """
    p = Path(path)
    if not p.exists():
        return {}
    g = torch.load(path, map_location="cpu")
    people = g.get("people", {})
    # ensure normalized
    for k in list(people.keys()):
        people[k] = F.normalize(people[k], p=2, dim=1)
    return people


def save_gallery(path: str, people: dict):
    torch.save({"people": people}, path)


def rebuild_gallery_from_folder(fr_model, fr_tf, device, face_cascade):
    """
    Optional: rebuild gallery embeddings from GALLERY_ROOT image folders.
    Uses the same face detection + cropping.
    """
    people = {}
    root = Path(GALLERY_ROOT)
    if not root.exists():
        return people

    for person_dir in sorted(root.iterdir()):
        if not person_dir.is_dir():
            continue

        embs = []
        for img_path in person_dir.iterdir():
            if img_path.suffix.lower() not in IMG_EXTS:
                continue
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            box = detect_face_bgr(img, face_cascade)
            if box is None:
                continue
            face, _ = crop_face(img, box)
            emb = facenet_embed(fr_model, fr_tf, device, face)
            embs.append(emb)

        if embs:
            people[person_dir.name] = torch.stack(embs, dim=0)

    return people


class WebcamDemoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Anti-Spoof Gate + Pretrained Face ID (Webcam Demo)")

        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Models
        self.as_model, self.as_tf = load_antispoof(CKPT_PATH, self.device)
        self.fr_model, self.fr_tf = load_facenet(self.device)

        # Face detector
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        ensure_dir(GALLERY_ROOT)
        ensure_dir(str(Path(GALLERY_PT).parent))

        # Load gallery embeddings
        self.people = load_gallery(GALLERY_PT)
        self.status = tk.StringVar(value=self._status_text("Loaded"))

        self.video_label = tk.Label(root)
        self.video_label.pack(padx=8, pady=8)

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=6)

        self.btn_register = tk.Button(btn_frame, text="Register (Video)", width=16, command=self.register_video)
        self.btn_register.grid(row=0, column=0, padx=6)

        self.btn_verify = tk.Button(btn_frame, text="Verify", width=14, command=self.verify)
        self.btn_verify.grid(row=0, column=1, padx=6)

        self.btn_reload = tk.Button(btn_frame, text="Reload Gallery", width=14, command=self.reload_gallery)
        self.btn_reload.grid(row=0, column=2, padx=6)

        self.btn_rebuild = tk.Button(btn_frame, text="Rebuild From Folders", width=18, command=self.rebuild_from_folders)
        self.btn_rebuild.grid(row=0, column=3, padx=6)

        tk.Label(root, textvariable=self.status).pack(pady=6)

        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Could not open webcam.")
            root.destroy()
            return

        self.latest_frame = None
        self.latest_box = None
        self.update_loop()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _status_text(self, prefix):
        return f"{prefix} | Device: {self.device} | Identities: {len(self.people)}"

    def update_loop(self):
        ok, frame = self.cap.read()
        if ok:
            self.latest_frame = frame.copy()

            vis = frame.copy()
            box = detect_face_bgr(vis, self.face_cascade)
            self.latest_box = box

            if box is not None:
                _, box2 = crop_face(vis, box)
                x, y, w, h = box2
                cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 255, 0), 2)
            else:
                cv2.putText(vis, "No face detected", (12, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            rgb = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

        self.root.after(30, self.update_loop)

    def reload_gallery(self):
        self.people = load_gallery(GALLERY_PT)
        self.status.set(self._status_text("Reloaded"))

    def rebuild_from_folders(self):
        people = rebuild_gallery_from_folder(self.fr_model, self.fr_tf, self.device, self.face_cascade)
        save_gallery(GALLERY_PT, people)
        self.people = people
        self.status.set(self._status_text("Rebuilt"))
        messagebox.showinfo("Gallery", "Rebuilt gallery from folders.")

    def register_video(self):
        if self.latest_frame is None:
            messagebox.showwarning("Warning", "No webcam frame yet.")
            return

        name = simpledialog.askstring("Register", "Enter identity name (folder name):")
        if not name:
            return

        # Capture short video and sample frames
        start = time.time()
        frame_count = 0
        saved = 0
        embs = []

        person_dir = Path(GALLERY_ROOT) / name
        person_dir.mkdir(parents=True, exist_ok=True)

        messagebox.showinfo("Register", f"Capturing for {CAPTURE_SECONDS:.1f} seconds.\nKeep your face centered.")

        while time.time() - start < CAPTURE_SECONDS:
            ok, frame = self.cap.read()
            if not ok:
                continue

            frame_count += 1
            if frame_count % SAMPLE_EVERY_N_FRAMES != 0:
                continue

            box = detect_face_bgr(frame, self.face_cascade)
            if box is None:
                continue

            face, _ = crop_face(frame, box)

            # Anti-spoof gate for enrollment frames
            p_spoof, p_real = antispoof_score(self.as_model, self.as_tf, self.device, face)
            if p_real < REAL_THRESH_ENROLL:
                continue

            # Save face image + embedding
            out_path = person_dir / f"{int(time.time() * 1000)}.jpg"
            cv2.imwrite(str(out_path), face)
            saved += 1

            emb = facenet_embed(self.fr_model, self.fr_tf, self.device, face)
            embs.append(emb)

        if len(embs) < MIN_FRAMES_REQUIRED:
            messagebox.showwarning(
                "Register Failed",
                f"Not enough valid REAL frames captured.\n"
                f"Captured: {saved} (need >= {MIN_FRAMES_REQUIRED})\n"
                f"Tip: improve lighting, face camera, remove blur."
            )
            return

        person_embs = torch.stack(embs, dim=0)  # [K, 512]
        person_embs = F.normalize(person_embs, p=2, dim=1)

        # Update gallery.pt
        people = load_gallery(GALLERY_PT)
        people[name] = person_embs
        save_gallery(GALLERY_PT, people)

        self.people = people
        self.status.set(self._status_text("Registered"))
        messagebox.showinfo("Success", f"Registered '{name}' with {len(embs)} frames.")

    def verify(self):
        if self.latest_frame is None:
            messagebox.showwarning("Warning", "No webcam frame yet.")
            return

        box = self.latest_box
        if box is None:
            messagebox.showwarning("Warning", "No face detected. Try again.")
            return

        face, _ = crop_face(self.latest_frame, box)

        # Anti-spoof gate
        p_spoof, p_real = antispoof_score(self.as_model, self.as_tf, self.device, face)
        if p_real < REAL_THRESH_VERIFY:
            messagebox.showwarning("Result", f"❌ Spoof/Uncertain\nP(spoof)={p_spoof:.2f}  P(real)={p_real:.2f}")
            return

        if not self.people:
            messagebox.showwarning("Result", f"✅ Real detected\nP(real)={p_real:.2f}\n(No identities enrolled)")
            return

        # Face embedding (pretrained)
        q = facenet_embed(self.fr_model, self.fr_tf, self.device, face)  # [512]

        # For each identity: compute MAX similarity across their K samples
        names = list(self.people.keys())
        best_name = None
        best_sim = -1.0

        sims_all = []
        for nm in names:
            E = self.people[nm]            # [K, 512]
            sims = (E @ q)                 # [K]
            s = float(torch.max(sims).item())
            sims_all.append((nm, s))

        sims_all.sort(key=lambda x: x[1], reverse=True)
        best_name, best_sim = sims_all[0]
        second_sim = sims_all[1][1] if len(sims_all) > 1 else -1.0
        gap = best_sim - second_sim

        # Open-set reject rules (UNKNOWN)
        if best_sim < SIM_THRESH or gap < GAP_THRESH:
            messagebox.showwarning(
                "Result",
                f"✅ REAL but UNKNOWN\n"
                f"Best: {best_name} ({best_sim:.2f})\n"
                f"2nd: {second_sim:.2f}  Gap: {gap:.2f}\n"
                f"P(real): {p_real:.2f}"
            )
            return

        messagebox.showinfo(
            "Result",
            f"✅ REAL + ID MATCH\n"
            f"Name: {best_name}\n"
            f"CosSim(max): {best_sim:.2f}\n"
            f"Gap: {gap:.2f}\n"
            f"P(real): {p_real:.2f}"
        )

    def on_close(self):
        try:
            self.cap.release()
        except Exception:
            pass
        self.root.destroy()


def main():
    if not os.path.exists(CKPT_PATH):
        raise FileNotFoundError(f"Anti-spoof checkpoint not found: {CKPT_PATH}")

    root = tk.Tk()
    WebcamDemoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
