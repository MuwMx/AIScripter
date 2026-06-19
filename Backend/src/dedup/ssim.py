import torch
import torch.jit
import torch.nn.functional as F

@torch.jit.script
def create_window(window_size: int, sigma: float, channel: int):
    coords = torch.arange(window_size, dtype=torch.float)
    coords -= window_size // 2
    g = torch.exp(-(coords**2) / (2 * sigma**2))
    g /= g.sum()
    g = g.reshape(1, 1, 1, -1).repeat(channel, 1, 1, 1)
    return g

@torch.jit.script
def _gaussian_filter(x, window_1d, use_padding: bool):
    C = x.shape[1]
    padding = window_1d.shape[3] // 2 if use_padding else 0
    out = F.conv2d(x, window_1d, stride=1, padding=(0, padding), groups=C)
    out = F.conv2d(out, window_1d.transpose(2, 3), stride=1, padding=(padding, 0), groups=C)
    return out

@torch.jit.script
def ssim(X, Y, window, data_range: float, use_padding: bool = False):
    K1, K2 = 0.01, 0.03
    C1 = (K1 * data_range) ** 2
    C2 = (K2 * data_range) ** 2

    mu1 = _gaussian_filter(X, window, use_padding)
    mu2 = _gaussian_filter(Y, window, use_padding)
    sigma1_sq = _gaussian_filter(X * X, window, use_padding) - mu1.pow(2)
    sigma2_sq = _gaussian_filter(Y * Y, window, use_padding) - mu2.pow(2)
    sigma12 = _gaussian_filter(X * Y, window, use_padding) - (mu1 * mu2)

    cs_map = F.relu((2 * sigma12 + C2) / (sigma1_sq + sigma2_sq + C2))
    ssim_map = ((2 * mu1 * mu2 + C1) / (mu1.pow(2) + mu2.pow(2) + C1)) * cs_map

    return ssim_map.mean(dim=(1, 2, 3)), cs_map.mean(dim=(1, 2, 3))

class SSIM(torch.jit.ScriptModule):
    __constants__ = ["data_range", "use_padding"]

    def __init__(self, window_size=11, window_sigma=1.5, data_range=255.0, channel=3, use_padding=False):
        super().__init__()
        window = create_window(window_size, window_sigma, channel)
        self.register_buffer("window", window)
        self.data_range = data_range
        self.use_padding = use_padding

    @torch.jit.script_method
    def forward(self, X, Y):
        r = ssim(X, Y, window=self.window, data_range=self.data_range, use_padding=self.use_padding)
        return r[0]