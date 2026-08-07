export default {
  async fetch(request, env, ctx) {
    // Enable CORS
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, X-Tavily-Key, X-Serper-Key",
    };

    // Handle Preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: corsHeaders
      });
    }

    if (request.method !== "POST") {
      return new Response(JSON.stringify({ error: "Only POST requests are allowed" }), {
        status: 405,
        headers: {
          "Content-Type": "application/json",
          ...corsHeaders
        }
      });
    }

    try {
      const body = await request.json();
      const action = body.action || "search";

      // 1. Synthesize Route (Uses Workers AI)
      if (action === "synthesize") {
        if (!env.AI) {
          return new Response(
            JSON.stringify({ 
              error: "Workers AI binding (env.AI) is missing in this Cloudflare Worker. Please add the AI binding in your wrangler.toml or Cloudflare Settings." 
            }), {
              status: 400,
              headers: {
                "Content-Type": "application/json",
                ...corsHeaders
              }
            }
          );
        }

        const context = body.context || "";
        const systemPrompt = `You are a professional lead intelligence researcher. Analyze the gathered web search records, crawled websites, and social media data to construct a comprehensive dossier.
You MUST output your response in raw JSON format matching the schema below. Do not output any conversational introduction, markdown code blocks, or extra text.

Required JSON Schema:
{
  "lead_name": "Lead's full name",
  "lead_email": "Lead's email address",
  "company_name": "Lead's current company name",
  "linkedin_url": "Lead's LinkedIn Profile URL",
  "summary": "A cohesive executive summary of the lead's professional background, specialties, and background details.",
  "skills": ["List of up to 8 core skills/competencies"],
  "experience": [
    {
      "title": "Role or Job Title",
      "company": "Company Name",
      "period": "Employment Period (e.g., Jan 2021 - Present)",
      "description": "Short summary of responsibilities, achievements, and impact"
    }
  ],
  "company_details": {
    "name": "Current company name",
    "industry": "Company's industry vertical",
    "size": "Employee size bracket (e.g., 50-200 employees)",
    "website": "Company website homepage URL",
    "description": "A comprehensive summary of the company's business model, value proposition, and market position."
  },
  "web_insights": [
    "Supplementary research discovery 1 (e.g., papers published, speaking roles, patents, news mentions)",
    "Supplementary research discovery 2"
  ]
}`;

        const aiResponse = await env.AI.run("@cf/meta/llama-3-8b-instruct", {
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: `Here is the gathered context about the lead:\n\n${context}\n\nCompile the JSON lead intelligence dossier:` }
          ],
          max_tokens: 1500
        });

        let modelText = "";
        if (typeof aiResponse === "string") {
          modelText = aiResponse;
        } else if (aiResponse && typeof aiResponse === "object") {
          if (typeof aiResponse.response === "string") {
            modelText = aiResponse.response;
          } else if (aiResponse.response) {
            modelText = JSON.stringify(aiResponse.response);
          } else {
            modelText = JSON.stringify(aiResponse);
          }
        } else {
          modelText = String(aiResponse || "");
        }
        
        // Clean and parse JSON from the response text
        let parsedReport;
        try {
          parsedReport = JSON.parse(modelText);
        } catch (e) {
          const startIndex = modelText.indexOf('{');
          const endIndex = modelText.lastIndexOf('}');
          if (startIndex !== -1 && endIndex !== -1) {
            try {
              parsedReport = JSON.parse(modelText.substring(startIndex, endIndex + 1));
            } catch (innerErr) {
              throw new Error("Model response was not valid JSON: " + modelText);
            }
          } else {
            throw new Error("Could not locate JSON output block in model response: " + modelText);
          }
        }

        return new Response(JSON.stringify(parsedReport), {
          status: 200,
          headers: {
            "Content-Type": "application/json",
            ...corsHeaders
          }
        });
      }

      // 2. Search Proxy Route (Default)
      const username = body.username || "";
      const email = body.email || "";

      if (!username && !email) {
        return new Response(JSON.stringify({ error: "Missing both username and email parameters" }), {
          status: 400,
          headers: {
            "Content-Type": "application/json",
            ...corsHeaders
          }
        });
      }

      // Grab API Keys from request headers or environment variables (secrets)
      const tavilyKey = request.headers.get("X-Tavily-Key") || env.TAVILY_API_KEY;
      const serperKey = request.headers.get("X-Serper-Key") || env.SERPER_API_KEY;

      if (!tavilyKey && !serperKey) {
        return new Response(JSON.stringify({ error: "No Web Search API key supplied. Set TAVILY_API_KEY or SERPER_API_KEY on the worker or headers." }), {
          status: 400,
          headers: {
            "Content-Type": "application/json",
            ...corsHeaders
          }
        });
      }

      // Build target search queries
      const targetQuery = `${username} ${email} LinkedIn profile`.trim();
      let searchResults = [];

      if (tavilyKey) {
        // Query Tavily search engine
        const searchResponse = await fetch("https://api.tavily.com/search", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            api_key: tavilyKey,
            query: targetQuery,
            search_depth: "advanced",
            max_results: 6
          })
        });

        if (searchResponse.ok) {
          const searchData = await searchResponse.json();
          searchResults = (searchData.results || []).map(item => ({
            title: item.title || "",
            url: item.url || "",
            content: item.content || item.snippet || ""
          }));
        } else {
          const errText = await searchResponse.text();
          throw new Error(`Tavily API responded with status ${searchResponse.status}: ${errText}`);
        }
      } else if (serperKey) {
        // Query Serper (Google Search API)
        const searchResponse = await fetch("https://google.serper.dev/search", {
          method: "POST",
          headers: {
            "X-API-KEY": serperKey,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            q: targetQuery,
            num: 6
          })
        });

        if (searchResponse.ok) {
          const searchData = await searchResponse.json();
          searchResults = (searchData.organic || []).map(item => ({
            title: item.title || "",
            url: item.link || "",
            content: item.snippet || ""
          }));
        } else {
          const errText = await searchResponse.text();
          throw new Error(`Serper API responded with status ${searchResponse.status}: ${errText}`);
        }
      }

      return new Response(JSON.stringify({ 
        success: true,
        query: targetQuery,
        results: searchResults 
      }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          ...corsHeaders
        }
      });

    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 500,
        headers: {
          "Content-Type": "application/json",
          ...corsHeaders
        }
      });
    }
  }
};
