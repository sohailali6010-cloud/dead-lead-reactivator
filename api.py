from fastapi.middleware.cors import CORSMiddleware

import pandas as pd
from datetime import datetime
from groq import Groq
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import io
import os
import time
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Setup
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
def score_lead(last_contact_str):
    last_contact = datetime.strptime(last_contact_str, "%Y-%m-%d")
    #how many days since last contacted?
    days_ago = (datetime.now() - last_contact).days

    # score based on how long ago
    if days_ago <=90:
        return "Warm", days_ago 
    elif days_ago <= 180:
        return "Hot", days_ago 
    else:
        return "Cold", days_ago


def generate_message(name, property_interest, location, score, days_ago):

    prompt = f"""
You are a friendly real estate broker assistant.
Write a short, warm reactivation text message to a lead.

Lead details:
- Name: {name}
- They were interested in: {property_interest}
- Location: {location}
- Last contacted: {days_ago} days ago
- Priority score: {score}

Rules:
- Maximum 3 sentences
- Sound human and friendly, not salesy
- Reference their specific property interest
- End with a soft question to re-open conversation
- Do not use emojis
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content.strip()


def generate_pdf(results, output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    # Styles
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        'title',
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=4
    )
    style_subtitle = ParagraphStyle(
        'subtitle',
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#888894'),
        spaceAfter=20
    )
    style_lead_name = ParagraphStyle(
        'lead_name',
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=4
    )
    style_detail = ParagraphStyle(
        'detail',
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#444444'),
        spaceAfter=3
    )
    style_message_label = ParagraphStyle(
        'message_label',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor('#5b3fd4'),
        spaceAfter=4,
        spaceBefore=8
    )
    style_message = ParagraphStyle(
        'message',
        fontName='Helvetica-Oblique',
        fontSize=10,
        textColor=colors.HexColor('#222222'),
        spaceAfter=6,
        leading=16,
        leftIndent=10,
        borderPad=8,
        backColor=colors.HexColor('#f5f3ff'),
        borderColor=colors.HexColor('#8b6ef5'),
        borderWidth=0,
        borderRadius=4
    )

    score_colors = {
        'Hot': '#d97706',
        'Warm': '#059669',
        'Cold': '#6b7280'
    }

    # Build content
    content = []

    # Header
  # Header
    from datetime import datetime as dt
    now = dt.now().strftime('%B %d, %Y')

    content.append(Paragraph("Orbitize AI", style_title))
    content.append(Paragraph(
        f"Lead Reactivation Report &nbsp;·&nbsp; Generated {now}",
        style_subtitle
    ))
    content.append(Spacer(1, 4*mm))
    content.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
    content.append(Spacer(1, 6*mm))

    # Summary section
    total = len(results)
    hot_count = sum(1 for r in results if r['score'] == 'Hot')
    warm_count = sum(1 for r in results if r['score'] == 'Warm')
    cold_count = sum(1 for r in results if r['score'] == 'Cold')

    style_summary_title = ParagraphStyle(
        'summary_title',
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=10
    )
    style_summary_item = ParagraphStyle(
        'summary_item',
        fontName='Helvetica',
        fontSize=11,
        textColor=colors.HexColor('#444444'),
        spaceAfter=6,
        leftIndent=10
    )

    content.append(Paragraph("Executive Summary", style_summary_title))
    content.append(Paragraph(
        f"Total leads analysed: <b>{total}</b>",
        style_summary_item
    ))
    content.append(Paragraph(
        f"<font color='#d97706'><b>Hot leads:</b></font> {hot_count} — prioritise these first",
        style_summary_item
    ))
    content.append(Paragraph(
        f"<font color='#059669'><b>Warm leads:</b></font> {warm_count} — follow up within the week",
        style_summary_item
    ))
    content.append(Paragraph(
        f"<font color='#6b7280'><b>Cold leads:</b></font> {cold_count} — long shot, worth a try",
        style_summary_item
    ))
    content.append(Spacer(1, 4*mm))
    content.append(Paragraph(
        "Leads are sorted by priority. Hot leads appear first.",
        ParagraphStyle('note', fontName='Helvetica-Oblique', fontSize=9,
                      textColor=colors.HexColor('#888894'), spaceAfter=6)
    ))
    content.append(Spacer(1, 6*mm))
    content.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
    content.append(Spacer(1, 6*mm))

    # Each lead
    for i, lead in enumerate(results):
        score = lead['score']
        color = score_colors.get(score, '#6b7280')

        content.append(Paragraph(
            f"Lead {str(i+1).zfill(2)} &nbsp;—&nbsp; {lead['name']} &nbsp;&nbsp;"
            f"<font color='{color}'><b>[{score.upper()}]</b></font>",
            style_lead_name
        ))
        content.append(Paragraph(
            f"📧 {lead['email']} &nbsp;&nbsp; 📞 {lead['phone']}",
            style_detail
        ))
        content.append(Paragraph(
            f"📍 {lead['location']} &nbsp;&nbsp; 🏠 {lead['property_interest']}",
            style_detail
        ))
        content.append(Paragraph(
            f"Last contact: {lead['last_contact']} ({lead['days_since_contact']} days ago)",
            style_detail
        ))
        content.append(Paragraph("Reactivation Message:", style_message_label))
        content.append(Paragraph(lead['reactivation_message'], style_message))
        content.append(Spacer(1, 4*mm))
        content.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e5e7eb')))
        content.append(Spacer(1, 5*mm))

    # Footer
    content.append(Paragraph(
        "Generated by Orbitize AI · sohail ali · orbitizeai.co@gmail.com",
        style_subtitle
    ))

    doc.build(content)
@app.post("/reactivate")
async def reactivate_leads(file: UploadFile = File(...)):
    
    # Read the uploaded CSV into memory
    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    
    # Process each lead
    results = []
    for index, row in df.iterrows():
        score, days = score_lead(row["last_contact"])
        message = generate_message(
            row["name"],
            row["property_interest"],
            row["location"],
            score,
            days
        )
        results.append({
            "name": row["name"],
            "email": row["email"],
            "phone": row["phone"],
            "location": row["location"],
            "property_interest": row["property_interest"],
            "last_contact": row["last_contact"],
            "days_since_contact": days,
            "score": score,
            "reactivation_message": message
        })
    # Sort leads: Hot first, then Warm, then Cold
    score_order = {"Hot": 0, "Warm": 1, "Cold": 2}
    results = sorted(results, key=lambda x: score_order[x["score"]])
    # Save as PDF instead of CSV
    output_path = f"reactivated_leads_{int(time.time())}.pdf"
    
    generate_pdf(results, output_path)

    return FileResponse(
        path=output_path,
        media_type="application/pdf",
        filename="reactivated_leads.pdf"
    )
        
       
@app.post("/reactivate-json")
async def reactivate_json(file: UploadFile = File(...)):
    
    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    
    results = []
    for _, row in df.iterrows():
        score, days = score_lead(row["last_contact"])
        message = generate_message(
            row["name"],
            row["property_interest"],
            row["location"],
            score,
            days
        )
        results.append({
            "name": row["name"],
            "email": row["email"],
            "phone": row["phone"],
            "location": row["location"],
            "property_interest": row["property_interest"],
            "last_contact": row["last_contact"],
            "days_since_contact": days,
            "score": score,
            "reactivation_message": message
        })

    # Sort: Hot first
    score_order = {"Hot": 0, "Warm": 1, "Cold": 2}
    results = sorted(results, key=lambda x: score_order[x["score"]])

    return {"leads": results}

@app.get("/ui", response_class=HTMLResponse)
def ui():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()