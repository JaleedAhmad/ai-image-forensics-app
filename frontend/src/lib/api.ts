/**
 * Sends an image file to the FastAPI backend for forensic analysis.
 * Uses the environment variable for the base URL to maintain flexibility.
 */
export async function analyzeImage(file: File) {
  // 1. Prepare the multipart form data
  const formData = new FormData();
  formData.append('file', file);

  // 2. Determine the API endpoint
  // Fallback to 127.0.0.1 if the environment variable is not loaded
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  const endpoint = `${baseUrl}/analyze_image/`;

  try {
    // 3. Execute the POST request
    const response = await fetch(endpoint, {
      method: 'POST',
      body: formData,
      // Note: Do NOT set Content-Type header manually when sending FormData; 
      // the browser needs to set the boundary automatically.
    });

    // 4. Handle non-200 responses
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      
      // Handle the specific 429 error format from your screenshot
      if (response.status === 429) {
        throw new Error("429: Resource Exhausted. Please wait for the quota to reset.");
      }

      throw new Error(errorData.detail || `Server error: ${response.status}`);
    }

    // 5. Parse and return the ForensicAnalysisResult
    return await response.json();
    
  } catch (error: any) {
    // Log the error for debugging but throw a clean message for the UI
    console.error("API Fetch Error:", error);
    throw error;
  }
}