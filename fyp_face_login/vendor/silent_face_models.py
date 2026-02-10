"""
MiniFASNet models and utilities from Silent-Face-Anti-Spoofing (minivision-ai).
Used for silent liveness / anti-spoofing prediction.
"""
import os
import torch
import torch.nn.functional as F
from torch.nn import (
    Linear,
    Conv2d,
    BatchNorm1d,
    BatchNorm2d,
    PReLU,
    ReLU,
    Sigmoid,
    AdaptiveAvgPool2d,
    Sequential,
    Module,
)


def get_kernel(height: int, width: int):
    return ((height + 15) // 16, (width + 15) // 16)


def parse_model_name(model_name: str):
    """Parse Silent Face model filename. Returns (h_input, w_input, model_type, scale)."""
    name = os.path.basename(model_name)
    parts = name.replace(".pth", "").split("_")
    if len(parts) < 3:
        return 80, 80, "MiniFASNetV1", None
    # e.g. 2.7_80x80_MiniFASNetV1 or org_1_80x80_MiniFASNetV1
    hw = parts[-2]  # 80x80
    model_type = parts[-1]  # MiniFASNetV1
    if "x" in hw:
        h_input, w_input = map(int, hw.split("x"))
    else:
        h_input = w_input = 80
    if parts[0] == "org":
        scale = None
    else:
        try:
            scale = float(parts[0])
        except ValueError:
            scale = 2.7
    return h_input, w_input, model_type, scale


# --- MiniFASNet architecture (from minivision-ai/Silent-Face-Anti-Spoofing) ---


class L2Norm(Module):
    def forward(self, input):
        return F.normalize(input)


class Flatten(Module):
    def forward(self, input):
        return input.view(input.size(0), -1)


class Conv_block(Module):
    def __init__(self, in_c, out_c, kernel=(1, 1), stride=(1, 1), padding=(0, 0), groups=1):
        super().__init__()
        self.conv = Conv2d(
            in_c, out_c, kernel_size=kernel, groups=groups, stride=stride, padding=padding, bias=False
        )
        self.bn = BatchNorm2d(out_c)
        self.prelu = PReLU(out_c)

    def forward(self, x):
        x = self.conv(x)
        x = self.bn(x)
        x = self.prelu(x)
        return x


class Linear_block(Module):
    def __init__(self, in_c, out_c, kernel=(1, 1), stride=(1, 1), padding=(0, 0), groups=1):
        super().__init__()
        self.conv = Conv2d(
            in_c, out_c, kernel_size=kernel, groups=groups, stride=stride, padding=padding, bias=False
        )
        self.bn = BatchNorm2d(out_c)

    def forward(self, x):
        x = self.conv(x)
        x = self.bn(x)
        return x


class Depth_Wise(Module):
    def __init__(
        self, c1, c2, c3, residual=False, kernel=(3, 3), stride=(2, 2), padding=(1, 1), groups=1
    ):
        super().__init__()
        (c1_in, c1_out), (c2_in, c2_out), (c3_in, c3_out) = c1, c2, c3
        self.conv = Conv_block(c1_in, c1_out, (1, 1), (1, 1), (0, 0))
        self.conv_dw = Conv_block(c2_in, c2_out, groups=c2_in, kernel=kernel, padding=padding, stride=stride)
        self.project = Linear_block(c3_in, c3_out, (1, 1), (1, 1), (0, 0))
        self.residual = residual

    def forward(self, x):
        if self.residual:
            short_cut = x
        x = self.conv(x)
        x = self.conv_dw(x)
        x = self.project(x)
        if self.residual:
            output = short_cut + x
        else:
            output = x
        return output


class Residual(Module):
    def __init__(
        self, c1, c2, c3, num_block, groups, kernel=(3, 3), stride=(1, 1), padding=(1, 1)
    ):
        super().__init__()
        modules = []
        for i in range(num_block):
            modules.append(
                Depth_Wise(
                    c1[i], c2[i], c3[i],
                    residual=True, kernel=kernel, padding=padding, stride=stride, groups=groups,
                )
            )
        self.model = Sequential(*modules)

    def forward(self, x):
        return self.model(x)


class SEModule(Module):
    def __init__(self, channels, reduction):
        super().__init__()
        self.avg_pool = AdaptiveAvgPool2d(1)
        self.fc1 = Conv2d(channels, channels // reduction, kernel_size=1, padding=0, bias=False)
        self.bn1 = BatchNorm2d(channels // reduction)
        self.relu = ReLU(inplace=True)
        self.fc2 = Conv2d(channels // reduction, channels, kernel_size=1, padding=0, bias=False)
        self.bn2 = BatchNorm2d(channels)
        self.sigmoid = Sigmoid()

    def forward(self, x):
        module_input = x
        x = self.avg_pool(x)
        x = self.fc1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.fc2(x)
        x = self.bn2(x)
        x = self.sigmoid(x)
        return module_input * x


class Depth_Wise_SE(Module):
    def __init__(
        self, c1, c2, c3, residual=False, kernel=(3, 3), stride=(2, 2), padding=(1, 1), groups=1, se_reduct=8
    ):
        super().__init__()
        (c1_in, c1_out), (c2_in, c2_out), (c3_in, c3_out) = c1, c2, c3
        self.conv = Conv_block(c1_in, c1_out, (1, 1), (1, 1), (0, 0))
        self.conv_dw = Conv_block(c2_in, c2_out, groups=c2_in, kernel=kernel, padding=padding, stride=stride)
        self.project = Linear_block(c3_in, c3_out, (1, 1), (1, 1), (0, 0))
        self.residual = residual
        self.se_module = SEModule(c3_out, se_reduct)

    def forward(self, x):
        if self.residual:
            short_cut = x
        x = self.conv(x)
        x = self.conv_dw(x)
        x = self.project(x)
        if self.residual:
            x = self.se_module(x)
            output = short_cut + x
        else:
            output = x
        return output


class ResidualSE(Module):
    def __init__(
        self, c1, c2, c3, num_block, groups, kernel=(3, 3), stride=(1, 1), padding=(1, 1), se_reduct=4
    ):
        super().__init__()
        modules = []
        for i in range(num_block):
            if i == num_block - 1:
                modules.append(
                    Depth_Wise_SE(
                        c1[i], c2[i], c3[i], residual=True,
                        kernel=kernel, padding=padding, stride=stride, groups=groups, se_reduct=se_reduct,
                    )
                )
            else:
                modules.append(
                    Depth_Wise(c1[i], c2[i], c3[i], residual=True, kernel=kernel, padding=padding, stride=stride, groups=groups)
                )
        self.model = Sequential(*modules)

    def forward(self, x):
        return self.model(x)


class MiniFASNet(Module):
    def __init__(self, keep, embedding_size, conv6_kernel=(7, 7), drop_p=0.0, num_classes=3, img_channel=3):
        super().__init__()
        self.embedding_size = embedding_size
        self.conv1 = Conv_block(img_channel, keep[0], kernel=(3, 3), stride=(2, 2), padding=(1, 1))
        self.conv2_dw = Conv_block(keep[0], keep[1], kernel=(3, 3), stride=(1, 1), padding=(1, 1), groups=keep[1])
        c1, c2, c3 = [(keep[1], keep[2])], [(keep[2], keep[3])], [(keep[3], keep[4])]
        self.conv_23 = Depth_Wise(c1[0], c2[0], c3[0], kernel=(3, 3), stride=(2, 2), padding=(1, 1), groups=keep[3])
        c1 = [(keep[4], keep[5]), (keep[7], keep[8]), (keep[10], keep[11]), (keep[13], keep[14])]
        c2 = [(keep[5], keep[6]), (keep[8], keep[9]), (keep[11], keep[12]), (keep[14], keep[15])]
        c3 = [(keep[6], keep[7]), (keep[9], keep[10]), (keep[12], keep[13]), (keep[15], keep[16])]
        self.conv_3 = Residual(c1, c2, c3, 4, keep[4], (3, 3), (1, 1), (1, 1))
        c1, c2, c3 = [(keep[16], keep[17])], [(keep[17], keep[18])], [(keep[18], keep[19])]
        self.conv_34 = Depth_Wise(c1[0], c2[0], c3[0], kernel=(3, 3), stride=(2, 2), padding=(1, 1), groups=keep[19])
        c1 = [(keep[19], keep[20]), (keep[22], keep[23]), (keep[25], keep[26]), (keep[28], keep[29]), (keep[31], keep[32]), (keep[34], keep[35])]
        c2 = [(keep[20], keep[21]), (keep[23], keep[24]), (keep[26], keep[27]), (keep[29], keep[30]), (keep[32], keep[33]), (keep[35], keep[36])]
        c3 = [(keep[21], keep[22]), (keep[24], keep[25]), (keep[27], keep[28]), (keep[30], keep[31]), (keep[33], keep[34]), (keep[36], keep[37])]
        self.conv_4 = Residual(c1, c2, c3, 6, keep[19], (3, 3), (1, 1), (1, 1))
        c1, c2, c3 = [(keep[37], keep[38])], [(keep[38], keep[39])], [(keep[39], keep[40])]
        self.conv_45 = Depth_Wise(c1[0], c2[0], c3[0], kernel=(3, 3), stride=(2, 2), padding=(1, 1), groups=keep[40])
        c1 = [(keep[40], keep[41]), (keep[43], keep[44])]
        c2 = [(keep[41], keep[42]), (keep[44], keep[45])]
        c3 = [(keep[42], keep[43]), (keep[45], keep[46])]
        self.conv_5 = Residual(c1, c2, c3, 2, keep[40], (3, 3), (1, 1), (1, 1))
        self.conv_6_sep = Conv_block(keep[46], keep[47], (1, 1), (1, 1), (0, 0))
        self.conv_6_dw = Linear_block(keep[47], keep[48], groups=keep[48], kernel=conv6_kernel, stride=(1, 1), padding=(0, 0))
        self.conv_6_flatten = Flatten()
        self.linear = Linear(512, embedding_size, bias=False)
        self.bn = BatchNorm1d(embedding_size)
        self.drop = torch.nn.Dropout(p=drop_p)
        self.prob = Linear(embedding_size, num_classes, bias=False)

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2_dw(x)
        x = self.conv_23(x)
        x = self.conv_3(x)
        x = self.conv_34(x)
        x = self.conv_4(x)
        x = self.conv_45(x)
        x = self.conv_5(x)
        x = self.conv_6_sep(x)
        x = self.conv_6_dw(x)
        x = self.conv_6_flatten(x)
        if self.embedding_size != 512:
            x = self.linear(x)
            x = self.bn(x)
            x = self.drop(x)
        x = self.prob(x)
        return x


class MiniFASNetSE(MiniFASNet):
    def __init__(self, keep, embedding_size=128, conv6_kernel=(7, 7), drop_p=0.75, num_classes=4, img_channel=3):
        super().__init__(keep=keep, embedding_size=embedding_size, conv6_kernel=conv6_kernel, drop_p=drop_p, num_classes=num_classes, img_channel=img_channel)
        c1 = [(keep[4], keep[5]), (keep[7], keep[8]), (keep[10], keep[11]), (keep[13], keep[14])]
        c2 = [(keep[5], keep[6]), (keep[8], keep[9]), (keep[11], keep[12]), (keep[14], keep[15])]
        c3 = [(keep[6], keep[7]), (keep[9], keep[10]), (keep[12], keep[13]), (keep[15], keep[16])]
        self.conv_3 = ResidualSE(c1, c2, c3, 4, keep[4], (3, 3), (1, 1), (1, 1), 4)
        c1 = [(keep[19], keep[20]), (keep[22], keep[23]), (keep[25], keep[26]), (keep[28], keep[29]), (keep[31], keep[32]), (keep[34], keep[35])]
        c2 = [(keep[20], keep[21]), (keep[23], keep[24]), (keep[26], keep[27]), (keep[29], keep[30]), (keep[32], keep[33]), (keep[35], keep[36])]
        c3 = [(keep[21], keep[22]), (keep[24], keep[25]), (keep[27], keep[28]), (keep[30], keep[31]), (keep[33], keep[34]), (keep[36], keep[37])]
        self.conv_4 = ResidualSE(c1, c2, c3, 6, keep[19], (3, 3), (1, 1), (1, 1), 4)
        c1 = [(keep[40], keep[41]), (keep[43], keep[44])]
        c2 = [(keep[41], keep[42]), (keep[44], keep[45])]
        c3 = [(keep[42], keep[43]), (keep[45], keep[46])]
        self.conv_5 = ResidualSE(c1, c2, c3, 2, keep[40], (3, 3), (1, 1), (1, 1), 4)


KEEP_18M = [
    32, 32, 103, 103, 64, 13, 13, 64, 26, 26, 64, 13, 13, 64, 52, 52, 64, 231, 231, 128,
    154, 154, 128, 52, 52, 128, 26, 26, 128, 52, 52, 128, 26, 26, 128, 26, 26, 128, 308, 308,
    128, 26, 26, 128, 26, 26, 128, 512, 512,
]
KEEP_18M_ = [
    32, 32, 103, 103, 64, 13, 13, 64, 13, 13, 64, 13, 13, 64, 13, 13, 64, 231, 231, 128,
    231, 231, 128, 52, 52, 128, 26, 26, 128, 77, 77, 128, 26, 26, 128, 26, 26, 128, 308, 308,
    128, 26, 26, 128, 26, 26, 128, 512, 512,
]


def MiniFASNetV1(embedding_size=128, conv6_kernel=(7, 7), drop_p=0.2, num_classes=3, img_channel=3):
    return MiniFASNet(KEEP_18M, embedding_size, conv6_kernel, drop_p, num_classes, img_channel)


def MiniFASNetV2(embedding_size=128, conv6_kernel=(7, 7), drop_p=0.2, num_classes=3, img_channel=3):
    return MiniFASNet(KEEP_18M_, embedding_size, conv6_kernel, drop_p, num_classes, img_channel)


def MiniFASNetV1SE(embedding_size=128, conv6_kernel=(7, 7), drop_p=0.75, num_classes=3, img_channel=3):
    return MiniFASNetSE(KEEP_18M, embedding_size, conv6_kernel, drop_p, num_classes, img_channel)


def MiniFASNetV2SE(embedding_size=128, conv6_kernel=(7, 7), drop_p=0.75, num_classes=4, img_channel=3):
    return MiniFASNetSE(KEEP_18M_, embedding_size, conv6_kernel, drop_p, num_classes, img_channel)


MODEL_MAPPING = {
    "MiniFASNetV1": MiniFASNetV1,
    "MiniFASNetV2": MiniFASNetV2,
    "MiniFASNetV1SE": MiniFASNetV1SE,
    "MiniFASNetV2SE": MiniFASNetV2SE,
}
