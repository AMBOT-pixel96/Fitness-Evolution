from fpdf import FPDF
import pandas as pd
import io
from datetime import datetime

class BiometricReport(FPDF):
    def header(self):
        # Full Page Dark Background
        self.set_fill_color(5, 10, 14) 
        self.rect(0, 0, 210, 297, 'F')
        
        # Header Text - Cyan Neon
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(0, 242, 255) 
        self.set_xy(15, 15)
        self.cell(0, 10, 'A.R.V.I.S. BIOMETRIC DOSSIER', 0, 1, 'L')
        
        # Neon Divider
        self.set_draw_color(0, 242, 255)
        self.set_line_width(0.5)
        self.line(15, 25, 195, 25)
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(160, 176, 185)
        self.cell(0, 10, f'Page {self.page_no()} | CONFIDENTIAL | ECCENTRIC GENIUS PROTOCOL', 0, 0, 'C')

def generate_pdf_report(df, metrics, start_date, end_date):
    pdf = BiometricReport()
    pdf.set_margins(15, 20, 15)
    pdf.add_page()
    
    # Date Reconciliation
    start_dt = pd.to_datetime(start_date).normalize()
    end_dt = pd.to_datetime(end_date).normalize()
    
    mask = (df['date'].dt.normalize() >= start_dt) & (df['date'].dt.normalize() <= end_dt)
    report_df = df.loc[mask]
    
    # --- EXECUTIVE SUMMARY ---
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, f"Analysis Period: {start_dt.strftime('%d %b %y')} - {end_dt.strftime('%d %b %y')}", 0, 1)
    
    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(160, 176, 185)
    summary = (f"Current Mass: {metrics['weight']}kg. Maintenance: {metrics['maintenance']}kcal. "
               f"Thermodynamic Status: {metrics['deficit']}% deficit.")
    pdf.multi_cell(0, 8, summary)
    pdf.ln(10)

    # --- DATA GRID ---
    pdf.set_fill_color(10, 25, 38) 
    pdf.set_text_color(0, 242, 255)
    pdf.set_font('Helvetica', 'B', 10)
    
    # Column Widths (Total 180mm)
    w_date, w_wt, w_cal, w_brn, w_net = 35, 30, 35, 35, 45
    
    pdf.cell(w_date, 10, ' DATE', 1, 0, 'C', True)
    pdf.cell(w_wt, 10, ' WEIGHT', 1, 0, 'C', True)
    pdf.cell(w_cal, 10, ' CALS IN', 1, 0, 'C', True)
    pdf.cell(w_brn, 10, ' BURNED', 1, 0, 'C', True)
    pdf.cell(w_net, 10, ' NET DELTA', 1, 1, 'C', True)

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(255, 255, 255)
    
    if report_df.empty:
        pdf.cell(180, 10, "DATABASE EMPTY FOR SELECTED PERIOD", 1, 1, 'C')
    else:
        for _, row in report_df.iterrows():
            pdf.cell(w_date, 8, row['date'].strftime('%d-%b-%y'), 1, 0, 'C')
            pdf.cell(w_wt, 8, f"{float(row.get('weight', 0)):.1f}", 1, 0, 'C')
            pdf.cell(w_cal, 8, f"{int(row.get('calories', 0))}", 1, 0, 'C')
            pdf.cell(w_brn, 8, f"{int(row.get('burned', 0))}", 1, 0, 'C')
            pdf.cell(w_net, 8, f"{int(row.get('Net', 0))}", 1, 1, 'C')

    # --- CRITICAL FIX: MANUALLY RESET POSITION ---
    pdf.ln(20) # Move down significantly
    pdf.set_x(15) # HARD RESET to left margin
    
    # --- ANALYTICS ---
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(0, 242, 255)
    pdf.cell(0, 10, "A.R.V.I.S. PREDICTIVE INSIGHTS", 0, 1)
    
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(255, 255, 255)
    
    avg_net = report_df['Net'].mean() if not report_df.empty else 0
    insight_1 = f"- METABOLIC STATUS: {'In Deficit' if avg_net < 0 else 'Surplus/Maintenance'}. Avg Net: {int(avg_net)} kcal/day."
    insight_2 = f"- PROJECTION: Current Rate of Change: {metrics['weekly_loss']} kg/week."
    insight_3 = f"- KETOSIS PROTOCOL: {'ACTIVE' if metrics['keto'] else 'INACTIVE (GLUCOSE DOMINANT)'}."

    # Using explicit width of 180 to prevent 'No space' error
    pdf.multi_cell(180, 8, insight_1)
    pdf.multi_cell(180, 8, insight_2)
    pdf.multi_cell(180, 8, insight_3)

    return pdf.output()
