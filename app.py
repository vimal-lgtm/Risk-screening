# -*- coding: utf-8 -*-
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import whois
from fpdf import FPDF
import io
from datetime import datetime
from urllib.parse import urlparse

# --- CONFIGURATION ---
RISK_KEYWORDS = {
    "High Risk / Illegal": ["narcotics", "escort", "marijuana", "weapons", "fake id", "casino", "betting", "matka"],
    "Financial Risk": ["forex", "binary options", "guaranteed returns", "crypto", "bitcoin", "daily profit"]
}

# --- HELPER: SAFE TEXT FOR PDF ---
def safe_text(text):
    """Strips complex Unicode characters that cause FPDF to crash."""
    if not text: return "N/A"
    return str(text).encode('latin-1', 'replace').decode('latin-1')

# --- 1. RISK & COMPLIANCE ENGINE ---
class MerchantScanner:
    def __init__(self, url):
        # Add http:// if missing to prevent requests crash
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        self.url = url
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    def scan(self):
        results = {
            "url": self.url,
            "status": "Failed",
            "domain_age": "Unknown",
            "gst_found": "No",
            "address_found": "No",
            "refund_policy": "No",
            "risks_detected": []
        }

        # 1. Check Domain Age
        try:
            domain = urlparse(self.url).netloc or self.url
            w = whois.whois(domain)
            creation_date = w.creation_date
            if isinstance(creation_date, list): creation_date = creation_date[0]
            if creation_date:
                days_old = (datetime.now() - creation_date).days
                results["domain_age"] = f"{days_old} days"
        except Exception:
            pass # Fails gracefully if WHOIS blocks the request

        # 2. Scrape Website
        try:
            res = requests.get(self.url, headers=self.headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')
            for script in soup(["script", "style"]): script.decompose()
            text = soup.get_text(separator=' ').lower()
            
            results["status"] = "Success"
            
            # Compliance Checks
            if re.search(r'\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}', text):
                results["gst_found"] = "Yes"
            if re.search(r'\b\d{6}\b', text):
                results["address_found"] = "Yes"
            if "refund" in text or "cancellation" in text:
                results["refund_policy"] = "Yes"

            # Risk Keyword Scan
            for category, words in RISK_KEYWORDS.items():
                for word in words:
                    if re.search(rf'\b{word}\b', text):
                        results["risks_detected"].append(word)

        except Exception as e:
            results["error_msg"] = str(e)

        return results

# --- 2. PDF GENERATOR ---
class PDFReport:
    @staticmethod
    def create(data, biz_name):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        
        # Header
        pdf.cell(0, 10, safe_text(f"Merchant Risk Audit: {biz_name}"), ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, safe_text(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Target: {data['url']}"), ln=True, align='C')
        pdf.ln(10)

        if data["status"] == "Failed":
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Scan Failed. Could not access website.", ln=True)
        else:
            # Domain & Compliance
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "1. Compliance & Identity Check", ln=True)
            pdf.set_font("Arial", size=11)
            pdf.cell(0, 8, safe_text(f"- Domain Age: {data['domain_age']}"), ln=True)
            pdf.cell(0, 8, safe_text(f"- GST Number Detected: {data['gst_found']}"), ln=True)
            pdf.cell(0, 8, safe_text(f"- Indian PIN Code Detected: {data['address_found']}"), ln=True)
            pdf.cell(0, 8, safe_text(f"- Refund Policy Detected: {data['refund_policy']}"), ln=True)
            pdf.ln(5)

            # Risk Findings
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "2. High-Risk Keyword Analysis", ln=True)
            pdf.set_font("Arial", size=11)
            if data["risks_detected"]:
                for r in set(data["risks_detected"]):
                    pdf.cell(0, 8, safe_text(f"- FLAG: {r.upper()}"), ln=True)
            else:
                pdf.cell(0, 8, "No high-risk keywords detected.", ln=True)

        # Output to Buffer
        buffer = io.BytesIO()
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        buffer.write(pdf_bytes)
        buffer.seek(0)
        return buffer

# --- 3. STREAMLIT UI ---
def main():
    st.set_page_config(page_title="Merchant OSINT Scanner", page_icon="🛡️")
    st.title("🛡️ Merchant OSINT & Risk Scanner")
    st.markdown("Streamlined RBI Compliance & Web Intelligence Tool")

    with st.container():
        col1, col2 = st.columns(2)
        url_input = col1.text_input("Merchant URL", placeholder="example.com")
        biz_name = col2.text_input("Legal Business Name", placeholder="XYZ Pvt Ltd")
        
        scan_btn = st.button("Run OSINT Audit", type="primary")

    # The "Google Engineer" fix: Use session_state to prevent data loss on re-renders
    if scan_btn:
        if not url_input or not biz_name:
            st.error("Please enter both URL and Business Name.")
        else:
            with st.spinner("Scanning website, checking WHOIS, and analyzing compliance..."):
                scanner = MerchantScanner(url_input)
                results = scanner.scan()
                st.session_state['scan_results'] = results
                st.session_state['biz_name'] = biz_name

    # Display results ONLY if they exist in session state
    if 'scan_results' in st.session_state:
        res = st.session_state['scan_results']
        b_name = st.session_state['biz_name']

        st.divider()
        if res["status"] == "Failed":
            st.error(f"Failed to scan website. The merchant might have an anti-bot firewall. (Error: {res.get('error_msg', 'Unknown')})")
        else:
            # Metrics
            st.subheader(f"Results for {b_name}")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Domain Age", res["domain_age"])
            m2.metric("GST Disclosed", res["gst_found"])
            m3.metric("Address Disclosed", res["address_found"])
            m4.metric("Refund Policy", res["refund_policy"])

            # Risk Alert
            if res["risks_detected"]:
                st.error(f"⚠️ High-Risk Keywords Found: {', '.join(set(res['risks_detected']))}")
            else:
                st.success("✅ No high-risk keywords detected on the main page.")

            # Social Media Quick Link
            st.info(f"🔍 [Click here to check Google for Scam/Fraud reviews regarding '{b_name}'](https://www.google.com/search?q={b_name.replace(' ', '+')}+reviews+scam+fraud)")

        # Generate & Show Download Button
        pdf_buffer = PDFReport.create(res, b_name)
        st.download_button(
            label="📥 Download Official Audit Report (PDF)",
            data=pdf_buffer,
            file_name=f"Audit_{b_name.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )

if __name__ == "__main__":
    main()