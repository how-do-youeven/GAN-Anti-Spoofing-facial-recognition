import argparse
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image

from ml.src.predictor.model import AntiSpoofAndIDModel


def load_gallery(path: str):
    """
    Expects a .pt file like:
    {
      "names": [str, ...],
      "embeddings": Tensor[N, D] (already normalized)
    }
    """
    g = torch.load(path, map_location="cpu")
    names = g["names"]
    emb = g["embeddings"]
    emb = F.normalize(emb, p=2, dim=1)
    return names, emb


@torch.no_grad()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--img", required=True)
    ap.add_argument("--ckpt", default="ml/exports/predictor_best.pt")
    ap.add_argument("--gallery", default=None, help="optional: path to embeddings gallery .pt")
    ap.add_argument("--real_thresh", type=float, default=0.70, help="min P(real) to proceed to ID match")
    ap.add_argument("--sim_thresh", type=float, default=0.35, help="min cosine similarity to accept identity")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    ckpt = torch.load(args.ckpt, map_location="cpu")

    model = AntiSpoofAndIDModel(num_spoof_classes=2, emb_dim=256, pretrained=False)
    model.load_state_dict(ckpt["model_state"])
    model.to(device).eval()

    img_size = ckpt["img_size"]
    mean = ckpt["mean"]
    std = ckpt["std"]

    tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ])

    x = tf(Image.open(args.img).convert("RGB")).unsqueeze(0).to(device)
    logits, emb = model(x)
    probs = torch.softmax(logits, dim=1).squeeze(0).cpu()
    p_spoof, p_real = float(probs[0]), float(probs[1])

    print("spoof:", p_spoof, "real:", p_real)

    # Gate: only attempt identity match if real is confident
    if p_real < args.real_thresh:
        print("❌ Not confident real -> skip identity match.")
        return

    if not args.gallery:
        print("✅ Real detected. (No gallery provided, so no ID match.)")
        return

    names, gallery_emb = load_gallery(args.gallery)
    emb_cpu = emb.squeeze(0).cpu()  # [D], already normalized

    sims = gallery_emb @ emb_cpu  # cosine similarity because normalized
    best_idx = int(torch.argmax(sims).item())
    best_name = names[best_idx]
    best_sim = float(sims[best_idx].item())

    print("best_match:", best_name, "cos_sim:", best_sim)

    if best_sim >= args.sim_thresh:
        print("✅ Identity accepted:", best_name)
    else:
        print("⚠️ No confident identity match.")


if __name__ == "__main__":
    main()