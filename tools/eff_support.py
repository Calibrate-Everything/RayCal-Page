"""Unnormalized effective support (soft observations per control) from a result artifact, by the
solver's own construction: E_c = sum over retained observations of the cubic B-spline weights,
evaluated back at every pixel by the same basis. Uses the stored per-pixel observation counts."""
import os, sys, numpy as np, torch
sys.path.insert(0, os.path.join(os.environ['RAYCAL_ROOT'], 'code/Spherical-Calibration-combined/src'))  # RAYCAL_ROOT: local data root
from spherical_calibration.ray_fields.sparse_bspline import cubic_bspline_stencil

def effective(count, periodic, shape=(16, 16)):
    H, W = count.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    uv = torch.from_numpy(np.stack((2 * xx.ravel() / (W - 1) - 1, 2 * yy.ravel() / (H - 1) - 1), -1))
    kw = dict(boundary_mode='periodic_x', period=2.0 * W / (W - 1)) if periodic else dict(boundary_mode='replicate')
    idx, w = cubic_bspline_stencil(uv, *shape, **kw)
    c = torch.from_numpy(count.ravel().astype(np.float64))
    E = torch.zeros(shape[0] * shape[1], dtype=torch.float64)
    E.scatter_add_(0, idx.reshape(-1), (w * c[:, None]).reshape(-1))
    eff = (w * E[idx]).sum(-1).clamp_min(0).numpy().reshape(H, W)
    return eff, E.numpy()
