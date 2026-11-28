"""Generate synthetic, uncompressed DICOM images so the PACS viewer has real
.dcm files to render. Replace server/dicom_store/<REF>.dcm with real studies
anytime — the viewer reads whatever is there.

The synthetic frame mimics a parasternal long-axis (PLAX) echocardiogram:
an ultrasound sector with dark blood-filled chambers, bright myocardial
walls and valve leaflets, depth attenuation and fine Rayleigh speckle.
It is illustrative only — not real patient data.
"""
import datetime
import io
import struct
import zlib

import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from .config import BASE_DIR

STORE = BASE_DIR / "dicom_store"

H = W = 576
# Bump when the synthetic image changes so previously generated .dcm files in a
# user's local store are detected as stale and regenerated on next access.
GEN_VERSION = "3"
GEN_TAG = f"cardiolink-gen-{GEN_VERSION}"
# Marker for a real DICOM a user imported — never overwritten by the generator.
UPLOAD_TAG = "cardiolink-upload"


def _gauss_blur(a: np.ndarray, sigma: float) -> np.ndarray:
    """Separable Gaussian blur (numpy only, fine for one-off generation)."""
    if sigma <= 0:
        return a
    radius = max(1, int(sigma * 3))
    xk = np.arange(-radius, radius + 1)
    k = np.exp(-(xk ** 2) / (2 * sigma ** 2))
    k /= k.sum()
    a = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 1, a)
    a = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 0, a)
    return a


def _ellipse(xx, yy, cx, cy, rx, ry, theta=0.0) -> np.ndarray:
    """Soft ellipse membership in [0,1] (1 inside, smooth edge)."""
    ct, st = np.cos(theta), np.sin(theta)
    xr = (xx - cx) * ct + (yy - cy) * st
    yr = -(xx - cx) * st + (yy - cy) * ct
    d = (xr / rx) ** 2 + (yr / ry) ** 2
    return 1.0 / (1.0 + np.exp(np.clip((d - 1.0) * 6.0, -60, 60)))


def _ridge(xx, yy, x0, y0, x1, y1, width) -> np.ndarray:
    """Bright ridge of given width along the segment (x0,y0)->(x1,y1)."""
    px, py = x1 - x0, y1 - y0
    L2 = px * px + py * py
    t = ((xx - x0) * px + (yy - y0) * py) / max(L2, 1e-6)
    t = np.clip(t, 0.0, 1.0)
    dx = xx - (x0 + t * px)
    dy = yy - (y0 + t * py)
    d2 = dx * dx + dy * dy
    return np.exp(-d2 / (2.0 * width ** 2))


def _synthetic_cardiac(seed: int) -> np.ndarray:
    """A plausible grayscale PLAX echo frame (not real patient data)."""
    rng = np.random.default_rng(seed)
    yy, xx = np.ogrid[:H, :W]
    yy = np.broadcast_to(yy, (H, W)).astype(np.float64)
    xx = np.broadcast_to(xx, (H, W)).astype(np.float64)

    cx = W / 2.0
    apex_y = 26.0
    r = np.sqrt((xx - cx) ** 2 + (yy - apex_y) ** 2)
    ang = np.arctan2(xx - cx, yy - apex_y)          # 0 = straight down
    half = 0.62
    r_min, r_max = 70.0, 540.0

    # --- soft tissue bed with depth-dependent gain (TGC) ---------------------
    depth = (r - r_min) / (r_max - r_min)
    tissue = 0.30 + 0.06 * np.cos(r / 26.0)
    tissue *= 0.75 + 0.45 * np.exp(-depth * 1.6)    # brighter near field

    # --- chambers (anechoic: pull brightness down) ---------------------------
    lv = _ellipse(xx, yy, cx - 34, 320, 96, 140, theta=-0.18)   # left ventricle
    la = _ellipse(xx, yy, cx + 74, 438, 78, 74, theta=0.0)      # left atrium
    rv = _ellipse(xx, yy, cx - 18, 168, 96, 60, theta=0.10)     # right ventricle
    ao = _ellipse(xx, yy, cx + 96, 268, 34, 86, theta=0.16)     # aortic root lumen
    chambers = np.clip(lv + la + rv + ao, 0, 1)
    tissue = tissue * (1.0 - 0.90 * chambers)

    # --- myocardial walls / septum / pericardium (echogenic: add) ------------
    walls = np.zeros((H, W))
    walls += 0.55 * _ridge(xx, yy, cx + 2, 232, cx - 78, 262, 7.0)   # IVS (septum)
    walls += 0.50 * _ridge(xx, yy, cx - 150, 356, cx - 28, 452, 9.0)  # posterior wall
    walls += 0.42 * _ridge(xx, yy, cx + 60, 206, cx + 132, 300, 6.0)  # ant. aortic wall
    walls += 0.40 * _ridge(xx, yy, cx + 112, 300, cx + 86, 388, 6.0)  # post. aortic wall
    # mitral + aortic valve leaflets (thin, bright, rooted near the walls)
    walls += 0.34 * _ridge(xx, yy, cx - 14, 300, cx + 34, 360, 2.6)
    walls += 0.30 * _ridge(xx, yy, cx + 70, 250, cx + 96, 296, 2.4)
    # pericardium: bright far-field arc
    peri = np.exp(-((r - 470) ** 2) / (2 * 10.0 ** 2)) * (np.abs(ang) < half * 0.9)
    walls += 0.35 * peri
    tissue = tissue + walls

    # --- Rayleigh speckle, multiplicative, finer in tissue than in blood -----
    speckle = rng.rayleigh(0.5, (H, W))
    speckle = _gauss_blur(speckle, 1.1)
    speckle /= speckle.mean()
    img = tissue * (0.55 + 0.55 * speckle)
    # chambers keep only faint swirl, not full speckle
    img = np.where(chambers > 0.5, tissue * (0.9 + 0.2 * (speckle - 1.0)), img)

    img = _gauss_blur(img, 0.9)

    # --- restrict to the ultrasound sector -----------------------------------
    sector = (np.abs(ang) < half) & (r > r_min) & (r < r_max)
    edge = _gauss_blur(sector.astype(np.float64), 2.0)
    img = img * edge + (1 - edge) * 0.012
    img = np.clip(img, 0.0, 1.0)

    # spread [0,1] across the stored range; windowing below matches this
    return (img * 65535).astype(np.uint16)


def ensure_dicom(reference: str, patient_name: str, description: str = "",
                 patient_id: str = "", issuer_oid: str = "") -> str:
    """Return the path to <reference>.dcm, generating it on first use.

    `reference` identifies the STUDY; `patient_id` is the patient's stable
    imaging-domain identifier (PACS domain, cross-referenced by PIX) and is
    shared by every study of that patient so a PACS can group them by patient.
    `issuer_oid` qualifies that id with its assigning authority (the PACS OID).
    """
    STORE.mkdir(parents=True, exist_ok=True)
    path = STORE / f"{reference}.dcm"
    if path.exists():
        try:
            head = pydicom.dcmread(str(path), stop_before_pixels=True)
            tag = getattr(head, "SoftwareVersions", "")
            # Keep the current synthetic image, and NEVER overwrite a real/
            # imported file (upload marker, or any non-synthetic DICOM).
            if tag == GEN_TAG or not tag.startswith("cardiolink-gen-"):
                return str(path)
        except Exception:
            pass
        # stale synthetic (older generator) or unreadable — regenerate preview too
        try:
            (STORE / f"{reference}.png").unlink()
        except OSError:
            pass

    pixels = _synthetic_cardiac(abs(hash(reference)) % 100000)

    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.UltrasoundImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid(entropy_srcs=[reference, "sop"])
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.PatientName = patient_name or "Anonyme"
    # Stable patient-level identifier (same across all this patient's studies),
    # qualified by its assigning authority — this is what groups studies by
    # patient in a PACS; falls back to the study reference if none is supplied.
    ds.PatientID = patient_id or reference
    if issuer_oid:
        ds.IssuerOfPatientID = issuer_oid
    ds.Modality = "US"
    ds.SoftwareVersions = GEN_TAG
    ds.StudyDescription = description or "Echocardiographie (synthetique)"
    ds.SeriesDescription = description or "Vue parasternale grand axe"
    # Deterministic per-study UIDs so a study keeps the same identity even
    # after the file is regenerated (study = one reference).
    ds.StudyInstanceUID = generate_uid(entropy_srcs=[reference, "study"])
    ds.SeriesInstanceUID = generate_uid(entropy_srcs=[reference, "series"])
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID

    ds.Rows, ds.Columns = pixels.shape
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    # window the full 16-bit span so the sector shows full grayscale contrast
    ds.WindowCenter = 28000
    ds.WindowWidth = 52000
    ds.PixelData = pixels.tobytes()

    now = datetime.datetime.now()
    ds.ContentDate = now.strftime("%Y%m%d")
    ds.ContentTime = now.strftime("%H%M%S")
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    ds.save_as(str(path))
    return str(path)


def save_uploaded_dicom(reference: str, data: bytes, patient_id: str,
                        patient_name: str, issuer_oid: str = "") -> str:
    """Store a DICOM file a user imported, and show it as this study's image.

    Raises ValueError if `data` is not a readable DICOM. The patient-level
    identity is rewritten to this app's PACS identifier so imported studies of
    the same patient still group together; the pixel data is kept untouched.
    """
    STORE.mkdir(parents=True, exist_ok=True)
    try:
        ds = pydicom.dcmread(io.BytesIO(data))
    except Exception as exc:  # not a DICOM / unreadable
        raise ValueError("Fichier DICOM invalide ou illisible") from exc

    ds.PatientID = patient_id or reference
    if issuer_oid:
        ds.IssuerOfPatientID = issuer_oid
    if patient_name:
        ds.PatientName = patient_name
    ds.SoftwareVersions = UPLOAD_TAG  # protects it from the generator

    path = STORE / f"{reference}.dcm"
    ds.save_as(str(path))
    try:
        (STORE / f"{reference}.png").unlink()  # force the preview to rebuild
    except OSError:
        pass
    return str(path)


def _write_png_gray(path: str, arr: np.ndarray) -> None:
    """Write an 8-bit grayscale PNG with the stdlib only (no Pillow)."""
    h, w = arr.shape
    raw = bytearray()
    for y in range(h):
        raw.append(0)                       # filter type 0 (none)
        raw.extend(arr[y].tobytes())

    def chunk(typ: bytes, data: bytes) -> bytes:
        body = typ + data
        return (struct.pack(">I", len(data)) + body
                + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
        f.write(chunk(b"IEND", b""))


def ensure_thumbnail(reference: str, patient_name: str, description: str = "",
                     patient_id: str = "", issuer_oid: str = "") -> str:
    """Return the path to a small windowed PNG preview of the study."""
    dcm = ensure_dicom(reference, patient_name, description, patient_id, issuer_oid)
    png = STORE / f"{reference}.png"
    if png.exists():
        return str(png)

    ds = pydicom.dcmread(dcm)
    px = ds.pixel_array.astype(np.float64)

    # Real DICOMs vary: take the first frame of a cine, and collapse colour.
    if px.ndim == 3 and px.shape[-1] in (3, 4):      # RGB / RGBA ultrasound
        px = px[..., :3].mean(axis=-1)
    while px.ndim > 2:                                # multi-frame -> first frame
        px = px[0]

    def _scalar(v, default):
        if v is None:
            return default
        try:
            return float(v[0] if isinstance(v, pydicom.multival.MultiValue) else v)
        except (TypeError, ValueError):
            return default

    wc = _scalar(ds.get("WindowCenter"), None)
    ww = _scalar(ds.get("WindowWidth"), None)
    if wc is None or ww is None or ww <= 0:
        lo, hi = float(px.min()), float(px.max())     # fall back to full range
    else:
        lo, hi = wc - ww / 2, wc + ww / 2
    disp = np.clip((px - lo) / max(hi - lo, 1.0), 0.0, 1.0)

    # Downsample to ~320 px on the long side (nearest-neighbour, any dimensions).
    long_side = max(disp.shape)
    step = max(1, long_side // 320)
    disp = disp[::step, ::step]
    _write_png_gray(str(png), (disp * 255).astype(np.uint8))
    return str(png)
