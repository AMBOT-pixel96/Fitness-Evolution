from fpdf import FPDF
import pandas as pd
import io
from datetime import datetime

class BiometricReport(FPDF):
    def header(self):
        # Background Dark Fill
        self.set_fill_color(5, 10, 14) 
        self.rect(0, 0, 210, 297, 'F')
        
        # Header Text
        self.set_font('Helvetica', 'B', 15)
        self.set_text_color(0, 242, 255) # CYAN
        self.cell(0, 10, 'A.R.V.I.S. BIOMETRIC DOSSIER', 0, 1, 'L')
        
        # Neon Divider Line
        self.set_draw_color(0, 242, 255)
        self.line(10, 20, 200, 20)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(160, 176, 185)
        self.cell(0, 10, f'Page {self.page_no()} | Confidential Playbook Genius Protocol', 0, 0, 'C')

def generate_pdf_report(df, metrics, start_date, end_date):
    # Enable Unicode-friendly handling if possible, or use standard fonts
    pdf = BiometricReport()
    pdf.add_page()
    
    # Filter Data
    # Ensure dates are comparable
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    mask = (df['date'] >= start_dt) & (df['date'] <= end_dt)
    report_df = df.loc[mask]
    
    # Section 1: Executive Summary
    pdf.set_font('Helvetica', 'B', 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, f"Period: {start_dt.strftime('%d %b')} - {end_dt.strftime('%d %b')}", 0, 1)
    
    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(160, 176, 185)
    summary_text = (
        f"Subject weight: {metrics['weight']}kg. "
        f"Efficiency: {metrics['deficit']}% deficit vs "
        f"maintenance of {metrics['maintenance']} kcal."
    )
    pdf.multi_cell(0, 7, summary_text)
    pdf.ln(10)

    # Section 2: Detailed Metrics Table
    pdf.set_fill_color(10, 25, 38) 
    pdf.set_text_color(0, 242, 255)
    pdf.set_font('Helvetica', 'B', 11)
    
    # Adjusted widths to fit 190mm total
    pdf.cell(35, 10, ' Date', 1, 0, 'C', True)
    pdf.cell(30, 10, ' Weight', 1, 0, 'C', True)
    pdf.cell(35, 10, ' Calories', 1, 0, 'C', True)
    pdf.cell(35, 10, ' Burned', 1, 0, 'C', True)
    pdf.cell(55, 10, ' Net Status', 1, 1, 'C', True)

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(255, 255, 255)
    
    for index, row in report_df.iterrows():
        pdf.cell(35, 8, row['date'].strftime('%d-%b-%y'), 1, 0, 'C')
        pdf.cell(30, 8, f"{row['weight']:.1f}", 1, 0, 'C')
        pdf.cell(35, 8, str(int(row['calories'])), 1, 0, 'C')
        pdf.cell(35, 8, str(int(row['burned'])), 1, 0, 'C')
        
        # Visual color cue for net
        net_val = int(row['Net'])
        pdf.cell(55, 8, str(net_val), 1, 1, 'C')

    # Section 3: A.R.V.I.S. Insights
    pdf.ln(10)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(0, 242, 255)
    pdf.cell(0, 10, "A.R.V.I.S. ANALYTICS & INSIGHTS", 0, 1)
    
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(255, 255, 255)
    
    # CLEANING INSIGHTS: Replaced '•' with '-' to avoid Unicode Errors
    avg_net = report_df['Net'].mean() if not report_df.empty else 0
    
    if avg_net < 0:
        insight = f"- FAT LOSS ENGINE: Active. Average daily deficit of {abs(int(avg_net))} kcal."
    else:
        insight = "- ANABOLIC PHASE: Net positive caloric intake detected."
        
    pdf.multi_cell(0, 7, insight)
    pdf.multi_cell(0, 7, f"- PROJECTION: Current Rate of Loss: {metrics['weekly_loss']} kg/week.")
    
    keto_status = "Strict adherence detected." if metrics['keto'] else "Glucose-dominant metabolism."
    pdf.multi_cell(0, 7, f"- KETOSIS PROTOCOL: {keto_status}")

    # Return as binary stream
    return pdf.output()
