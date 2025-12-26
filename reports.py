from fpdf import FPDF
import pandas as pd
import io
from datetime import datetime

class BiometricReport(FPDF):
    def header(self):
        self.set_fill_color(5, 10, 14) # BG_DARK
        self.rect(0, 0, 210, 297, 'F')
        self.set_font('Arial', 'B', 15)
        self.set_text_color(0, 242, 255) # CYAN
        self.cell(0, 10, 'A.R.V.I.S. BIOMETRIC DOSSIER', 0, 1, 'L')
        self.set_draw_color(0, 242, 255)
        self.line(10, 20, 200, 20)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(160, 176, 185)
        self.cell(0, 10, f'Page {self.page_no()} | Confidential Playbook Genius Protocol', 0, 0, 'C')

def generate_pdf_report(df, metrics, start_date, end_date):
    pdf = BiometricReport()
    pdf.add_page()
    
    # Filter Data
    mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
    report_df = df.loc[mask]
    
    # Section 1: Executive Summary
    pdf.set_font('Arial', 'B', 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, f"Period: {start_date.strftime('%d %b')} - {end_date.strftime('%d %b')}", 0, 1)
    
    pdf.set_font('Arial', '', 12)
    pdf.set_text_color(160, 176, 185)
    summary_text = (
        f"The subject's current weight is stabilized at {metrics['weight']}kg. "
        f"Thermodynamic efficiency is running at {metrics['deficit']}% deficit relative to "
        f"a maintenance threshold of {metrics['maintenance']} kcal."
    )
    pdf.multi_cell(0, 7, summary_text)
    pdf.ln(10)

    # Section 2: Detailed Metrics Table
    pdf.set_fill_color(10, 25, 38) # Card Color
    pdf.set_text_color(0, 242, 255)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(40, 10, ' Date', 1, 0, 'C', True)
    pdf.cell(35, 10, ' Weight', 1, 0, 'C', True)
    pdf.cell(35, 10, ' Calories', 1, 0, 'C', True)
    pdf.cell(35, 10, ' Burned', 1, 0, 'C', True)
    pdf.cell(45, 10, ' Net Status', 1, 1, 'C', True)

    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(255, 255, 255)
    for index, row in report_df.iterrows():
        pdf.cell(40, 8, row['date'].strftime('%d-%b-%y'), 1, 0, 'C')
        pdf.cell(35, 8, str(row['weight']), 1, 0, 'C')
        pdf.cell(35, 8, str(int(row['calories'])), 1, 0, 'C')
        pdf.cell(35, 8, str(int(row['burned'])), 1, 0, 'C')
        net_color = (57, 255, 20) if row['Net'] < 0 else (255, 49, 49)
        pdf.cell(45, 8, str(int(row['Net'])), 1, 1, 'C')

    # Section 3: A.R.V.I.S. Insights
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(0, 242, 255)
    pdf.cell(0, 10, "A.R.V.I.S. ANALYTICS & INSIGHTS", 0, 1)
    
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(255, 255, 255)
    
    avg_net = report_df['Net'].mean()
    if avg_net < 0:
        insight = f"• FAT LOSS ENGINE: Active. Average daily deficit of {abs(int(avg_net))} kcal is sustainable."
    else:
        insight = "• ANABOLIC PHASE: Net positive caloric intake detected. Monitor for potential fat gain."
        
    pdf.multi_cell(0, 7, insight)
    pdf.multi_cell(0, 7, f"• PROJECTION: At current Rate of Loss ({metrics['weekly_loss']} kg/week), target physique realization is optimized.")
    pdf.multi_cell(0, 7, f"• KETOSIS PROTOCOL: {'Strict adherence detected. Metabolic flexibility increasing.' if metrics['keto'] else 'Glucose-dominant metabolism detected. Re-calibrate stack if Ketosis is the objective.'}")

    return pdf.output(dest='S')
