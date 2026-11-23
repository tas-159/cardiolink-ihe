// Cornerstone.js setup for rendering DICOM files in the browser (a real
// client-side DICOM viewer). Uncompressed images decode without web workers.
import cornerstone from "cornerstone-core";
import cornerstoneWADOImageLoader from "cornerstone-wado-image-loader";
import dicomParser from "dicom-parser";

import { API_BASE, getToken } from "./api";

let configured = false;

export function initCornerstone() {
  if (configured) return;
  cornerstoneWADOImageLoader.external.cornerstone = cornerstone;
  cornerstoneWADOImageLoader.external.dicomParser = dicomParser;
  cornerstoneWADOImageLoader.configure({
    // Attach the JWT so the protected /studies/<ref>/file endpoint accepts us.
    beforeSend(xhr: XMLHttpRequest) {
      const token = getToken();
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    },
  });
  configured = true;
}

export function studyImageId(reference: string): string {
  return `wadouri:${API_BASE}/studies/${encodeURIComponent(reference)}/file`;
}

export { cornerstone };
