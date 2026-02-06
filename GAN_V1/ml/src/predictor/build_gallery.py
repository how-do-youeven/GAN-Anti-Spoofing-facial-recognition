import argparse
from pathlib import Path

import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image

from ml.src.predictor.model import AntiSpoofAndIDModel


IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@torch.no_grad()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gallery_root", required=True, help="root folder with identity subfolders")
    ap.add_argument("--ckpt", default="ml/exports/predictor_best.pt")
    ap.add_argument("--out", default="ml/exports/gallery.pt")
    ap.add_argument("--img_size", type=int, default=224)
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"

    ckpt = torch.load(args.ckpt, map_location="cpu")
    model = AntiSpoofAndIDModel(pretrained=False)
    model.load_state_dict(ckpt["model_state"])
    model.to(device).eval()

    tf = transforms.Compose([
        transforms.Resize((ckpt["img_size"], ckpt["img_size"])),
        transforms.ToTensor(),
        transforms.Normalize(ckpt["mean"], ckpt["std"]),
    ])

    names = []
    embeddings = []

    root = Path(args.gallery_root)

    for person_dir in sorted(root.iterdir()):
        if not person_dir.is_dir():
            continue

        person_embs = []

        for img_path in person_dir.iterdir():
            if img_path.suffix.lower() not in IMG_EXTS:
                continue

            img = Image.open(img_path).convert("RGB")
            x = tf(img).unsqueeze(0).to(device)

            _, emb = model(x)
            person_embs.append(emb.squeeze(0).cpu())

        if not person_embs:
            continue

        mean_emb = torch.stack(person_embs).mean(dim=0)
        mean_emb = F.normalize(mean_emb, p=2, dim=0)

        names.append(person_dir.name)
        embeddings.append(mean_emb)

        print(f"Enrolled {person_dir.name} ({len(person_embs)} images)")

    gallery = {
        "names": names,
        "embeddings": torch.stack(embeddings)
    }

    torch.save(gallery, args.out)
    print("✅ Gallery saved to:", args.out)


if __name__ == "__main__":
    main()
