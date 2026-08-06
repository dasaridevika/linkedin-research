import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    print("Testing imports...")
    try:
        import config
        import search_client
        import crawler
        import pdf_generator
        import researcher
        print("[SUCCESS] All modules imported successfully!")
    except Exception as e:
        print(f"[ERROR] Import failed: {str(e)}")
        sys.exit(1)

def test_pdf_generation():
    print("\nTesting PDF generation...")
    try:
        from pdf_generator import generate_lead_pdf
        
        # Test mock data structure
        sample_data = {
            "lead_name": "Alex Mercer",
            "lead_email": "alex@techvanguard.ai",
            "company_name": "TechVanguard",
            "linkedin_url": "https://linkedin.com/in/alex-mercer",
            "summary": "Alex Mercer is a seasoned solutions architect with over 8 years of experience. He is dedicated to crafting scalable and robust products.",
            "skills": ["Python", "Go", "Cloud Architecture", "Generative AI", "System Design"],
            "experience": [
                {
                    "title": "Lead Solutions Architect",
                    "company": "TechVanguard",
                    "period": "2023 - Present",
                    "description": "Leading AI development teams and deploying machine learning pipelines in production environment."
                },
                {
                    "title": "Senior Systems Engineer",
                    "company": "CloudFlow",
                    "period": "2020 - 2023",
                    "description": "Architected low-latency streaming infrastructure processing 1M+ messages daily."
                }
            ],
            "company_details": {
                "name": "TechVanguard",
                "website": "https://techvanguard.ai",
                "industry": "Software Development",
                "size": "51-200 employees",
                "description": "TechVanguard designs enterprise software with built-in predictive analytics, serving business workflows worldwide."
            },
            "web_insights": [
                "Alex Mercer spoke at PyCon 2024 on 'Robust Async Scraping Patterns in Python'.",
                "TechVanguard recently announced $15M Series A funding led by Nexus Capital.",
                "Featured in 'TechWeekly' list of top enterprise AI solutions."
            ]
        }
        
        output_filepath = os.path.join("downloads", "test_report.pdf")
        generate_lead_pdf(sample_data, output_filepath)
        
        if os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 0:
            print(f"[SUCCESS] PDF successfully generated at: {os.path.abspath(output_filepath)}")
        else:
            print("[ERROR] PDF file was created but is empty or does not exist.")
            sys.exit(1)
            
    except Exception as e:
        print(f"[ERROR] PDF generation failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("=== Verification Script ===")
    test_imports()
    test_pdf_generation()
    print("=== All Tests Passed! ===")
