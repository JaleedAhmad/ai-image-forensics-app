"use client";
import { useState, useRef, useEffect } from 'react';
import { analyzeImage } from '@/lib/api';

export default function Home() {
  // Core State
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [scanStep, setScanStep] = useState(0);
  
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
    "Finalizing Integrity Report..."
  ];

  // Cooldown Timer Logic
  useEffect(() => {
    if (cooldown > 0) {
      const timer = setInterval(() => setCooldown(c => c - 1), 1000);
      return () => clearInterval(timer);
    }
  }, [cooldown]);

  // Scanning Animation Logic
  useEffect(() => {
    let interval: any;
    if (loading) {
      setScanStep(0);
      interval = setInterval(() => {
        setScanStep((prev) => (prev < scanSteps.length - 1 ? prev + 1 : prev));
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [loading]);

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

    const ctx = canvas.getContext('2d');
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
    const selectedFile = e.target.files?.[0] || null;
    setFile(selectedFile);
    if (selectedFile) {
      setPreviewUrl(URL.createObjectURL(selectedFile));
      setResult(null);
      setError("");
      setZoom({ scale: 1, x: 0, y: 0 });
      setSelectedOverlay(null);
    }
  };

  const handleUpload = async () => {
    if (!file || cooldown > 0) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await analyzeImage(file);
      setResult(data);
      // Generate a stable case ID for this result to avoid hydration mismatch
      setCaseId(`${data.verdict.substring(0,4)}-${Math.floor(Math.random()*9000)+1000}`);
      
      // Auto-select ELA as default overlay if available
      if (data.evidence_images?.length > 0) {
        setSelectedOverlay(data.evidence_images[0].url);
      }
    } catch (err: any) {
      if (err.message.includes("429")) {
        setError("QUOTA EXHAUSTED: System entering cooldown protocol.");
        setCooldown(60);
      } else {
        setError(err.message || "Forensic Error: Check data link.");
      }
    } finally {
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
      y: (500 - centerY) * 0.5
    });
  };

  const resetZoom = () => setZoom({ scale: 1, x: 0, y: 0 });

  const handleExport = () => {
    window.print();
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
            <p className="text-slate-500 font-mono text-xs tracking-widest uppercase flex items-center print:text-slate-800">
              <span className="w-2 h-2 bg-emerald-500 rounded-full mr-2 animate-pulse print:hidden"></span>
              SECURE INTERROGATION SUITE // {new Date().toLocaleDateString()}
            </p>
          </div>
          <div className="mt-6 md:mt-0 flex gap-4 print:hidden">
             {result && (
               <button 
                 onClick={handleExport}
                 className="px-6 py-2 border border-slate-700 rounded-full font-mono text-[10px] hover:bg-slate-800 transition-colors uppercase tracking-widest"
               >
                 Export Report
               </button>
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
                className="relative group overflow-hidden rounded-2xl border-2 border-slate-800 aspect-square bg-slate-950 flex items-center justify-center cursor-crosshair"
                style={{ overflow: 'hidden' }}
              >
                {previewUrl ? (
                  <div 
                    className="w-full h-full relative transition-transform duration-500 ease-in-out"
                    style={{ 
                      transform: `scale(${zoom.scale}) translate(${zoom.x}px, ${zoom.y}px)`
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
                  <div className="flex flex-col items-center space-y-4 text-slate-700">
                    <svg className="w-16 h-16 opacity-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="0.5" d="M10 21h7a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v11m0 5l4.879-4.879m0 0a3 3 0 104.243-4.242 3 3 0 00-4.243 4.242z"></path></svg>
                    <span className="text-[10px] font-mono tracking-[0.2em] uppercase">Booth-1: No Input</span>
                  </div>
                )}
                
                {/* Slider Handle */}
                {previewUrl && selectedOverlay && (
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                     <div 
                       className="absolute h-full w-0.5 bg-cyan-400 shadow-[0_0_10px_cyan] pointer-events-auto cursor-ew-resize flex items-center justify-center"
                       style={{ left: `${sliderPos}%` }}
                     >
                       <div className="w-6 h-10 bg-slate-900 border border-cyan-400 rounded-md flex flex-col items-center justify-center gap-1">
                          <div className="w-0.5 h-3 bg-cyan-400/50"></div>
                          <div className="w-0.5 h-3 bg-cyan-400/50"></div>
                       </div>
                       <input 
                         type="range"
                         min="0" max="100"
                         value={sliderPos}
                         onChange={(e) => setSliderPos(Number(e.target.value))}
                         className="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize"
                       />
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
                <input type="file" id="forensic-input" className="hidden" onChange={handleFileChange} disabled={loading}/>
                <div className="flex gap-4">
                  <label htmlFor="forensic-input" className="flex-1 text-center py-4 rounded-xl border border-slate-700 bg-slate-800/50 text-slate-400 font-bold cursor-pointer hover:bg-slate-700 transition-colors tracking-widest text-[10px] uppercase">
                    {file ? "Replace Subject" : "Load Evidence"}
                  </label>
                  
                  <button 
                    onClick={handleUpload}
                    disabled={!file || loading || cooldown > 0}
                    className={`flex-[2] py-4 rounded-xl font-black uppercase text-xs tracking-[0.2em] transition-all shadow-xl active:scale-95 flex items-center justify-center group ${
                      cooldown > 0 ? 'bg-red-950/20 text-red-500 border border-red-900/50' : 'bg-cyan-600 text-white hover:bg-cyan-500'
                    }`}
                  >
                    {loading ? (
                      <span className="flex items-center">
                        <svg className="animate-spin h-3 w-3 mr-3 text-white" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
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

            {/* Progress Log */}
            {loading && (
              <div className="bg-slate-900/80 border border-slate-800 p-6 rounded-2xl space-y-3 font-mono text-[9px] animate-pulse">
                <div className="flex justify-between items-center text-cyan-400">
                  <span className="flex items-center"><span className="w-1.5 h-1.5 bg-cyan-500 rounded-full mr-2"></span>NEURAL PIPELINE ACTIVE</span>
                  <span>{Math.round(((scanStep + 1) / scanSteps.length) * 100)}%</span>
                </div>
                <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-cyan-500" style={{ width: `${((scanStep + 1) / scanSteps.length) * 100}%` }}></div>
                </div>
                <div className="text-slate-500 italic flex justify-between">
                   <span>LOG: {scanSteps[scanStep]}</span>
                   <span className="animate-pulse">_PROCESSING</span>
                </div>
              </div>
            )}

            {error && (
              <div className="bg-red-950/20 border border-red-900/50 p-4 rounded-xl flex items-center text-red-500 text-[10px] font-mono">
                <span className="mr-3 text-lg opacity-50">!</span> {error}
              </div>
            )}
          </section>

          {/* RIGHT: Intelligence Report */}
          <section className="lg:col-span-7 space-y-12">
            
            {!result && !loading && (
              <div className="h-full hidden md:flex items-center justify-center border border-dashed border-slate-900 rounded-3xl p-12 text-center opacity-20">
                <div className="space-y-6">
                  <div className="relative inline-block">
                    <div className="absolute inset-0 bg-cyan-500/20 blur-2xl rounded-full"></div>
                    <svg className="w-24 h-24 relative text-cyan-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="0.5" d="M9.75 17L9 21h6l-.75-4M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                  </div>
                  <p className="text-xs font-mono tracking-[0.3em] uppercase">Neural Interrogator Idle</p>
                </div>
              </div>
            )}

            {result && (
              <div className="animate-in fade-in fill-mode-both duration-1000 space-y-10">
                
                {/* Result Header */}
                <div className="flex flex-col md:flex-row gap-6">
                  <div className={`flex-1 p-6 rounded-3xl border-2 ${
                    result.verdict === 'AI-Generated' ? 'bg-red-950/10 border-red-900/50' : result.verdict === 'AI-Enhanced/Manipulated' ? 'bg-orange-950/10 border-orange-900/50' : 'bg-emerald-950/10 border-emerald-900/50'
                  }`}>
                    <span className="text-[9px] uppercase font-black text-slate-600 block mb-2 tracking-[0.2em]">Primary Verdict</span>
                    <h2 className={`text-3xl font-black italic tracking-tighter ${
                      result.verdict === 'AI-Generated' ? 'text-red-500' : result.verdict === 'AI-Enhanced/Manipulated' ? 'text-orange-500' : 'text-emerald-500'
                    }`}>
                      {result.verdict.toUpperCase().replace('AI-', 'NEURAL-')}
                    </h2>
                  </div>
                  <div className="md:w-48 p-6 rounded-3xl border border-slate-800 bg-slate-900/30 backdrop-blur-xl">
                    <span className="text-[9px] uppercase font-black text-slate-600 block mb-2 tracking-[0.2em]">Engine Confidence</span>
                    <h2 className="text-3xl font-black text-white italic tracking-tighter">
                      {result.confidence_level.toUpperCase()}
                    </h2>
                  </div>
                </div>

                {/* Evidence Narrative */}
                <div className="bg-slate-900/30 border border-slate-800 p-8 md:p-10 rounded-3xl relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-4 font-mono text-[8px] text-slate-800 flex flex-col items-end uppercase pointer-events-none">
                     <span>Case Ref: #FF-{caseId}</span>
                     <span>Subject: BGD-IMAGE</span>
                  </div>
                  <h3 className="text-[10px] font-black text-cyan-500 uppercase tracking-[0.3em] flex items-center mb-6">
                    <span className="w-2 h-0.5 bg-cyan-500 mr-4 shadow-[0_0_5px_cyan]"></span>
                    Technical Integrity Summation
                  </h3>
                  <p className="text-slate-400 leading-relaxed font-mono text-sm border-l border-slate-800 pl-8 md:pl-12 py-2">
                    {result.explanation}
                  </p>
                </div>

                {/* EVIDENCE GALLERY / SLIDER SELECTOR */}
                <div className="space-y-6">
                  <div className="flex justify-between items-end px-2">
                    <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Forensic Evidence Grid</h3>
                    <span className="text-[8px] text-slate-700 italic lowercase print:hidden">Select a map for comparison slider</span>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 print:grid-cols-2">
                    {result.evidence_images?.map((img: any, idx: number) => (
                      <button 
                        key={idx} 
                        onClick={() => setSelectedOverlay(img.url)}
                        className={`group relative aspect-square bg-slate-900 rounded-2xl overflow-hidden border transition-all ${
                          selectedOverlay === img.url ? 'border-cyan-500 ring-2 ring-cyan-500/20 scale-105' : 'border-slate-800 hover:border-slate-600'
                        }`}
                      >
                        <img src={img.url} alt={img.name} className="w-full h-full object-cover grayscale opacity-60 group-hover:opacity-100 group-hover:grayscale-0 transition-opacity" />
                        <div className="absolute inset-x-0 bottom-0 bg-black/80 backdrop-blur-sm p-2 transform transition-transform text-[8px] font-mono text-cyan-500 uppercase flex justify-between items-center">
                          <span className="truncate mr-1">{img.name}</span>
                          {selectedOverlay === img.url && <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-pulse shadow-[0_0_5px_cyan]"></span>}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* INTERACTIVE FINDINGS */}
                <div className="space-y-5 print:mt-10">
                   <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-2">Anomalous Artifacts Detected</h3>
                   <div className="grid grid-cols-1 gap-3">
                      {result.detailed_findings?.map((finding: any, idx: number) => (
                        <button 
                          key={idx} 
                          onClick={() => handleFindingClick(finding)}
                          className="flex items-center justify-between bg-slate-900/40 border border-slate-800 p-5 rounded-2xl group hover:bg-slate-900/60 hover:border-cyan-500/30 transition-all text-left w-full print:border-slate-200"
                        >
                           <div className="flex items-center">
                              <div className="w-8 h-8 rounded-lg bg-slate-950 flex items-center justify-center mr-5 border border-slate-800 group-hover:border-cyan-500/50">
                                 <span className="text-[9px] font-black text-slate-600 group-hover:text-cyan-500">0{idx+1}</span>
                              </div>
                              <span className="text-xs font-mono text-slate-300 group-hover:text-white transition-colors">{finding.description}</span>
                           </div>
                           <div className="flex items-center gap-4">
                              {finding.location_normalized && (
                                <span className="text-[8px] font-mono text-slate-600 bg-slate-950 px-2 py-1 rounded-md tracking-tighter">
                                  HIT @ [{finding.location_normalized.join(',')}]
                                </span>
                              )}
                              <span className="text-[10px] text-cyan-600 opacity-0 group-hover:opacity-100 transition-opacity font-bold uppercase tracking-tighter hidden md:inline">Inspect →</span>
                           </div>
                        </button>
                      ))}
                   </div>
                </div>

              </div>
            )}
          </section>
        </div>

        {/* Global Stats Footer */}
        <footer className="mt-24 pt-8 border-t border-slate-900 text-[9px] font-mono text-slate-700 flex flex-col md:flex-row justify-between items-center uppercase tracking-[0.4em] gap-6 print:text-black print:border-black print:mt-12">
          <div className="flex gap-10">
            <span className="flex items-center"><span className="w-1.5 h-1.5 bg-emerald-900 rounded-full mr-2"></span>Node_active</span>
            <span>Auth_Session: 8829-X</span>
            <span className="hidden md:inline">Precision_Gate: 0.9997</span>
          </div>
          <div className="italic text-slate-800 font-black">
             &copy; 2026 NEURAL INTERROGATOR // V6.0 SUITE
          </div>
        </footer>

      </div>
      
      {/* Print-specific header for PDF export */}
      <div className="hidden print:block fixed top-0 right-0 p-8 text-[10px] font-mono text-right border-l-2 border-slate-200">
         <p className="font-bold">FORENSIC CASE REPORT</p>
         <p>ID: {caseId}</p>
         <p>STATUS: CLOSED_INVESTIGATION</p>
      </div>
    </main>
  );
}