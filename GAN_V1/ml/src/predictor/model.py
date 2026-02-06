import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models


class PatchAttentionPool(nn.Module):
    """
    Takes feature map [B, C, H, W] -> pooled vector [B, C]
    by learning attention weights per spatial patch.
    """
    def __init__(self, channels: int, hidden: int = 256):
        super().__init__()
        self.attn = nn.Sequential(
            nn.Linear(channels, hidden),
            nn.ReLU(inplace=True),
            nn.Linear(hidden, 1)  # score per patch
        )

    def forward(self, feat: torch.Tensor):
        # feat: [B, C, H, W]
        b, c, h, w = feat.shape
        patches = feat.flatten(2).transpose(1, 2)  # [B, HW, C]

        scores = self.attn(patches).squeeze(-1)    # [B, HW]
        weights = torch.softmax(scores, dim=1)     # [B, HW]

        pooled = torch.sum(patches * weights.unsqueeze(-1), dim=1)  # [B, C]
        return pooled, weights  # weights is useful for visualization/debug


class ResNet18FeatureExtractor(nn.Module):
    """
    ResNet18 without global pooling + fc.
    Outputs final conv feature map: [B, 512, H, W]
    """
    def __init__(self, pretrained: bool = True):
        super().__init__()
        m = models.resnet18(weights=models.ResNet18_Weights.DEFAULT if pretrained else None)
        self.conv1 = m.conv1
        self.bn1 = m.bn1
        self.relu = m.relu
        self.maxpool = m.maxpool
        self.layer1 = m.layer1
        self.layer2 = m.layer2
        self.layer3 = m.layer3
        self.layer4 = m.layer4
        self.out_channels = 512

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        return x  # [B, 512, H, W]


class AntiSpoofAndIDModel(nn.Module):
    """
    Shared backbone + patch-attention pooling.
    Head A: anti-spoof logits [spoof, real]
    Head B: identity embedding (normalized)
    """
    def __init__(self, num_spoof_classes: int = 2, emb_dim: int = 256, pretrained: bool = True):
        super().__init__()
        self.backbone = ResNet18FeatureExtractor(pretrained=pretrained)
        self.pool = PatchAttentionPool(channels=self.backbone.out_channels)

        self.spoof_head = nn.Sequential(
            nn.Linear(self.backbone.out_channels, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(256, num_spoof_classes)
        )

        self.emb_head = nn.Sequential(
            nn.Linear(self.backbone.out_channels, 512),
            nn.ReLU(inplace=True),
            nn.Linear(512, emb_dim)
        )

    def forward(self, x, return_attention: bool = False):
        feat = self.backbone(x)
        pooled, attn = self.pool(feat)

        spoof_logits = self.spoof_head(pooled)
        emb = self.emb_head(pooled)
        emb = F.normalize(emb, p=2, dim=1)

        if return_attention:
            return spoof_logits, emb, attn
        return spoof_logits, emb
