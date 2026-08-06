import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# Define custom color palette
PRIMARY_COLOR = colors.HexColor("#1A365D")   # Deep navy
SECONDARY_COLOR = colors.HexColor("#2B6CB0") # Slate blue
TEXT_COLOR = colors.HexColor("#2D3748")      # Dark gray text
ACCENT_COLOR = colors.HexColor("#E2E8F0")    # Light gray borders/backgrounds
HIGHLIGHT_COLOR = colors.HexColor("#319795") # Teal accent

class NumberedCanvas(canvas.Canvas):
    """
    Canvas to calculate and draw page numbers 'Page X of Y' dynamically.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_elements(num_pages)
            super().showPage()
        super().save()

    def draw_page_elements(self, page_count):
        self.saveState()
        
        # Draw header (on pages > 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica", 8)
            self.setFillColor(TEXT_COLOR)
            self.drawString(54, 750, "Executive Intelligence Report | Confidential")
            self.setStrokeColor(ACCENT_COLOR)
            self.setLineWidth(0.5)
            self.line(54, 742, letter[0] - 54, 742)

        # Draw footer (on all pages)
        self.setFont("Helvetica", 9)
        self.setFillColor(TEXT_COLOR)
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 40, footer_text)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.drawString(54, 40, f"Generated on {timestamp} • LinkedIn Lead Research Tool")
        self.setStrokeColor(ACCENT_COLOR)
        self.setLineWidth(0.5)
        self.line(54, 55, letter[0] - 54, 55)
        
        self.restoreState()


def generate_lead_pdf(data: dict, filepath: str):
    """
    Generates a beautifully structured PDF document for the lead research data.
    """
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

    # Document setup: standard letter size with 0.75-inch (54 points) margins
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )

    styles = getSampleStyleSheet()
    
    # Custom typography configurations
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=PRIMARY_COLOR,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=SECONDARY_COLOR,
        spaceAfter=25
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=PRIMARY_COLOR,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=SECONDARY_COLOR,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=TEXT_COLOR,
        spaceAfter=10
    )

    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=6
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.white
    )

    table_body_style = ParagraphStyle(
        'TableBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=TEXT_COLOR
    )

    table_body_bold_style = ParagraphStyle(
        'TableBodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=TEXT_COLOR
    )

    story = []

    # 1. Header Banner & Title Block
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Executive Intelligence Report", title_style))
    story.append(Paragraph(f"Lead Research and Profiling: {data.get('lead_name', 'N/A')}", subtitle_style))
    
    # Decorative line under title block
    d_table = Table([[""]], colWidths=[letter[0] - 108])
    d_table.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 2, PRIMARY_COLOR),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(d_table)
    story.append(Spacer(1, 15))

    # 2. Lead Overview Meta Table
    meta_data = [
        [
            Paragraph("Lead Name", table_body_bold_style), 
            Paragraph(str(data.get('lead_name') or 'N/A'), table_body_style),
            Paragraph("Current Company", table_body_bold_style),
            Paragraph(str(data.get('company_name') or 'N/A'), table_body_style)
        ],
        [
            Paragraph("Email Address", table_body_bold_style),
            Paragraph(str(data.get('lead_email') or 'N/A'), table_body_style),
            Paragraph("LinkedIn Profile", table_body_bold_style),
            Paragraph(str(data.get('linkedin_url') or 'N/A'), table_body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[1.2*inch, 2.3*inch, 1.3*inch, 2.2*inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), ACCENT_COLOR),
        ('BACKGROUND', (2,0), (2,-1), ACCENT_COLOR),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 20))

    # 3. Executive Professional Summary
    story.append(Paragraph("Professional Profile Summary", h1_style))
    summary_text = data.get('summary', "No professional summary available. Standard profile details could not be extracted.")
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 10))

    # 4. Work Experience & Education
    if data.get('experience'):
        story.append(Paragraph("Key Professional Experiences", h1_style))
        for exp in data['experience'][:4]:  # limit to top 4 experiences
            title = exp.get('title', 'Position')
            comp = exp.get('company', 'Company')
            period = exp.get('period', '')
            desc = exp.get('description', '')
            
            exp_header = f"<b>{title}</b> at <i>{comp}</i>"
            if period:
                exp_header += f" ({period})"
            
            story.append(Paragraph(exp_header, h2_style))
            if desc:
                story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 10))

    # Page Break for Company Profile and Web Research Insights
    story.append(PageBreak())

    # 5. Company Intelligence Section
    comp_info = data.get('company_details', {})
    story.append(Paragraph("Company Profile & Intelligence", h1_style))
    
    comp_meta = [
        [Paragraph("Detail", table_header_style), Paragraph("Value", table_header_style)],
        [Paragraph("Company Name", table_body_bold_style), Paragraph(str(comp_info.get('name') or data.get('company_name') or 'N/A'), table_body_style)],
        [Paragraph("Industry", table_body_bold_style), Paragraph(str(comp_info.get('industry') or 'N/A'), table_body_style)],
        [Paragraph("Company Size", table_body_bold_style), Paragraph(str(comp_info.get('size') or 'N/A'), table_body_style)],
        [Paragraph("Website", table_body_bold_style), Paragraph(str(comp_info.get('website') or 'N/A'), table_body_style)]
    ]
    comp_table = Table(comp_meta, colWidths=[1.8*inch, 5.2*inch])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), PRIMARY_COLOR),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 12))
    
    comp_desc = comp_info.get('description', "No detailed company description was found via search or crawling.")
    story.append(Paragraph(f"<b>About the Company:</b> {comp_desc}", body_style))
    story.append(Spacer(1, 15))

    # 6. Web Search & Background Insights
    story.append(Paragraph("Web Search & Background Insights", h1_style))
    web_insights = data.get('web_insights', [])
    if web_insights:
        for insight in web_insights:
            story.append(Paragraph(f"• {insight}", bullet_style))
    else:
        story.append(Paragraph("No supplementary background information was discovered on web search index endpoints.", body_style))
    
    story.append(Spacer(1, 15))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
