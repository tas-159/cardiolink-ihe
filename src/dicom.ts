// Cornerstone.js setup for rendering DICOM files in the browser (a real
// client-side DICOM viewer). Uncompressed images decode without web workers.
import cornerstone from "cornerstone-core";
import cornerstoneMath from "cornerstone-math";
import cornerstoneTools from "cornerstone-tools";
import cornerstoneWADOImageLoader from "cornerstone-wado-image-loader";
import dicomParser from "dicom-parser";
import Hammer from "hammerjs";

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

  // Measurement / annotation tools (distance, angle, arrow).
  cornerstoneTools.external.cornerstone = cornerstone;
  cornerstoneTools.external.cornerstoneMath = cornerstoneMath;
  cornerstoneTools.external.Hammer = Hammer;
  cornerstoneTools.init({ showSVGCursors: true });
  // Tools are added per enabled element (see registerDicomTools), which is more
  // reliable than global addTool across element enable/disable cycles.

  configured = true;
}

export function studyImageId(reference: string): string {
  return `wadouri:${API_BASE}/studies/${encodeURIComponent(reference)}/file`;
}

// Add the measurement/annotation tools to a specific enabled element.
export function registerDicomTools(element: HTMLElement) {
  try {
    cornerstoneTools.addToolForElement(element, cornerstoneTools.LengthTool);
    cornerstoneTools.addToolForElement(element, cornerstoneTools.AngleTool);
    cornerstoneTools.addToolForElement(element, cornerstoneTools.ArrowAnnotateTool, {
      // Fixed label, so it never opens a blocking browser prompt.
      configuration: {
        getTextCallback: (cb: (t: string) => void) => cb("Repère"),
        changeTextCallback: (_d: unknown, _e: unknown, cb: (t: string) => void) => cb("Repère"),
      },
    });
  } catch {
    /* tools unavailable — viewer still works without annotations */
  }
}

export { cornerstone, cornerstoneTools };
