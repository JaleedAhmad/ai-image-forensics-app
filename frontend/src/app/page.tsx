"use client";
import { useState, useRef, useEffect } from "react";
import { analyzeImageStream } from "@/lib/api";
import ProviderStatusBar from "@/components/ProviderStatusBar";
import AgentConsensusPanel from "@/components/AgentConsensusPanel";
import JSZip from "jszip";
import { saveAs } from "file-saver";

export default function Home() {
  // Core State
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [liveSteps, setLiveSteps] = useState<any[]>([]);
  const [exporting, setExporting] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // V6.0 Interactive Features State
  const [cooldown, setCooldown] = useState(0);
  const [sliderPos, setSliderPos] = useState(50);
  const [selectedOverlay, setSelectedOverlay] = useState<string | null>(null);
  const [zoom, setZoom] = useState({ scale: 1, x: 0, y: 0 });
  const [caseId, setCaseId] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const sliderRef = useRef<HTMLDivElement>(null);

  const scanSteps = [
    "Initializing Neural Pipeline...",
    "Extracting High-Res Quadrants...",
    "Generating ELA Heatmaps (20x)...",
    "Super-Zooming Corner Watermark Zone...",
    "Running Canny Edge Geometry Scan...",
    "Applying Universal Forensic Logic...",
    "Finalizing Integrity Report...",
  ];

  // Cooldown Timer Logic
  useEffect(() => {
    if (cooldown > 0) {
      const timer = setInterval(() => setCooldown((c) => c - 1), 1000);
      return () => clearInterval(timer);
    }
  }, [cooldown]);

  // Removed old fake Scanning Animation Logic

  // Bounding Box Logic
  useEffect(() => {
    if (result && imageRef.current && canvasRef.current) {
      drawBoundingBoxes();
    }
  }, [result, zoom]);

  const drawBoundingBoxes = () => {
    const canvas = canvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img || !result) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Reset canvas to image size and clear previous boxes
    canvas.width = img.clientWidth;
    canvas.height = img.clientHeight;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!result || !result.detailed_findings) return;

    result.detailed_findings.forEach((finding: any) => {
      if (finding.location_normalized) {
        const [ymin, xmin, ymax, xmax] = finding.location_normalized;
        const x = (xmin / 1000) * canvas.width;
        const y = (ymin / 1000) * canvas.height;
        const width = ((xmax - xmin) / 1000) * canvas.width;
        const height = ((ymax - ymin) / 1000) * canvas.height;

        ctx.strokeStyle = "#ef4444";
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 3]);
        ctx.strokeRect(x, y, width, height);

        ctx.fillStyle = "rgba(239, 68, 68, 0.8)";
        ctx.fillRect(x, y - 18, 90, 18);
        ctx.fillStyle = "white";
        ctx.font = "bold 9px monospace";
        ctx.fillText("FORENSIC HIT", x + 5, y - 5);
      }
    });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setPreviewUrl(URL.createObjectURL(selectedFile));
      setResult(null);
      setCaseId(null);
      setLiveSteps([]);
      setSelectedOverlay(null);
      resetZoom();
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selectedFile = e.dataTransfer.files[0];
      setFile(selectedFile);
      setPreviewUrl(URL.createObjectURL(selectedFile));
      setResult(null);
      setCaseId(null);
      setLiveSteps([]);
      setSelectedOverlay(null);
      resetZoom();
    }
  };

  const handleUpload = async () => {
    if (!file || cooldown > 0) return;
    setLoading(true);
    setError("");
    setResult(null);
    setLiveSteps([]);

    try {
      await analyzeImageStream(
        file,
        (step) => setLiveSteps((prev) => [...prev, step]),
        (data) => {
          // Adapt new multi-agent format to support legacy UI features (bounding boxes, slider)
          const detailed_findings: any[] = [];
          const all_findings = [
            ...(data.agent_a_report?.findings || []),
            ...(data.agent_b_report?.findings || []),
          ];
          all_findings.forEach((f: any) => {
            if (f.location) {
              const xmin = f.location.x * 1000;
              const ymin = f.location.y * 1000;
              const xmax = (f.location.x + f.location.w) * 1000;
              const ymax = (f.location.y + f.location.h) * 1000;
              detailed_findings.push({
                description: f.description,
                location_normalized: [ymin, xmin, ymax, xmax],
              });
            } else {
              detailed_findings.push({ description: f.description });
            }
          });

          const enhancedData = {
            ...data,
            detailed_findings,
            confidence_level: `${Math.round((data.confidence || 0) * 100)}%`,
            explanation: data.arbitrator_reasoning || "Reasoning complete.",
          };

          setResult(enhancedData);
          if (enhancedData.case_id) {
            setCaseId(enhancedData.case_id);
          } else {
            setCaseId(
              `${enhancedData.verdict.substring(0, 4)}-${Math.floor(Math.random() * 9000) + 1000}`,
            );
          }
          if (enhancedData.evidence_images?.length > 0) {
            setSelectedOverlay(enhancedData.evidence_images[0].url);
          }
          setLoading(false);
        },
        (errMsg) => {
          if (errMsg.includes("429")) {
            setError("QUOTA EXHAUSTED: System entering cooldown protocol.");
            setCooldown(60);
          } else {
            setError(errMsg || "Forensic Error: Check data link.");
          }
          setLoading(false);
        },
      );
    } catch (err: any) {
      setError("Initialization Error. Check console.");
      setLoading(false);
    }
  };

  const handleFindingClick = (finding: any) => {
    if (!finding.location_normalized) return;
    const [ymin, xmin, ymax, xmax] = finding.location_normalized;

    // Calculate center and zoom
    const centerX = (xmin + xmax) / 2;
    const centerY = (ymin + ymax) / 2;

    // Set zoom state
    setZoom({
      scale: 3,
      x: (500 - centerX) * 0.5, // Relative movement
      y: (500 - centerY) * 0.5,
    });
  };

  const resetZoom = () => setZoom({ scale: 1, x: 0, y: 0 });

  const handleExport = async () => {
    setExporting(true);
    try {
      const html2pdf = (await import("html2pdf.js")).default;
      const element = document.getElementById("report-template");
      if (!element) throw new Error("Report template not found");

      element.classList.remove("hidden");

      const opt: any = {
        margin: 10,
        filename: `Forensic-Case-${caseId}.pdf`,
        image: { type: "jpeg", quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
      };

      await html2pdf().set(opt).from(element).save();

      element.classList.add("hidden");
    } catch (e) {
      console.error("PDF Export failed", e);
    } finally {
      setExporting(false);
    }
  };

  const handleDownloadZip = async () => {
    if (!result) return;
    try {
      const zip = new JSZip();

      // Add JSON report
      zip.file(`Case_${caseId}_Report.json`, JSON.stringify(result, null, 2));

      // Download and add Original Image if available
      if (result.original_image_url) {
        try {
          const res = await fetch(result.original_image_url);
          const blob = await res.blob();
          zip.file(`Case_${caseId}_Original.jpg`, blob);
        } catch (e) {
          console.error("Failed to download original image", e);
        }
      }

      // Download and add all evidence images
      if (result.evidence_images) {
        const evidenceFolder = zip.folder("Evidence_Maps");
        for (let i = 0; i < result.evidence_images.length; i++) {
          const img = result.evidence_images[i];
          try {
            const res = await fetch(img.url);
            const blob = await res.blob();
            // Sanitize filename
            const safeName = img.name.replace(/[^a-z0-9]/gi, "_").toLowerCase();
            evidenceFolder?.file(`${safeName}.jpg`, blob);
          } catch (e) {
            console.error(`Failed to download evidence image ${img.name}`, e);
          }
        }
      }

      const content = await zip.generateAsync({ type: "blob" });
      saveAs(content, `Neural_Forensics_Archive_${caseId}.zip`);
    } catch (e) {
      console.error("ZIP Generation Failed", e);
    }
  };

  return (
    <main className="min-h-screen p-4 md:p-8 bg-slate-950 text-slate-200 font-sans selection:bg-cyan-500/30 print:bg-white print:text-black">
      <div className="max-w-6xl mx-auto">
        {/* Header Unit */}
        <header className="flex flex-col md:flex-row justify-between items-center mb-12 border-b border-slate-800 pb-8 print:border-black print:mb-4">
          <div>
            <h1 className="text-4xl md:text-5xl font-black italic tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-600 mb-2 print:text-black print:bg-none">
              NEURAL FORENSICS V6.0
            </h1>
            <div className="flex flex-col gap-3">
              <p className="text-slate-500 font-mono text-xs tracking-widest uppercase flex items-center print:text-slate-800">
                <span className="w-2 h-2 bg-emerald-500 rounded-full mr-2 animate-pulse print:hidden"></span>
                SECURE INTERROGATION SUITE // {new Date().toLocaleDateString()}
              </p>
              <ProviderStatusBar />
            </div>
          </div>
          <div className="mt-6 md:mt-0 flex gap-4 print:hidden">
            {result && (
              <div className="flex gap-4">
                <button
                  onClick={handleDownloadZip}
                  className="px-6 py-2 border border-slate-700 rounded-full font-mono text-[10px] hover:bg-slate-800 transition-colors uppercase tracking-widest text-slate-300 flex items-center"
                >
                  <svg
                    className="w-3 h-3 mr-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                    ></path>
                  </svg>{" "}
                  Download Archive
                </button>
                <button
                  onClick={handleExport}
                  disabled={exporting}
                  className={`px-6 py-2 border border-slate-700 rounded-full font-mono text-[10px] uppercase tracking-widest transition-colors flex items-center ${
                    exporting
                      ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                      : "hover:bg-slate-800 text-white"
                  }`}
                >
                  {exporting ? (
                    <>
                      <svg
                        className="animate-spin -ml-1 mr-2 h-3 w-3 text-cyan-500"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>{" "}
                      Generating...
                    </>
                  ) : (
                    "Export PDF"
                  )}
                </button>
              </div>
            )}
            <div className="text-right font-mono text-[10px] text-slate-600 space-y-1 invisible md:visible">
              <p>LATENCY: 38MS</p>
              <p>SIGNATURE: VERIFIED</p>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
          {/* LEFT: Interrogation Booth */}
          <section className="lg:col-span-5 space-y-8 print:hidden">
            <div className="bg-slate-900/50 border border-slate-800 p-6 md:p-8 rounded-3xl shadow-2xl backdrop-blur-sm relative transition-all">
              {/* Visual Interrogation Area */}
              <div
                className={`relative bg-slate-900/50 border-2 rounded-3xl overflow-hidden aspect-square flex items-center justify-center transition-all ${
                  isDragging
                    ? "border-cyan-500 bg-cyan-950/20 shadow-[0_0_30px_rgba(6,182,212,0.2)]"
                    : "border-slate-800"
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                {previewUrl ? (
                  <div
                    className="w-full h-full relative transition-transform duration-500 ease-in-out"
                    style={{
                      transform: `scale(${zoom.scale}) translate(${zoom.x}px, ${zoom.y}px)`,
                    }}
                  >
                    {/* Background Layer (Forensic Map) */}
                    {selectedOverlay && (
                      <img
                        src={selectedOverlay}
                        className="absolute inset-0 w-full h-full object-contain"
                        alt="Evidence Overlay"
                      />
                    )}

                    {/* Foreground Layer (Original) */}
                    <div
                      className="absolute inset-0 w-full h-full overflow-hidden"
                      style={{ clipPath: `inset(0 ${100 - sliderPos}% 0 0)` }}
                    >
                      <img
                        ref={imageRef}
                        src={previewUrl}
                        alt="Source Evidence"
                        className="w-full h-full object-contain bg-slate-950"
                        onLoad={drawBoundingBoxes}
                      />
                    </div>

                    <canvas
                      ref={canvasRef}
                      className="absolute top-0 left-0 w-full h-full pointer-events-none opacity-80"
                    />
                  </div>
                ) : (
                  <div className="text-center p-8 pointer-events-none">
                    <svg
                      className={`w-16 h-16 mx-auto mb-4 transition-colors ${isDragging ? "text-cyan-400" : "text-slate-700"}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="1"
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                      ></path>
                    </svg>
                    <p
                      className={`font-mono text-[10px] tracking-widest uppercase transition-colors ${isDragging ? "text-cyan-400 font-bold" : "text-slate-500"}`}
                    >
                      {isDragging
                        ? "Drop Evidence Here"
                        : "AWAITING VISUAL EVIDENCE"}
                    </p>
                    <p className="text-slate-600 text-[9px] mt-2 font-mono uppercase tracking-widest">
                      Drag & Drop or use button below
                    </p>
                  </div>
                )}

                {/* Slider Handle */}
                {previewUrl && selectedOverlay && (
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none overflow-hidden">
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={sliderPos}
                      onChange={(e) => setSliderPos(Number(e.target.value))}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize z-20 pointer-events-auto"
                    />
                    <div
                      className="absolute h-full w-0.5 bg-cyan-400 shadow-[0_0_10px_cyan] flex items-center justify-center z-10"
                      style={{ left: `${sliderPos}%` }}
                    >
                      <div className="w-6 h-10 bg-slate-900 border border-cyan-400 rounded-md flex flex-col items-center justify-center gap-1 transition-colors">
                        <div className="w-0.5 h-3 bg-cyan-400/50"></div>
                        <div className="w-0.5 h-3 bg-cyan-400/50"></div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Reset Zoom Button */}
                {zoom.scale > 1 && (
                  <button
                    onClick={resetZoom}
                    className="absolute bottom-4 right-4 bg-red-600/80 hover:bg-red-600 text-[9px] font-black uppercase px-3 py-1 rounded-full text-white backdrop-blur-md"
                  >
                    Reset Zoom
                  </button>
                )}
              </div>

              {/* Input Controls */}
              <div className="mt-8 space-y-4">
                <input
                  type="file"
                  id="forensic-input"
                  className="hidden"
                  onChange={handleFileChange}
                  disabled={loading}
                />
                <div className="flex gap-4">
                  <label
                    htmlFor="forensic-input"
                    className="flex-1 text-center py-4 rounded-xl border border-slate-700 bg-slate-800/50 text-slate-400 font-bold cursor-pointer hover:bg-slate-700 transition-colors tracking-widest text-[10px] uppercase"
                  >
                    {file ? "Replace Subject" : "Load Evidence"}
                  </label>

                  <button
                    onClick={handleUpload}
                    disabled={!file || loading || cooldown > 0}
                    className={`flex-[2] py-4 rounded-xl font-black uppercase text-xs tracking-[0.2em] transition-all shadow-xl active:scale-95 flex items-center justify-center group ${
                      cooldown > 0
                        ? "bg-red-950/20 text-red-500 border border-red-900/50"
                        : "bg-cyan-600 text-white hover:bg-cyan-500"
                    }`}
                  >
                    {loading ? (
                      <span className="flex items-center">
                        <svg
                          className="animate-spin h-3 w-3 mr-3 text-white"
                          viewBox="0 0 24 24"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                          ></circle>
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                          ></path>
                        </svg>
                        ANALYZING...
                      </span>
                    ) : cooldown > 0 ? (
                      `Engine Cool-down: ${cooldown}s`
                    ) : (
                      "Initiate Deep Scan"
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Fake Progress Log Removed - Replaced by Live Stream */}

            {error && (
              <div className="bg-red-950/20 border border-red-900/50 p-4 rounded-xl flex items-center text-red-500 text-[10px] font-mono">
                <span className="mr-3 text-lg opacity-50">!</span> {error}
              </div>
            )}
          </section>

          {/* RIGHT: Intelligence Report */}
          <section className="lg:col-span-7 space-y-12">
            {!result && !loading && liveSteps.length === 0 && (
              <div className="h-full hidden md:flex items-center justify-center border border-dashed border-slate-900 rounded-3xl p-12 text-center opacity-20">
                <div className="space-y-6">
                  <div className="relative inline-block">
                    <div className="absolute inset-0 bg-cyan-500/20 blur-2xl rounded-full"></div>
                    <svg
                      className="w-24 h-24 relative text-cyan-500"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="0.5"
                        d="M9.75 17L9 21h6l-.75-4M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                      ></path>
                    </svg>
                  </div>
                  <p className="text-xs font-mono tracking-[0.3em] uppercase">
                    Neural Interrogator Idle
                  </p>
                </div>
              </div>
            )}

            {/* LIVE REASONING STREAM */}
            {liveSteps.length > 0 && (
              <div className="space-y-6 animate-in fade-in duration-500">
                <h3 className="text-[10px] font-black text-cyan-500 uppercase tracking-[0.3em] flex items-center px-2">
                  <span className="w-2 h-0.5 bg-cyan-500 mr-4 shadow-[0_0_5px_cyan]"></span>
                  Investigation Reasoning Chain
                </h3>
                <div className="space-y-4">
                  {liveSteps.map((step: any, idx: number) => (
                    <div
                      key={idx}
                      className="bg-slate-900/40 border border-slate-800 p-4 rounded-xl font-mono text-[11px] relative overflow-hidden group animate-in slide-in-from-right-4 fade-in duration-300"
                    >
                      <div className="absolute top-0 left-0 w-1 h-full bg-cyan-500/30 group-hover:bg-cyan-500 transition-colors"></div>
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-cyan-400 font-bold uppercase tracking-tighter">
                          Step 0{idx + 1}: {step.stage.replace(/_/g, " ")}
                        </span>
                        <span className="text-slate-600 text-[9px] uppercase">
                          Interrogator_Logic
                        </span>
                      </div>
                      <p className="text-slate-300 italic mb-2">
                        "{step.message}"
                      </p>
                    </div>
                  ))}
                  {loading && (
                    <div className="flex items-center text-[10px] text-cyan-500 font-mono px-4 space-x-2">
                      <span className="animate-pulse">
                        _Awaiting neural response
                      </span>
                      <span className="flex space-x-1 items-end h-3">
                        <span
                          className="animate-bounce w-1 h-1 bg-cyan-500 rounded-full"
                          style={{ animationDelay: "0ms" }}
                        ></span>
                        <span
                          className="animate-bounce w-1 h-1 bg-cyan-500 rounded-full"
                          style={{ animationDelay: "150ms" }}
                        ></span>
                        <span
                          className="animate-bounce w-1 h-1 bg-cyan-500 rounded-full"
                          style={{ animationDelay: "300ms" }}
                        ></span>
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {(loading || result) && (
              <div className="mb-10">
                <AgentConsensusPanel
                  agentAReport={result?.agent_a_report || null}
                  agentBReport={result?.agent_b_report || null}
                  finalVerdict={result}
                  streamingStage={
                    liveSteps.length > 0
                      ? liveSteps[liveSteps.length - 1].stage
                      : ""
                  }
                />
              </div>
            )}

            {result && (
              <div className="animate-in fade-in fill-mode-both duration-1000 space-y-10">
                {/* EVIDENCE GALLERY / SLIDER SELECTOR */}
                <div className="space-y-6">
                  <div className="flex justify-between items-end px-2">
                    <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                      Forensic Evidence Grid
                    </h3>
                    <span className="text-[8px] text-slate-700 italic lowercase print:hidden">
                      Select a map for comparison slider
                    </span>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 print:grid-cols-2">
                    {result.evidence_images?.map((img: any, idx: number) => (
                      <button
                        key={idx}
                        onClick={() => setSelectedOverlay(img.url)}
                        className={`group relative aspect-square bg-slate-900 rounded-2xl overflow-hidden border transition-all ${
                          selectedOverlay === img.url
                            ? "border-cyan-500 ring-2 ring-cyan-500/20 scale-105"
                            : "border-slate-800 hover:border-slate-600"
                        }`}
                      >
                        <img
                          src={img.url}
                          alt={img.name}
                          className="w-full h-full object-cover grayscale opacity-60 group-hover:opacity-100 group-hover:grayscale-0 transition-opacity"
                        />
                        <div className="absolute inset-x-0 bottom-0 bg-black/80 backdrop-blur-sm p-2 transform transition-transform text-[8px] font-mono text-cyan-500 uppercase flex justify-between items-center">
                          <span className="truncate mr-1">{img.name}</span>
                          {selectedOverlay === img.url && (
                            <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-pulse shadow-[0_0_5px_cyan]"></span>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* AGENT REASONING CHAIN REMOVED FROM HERE - RENDERED ABOVE */}

                {/* INTERACTIVE FINDINGS */}
                <div className="space-y-5 print:mt-10">
                  <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-2">
                    Anomalous Artifacts Detected
                  </h3>
                  <div className="grid grid-cols-1 gap-3">
                    {result.detailed_findings?.map(
                      (finding: any, idx: number) => {
                        const isInteractive = !!finding.location_normalized;
                        return (
                          <div
                            key={idx}
                            onClick={() =>
                              isInteractive && handleFindingClick(finding)
                            }
                            className={`flex items-center justify-between bg-slate-900/40 border border-slate-800 p-5 rounded-2xl text-left w-full print:border-slate-200 ${isInteractive ? "group hover:bg-slate-900/60 hover:border-cyan-500/30 transition-all cursor-pointer" : "cursor-default"}`}
                          >
                            <div className="flex items-center">
                              <div
                                className={`w-8 h-8 rounded-lg bg-slate-950 flex items-center justify-center mr-5 border border-slate-800 ${isInteractive ? "group-hover:border-cyan-500/50" : ""}`}
                              >
                                <span
                                  className={`text-[9px] font-black text-slate-600 ${isInteractive ? "group-hover:text-cyan-500" : ""}`}
                                >
                                  0{idx + 1}
                                </span>
                              </div>
                              <span
                                className={`text-xs font-mono text-slate-300 transition-colors ${isInteractive ? "group-hover:text-white" : ""}`}
                              >
                                {finding.description}
                              </span>
                            </div>
                            <div className="flex items-center gap-4">
                              {isInteractive && (
                                <>
                                  <span className="text-[8px] font-mono text-slate-600 bg-slate-950 px-2 py-1 rounded-md tracking-tighter shrink-0">
                                    HIT @ [
                                    {finding.location_normalized
                                      .map((n: number) => Math.round(n))
                                      .join(",")}
                                    ]
                                  </span>
                                  <span className="text-[10px] text-cyan-600 opacity-0 group-hover:opacity-100 transition-opacity font-bold uppercase tracking-tighter hidden md:inline">
                                    Inspect →
                                  </span>
                                </>
                              )}
                            </div>
                          </div>
                        );
                      },
                    )}
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>

        {/* Global Stats Footer */}
        <footer className="mt-24 pt-8 border-t border-slate-900 text-[9px] font-mono text-slate-700 flex flex-col md:flex-row justify-between items-center uppercase tracking-[0.4em] gap-6 print:text-black print:border-black print:mt-12">
          <div className="flex gap-10">
            <span className="flex items-center">
              <span className="w-1.5 h-1.5 bg-emerald-900 rounded-full mr-2"></span>
              Node_active
            </span>
            <span>Auth_Session: 8829-X</span>
            <span className="hidden md:inline">Precision_Gate: 0.9997</span>
          </div>
          <div className="italic text-slate-800 font-black">
            &copy; 2026 NEURAL INTERROGATOR // V6.0 SUITE
          </div>
        </footer>
      </div>

      {/* Hidden Print Template for html2pdf.js */}
      {result && (
        <div
          id="report-template"
          className="hidden p-8 font-sans w-[800px]"
          style={{ backgroundColor: "#ffffff", color: "#000000" }}
        >
          <div
            className="border-b-4 pb-4 mb-8 flex justify-between items-end"
            style={{ borderColor: "#000000" }}
          >
            <div>
              <h1 className="text-4xl font-black italic tracking-tighter uppercase">
                Neural Forensics
              </h1>
              <p className="text-xs font-mono font-bold mt-1 tracking-widest">
                OFFICIAL CASE REPORT
              </p>
            </div>
            <div className="text-right font-mono text-xs">
              <p>ID: {caseId}</p>
              <p>DATE: {new Date().toLocaleDateString()}</p>
            </div>
          </div>

          <div className="flex gap-8 mb-8">
            <div className="w-1/2">
              <div
                className="border-2 aspect-square flex items-center justify-center p-2"
                style={{ backgroundColor: "#f1f5f9", borderColor: "#000000" }}
              >
                <img
                  src={previewUrl!}
                  className="max-w-full max-h-full object-contain"
                />
              </div>
              <p className="text-center font-mono text-[10px] mt-2 font-bold">
                EXHIBIT A: SOURCE IMAGE
              </p>
            </div>
            <div className="w-1/2 flex flex-col justify-center">
              <div className="mb-6">
                <p
                  className="text-[10px] font-mono font-bold uppercase tracking-widest border-b mb-2"
                  style={{ color: "#64748b", borderColor: "#cbd5e1" }}
                >
                  Final Verdict
                </p>
                <h2 className="text-3xl font-black uppercase">
                  {result.verdict}
                </h2>
              </div>
              <div>
                <p
                  className="text-[10px] font-mono font-bold uppercase tracking-widest border-b mb-2"
                  style={{ color: "#64748b", borderColor: "#cbd5e1" }}
                >
                  Confidence
                </p>
                <h2 className="text-2xl font-bold uppercase">
                  {result.confidence_level}
                </h2>
              </div>
            </div>
          </div>

          <div className="mb-8">
            <h3
              className="text-sm font-black uppercase tracking-widest border-b-2 pb-2 mb-4"
              style={{ borderColor: "#000000" }}
            >
              Arbitrator Reasoning & Specialist Reports
            </h3>
            <p className="text-sm leading-relaxed text-justify mb-6">
              {result.arbitrator_reasoning || result.explanation}
            </p>

            <div className="grid grid-cols-2 gap-6">
              {result.agent_a_report && (
                <div
                  className="p-4 border"
                  style={{ backgroundColor: "#f8fafc", borderColor: "#e2e8f0" }}
                >
                  <h4
                    className="text-[10px] font-black uppercase tracking-widest mb-2 border-b pb-1"
                    style={{ borderColor: "#cbd5e1" }}
                  >
                    Compression Analyst
                  </h4>
                  <p className="text-xs italic mb-2">
                    Verdict:{" "}
                    {result.agent_a_report.preliminary_verdict.replace(
                      "_",
                      " ",
                    )}{" "}
                    ({Math.round(result.agent_a_report.confidence * 100)}%)
                  </p>
                  <ul className="text-[10px] list-disc pl-4 space-y-1 break-words">
                    {result.agent_a_report.findings
                      .slice(0, 3)
                      .map((f: any, i: number) => (
                        <li key={i}>{f.description}</li>
                      ))}
                  </ul>
                </div>
              )}

              {result.agent_b_report && (
                <div
                  className="p-4 border"
                  style={{ backgroundColor: "#f8fafc", borderColor: "#e2e8f0" }}
                >
                  <h4
                    className="text-[10px] font-black uppercase tracking-widest mb-2 border-b pb-1"
                    style={{ borderColor: "#cbd5e1" }}
                  >
                    Geometry Auditor
                  </h4>
                  <p className="text-xs italic mb-2">
                    Verdict:{" "}
                    {result.agent_b_report.preliminary_verdict.replace(
                      "_",
                      " ",
                    )}{" "}
                    ({Math.round(result.agent_b_report.confidence * 100)}%)
                  </p>
                  <ul className="text-[10px] list-disc pl-4 space-y-1 break-words">
                    {result.agent_b_report.findings
                      .slice(0, 3)
                      .map((f: any, i: number) => (
                        <li key={i}>{f.description}</li>
                      ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          <div>
            <h3
              className="text-sm font-black uppercase tracking-widest border-b-2 pb-2 mb-4"
              style={{ borderColor: "#000000" }}
            >
              Forensic Evidence Catalog
            </h3>
            <div className="grid grid-cols-2 gap-4">
              {result.evidence_images?.map((img: any, idx: number) => (
                <div
                  key={idx}
                  className="border p-2"
                  style={{ borderColor: "#cbd5e1" }}
                >
                  <div
                    className="aspect-square flex items-center justify-center mb-2"
                    style={{ backgroundColor: "#f1f5f9" }}
                  >
                    <img
                      src={img.url}
                      className="max-w-full max-h-full object-contain"
                    />
                  </div>
                  <p className="font-mono text-[9px] font-bold text-center uppercase">
                    {img.name}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
