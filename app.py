# -*- coding: utf-8 -*-
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import whois
import plotly.express as px
import io

# --- 1. PII & SECURITY SHIELD ---
class SecurityShield:
    @staticmethod
    def mask_pii(df):
        """Masks Email and Name for PCI-DSS compliance."""
        if 'email' in df.columns:
            df['email'] = df['email'].apply(lambda x: f"{str(x)[0]}***@{str(x).split('@')[-1]}" if '@' in str(x) else x)
        if 'name' in df.columns:
            df['name'] = df['name'].apply(lambda x: " ".join([n[0] + "*"*2 for n in str(x).split()]) if pd.notnull(x) else x)
        return df

# --- 2. RISK & COMPLIANCE ENGINE ---
class RiskEngine:
    def __init__(self, url):
        self.url = url
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        self.content = ""

    def run_site_audit(self):
        try:
            res = requests.get(self.url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            for s in soup(["script", "style"]): s.decompose()
            self.content = soup.get_text().lower()
            
            # Compliance Check (GST & PIN)
            gst = re.search(r'\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}', self.content)
            pin = re.search(r'\b\d{6}\b', self.content)
            
            # Risk Scoring
            risk_words = ["forex", "binary", "guaranteed", "scam", "betting", "casino"]
            found_words = [w for w in risk_words if w in self.content]
            
            return {
                "GST": gst.group(0) if gst else "Missing",
                "Address": "Found" if pin else "Missing",
                "Risk Words": found_words,
                "Risk Score": len(found_words) * 20
            }
        except:
            return None

# --- 3. AUDIT REPORT GENERATOR ---
class AuditReporter:
    @staticmethod
    def generate_pdf(audit_data, tx_anomalies):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="Merchant Audit Report", ln=True, align='C')
        pdf.set_font("Arial", size=12)
        pdf.ln(10)
        
        # Section 1: Web Audit
        pdf.cell(200, 10, txt="1. Website Compliance & Risk", ln=True)
        for k, v in audit_data.items():
            pdf.cell(200, 10, txt=f"- {k}: {v}", ln=True)
        
        pdf.ln(10)
        # Section 2: Transactions
        pdf.cell(200, 10, txt="2. Transaction Anomalies", ln=True)
        if tx_anomalies:
            for a in tx_anomalies:
                pdf.cell(200, 10, txt=f"- {a}", ln=True)
        else:
            pdf.cell(200, 10, txt="- No significant anomalies detected.", ln=True)
        
        # Save to Buffer (Crucial for Streamlit Cloud)
        buffer = io.BytesIO()
        pdf_out = pdf.output(dest='S').encode('latin-1')
        buffer.write(pdf_out)
        buffer.seek(0)
        return buffer

# --- 4. STREAMLIT UI ---
def main():
    st.set_page_config(page_title="Fintech Risk Auditor", layout="wide")
    st.title("🛡️ RBI-Standard Merchant Auditor")
    
    url = st.text_input("Merchant Website URL", placeholder="https://merchant-site.com")
    biz_name = st.text_input("Legal Business Name")
    
    col1, col2 = st.tabs(["🌐 Site & Risk Scan", "📊 Transaction Dump"])
    
    audit_results = {}
    tx_anomalies = []

    with col1:
        if st.button("Run Website Audit"):
            engine = RiskEngine(url)
            audit_results = engine.run_site_audit()
            if audit_results:
                st.write("### Audit Findings")
                st.json(audit_results)
                st.session_state['audit_results'] = audit_results
            else:
                st.error("Could not reach website.")

    with col2:
        file = st.file_uploader("Upload Transaction CSV (customer_id, amount, email, name)", type="csv")
        if file:
            df = pd.read_csv(file)
            df = SecurityShield.mask_pii(df)
            st.write("### Masked Audit View")
            st.dataframe(df.head())
            
            # Anomaly: Check for high-value outliers
            high_val = df[df['amount'] > (df['amount'].mean() * 5)]
            if not high_val.empty:
                tx_anomalies.append(f"Detected {len(high_val)} High-Value Outliers.")
                for a in tx_anomalies: st.warning(a)
            st.session_state['tx_anomalies'] = tx_anomalies

    # DOWNLOAD BUTTON
    if 'audit_results' in st.session_state:
        st.divider()
        report_buffer = AuditReporter.generate_pdf(st.session_state['audit_results'], st.session_state.get('tx_anomalies', []))
        st.download_button(
            label="📥 Download Full Audit Report",
            data=report_buffer,
            file_name=f"Audit_{biz_name}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )

if __name__ == "__main__":
    main()