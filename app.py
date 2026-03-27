# -*- coding: utf-8 -*-
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from urllib.parse import urljoin, urlparse

# --- CONFIGURATION: RISK TAXONOMY ---
RISK_TAXONOMY = {
    "Financial/Investment": {"keywords": ["forex", "binary options", "guaranteed returns", "daily profit", "get rich"], "weight": 1.5},
    "Banned/Illegal": {"keywords": ["narcotics", "escort", "marijuana", "weed", "weapons", "fake id"], "weight": 2.0},
    "Gambling/Gaming": {"keywords": ["betting", "casino", "poker", "lottery", "wager", "matka"], "weight": 1.2},
    "High-Risk (EDD)": {"keywords": ["crypto", "bitcoin", "auction", "jewelry", "investment"], "weight": 0.8}
}

class RiskEngine:
    """Handles Web Scraping, Keyword Analysis, and Compliance Checks."""
    def __init__(self, url):
        self.url = url
        self.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        self.all_text = ""

    def deep_scan(self):
        try:
            r = requests.get(self.url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # 1. Extract Homepage
            for s in soup(["script", "style"]): s.decompose()
            self.all_text = soup.get_text().lower()

            # 2. Extract Sub-pages (T&C, About, Contact)
            links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(self.url, href)
                if urlparse(full_url).netloc == urlparse(self.url).netloc:
                    if any(word in href.lower() for word in ['terms', 'about', 'legal', 'contact', 'policy']):
                        links.add(full_url)
            
            for link in list(links)[:3]:
                sub_r = requests.get(link, headers=self.headers, timeout=5)
                sub_soup = BeautifulSoup(sub_r.text, 'html.parser')
                for s in sub_soup(["script", "style"]): s.decompose()
                self.all_text += " " + sub_soup.get_text().lower()
                
            return True
        except Exception as e:
            st.error(f"Scan failed: {e}")
            return False

    def analyze_keywords(self):
        findings = []
        score = 0
        for cat, data in RISK_TAXONOMY.items():
            found = [kw for kw in data['keywords'] if re.search(rf'\b{kw}\b', self.all_text)]
            if found:
                score += len(found) * 15 * data['weight']
                findings.append({"Category": cat, "Detected": ", ".join(found), "Severity": "High" if data['weight'] >= 1.5 else "Medium"})
        return findings, min(int(score), 100)

    def check_compliance(self):
        gst_pattern = r'\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}'
        pin_pattern = r'\b\d{6}\b'
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        
        results = {
            "GST Number": "✅ Found" if re.search(gst_pattern, self.all_text) else "❌ Missing",
            "Address (PIN)": "✅ Found" if re.search(pin_pattern, self.all_text) else "❌ Missing",
            "Support Email": "✅ Found" if re.search(email_pattern, self.all_text) else "❌ Missing",
            "Refund Policy": "✅ Found" if any(x in self.all_text for x in ["refund", "cancellation", "return"]) else "❌ Missing"
        }
        score = (list(results.values()).count("✅ Found") / len(results)) * 100
        return results, score

# --- STREAMLIT UI ---
def main():
    st.set_page_config(page_title="Merchant Risk Intelligence", layout="wide")
    st.title("🛡️ Merchant Risk & Compliance Intelligence")
    
    url = st.text_input("Enter Merchant URL:", placeholder="https://example.com")
    
    if st.button("Run Full Audit", type="primary"):
        if url:
            engine = RiskEngine(url)
            with st.spinner("Performing Deep Scan and Compliance Audit..."):
                if engine.deep_scan():
                    # 1. Keyword Risk
                    findings, risk_score = engine.analyze_keywords()
                    
                    # 2. Compliance Results
                    comp_data, trans_score = engine.check_compliance()

                    # --- UI DISPLAY ---
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Risk Score", f"{risk_score}/100", delta="High Risk" if risk_score > 60 else "Low Risk", delta_color="inverse")
                    with col2:
                        st.metric("Transparency Score", f"{int(trans_score)}%", delta="Compliant" if trans_score > 70 else "Non-Compliant")

                    st.divider()
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.write(f"**GST:** {comp_data['GST Number']}")
                    c2.write(f"**Address:** {comp_data['Address (PIN)']}")
                    c3.write(f"**Email:** {comp_data['Support Email']}")
                    c4.write(f"**Refund:** {comp_data['Refund Policy']}")

                    if findings:
                        st.subheader("High-Risk Keywords Detected")
                        st.table(pd.DataFrame(findings))
                    else:
                        st.success("No risky keywords found.")

if __name__ == "__main__":
    main()