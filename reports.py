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
        self.set_xy(10, 10)
        self.cell(0, 10, 'A.R.V.I.S. BIOMETRIC DOSSIER', 0, 1, 'L')
        
        # Neon Divider Line
        self.set_draw_color(0, 242, 255)
        self.line(10, 22, 200, 22)
        self.set_y(30) # Ensure content starts below header

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(160, 176, 185)
        self.cell(0, 10, f'Page {self.page_no()} | Confidential Playbook Genius Protocol', 0, 0, 'C')

def generate_pdf_report(df, metrics, start_date, end_date):
    pdf = BiometricReport()
    pdf.set_margins(15, 20, 15) # Standardized margins
    pdf.add_page()
    
    # Ensure dates are comparable
    start_dt = pd.to_datetime(start_date).normalize()
    end_dt = pd.to_datetime(end_date).normalize()
    
    # Filter Data
    mask = (df['date'].dt.normalize() >= start_dt) & (df['date'].dt.normalize() <= end_dt)
    report_df = df.loc[mask]
    
    # --- SECTION 1: EXECUTIVE SUMMARY ---
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

    # --- SECTION 2: DETAILED METRICS TABLE ---
    # We use a total width of 180mm (to fit in 210mm with 15mm margins)
    pdf.set_fill_color(10, 25, 38) 
    pdf.set_text_color(0, 242, 255)
    pdf.set_font('Helvetica', 'B', 10)
    
    # Table Header
    pdf.cell(35, 10, ' Date', 1, 0, 'C', True)
    pdf.cell(30, 10, ' Weight', 1, 0, 'C', True)
    pdf.cell(35, 10, ' Calories', 1, 0, 'C', True)
    pdf.cell(35, 10, ' Burned', 1, 0, 'C', True)
    pdf.cell(45, 10, ' Net Status', 1, 1, 'C', True)

    # Table Body
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(255, 255, 255)
    
    if report_df.empty:
        pdf.cell(180, 10, "No data logged for this period.", 1, 1, 'C')
    else:
        for index, row in report_df.iterrows():
            pdf.cell(35, 8, row['date'].strftime('%d-%b-%y'), 1, 0, 'C')
            pdf.cell(30, 8, f"{float(row.get('weight', 0)):.1f}", 1, 0, 'C')
            pdf.cell(35, 8, f"{int(row.get('calories', 0))}", 1, 0, 'C')
            pdf.cell(35, 8, f"{int(row.get('burned', 0))}", 1, 0, 'C')
            pdf.cell(45, 8, f"{int(row.get('Net', 0))}", 1, 1, 'C')

    # --- SECTION 3: ANALYTICS & INSIGHTS ---
    pdf.ln(15) # Big jump to clear the table
    pdf.set_x(15) # Force cursor back to left margin
    
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(0, 242, 255)
    pdf.cell(0, 10, "A.R.V.I.S. ANALYTICS & INSIGHTS", 0, 1)
    
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(255, 255, 255)
    
    avg_net = report_df['Net'].mean() if not report_df.empty else 0
    
    # Build text blocks
    if avg_net < 0:
        i1 = f"- FAT LOSS ENGINE: Active. Average daily deficit of {abs(int(avg_net))} kcal."
    else:
        i1 = "- ANABOLIC PHASE: Net positive caloric intake detected."
        
    i2 = f"- PROJECTION: Current Rate of Loss: {metrics['weekly_loss']} kg/week."
    i3 = f"- KETOSIS PROTOCOL: {'Strict adherence detected.' if metrics['keto'] else 'Glucose-dominant metabolism.'}"

    # Render Multi-cells with explicit width (0 = margin to margin)
    pdf.multi_cell(0, 8, i1)
    pdf.multi_cell(0, 8, i2)
    pdf.multi_cell(0, 8, i3)

    return pdf.output()
