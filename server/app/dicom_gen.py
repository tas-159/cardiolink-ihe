"""Generate synthetic, uncompressed DICOM images so the PACS viewer has real
.dcm files to render. Replace server/dicom_store/<REF>.dcm with real studies
anytime — the viewer reads whatever is there."""
import datetime

import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from .config import BASE_DIR

STORE = BASE_DIR / "dicom_store"


def _synthetic_cardiac(seed: int) -> np.ndarray:
    """A plausible grayscale echo-like frame (not real patient data)."""
    rng = np.random.default_rng(seed)
    h = w = 512
    y, x = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2 + 40
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

    # ultrasound sector cone
    angle = np.arctan2(x - cx, y - cy)
    cone = (np.abs(angle) < 0.62) & (r < 300) & (r > 20)

    img = 70 + 70 * np.cos(r / 24) * np.exp(-r / 230)
    # a brighter myocardium ring + a dark chamber
    ring = 80 * np.exp(-((r - 150) ** 2) / (2 * 34 ** 2))
    chamber = -55 * np.exp(-((x - cx + 40) ** 2 + (y - cy) ** 2) / (2 * 70 ** 2))
    img = img + ring + chamber
    img = img + rng.normal(0, 13, (h, w))  # speckle

    img = np.where(cone, img, 6 + rng.normal(0, 3, (h, w)))
    img = np.clip(img, 0, 255)
    return (img * 257).astype(np.uint16)  # spread into 16-bit range


def ensure_dicom(reference: str, patient_name: str, description: str = "") -> str:
    """Return the path to <reference>.dcm, generating it on first use."""
    STORE.mkdir(parents=True, exist_ok=True)
    path = STORE / f"{reference}.dcm"
    if path.exists():
        return str(path)

    pixels = _synthetic_cardiac(abs(hash(reference)) % 100000)

    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.UltrasoundImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.PatientName = patient_name or "Anonyme"
    ds.PatientID = reference
    ds.Modality = "US"
    ds.StudyDescription = description or "Echocardiographie (synthetique)"
    ds.SeriesDescription = description or "Vue parasternale"
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID

    ds.Rows, ds.Columns = pixels.shape
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.WindowCenter = 32768
    ds.WindowWidth = 65536
    ds.PixelData = pixels.tobytes()

    now = datetime.datetime.now()
    ds.ContentDate = now.strftime("%Y%m%d")
    ds.ContentTime = now.strftime("%H%M%S")
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    ds.save_as(str(path))
    return str(path)
