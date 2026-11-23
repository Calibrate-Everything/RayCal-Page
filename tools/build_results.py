"""Result strips for the project page: per sequence, 4 input frames, the GT ray sphere and ray map, the angular error
of the best baseline and of ours, and our support. One JPEG sprite per group and error style, plus meta.json.
Reads the reported runs. Usage: build_results.py OUT_DIR [WORKERS]"""
import collections, csv, glob, io, json, os, sys, tarfile
from multiprocessing import Pool
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.environ['RAYCAL_ROOT'], 'code/Spherical-Calibration-combined/src'))  # RAYCAL_ROOT: local data root
from spherical_calibration.visualization.bearing_error import bearing_error_rgb, bearing_error_legend, spherical_bearing_error
from spherical_calibration.visualization._render.sphere import sphere_view
import eff_support as S   # effective support (soft observations per control), as in the paper
ERR = dict(curve='asinh', soft_scale_deg=0.1, full_scale_deg=10.0)
G = os.environ['RAYCAL_ROOT']; T3 = f'{G}/psc-ocean/init-study/table3'; U5 = f'{G}/migcheck/formal/scale/U5R'  # reported runs
F = f'{G}/migcheck/formal'
PH = 140  # panel height (px)
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
# ---------- baseline records (same sources as the tables) ----------
def load(out, m):
    d = {}
    for f in glob.glob(f'{G}/baseline-runs/{out}/scores/{m}/*.json'):
        r = json.load(open(f)); d[r['case_id']] = r
    return d
MAIN = {'colmap': ['pool60'], 'geocalib': ['pool60'], 'unik3d': ['pool60'], 'anycalib': ['pool60'], 'wildcamera': ['pool60'],
        'droidcalib': ['pool60-droid-s2', 'pool60-droid-s2b'], 'gensfm': ['pool60-gensfm-kf', 'pool60-gensfm-kf3', 'pool60-gensfm-kf-u5'], 'prada': ['pool60-prada32']}
DIST = {'colmap': ['pool60-dist', 'pool60-dist-colmap-opencv', 'pool60-dist17', 'pool60-dist23'],
        'droidcalib': ['pool60-dist-droid-s2b', 'pool60-dist17-droid-s2b', 'pool60-dist23-droid-s2b'],
        'prada': ['pool60-dist-prada32', 'pool60-dist17-prada32', 'pool60-dist23-prada32'],
        'unik3d': ['pool60-dist-unik3d', 'pool60-dist17-unik3d', 'pool60-dist23-unik3d']}
def records(table):
    rec = collections.defaultdict(dict)
    for m, outs in table.items():
        for o in outs: rec[m].update(load(o, m))
    return rec
NAMES = {'colmap': 'COLMAP', 'gensfm': 'GenSfM', 'droidcalib': 'DroidCalib', 'prada': 'PRaDA', 'geocalib': 'GeoCalib',
         'wildcamera': 'WildCamera', 'anycalib': 'AnyCalib', 'unik3d': 'UniK3D'}
# ---------- case lists ----------
def man_csv(root): return list(csv.DictReader(open(f'{T3}/{root}/manifest.csv')))
def man_tsv(root):
    L = open(f'{T3}/{root}/manifest.tsv').read().splitlines(); h = L[0].split('\t')
    return [dict(zip(h, l.split('\t'))) for l in L[1:]]
groups = []  # (group_id, title, kind, [(case, root, seq_label)])
for gid, title, root, camf in [('euroc', 'EuRoC (pinhole)', 'euroc-pool60', None), ('tumvi', 'TUM-VI (fisheye)', 'tumvi-pool60', None),
                               ('kitti-pin', 'KITTI-360 pinhole', 'kitti360-pool60', ('image_00', 'image_01'))]:
    rows = [r for r in man_csv(root) if camf is None or r['camera'] in camf]
    groups.append((gid, title, 'main', [(r['case_id'], root, f"{r['camera']} / {r['trajectory'].replace('dataset-','').replace('_512_16','')}") for r in sorted(rows, key=lambda r: (r['trajectory'], r['camera']))]))
for cam, nm in [('pinhole-90', 'pinhole'), ('equisolid-180', 'fisheye'), ('erp-360x180', 'ERP')]:
    rows = [r for r in man_csv('tartanair-pool60') if r['camera'] == cam]
    groups.append((f'ta-{nm.lower()}', f'TartanAir V2 {nm}', 'main', [(r['case_id'], 'tartanair-pool60', r['trajectory']) for r in sorted(rows, key=lambda r: r['trajectory'])]))
    rows = [r for r in man_tsv('replica-clean') if r['camera'] == cam]
    groups.append((f're-{nm.lower()}', f'Replica {nm}', 'main', [(r['case_id'], 'replica-clean', r['scene']) for r in sorted(rows, key=lambda r: r['scene'])]))
CAMS = [('c004', 'Pinhole, radial, low'), ('c005', 'Pinhole, radial, high'), ('c006', 'Pinhole, tangential, low'), ('c007', 'Pinhole, tangential, high'),
        ('c008', 'Pinhole, radial + tangential, low'), ('c009', 'Pinhole, radial + tangential, high'), ('c010', 'Fisheye, radial, low'),
        ('c011', 'Fisheye, radial, high'), ('c012', 'Fisheye, tangential, low'), ('c013', 'Fisheye, tangential, high'),
        ('c014', 'Fisheye, radial + tangential, low'), ('c015', 'Fisheye, radial + tangential, high'), ('c016', 'Fisheye, multimodal radial density'),
        ('c019', 'Fisheye, non-radial shear'), ('c021', 'ERP, rotated'), ('c023', 'Catadioptric (UCM)')]
dist_cases = collections.defaultdict(list)
for root in ('tartanair-dist', 'tartanair-dist17', 'tartanair-dist23'):
    for r in man_csv(root): dist_cases[r['camera'].replace('bank-', '')].append((r['case_id'], root, 'TA ' + r['trajectory']))
for root in ('replica-dist', 'replica-dist17', 'replica-dist23'):
    for r in man_tsv(root): dist_cases[r['camera'].replace('bank-', '')].append((r['case_id'], root, 'RE ' + r['scene']))
for cam, lab in CAMS:
    groups.append((f'dist-{cam}', f'Distortion: {lab}', 'dist', sorted(dist_cases[cam], key=lambda x: x[2])))
# ---------- rendering ----------
import matplotlib; matplotlib.use('Agg'); from matplotlib import colormaps
CM = colormaps['magma']
def err_rgb(e, valid):
    t = np.clip((np.log10(np.clip(e, 1e-2, None)) + 2.0) / 3.0, 0, 1)   # 0.01 deg .. 10 deg, log scale
    rgb = (CM(t)[..., :3] * 255).astype(np.uint8); rgb[~valid] = 128; return rgb
def native(p):
    return np.stack((p[..., 2], -p[..., 0], -p[..., 1]), -1)
def bear_rgb(est_scorer, gt_scorer, valid):
    return bearing_error_rgb(native(est_scorer), native(gt_scorer), valid, **ERR)
def sphere_rgb(p, valid, H, W):
    stride = max(2, round(max(H, W) / 128))
    return sphere_view(native(p), valid, "front (+X)", size=240, stride=stride)
# Direction wheel of Schoeps et al. (CVPR 2020, Fig. 7 legend), sampled per degree on a circle of the legend image.
_LEG = np.asarray(Image.open(f'{G}/migcheck/figviz/schops-legend.jpg').convert('RGB')).astype(float)
_cy, _cx = (_LEG.shape[0] - 1) / 2, (_LEG.shape[1] - 1) / 2
_th = np.radians(np.arange(360))
WHEEL = np.stack([_LEG[np.clip(np.rint(_cy + r * np.sin(_th)).astype(int), 0, _LEG.shape[0] - 1),
                       np.clip(np.rint(_cx + r * np.cos(_th)).astype(int), 0, _LEG.shape[1] - 1)] for r in (70, 75, 80, 85)]).mean(0)
SCH_KNEE = 1.0  # degrees: saturation m / (m + knee), linear for small errors, compressed for large ones
def sch_sat(m):
    m = np.clip(np.nan_to_num(m), 0, None); return m / (m + SCH_KNEE)
def sch_inv(s):
    return SCH_KNEE * s / (1 - s)
def sch_rgb(est_scorer, gt_scorer, valid):
    comp, mag, defined = spherical_bearing_error(native(est_scorer), native(gt_scorer), valid)
    ang_img = np.degrees(np.arctan2(-np.nan_to_num(comp[..., 1]), np.nan_to_num(comp[..., 0]))) % 360   # image-down y as in the legend
    col = WHEEL[np.clip(np.rint(ang_img).astype(int) % 360, 0, 359)]
    sat = sch_sat(mag)[..., None]
    rgb = np.rint(128 + sat * (col - 128)).astype(np.uint8)
    rgb[~valid] = 255; return rgb
def sch_legend(size=220, rings=(0.25, 1.0, 3.0, 10.0)):
    yy, xx = np.mgrid[0:size, 0:size]; c = (size - 1) / 2; dx, dy = (xx - c) / c, (yy - c) / c
    r = np.hypot(dx, dy); a = np.degrees(np.arctan2(dy, dx)) % 360
    col = WHEEL[np.rint(a).astype(int) % 360]; sat = np.clip(r, 0, 1)[..., None]  # radius = saturation
    img = np.rint(128 + sat * (col - 128)).astype(np.uint8); img[r > 1] = 255
    im = Image.fromarray(img)
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    for t in rings:
        rr = c * float(sch_sat(np.array(t))); d.ellipse((c - rr, c - rr, c + rr, c + rr), outline=(255, 255, 255))
        d.text((c + rr * 0.72 + 2, c - rr * 0.72 - 12), f"{t:g}°", fill=(255, 255, 255))
    return im
def dir_rgb(p, valid):
    # same encoding as the camera-bank GT maps: native x-forward / y-left / z-up, RGB = (dir + 1) * 127.5
    native = np.stack((p[..., 2], -p[..., 0], -p[..., 1]), -1)
    rgb = np.rint((np.clip(native, -1, 1) + 1) * 127.5).astype(np.uint8); rgb[~valid] = 128; return rgb
BLUES = colormaps['Blues']
VIRIDIS = colormaps['viridis']
SUP_FULL = 300.0  # per-cell count at which the support colour saturates (about the 90th percentile)
SUP_STOPS = np.array([[0, 0, 0], [10, 40, 140], [30, 110, 230], [110, 200, 255]], float)
SUP_X = np.array([0.0, 1 / 3, 2 / 3, 1.0])
def sup_color(t):
    return np.stack([np.interp(t, SUP_X, SUP_STOPS[:, k]) for k in range(3)], -1)
def sup_rgb(count, valid, cell=16, full=SUP_FULL):
    # observations retained by the solve, summed over cell x cell pixel bins, log scale 0..full
    H, W = count.shape; hh, ww = -(-H // cell), -(-W // cell)
    pad = np.zeros((hh * cell, ww * cell)); pad[:H, :W] = count
    binned = pad.reshape(hh, cell, ww, cell).sum((1, 3))
    up = np.repeat(np.repeat(binned, cell, 0), cell, 1)[:H, :W]
    t = np.clip(np.log10(1 + up) / np.log10(1 + full), 0, 1)
    # black (no observation) -> dark blue -> blue -> sky blue (>= full observations)
    rgb = sup_color(t).astype(np.uint8)
    rgb[up == 0] = 0; rgb[~valid] = 255; return rgb
EFF_FULL = 1000.0  # soft observations per control at which the effective-support colour saturates
# Even lightness steps: 0 black, 1 navy (L* 19), 10 blue (L* 45), 100 cyan-blue (L* 69), >=1000 pale sky blue (L* 92).
EFF_X = np.log10(1 + np.array([0.0, 1.0, 10.0, 100.0, 1000.0])) / np.log10(1 + 1000.0)
EFF_STOPS = np.array([[0, 0, 0], [14, 32, 128], [22, 100, 222], [40, 182, 236], [196, 240, 255]], float)
def eff_color(t):
    return np.stack([np.interp(t, EFF_X, EFF_STOPS[:, k]) for k in range(3)], -1)
def eff_rgb(eff, valid, full=EFF_FULL):
    # unnormalized effective support of the B-spline field, log scale 0..full, smooth per pixel
    t = np.clip(np.log10(1 + np.maximum(eff, 0)) / np.log10(1 + full), 0, 1)
    rgb = eff_color(t).astype(np.uint8); rgb[~valid] = 255; return rgb
def panel(a):
    im = Image.fromarray(a); w = max(1, round(im.width * PH / im.height)); return im.resize((w, PH), Image.BILINEAR)
def kabsch(p, g, m):
    u, _, vt = np.linalg.svd(g[m].T @ p[m]); R = u @ vt
    if np.linalg.det(R) < 0: u[:, -1] *= -1; R = u @ vt
    return R
def ang(p, g): return np.degrees(np.arccos(np.clip((p * g).sum(-1), -1, 1)))
def render(case, root, kind):
    """Full-resolution panel arrays of one sequence (frames, GT ray sphere/map, error maps per style, support)."""
    meta = json.load(open(f'{T3}/{root}/blind/{case}/case.json')); H, W = int(meta['height']), int(meta['width'])
    z = np.load(f'{T3}/{root}/scorer/{case}/rays.npz'); g = z['rays'].reshape(H, W, 3).astype(float); sup = z['support'].reshape(H, W).astype(bool)
    tf = tarfile.open(f'{T3}/{root}/blind/{case}/images.tar'); names = sorted([m for m in tf.getmembers() if m.isfile()], key=lambda m: m.name)
    frames = []
    for k in np.linspace(0, len(names) - 1, 6)[1:5].round().astype(int):
        im = Image.open(tf.extractfile(names[k]))
        if im.mode in ('I;16', 'I;16B', 'I;16L', 'I'):
            a = np.asarray(im, dtype=np.float64); im = Image.fromarray(np.clip(a / (65535.0 if a.max() > 255 else 255.0) * 255, 0, 255).astype(np.uint8))
        frames.append(np.asarray(im.convert('RGB')))
    out = {'case': case}
    z2 = np.load(f'{U5}/{root}/{case}.npz'); r = z2['rays'].reshape(H, W, 3).astype(float)
    p = np.stack((-r[..., 1], -r[..., 2], r[..., 0]), -1); n = np.linalg.norm(p, axis=-1, keepdims=True); ok = np.isfinite(p).all(-1) & (n[..., 0] > 0)
    p = np.where(ok[..., None], p / np.where(n > 0, n, 1), 0.0); R = kabsch(p, g, sup & ok); pa = p @ R.T
    eo = np.where(ok, ang(pa, g), 180.0); vo = sup & ok
    cnt = z2['support_observation_count'].reshape(H, W).astype(float) if 'support_observation_count' in z2 else np.zeros((H, W))
    s = json.load(open(f'{U5}/{root}/{case}.score.json')); out['ours'] = [s.get('mean'), s.get('p90')]
    rec = REC[kind]; best = None
    for m in rec:
        x = rec[m].get(case)
        if x and x.get('status') == 'M' and x.get('Mean_deg') is not None and (best is None or x['Mean_deg'] < best[1]['Mean_deg']):
            best = (m, x)
    eb = None
    if best:
        rp = glob.glob(f"{best[1]['attempt_dir']}/run-*/cases/{case}/rays.npz")
        if rp:
            zb = np.load(rp[0]); pb = zb['rays'].reshape(H, W, 3).astype(float); vb = zb['valid'].reshape(H, W).astype(bool) & np.isfinite(pb).all(-1)
            nb = np.linalg.norm(pb, axis=-1, keepdims=True); pb = np.where(vb[..., None], pb / np.where(nb > 0, nb, 1), 0.0)
            Rb = kabsch(pb, g, sup & vb); eb = (pb @ Rb.T, sup & vb)
        out['best'] = [NAMES[best[0]], best[1]['Mean_deg'], best[1]['P90_deg']]
    gn = np.where(sup[..., None], g / np.maximum(np.linalg.norm(g, axis=-1, keepdims=True), 1e-12), 0.0)
    none = np.full((H, W, 3), 128, np.uint8)
    A = {'frames': frames, 'gt_sphere': sphere_rgb(gn, sup, H, W), 'gt_map': dir_rgb(gn, sup), 'support': eff_rgb(S.effective(cnt, W == 2 * H)[0], sup),
         'our_sphere': sphere_rgb(pa, vo, H, W), 'our_map': dir_rgb(pa, vo),  # ours after the scoring rotation
         'mag': (err_rgb(np.where(eb[1], ang(eb[0], g), 180.0), sup) if eb is not None else none, err_rgb(eo, sup)),
         'dir': (bear_rgb(eb[0], gn, eb[1]) if eb is not None else none, bear_rgb(pa, gn, vo)),
         'sch': (sch_rgb(eb[0], gn, eb[1]) if eb is not None else none, sch_rgb(pa, gn, vo))}
    return A, out
ORDER_GAPS = (3, 5, 7)  # extra space after the frames, the GT pair and the error pair
def job(item):
    gi, case, root, label, kind = item
    try:
        A, out = render(case, root, kind); out['label'] = label
        strips = []
        for style in ('sch',):   # the paper's error visualization (direction hue, magnitude saturation)
            panels = [panel(f) for f in A['frames']] + [panel(A['gt_sphere']), panel(A['gt_map']), panel(A[style][0]), panel(A[style][1]), panel(A['support'])]
            gap = 4; Wt = sum(q.width for q in panels) + gap * (len(panels) - 1) + 3 * gap * len(ORDER_GAPS)
            strip = Image.new('RGB', (Wt, PH), (255, 255, 255)); x = 0
            for i, q in enumerate(panels):
                strip.paste(q, (x, 0)); x += q.width + gap + (3 * gap if i in ORDER_GAPS else 0)
            strips.append(strip)
            out['widths'] = [q.width for q in panels]
        return gi, out, strips
    except Exception as ex:  # noqa: BLE001
        return gi, {'case': case, 'label': label, 'error': repr(ex)[:200]}, None
REC = {}
if __name__ == '__main__':
    REC['main'] = records(MAIN); REC['dist'] = records(DIST)
    items = [(gi, c, root, lab, kind) for gi, (gid, title, kind, cases) in enumerate(groups) for c, root, lab in cases]
    if os.environ.get('FIGVIZ_LIMIT'):
        keep = int(os.environ['FIGVIZ_LIMIT']); items = [it for it in items if it[0] in (0, 4, 6, len(groups) - 3)][:keep]
    with Pool(int(sys.argv[2]) if len(sys.argv) > 2 else 32) as pool:
        results = pool.map(job, items, chunksize=2)
    meta = []
    for gi, (gid, title, kind, cases) in enumerate(groups):
        res = [(o, s) for g2, o, s in results if g2 == gi]
        if not res: continue
        W = max([s[0].width for _, s in res if s is not None] + [10]); Hs = (PH + 8) * len(res)
        sprites = [Image.new('RGB', (W, Hs), (255, 255, 255))]; rows = []
        for i, (o, s) in enumerate(res):
            if s is not None:
                sprites[0].paste(s[0], (0, i * (PH + 8)))
            o['y'] = i * (PH + 8); rows.append(o)
        sprites[0].save(f'{OUT}/{gid}.jpg', quality=82, optimize=True)
        meta.append({'id': gid, 'title': title, 'kind': kind, 'width': W, 'height': Hs, 'ph': PH, 'rows': rows})
    json.dump(meta, open(f'{OUT}/meta.json', 'w'))
    print('done', sum(len(m['rows']) for m in meta), 'rows', sum(1 for m in meta for r in m['rows'] if 'error' in r), 'errors')
