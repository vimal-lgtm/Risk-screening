# -*- coding: utf-8 -*-
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from urllib.parse import urljoin, urlparse
import whois
import plotly.express as px
import io

# --- CONFIGURATION: RISK TAXONOMY ---
RISK_TAXONOMY = {
    "Financial/Investment": {"keywords": ["forex", "binary options", "guaranteed returns", "daily profit"], "weight": 1.5},
    "Banned/Illegal": {"keywords": ["narcotics", "escort", "marijuana", "weed", "weapons"], "weight": 2.0},
    "Gambling/Gaming": {"keywords": ["betting", "casino", "poker", "lottery", "wager"], "weight": 1.2},
    "Negative Sentiment": {"keywords": ["scam", "fraud", "fake", "worst", "stole", "cheated"], "weight": 1.5}
}

class PIIShield:
    """Masks sensitive customer data for PCI-DSS & DPDP compliance."""
    @staticmethod
    def mask_email(email):
        if pd.isna(email) or "@" not in str(email): return email
        name, domain = str(email).split("@")
        return f"{name[0]}***@{domain}"

    @staticmethod
    def mask_name(name):
        if pd.isna(name): return name
        parts = str(name).split()
        masked = [p[0] + "*" * (len(p)-1) for p in parts]
        return " ".join(masked)

class RiskEngine:
    """Handles Web Scraping, Compliance, and Domain Intelligence."""
    def __init__(self, url):
        self.url = url
        self.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        self.all_text = ""

    def deep_scan(self):
        try:
            r = requests.get(self.url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            for s in soup(["script", "style"]): s.decompose()
            self.all_text = soup.get_text().lower()
            
            # Sub-page crawling (T&C, About)
            links = {urljoin(self.url, a['href']) for a in soup.find_all('a', href=True) 
                     if any(x in a['href'].lower() for x in ['terms', 'about', 'legal', 'policy'])}
            for link in list(links)[:2]:
                sub_r = requests.get(link, headers=self.headers, timeout=5)
                sub_soup = BeautifulSoup(sub_r.text, 'html.parser')
                self.all_text += " " + sub_soup.get_text().lower()
            return True
        except: return False

    def get_domain_age(self):
        try:
            w = whois.whois(urlparse(self.url).netloc)
            c_date = w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
            age_days = (datetime.now() - c_date).days
            return age_days, "✅ Mature" if age_days > 365 else "⚠️ New Domain"
        except: return 0, "❌ Unknown"

    def check_compliance(self):
        gst = r'\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}'
        pin = r'\b\d{6}\b'
        results = {
            "GST": "✅ Found" if re.search(gst, self.all_text) else "❌ Missing",
            "Address (PIN)": "✅ Found" if re.search(pin, self.all_text) else "❌ Missing",
            "Refund Policy": "✅ Found" if "refund" in self.all_text else "❌ Missing"
        }
        return results

class TransactionAnalyst:
    """Analyzes Fintech Transaction Dumps with Anomaly Detection."""
    @staticmethod
    def run_audit(df):
        # Apply PII Masking
        if 'email' in df.columns: df['email'] = df['email'].apply(PIIShield.mask_email)
        if 'name' in df.columns: df['name'] = df['name'].apply(PIIShield.mask_name)
        
        anomalies = []
        if 'amount' in df.columns:
            high_val = df[df['amount'] > (df['amount'].mean() * 5)]
            if not high_val.empty: anomalies.append(f"Found {len(high_val)} High-Value Outliers (>5x average).")
        
        if 'customer_id' in df.columns:
            velocity = df.groupby('customer_id').size()
            if not velocity[velocity > 5].empty: anomalies.append("Velocity Trigger: Multiple customers with >5 txns.")
            
        return df, anomalies

# --- STREAMLIT UI ---
def main():
    st.set_page_config(page_title="Merchant Risk 360", layout="wide")
    st.title("🛡️ Merchant Risk & Transaction Intelligence 360")

    tab1, tab2 = st.tabs(["🌐 Website & OSINT Audit", "📊 Transaction Anomaly Analysis"])

    with tab1:
        col_in1, col_in2 = st.columns(2)
        url = col_in1.text_input("Merchant URL", placeholder="https://example.com")
        biz_name = col_in2.text_input("Business Name (for Social Search)")

        if st.button("Run Full Website Audit", type="primary"):
            engine = RiskEngine(url)
            if engine.deep_scan():
                days, age_status = engine.get_domain_age()
                comp = engine.check_compliance()
                
                # Metrics Row
                m1, m2, m3 = st.columns(3)
                m1.metric("Domain Age", f"{days} Days", age_status)
                m2.metric("GST Disclosure", comp["GST"])
                m3.metric("Address Disclosure", comp["Address (PIN)"])

                # Social Search
                st.info(f"🔍 [Click to search Social Media Sentiment for {biz_name}](https://www.google.com/search?q={biz_name}+reviews+scam)")
            else:
                st.error("Could not scan website. Check URL.")

    with tab2:
        st.subheader("Transaction Dump Upload (CSV)")
        file = st.file_uploader("Upload CSV (Required: name, email, amount, customer_id)", type="csv")
        if file:
            df = pd.read_csv(file)
            clean_df, anomalies = TransactionAnalyst.run_audit(df)
            
            st.write("### Masked Transaction Data (PCI-DSS Compliant)")
            st.dataframe(clean_df.head(10))
            
            if anomalies:
                for a in anomalies: st.warning(f"🚩 {a}")
            else: st.success("No major anomalies detected.")
            
            st.plotly_chart(px.histogram(df, x="amount", title="Transaction Volume Distribution"))

if __name__ == "__main__":
    main()