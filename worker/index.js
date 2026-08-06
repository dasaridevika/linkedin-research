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
      // Query 1: Find target's identity and LinkedIn profile
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
