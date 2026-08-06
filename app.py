import os
import streamlit as st
from datetime import datetime

# Set page configurations (tab title, layout, icon)
st.set_page_config(
    page_title="Executive Lead Researcher",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply premium styling using custom CSS
st.markdown("""
<style>
    /* Import modern Google font */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    /* Global styles */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Glassmorphism containers */
    .card-container {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 24px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 20px;
    }
    
    /* Sleek badge styling */
    .skill-badge {
        display: inline-block;
        background: linear-gradient(135deg, #319795 0%, #2B6CB0 100%);
        color: white;
        border-radius: 20px;
        padding: 5px 12px;
        font-size: 0.85rem;
        font-weight: 500;
        margin-right: 8px;
        margin-bottom: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Primary buttons */
    .stButton>button {
        background: linear-gradient(135deg, #1A365D 0%, #2B6CB0 100%) !important;
        color: white !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 12px rgba(43, 108, 176, 0.3) !important;
        opacity: 0.95 !important;
    }
    
    /* Titles and Headers */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #E2E8F0 30%, #90CDF4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }
    .main-subtitle {
        font-size: 1.1rem;
        color: #A0AEC0;
        margin-bottom: 30px;
        font-weight: 300;
    }
    
    /* Sidebar styling tweaks */
    .css-1639gjc {
        background-color: #0F172A !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session States
if "research_results" not in st.session_state:
    st.session_state.research_results = None

if "pdf_ready" not in st.session_state:
    st.session_state.pdf_ready = False

# Read environment variables directly
import os
gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
tavily_key = os.getenv("TAVILY_API_KEY")
serper_key = os.getenv("SERPER_API_KEY")
apify_token = os.getenv("APIFY_TOKEN")
cloudflare_worker = os.getenv("CLOUDFLARE_WORKER_URL")

# Main Content Area
st.markdown("<h1 class='main-title'>Lead Intelligence Researcher</h1>", unsafe_allow_html=True)
st.markdown("<p class='main-subtitle'>Search, scrape, and compile public web intelligence into a professional PDF dossier.</p>", unsafe_allow_html=True)

# Centered research request form
with st.form("research_form"):
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        lead_username = st.text_input("LinkedIn Username or Profile URL*", placeholder="e.g. alex-mercer or https://www.linkedin.com/in/...")
    with r_col2:
        lead_email = st.text_input("Lead Email Address*", placeholder="e.g. alex@techvanguard.ai")
        
    submitted = st.form_submit_button("Generate Intelligence PDF")

# If form is submitted, launch research pipeline
if submitted:
    if not lead_username or not lead_email:
        st.error("Missing fields: Username and Email are required.")
    elif not gemini_key:
        st.error("Please configure the GEMINI_API_KEY variable in your Railway dashboard to generate reports.")
    elif not tavily_key and not serper_key:
        st.error("Please configure a web search API variable (TAVILY_API_KEY or SERPER_API_KEY) in your Railway dashboard.")
    else:
        # Import research and pdf components
        from researcher import perform_full_research
        from pdf_generator import generate_lead_pdf
        
        # Track pipeline stages using st.status (collapsible workflow steps)
        with st.status("Initializing Intelligence Pipeline...", expanded=True) as status:
            try:
                # Stage 1
                status.write("Fetching profile & resolving identity...")
                results = perform_full_research(
                    lead_username=lead_username,
                    lead_email=lead_email
                )
                
                # Stage 2
                status.write("Synthesizing lead summaries with Gemini API...")
                
                # Stage 3
                status.write("Compiling Report PDF...")
                resolved_name = results.get('lead_name', 'Lead')
                pdf_filename = f"report_{resolved_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M')}.pdf"
                pdf_filepath = os.path.join("downloads", pdf_filename)
                
                generate_lead_pdf(results, pdf_filepath)
                
                # Save to session state
                st.session_state.research_results = results
                st.session_state.pdf_path = pdf_filepath
                st.session_state.pdf_filename = pdf_filename
                st.session_state.pdf_ready = True
                
                status.update(label="Research Complete! Check the dossier below.", state="complete", expanded=False)
                
            except Exception as e:
                status.update(label=f"Pipeline error: {str(e)}", state="error")
                st.exception(e)

# Render results and PDF viewer if ready
if st.session_state.pdf_ready:
    st.markdown("---")
    
    # Download Button
    with open(st.session_state.pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    st.download_button(
        label="📥 Download PDF Intelligence Report",
        data=pdf_bytes,
        file_name=st.session_state.pdf_filename,
        mime="application/pdf",
        use_container_width=True
    )
    
    # PDF Iframe Preview
    import base64
    try:
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" style="border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; margin-top: 15px;"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.warning("Could not render inline PDF preview in this browser session. Please download using the button above.")

