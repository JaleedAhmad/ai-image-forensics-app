export async function analyzeImageStream(
  file: File, 
  onStep: (step: any) => void, 
  onComplete: (result: any) => void, 
  onError: (error: string) => void
) {
  const formData = new FormData();
  formData.append('file', file);

  const baseUrl = 'https://forensics-backend-1034457982605.us-central1.run.app';
  const endpoint = `${baseUrl}/analyze_image/`;

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      if (response.status === 429) {
        throw new Error("429: Resource Exhausted. Please wait for the quota to reset.");
      }
      try {
        const errJson = await response.json();
        throw new Error(errJson.detail || `Server error: ${response.status}`);
      } catch (e: any) {
        if (e.message.includes("Server error") || e.message.includes("429")) throw e;
        throw new Error(`Server error: ${response.status}`);
      }
    }

    if (!response.body) throw new Error("No response body");

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      
      // Keep the last incomplete chunk in the buffer
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const dataStr = line.substring(6);
            const data = JSON.parse(dataStr);
            
            if (data.type === 'step') {
              onStep(data.step);
            } else if (data.type === 'complete') {
              onComplete(data.result);
            } else if (data.type === 'error') {
              onError(data.detail);
            }
          } catch (e) {
            console.error("Error parsing SSE data:", e, line);
          }
        }
      }
    }
  } catch (error: any) {
    console.error("API Fetch Error:", error);
    onError(error.message);
  }
}