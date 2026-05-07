import Link from 'next/link';

import ShareButton from './ShareButton';

// Helper to fetch the case
async function getCase(id: string) {
  const baseUrl = 'https://forensics-backend-1034457982605.us-central1.run.app';
  const res = await fetch(`${baseUrl}/cases/${id}`, { cache: 'no-store' });
  if (!res.ok) return null;
  return res.json();
}

export default async function CasePage({ params }: { params: { id: string } }) {
  const caseData = await getCase(params.id);

  if (!caseData) {
    return (
      <main className="min-h-screen p-8 bg-slate-950 text-slate-200 flex flex-col items-center justify-center font-mono">
        <h1 className="text-4xl font-black text-red-500 mb-4">CASE NOT FOUND</h1>
        <p className="text-slate-500 mb-8">The requested forensic record [{params.id}] does not exist or has been purged.</p>
        <Link href="/" className="px-6 py-2 border border-slate-700 hover:bg-slate-800 rounded-full transition-colors">
          Return to Interrogation Suite
        </Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen p-4 md:p-8 bg-slate-950 text-slate-200 font-sans selection:bg-cyan-500/30">
      <div className="max-w-4xl mx-auto">
        <header className="flex justify-between items-end mb-12 border-b border-slate-800 pb-8">
          <div>
            <h1 className="text-3xl font-black italic tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-600 mb-2">
              NEURAL FORENSICS ARCHIVE
            </h1>
            <p className="text-slate-500 font-mono text-xs tracking-widest uppercase">
              CASE RECORD // {params.id}
            </p>
          </div>
          <div className="flex gap-4">
            <ShareButton />
            <Link href="/" className="px-6 py-2 border border-slate-700 hover:bg-slate-800 rounded-full font-mono text-[10px] transition-colors uppercase tracking-widest flex items-center">
              New Scan
            </Link>
          </div>
        </header>

        <div className="space-y-12">
          {/* Result Header */}
          <div className="flex flex-col md:flex-row gap-6">
            <div className={`flex-1 p-6 rounded-3xl border-2 ${
              caseData.verdict === 'AI-Generated' ? 'bg-red-950/10 border-red-900/50' : caseData.verdict === 'AI-Enhanced/Manipulated' ? 'bg-orange-950/10 border-orange-900/50' : 'bg-emerald-950/10 border-emerald-900/50'
            }`}>
              <span className="text-[9px] uppercase font-black text-slate-600 block mb-2 tracking-[0.2em]">Archived Verdict</span>
              <h2 className={`text-3xl font-black italic tracking-tighter ${
                caseData.verdict === 'AI-Generated' ? 'text-red-500' : caseData.verdict === 'AI-Enhanced/Manipulated' ? 'text-orange-500' : 'text-emerald-500'
              }`}>
                {caseData.verdict.toUpperCase().replace('AI-', 'NEURAL-')}
              </h2>
            </div>
            <div className="md:w-48 p-6 rounded-3xl border border-slate-800 bg-slate-900/30 backdrop-blur-xl">
              <span className="text-[9px] uppercase font-black text-slate-600 block mb-2 tracking-[0.2em]">Engine Confidence</span>
              <h2 className="text-3xl font-black text-white italic tracking-tighter">
                {caseData.confidence_level.toUpperCase()}
              </h2>
            </div>
          </div>

          {/* Evidence Narrative */}
          <div className="bg-slate-900/30 border border-slate-800 p-8 md:p-10 rounded-3xl">
            <h3 className="text-[10px] font-black text-cyan-500 uppercase tracking-[0.3em] flex items-center mb-6">
              <span className="w-2 h-0.5 bg-cyan-500 mr-4 shadow-[0_0_5px_cyan]"></span>
              Archived Integrity Summation
            </h3>
            <p className="text-slate-400 leading-relaxed font-mono text-sm border-l border-slate-800 pl-8 md:pl-12 py-2">
              {caseData.explanation}
            </p>
          </div>

          {/* INTERACTIVE FINDINGS */}
          {caseData.detailed_findings?.length > 0 && (
            <div className="space-y-5">
              <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-2">Anomalous Artifacts Detected</h3>
              <div className="grid grid-cols-1 gap-3">
                  {caseData.detailed_findings.map((finding: any, idx: number) => (
                    <div 
                      key={idx} 
                      className="flex items-center justify-between bg-slate-900/40 border border-slate-800 p-5 rounded-2xl w-full"
                    >
                        <div className="flex items-center">
                          <div className="w-8 h-8 rounded-lg bg-slate-950 flex items-center justify-center mr-5 border border-slate-800">
                              <span className="text-[9px] font-black text-slate-600">0{idx+1}</span>
                          </div>
                          <span className="text-xs font-mono text-slate-300">{finding.description}</span>
                        </div>
                        <div className="flex items-center gap-4">
                          {finding.location_normalized && (
                            <span className="text-[8px] font-mono text-slate-600 bg-slate-950 px-2 py-1 rounded-md tracking-tighter">
                              HIT @ [{finding.location_normalized.join(',')}]
                            </span>
                          )}
                        </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* EVIDENCE GALLERY (Served from Google Cloud Storage) */}
          <div className="mt-12">
             <h3 className="text-sm font-black uppercase tracking-widest border-b-2 border-slate-800 pb-2 mb-6 text-cyan-500">Forensic Evidence Catalog</h3>
             <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {caseData.original_image_url && (
                  <div className="bg-slate-900/40 border border-slate-800 p-4 rounded-2xl flex flex-col items-center">
                    <div className="w-full aspect-square bg-slate-950 flex items-center justify-center rounded-xl overflow-hidden mb-4 border border-slate-800">
                      <img src={caseData.original_image_url} alt="Original Evidence" className="max-w-full max-h-full object-contain" />
                    </div>
                    <p className="font-mono text-xs font-bold text-slate-300 tracking-widest uppercase">Exhibit A: Original Image</p>
                  </div>
                )}

                {caseData.evidence_images?.map((img: any, idx: number) => (
                   <div key={idx} className="bg-slate-900/40 border border-slate-800 p-4 rounded-2xl flex flex-col items-center">
                     <div className="w-full aspect-square bg-slate-950 flex items-center justify-center rounded-xl overflow-hidden mb-4 border border-slate-800 relative group">
                       <img src={img.url} alt={img.name} className="max-w-full max-h-full object-contain" />
                     </div>
                     <p className="font-mono text-[10px] font-bold text-slate-400 tracking-widest uppercase">{img.name}</p>
                   </div>
                ))}
             </div>
          </div>

        </div>
      </div>
    </main>
  );
}
