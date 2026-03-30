import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from fpdf import FPDF
import io
from datetime import datetime
from urllib.parse import urlparse

# --- 1. RUTHLESS SANITIZATION ---
def sanitize_for_pdf(text):
    """Strips ALL non-ASCII characters (emojis, ₹, smart quotes) to prevent PDF crashes."""
    if not text: return "N/A"
    # Keep only basic standard keyboard characters
    clean_text = re.sub(r'[^\x00-\x7F]+', ' ', str(text))
    return clean_text.strip()

# --- 2. RISK ENGINE (No OS-level dependencies) ---
class StableRiskEngine:
    def __init__(self, url):
        # Force strict HTTP/HTTPS
        if not url.startswith("http"):
            url = "https://" + url
        self.url = url
        # Impersonate a standard Chrome browser to bypass basic anti-bot blockers
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }

    def run_audit(self):
        domain = urlparse(self.url).netloc or self.url
        results = {
            "domain": domain,
            "status": "Failed to connect",
            "gst_detected": "No",
            "pin_detected": "No",
            "refund_policy": "No",
            "flags": []
        }

        try:
            # 10-second timeout to prevent indefinite hanging
            res = requests.get(self.url, headers=self.headers, timeout=10)
            res.raise_for_status()
            
            soup = BeautifulSoup(res.text, 'html.parser')
            for script in soup(["script", "style", "nav", "footer"]): 
                script.decompose()
            
            text = soup.get_text(separator=' ').lower()
            results["status"] = "Success"

            # Compliance Regex
            if re.search(r'\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}', text):
                results["gst_detected"] = "Yes"
            if re.search(r'\b\d{6}\b', text):
                results["pin_detected"] = "Yes"
            if any(word in text for word in ["refund", "cancellation", "return policy"]):
                results["refund_policy"] = "Yes"

            # Risk Regex (Targeted list)
            risk_words = ["forex", "binary options", "guaranteed returns", "crypto", "betting", "casino", "escort"]
            for word in risk_words:
                if re.search(rf'\b{word}\b', text):
                    results["flags"].append(word.upper())

        except Exception as e:
            results["error_detail"] = str(e)

        return results

# --- 3. SAFE PDF GENERATOR ---
def generate_audit_pdf(data, biz_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    # Header
    pdf.cell(0, 10, sanitize_for_pdf(f"Merchant Risk Audit: {biz_name}"), ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Domain: {data['domain']}", ln=True)
    pdf.ln(10)

    if data["status"] != "Success":
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, sanitize_for_pdf(f"Audit Failed: {data.get('error_detail', 'Network Error')}"), ln=True)
    else:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "1. Compliance Disclosures", ln=True)
        pdf.set_font("Arial", size=11)
        pdf.cell(0, 8, f"- GST Number: {data['gst_detected']}", ln=True)
        pdf.cell(0, 8, f"- Physical PIN: {data['pin_detected']}", ln=True)
        pdf.cell(0, 8, f"- Refund Policy: {data['refund_policy']}", ln=True)
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. High-Risk Triggers", ln=True)
        pdf.set_font("Arial", size=11)
        if data["flags"]:
            for flag in set(data["flags"]):
                pdf.cell(0, 8, f"- DETECTED: {flag}", ln=True)
        else:
            pdf.cell(0, 8, "- No high-risk keywords detected.", ln=True)

    pdf_bytes = pdf.output()
    return bytes(pdf_bytes)

# --- 4. DECOUPLED STREAMLIT UI ---
def main():
    st.set_page_config(page_title="Risk Scanner", page_icon="🛡️")
    st.title("🛡️ Core Risk Scanner")

    # Input Section
    col1, col2 = st.columns(2)
    url_input = col1.text_input("Merchant URL")
    biz_name = col2.text_input("Business Name")

    # Action Section
    if st.button("Run Security Audit", type="primary"):
        if url_input and biz_name:
            with st.spinner("Executing secure scan..."):
                engine = StableRiskEngine(url_input)
                # Store results safely in session state
                st.session_state['audit_data'] = engine.run_audit()
                st.session_state['biz_name'] = biz_name
        else:
            st.error("Please provide both URL and Business Name.")

    # Render Section (Only runs if data exists in state)
    if 'audit_data' in st.session_state:
        data = st.session_state['audit_data']
        b_name = st.session_state['biz_name']
        
        st.divider()
        if data["status"] != "Success":
            st.error(f"Website inaccessible. Error: {data.get('error_detail', 'Unknown')}")
        else:
            st.subheader(f"Audit Complete: {data['domain']}")
            m1, m2, m3 = st.columns(3)
            m1.metric("GST Disclosure", data["gst_detected"])
            m2.metric("Address Disclosure", data["pin_detected"])
            m3.metric("Refund Policy", data["refund_policy"])

            if data["flags"]:
                st.warning(f"🚩 Risks Found: {', '.join(set(data['flags']))}")
            else:
                st.success("✅ Clean keyword scan.")

        # Download button is entirely separate from the Scan button logic
        st.download_button(
            label="📥 Download Secure Audit Report",
            data=generate_audit_pdf(data, b_name),
            file_name=f"Audit_{b_name.replace(' ', '')}.pdf",
            mime="application/pdf"
        )

if __name__ == "__main__":
    main()