from fpdf import FPDF
import pandas as pd
import io
from datetime import datetime

class GeniusDossier(FPDF):
    def header(self):
        # Deep Black Canvas
        self.set_fill_color(5, 10, 14) 
        self.rect(0, 0, 210, 297, 'F')
        
        # Top-Right Branding
        self.set_font('Courier', 'B', 8)
        self.set_text_color(0, 242, 255)
        self.set_xy(160, 10)
        self.cell(40, 5, 'GENIUS PROTOCOL V4.0', 0, 1, 'R')
        
        # Main Title
        self.set_font('Helvetica', 'B', 24)
        self.set_text_color(255, 255, 255)
        self.set_xy(15, 20)
        self.cell(0, 15, 'BIOMETRIC DOSSIER', 0, 1, 'L')
        
        # Sleek Underline
        self.set_draw_color(0, 242, 255)
        self.set_line_width(0.8)
        self.line(15, 36, 60, 36)
        self.ln(15)

    def footer(self):
        self.set_y(-20)
        self.set_font('Courier', 'B', 8)
        self.set_text_color(50, 70, 80)
        self.line(15, 280, 195, 280)
        self.cell(0, 10, 'CLASSIFIED DATA | AUTHORIZED ACCESS ONLY | PHYSIQUE ASCENDING', 0, 0, 'L')
        self.cell(0, 10, f'SECURE PAGE {self.page_no()}', 0, 0, 'R')

def generate_pdf_report(df, metrics, start_date, end_date):
    pdf = GeniusDossier()
    pdf.set_margins(15, 25, 15)
    pdf.add_page()
    
    start_dt = pd.to_datetime(start_date).normalize()
    end_dt = pd.to_datetime(end_date).normalize()
    mask = (df['date'].dt.normalize() >= start_dt) & (df['date'].dt.normalize() <= end_dt)
    report_df = df.loc[mask]

    # --- TACTICAL OVERVIEW ---
    pdf.set_y(45)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0, 242, 255)
    pdf.cell(0, 10, 'I. EXECUTIVE SUMMARY', 0, 1)
    
    # Summary Box
    pdf.set_fill_color(15, 30, 45)
    pdf.rect(15, 55, 180, 35, 'F')
    pdf.set_xy(20, 58)
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(160, 176, 185)
    pdf.cell(60, 8, 'CURRENT MASS:', 0, 0)
    pdf.cell(60, 8, 'DAILY MAINTENANCE:', 0, 0)
    pdf.cell(60, 8, 'WEEKLY PROJECTION:', 0, 1)
    
    pdf.set_xy(20, 68)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(60, 10, f"{metrics['weight']} KG", 0, 0)
    pdf.cell(60, 10, f"{metrics['maintenance']} KCAL", 0, 0)
    pdf.set_text_color(57, 255, 20)
    pdf.cell(60, 10, f"-{metrics['weekly_loss']} KG", 0, 1)

    # --- BIOMETRIC LOG ---
    pdf.set_y(100)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0, 242, 255)
    pdf.cell(0, 10, 'II. BIOMETRIC LOG', 0, 1)
    
    # Minimalist Table Header
    pdf.set_font('Courier', 'B', 9)
    pdf.set_text_color(0, 242, 255)
    cols = {'DATE': 35, 'WEIGHT': 30, 'CALS IN': 35, 'BURNED': 35, 'NET DELTA': 45}
    for label, width in cols.items():
        pdf.cell(width, 10, label, 'B', 0, 'C')
    pdf.ln(12)

    # Data Rows
    pdf.set_font('Courier', '', 10)
    pdf.set_text_color(255, 255, 255)
    for _, row in report_df.iterrows():
        pdf.cell(35, 8, row['date'].strftime('%d %b %y').upper(), 0, 0, 'C')
        pdf.cell(30, 8, f"{float(row.get('weight', 0)):.1f}", 0, 0, 'C')
        pdf.cell(35, 8, f"{int(row.get('calories', 0))}", 0, 0, 'C')
        pdf.cell(35, 8, f"{int(row.get('burned', 0))}", 0, 0, 'C')
        
        net_val = int(row.get('Net', 0))
        pdf.set_text_color(57, 255, 20) if net_val < 0 else pdf.set_text_color(255, 49, 49)
        pdf.cell(45, 8, f"{net_val:+d}", 0, 1, 'C')
        pdf.set_text_color(255, 255, 255)

    # --- TACTICAL EVALUATION ---
    pdf.ln(15)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(0, 242, 255)
    pdf.cell(0, 10, 'III. TACTICAL EVALUATION', 0, 1)
    
    pdf.set_font('Helvetica', '', 11)
    avg_net = report_df['Net'].mean() if not report_df.empty else 0
    
    # Insights with icons replaced by text-safe markers
    evals = [
        f"[EFFICIENCY] Avg Net: {int(avg_net)} kcal. {'Optimal fat-burning state.' if avg_net < 0 else 'Surplus detected.'}",
        f"[PROJECTION] Current trajectory leads to target realization.",
        f"[METABOLISM] Ketosis Protocol: {'ACTIVE' if metrics['keto'] else 'GLUCOSE DOMINANT'}.",
        f"[BIO-STACK] Adherence to ECA/Berberine stack required for insulin sensitivity."
    ]
    
    for eval in evals:
        pdf.set_text_color(160, 176, 185)
        pdf.multi_cell(0, 8, eval)
        pdf.ln(2)

    return bytes(pdf.output())
