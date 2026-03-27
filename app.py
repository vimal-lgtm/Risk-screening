import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURATION ---
RISK_LIBRARY = {
    "forex trading": 40, "binary options": 50, "guaranteed returns": 50,
    "daily profit": 30, "signals": 20, "crypto exchange": 40,
    "bitcoin": 15, "escort": 100, "narcotics": 100, "lottery": 30,
    "investment scheme": 45, "auction": 10
}

class ReportGenerator:
    @staticmethod
    def create_pdf(url, score, level, keywords):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Merchant Risk Assessment Report", ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "1. Executive Summary", ln=True)
        pdf.set_font("Arial", size=11)
        pdf.cell(50, 10, "Merchant URL:", border=1)
        pdf.cell(0, 10, url, border=1, ln=True)
        pdf.cell(50, 10, "Risk Score:", border=1)
        pdf.cell(0, 10, f"{score}/100", border=1, ln=True)
        pdf.cell(50, 10, "Risk Level:", border=1)
        pdf.cell(0, 10, level, border=1, ln=True)
        
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. Detected Risk Keywords", ln=True)
        pdf.set_font("Arial", size=11)
        if keywords:
            for kw in keywords:
                pdf.cell(0, 8, f"- {kw}", ln=True)
        else:
            pdf.cell(0, 8, "No high-risk keywords detected.", ln=True)
            
        return pdf.output()

class RiskEngine:
    @staticmethod
    def extract_text(url):
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        for s in soup(["script", "style"]): s.decompose()
        return soup.get_text().lower()

    @staticmethod
    def analyze(text):
        detected = [kw for kw in RISK_LIBRARY if re.search(rf'\b{kw}\b', text)]
        score = min(sum(RISK_LIBRARY[kw] for kw in detected), 100)
        return detected, score

def main():
    st.set_page_config(page_title="Merchant Risk Pro", page_icon="🛡️")
    st.title("🛡️ Merchant Risk Pro")
    st.caption("Automated Underwriting Tool for Payment Aggregators")
    
    url_input = st.text_input("Enter Merchant URL (e.g., https://xyz.com):")
    
    if st.button("Run Audit", type="primary"):
        if url_input:
            try:
                engine = RiskEngine()
                text = engine.extract_text(url_input)
                detected, score = engine.analyze(text)
                
                level = "HIGH" if score >= 70 else "MEDIUM" if score >= 30 else "LOW"
                color = "red" if level == "HIGH" else "orange" if level == "MEDIUM" else "green"
                
                st.metric("Risk Score", f"{score}/100", delta=level, delta_color="inverse")
                
                if detected:
                    st.warning(f"Detected Flags: {', '.join(detected)}")
                
                pdf_data = ReportGenerator.create_pdf(url_input, score, level, detected)
                st.download_button(
                    label="📥 Download Audit PDF",
                    data=bytes(pdf_data),
                    file_name=f"Audit_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
