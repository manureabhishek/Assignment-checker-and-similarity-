"""
AssignCheck - Pure Python PDF Report Generator
Generates PDF 1.4 compliant reports with zero external dependencies.
"""

import time


class SimplePDF:
    def __init__(self):
        self.pages = []
        self.stream = []
        self.page_w = 595.28  # A4 width in pt
        self.page_h = 841.89  # A4 height in pt
        self.margin_x = 40
        self.margin_top = 800
        self.margin_bottom = 45
        self.y = self.margin_top
        self.page_num = 0

    def new_page(self):
        if self.stream:
            self.pages.append(" ".join(self.stream))
            self.stream = []
        self.page_num += 1
        self.y = self.margin_top
        self._draw_page_decorations()

    def _draw_page_decorations(self):
        # Header line
        self.set_stroke_color(0.85, 0.88, 0.92)
        self.set_line_width(0.75)
        self.line(self.margin_x, 815, self.page_w - self.margin_x, 815)

        # Header title
        self.draw_text("AssignCheck Evaluation Report", self.margin_x, 820, font="/F1", size=8, r=0.4, g=0.45, b=0.55)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        self.draw_text(f"Generated: {now_str}", self.page_w - self.margin_x - 130, 820, font="/F2", size=8, r=0.4, g=0.45, b=0.55)

        # Footer line
        self.line(self.margin_x, 38, self.page_w - self.margin_x, 38)
        self.draw_text("AssignCheck C++ DSA Engine  |  Confidential Academic Report", self.margin_x, 26, font="/F2", size=7.5, r=0.45, g=0.5, b=0.55)
        self.draw_text(f"Page {self.page_num}", self.page_w - self.margin_x - 40, 26, font="/F1", size=7.5, r=0.45, g=0.5, b=0.55)

    def check_space(self, height_needed):
        if (self.y - height_needed) < self.margin_bottom:
            self.new_page()

    def set_fill_color(self, r, g, b):
        self.stream.append(f"{r:.3f} {g:.3f} {b:.3f} rg")

    def set_stroke_color(self, r, g, b):
        self.stream.append(f"{r:.3f} {g:.3f} {b:.3f} RG")

    def set_line_width(self, w):
        self.stream.append(f"{w:.2f} w")

    def rect(self, x, y, w, h, fill=True, stroke=False):
        op = "B" if (fill and stroke) else ("f" if fill else "S")
        self.stream.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re {op}")

    def line(self, x1, y1, x2, y2):
        self.stream.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def draw_text(self, text, x, y, font="/F2", size=10, r=0.1, g=0.1, b=0.1):
        if not text:
            return
        clean_text = (
            str(text)
            .replace("—", "-")
            .replace("–", "-")
            .replace("•", "*")
            .replace("“", '"')
            .replace("”", '"')
            .replace("‘", "'")
            .replace("’", "'")
            .replace("≥", ">=")
            .replace("≤", "<=")
            .replace("×", "x")
            .replace("·", ".")
            .replace("…", "...")
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        self.stream.append(f"{r:.3f} {g:.3f} {b:.3f} rg BT {font} {size} Tf {x:.2f} {y:.2f} Td ({clean_text}) Tj ET")

    def build(self):
        if self.stream:
            self.pages.append(" ".join(self.stream))
            self.stream = []

        total_pages = len(self.pages)
        if total_pages == 0:
            self.new_page()
            self.pages.append(" ".join(self.stream))
            total_pages = 1

        objects = []
        # obj 1: Catalog
        objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

        # obj 2: Pages
        page_obj_ids = [f"{8 + i * 2} 0 R" for i in range(total_pages)]
        kids_str = "[" + " ".join(page_obj_ids) + "]"
        objects.append(f"2 0 obj\n<< /Type /Pages /Kids {kids_str} /Count {total_pages} >>\nendobj\n".encode("latin1"))

        # obj 3..7: Fonts
        objects.append(b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n")
        objects.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
        objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n")
        objects.append(b"6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold >>\nendobj\n")
        objects.append(b"7 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique >>\nendobj\n")

        curr_obj = 8
        for p in self.pages:
            contents_id = curr_obj + 1
            page_obj = (
                f"{curr_obj} 0 obj\n"
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.page_w:.2f} {self.page_h:.2f}]\n"
                f"   /Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R /F4 6 0 R /F5 7 0 R >> >>\n"
                f"   /Contents {contents_id} 0 R >>\nendobj\n"
            )
            objects.append(page_obj.encode("latin1"))
            curr_obj += 1

            p_bytes = p.encode("latin1", errors="replace")
            stream_obj = (
                f"{curr_obj} 0 obj\n<< /Length {len(p_bytes)} >>\nstream\n".encode("latin1")
                + p_bytes
                + b"\nendstream\nendobj\n"
            )
            objects.append(stream_obj)
            curr_obj += 1

        out = bytearray(b"%PDF-1.4\n")
        xref = [0]
        for obj in objects:
            xref.append(len(out))
            out.extend(obj)

        startxref = len(out)
        out.extend(f"xref\n0 {len(xref)}\n0000000000 65535 f \n".encode("latin1"))
        for x in xref[1:]:
            out.extend(f"{x:010d} 00000 n \n".encode("latin1"))
        out.extend(f"trailer\n<< /Size {len(xref)} /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF\n".encode("latin1"))
        return bytes(out)


def build_final_report_pdf(report_data):
    """
    Builds a complete, formatted PDF evaluation report using data from parse_final_report().
    """
    pdf = SimplePDF()
    pdf.new_page()

    summary = report_data.get("summary", {})
    submissions = report_data.get("submissions", [])
    similarities = report_data.get("similarities", [])
    last_mod = report_data.get("last_modified") or time.strftime("%Y-%m-%d %H:%M:%S")

    # 1. Title Banner
    pdf.set_fill_color(0.06, 0.09, 0.16)  # Dark navy
    pdf.rect(pdf.margin_x, pdf.y - 52, pdf.page_w - 2 * pdf.margin_x, 56, fill=True, stroke=False)

    pdf.draw_text("ASSIGNCHECK  |  EVALUATION REPORT", pdf.margin_x + 16, pdf.y - 20, font="/F1", size=15, r=1, g=1, b=1)
    pdf.draw_text(f"Intelligent C++ DSA Engine  |  Last Evaluated: {last_mod}", pdf.margin_x + 16, pdf.y - 38, font="/F2", size=9, r=0.75, g=0.82, b=0.95)

    pdf.y -= 70

    # 2. Executive Summary Metrics Cards
    pdf.check_space(70)
    pdf.draw_text("EXECUTIVE EVALUATION SUMMARY", pdf.margin_x, pdf.y, font="/F1", size=11, r=0.15, g=0.2, b=0.3)
    pdf.y -= 8
    pdf.set_stroke_color(0.38, 0.4, 0.95)
    pdf.set_line_width(2)
    pdf.line(pdf.margin_x, pdf.y, pdf.margin_x + 180, pdf.y)
    pdf.y -= 14

    card_w = (pdf.page_w - 2 * pdf.margin_x - 30) / 4
    cards = [
        ("Submissions", str(summary.get("total_submissions", len(submissions))), "Processed in Queue", (0.23, 0.51, 0.96)),
        ("Compilation", f"{summary.get('successful_compilations', 0)}/{summary.get('total_submissions', len(submissions))}", "Passed gcc compile", (0.06, 0.72, 0.51)),
        ("Avg Correctness", f"{summary.get('average_correctness', 0.0)}%", "Test case pass rate", (0.55, 0.36, 0.96)),
        ("Similarity Alerts", str(summary.get("similarity_alerts", 0)), f"Max: {summary.get('max_similarity', 0.0)}%", (0.94, 0.27, 0.27) if summary.get("similarity_alerts", 0) > 0 else (0.45, 0.5, 0.6)),
    ]

    for idx, (label, val, sub_text, color) in enumerate(cards):
        cx = pdf.margin_x + idx * (card_w + 10)
        # Card background
        pdf.set_fill_color(0.96, 0.97, 0.99)
        pdf.set_stroke_color(0.88, 0.9, 0.94)
        pdf.set_line_width(1)
        pdf.rect(cx, pdf.y - 44, card_w, 48, fill=True, stroke=True)

        # Top color accent bar
        pdf.set_fill_color(*color)
        pdf.rect(cx, pdf.y + 2, card_w, 2, fill=True, stroke=False)

        pdf.draw_text(label, cx + 8, pdf.y - 12, font="/F1", size=8, r=0.4, g=0.45, b=0.55)
        pdf.draw_text(val, cx + 8, pdf.y - 28, font="/F1", size=14, r=color[0], g=color[1], b=color[2])
        pdf.draw_text(sub_text, cx + 8, pdf.y - 40, font="/F2", size=7, r=0.5, g=0.55, b=0.6)

    pdf.y -= 62

    # 3. Submissions Table
    pdf.check_space(80)
    pdf.draw_text("SUBMISSION VERIFICATION RESULTS", pdf.margin_x, pdf.y, font="/F1", size=11, r=0.15, g=0.2, b=0.3)
    pdf.y -= 8
    pdf.set_stroke_color(0.38, 0.4, 0.95)
    pdf.line(pdf.margin_x, pdf.y, pdf.margin_x + 190, pdf.y)
    pdf.y -= 14

    cols = [
        (pdf.margin_x, 120, "File Name"),
        (pdf.margin_x + 120, 95, "Compilation"),
        (pdf.margin_x + 215, 95, "Bracket Check"),
        (pdf.margin_x + 310, 85, "Tests Passed"),
        (pdf.margin_x + 395, 120, "Correctness"),
    ]

    def draw_sub_header():
        pdf.set_fill_color(0.91, 0.93, 0.97)
        pdf.rect(pdf.margin_x, pdf.y - 16, pdf.page_w - 2 * pdf.margin_x, 20, fill=True, stroke=False)
        for x_pos, _, title in cols:
            pdf.draw_text(title, x_pos + 6, pdf.y - 12, font="/F1", size=8.5, r=0.2, g=0.25, b=0.35)
        pdf.y -= 22

    draw_sub_header()

    if not submissions:
        pdf.draw_text("No submissions found in current report.", cols[0][0] + 6, pdf.y - 12, font="/F2", size=8.5, r=0.5, g=0.5, b=0.5)
        pdf.y -= 20

    for s in submissions:
        p_before = pdf.page_num
        pdf.check_space(24)
        if pdf.page_num != p_before:
            draw_sub_header()

        fname = s.get("filename", "")
        comp = s.get("compilation", "Unknown")
        bracket = s.get("bracket_check", "Unknown")
        passed = f"{s.get('tests_passed', 0)}/{s.get('total_tests', 0)}"
        corr = f"{s.get('correctness', 0.0)}%"

        # Alternating background
        pdf.set_fill_color(0.98, 0.99, 1.0)
        pdf.rect(pdf.margin_x, pdf.y - 14, pdf.page_w - 2 * pdf.margin_x, 18, fill=True, stroke=False)
        pdf.set_stroke_color(0.92, 0.93, 0.96)
        pdf.set_line_width(0.5)
        pdf.line(pdf.margin_x, pdf.y - 14, pdf.page_w - 2 * pdf.margin_x, pdf.y - 14)

        pdf.draw_text(fname, cols[0][0] + 6, pdf.y - 10, font="/F4", size=8.5, r=0.1, g=0.15, b=0.25)

        comp_col = (0.05, 0.6, 0.35) if s.get("compiled") else (0.85, 0.2, 0.2)
        pdf.draw_text(comp, cols[1][0] + 6, pdf.y - 10, font="/F1", size=8.5, r=comp_col[0], g=comp_col[1], b=comp_col[2])

        brk_col = (0.1, 0.4, 0.7) if s.get("balanced") else (0.85, 0.2, 0.2)
        pdf.draw_text(bracket, cols[2][0] + 6, pdf.y - 10, font="/F2", size=8.5, r=brk_col[0], g=brk_col[1], b=brk_col[2])

        pdf.draw_text(passed, cols[3][0] + 6, pdf.y - 10, font="/F4", size=8.5, r=0.2, g=0.25, b=0.3)
        pdf.draw_text(corr, cols[4][0] + 6, pdf.y - 10, font="/F1", size=8.5, r=comp_col[0], g=comp_col[1], b=comp_col[2])

        pdf.y -= 18

        # Test details if available
        details = s.get("test_details", [])
        if details:
            for td in details:
                p_td = pdf.page_num
                pdf.check_space(14)
                if pdf.page_num != p_td:
                    draw_sub_header()
                status_str = "PASS" if td.get("passed") else "FAIL"
                col_td = (0.05, 0.6, 0.35) if td.get("passed") else (0.85, 0.2, 0.2)
                t_str = f"  - Test {td.get('test_num')}: {status_str} | Input: [{td.get('input')}] | Expected: [{td.get('expected')}] | Actual: [{td.get('actual')}]"
                if len(t_str) > 78:
                    t_str = t_str[:75] + "..."
                pdf.draw_text(t_str, cols[0][0] + 14, pdf.y - 8, font="/F3", size=7.5, r=col_td[0], g=col_td[1], b=col_td[2])
                pdf.y -= 12

        # Compile error if compilation failed
        if not s.get("compiled") and s.get("compile_error"):
            p_ce = pdf.page_num
            pdf.check_space(14)
            if pdf.page_num != p_ce:
                draw_sub_header()
            first_err = s.get("compile_error").strip().splitlines()[0]
            if len(first_err) > 75:
                first_err = first_err[:72] + "..."
            pdf.draw_text(f"  * Error: {first_err}", cols[0][0] + 14, pdf.y - 8, font="/F3", size=7.5, r=0.85, g=0.2, b=0.2)
            pdf.y -= 12

    pdf.y -= 16

    # 4. Pairwise Similarity Table
    pdf.check_space(100)
    pdf.draw_text("PAIRWISE STRUCTURAL SIMILARITY ANALYSIS", pdf.margin_x, pdf.y, font="/F1", size=11, r=0.15, g=0.2, b=0.3)
    pdf.y -= 8
    pdf.set_stroke_color(0.38, 0.4, 0.95)
    pdf.line(pdf.margin_x, pdf.y, pdf.margin_x + 230, pdf.y)
    pdf.y -= 14

    sim_cols = [
        (pdf.margin_x, 140, "Submission Pair"),
        (pdf.margin_x + 140, 75, "Token (50%)"),
        (pdf.margin_x + 215, 75, "Tree (25%)"),
        (pdf.margin_x + 290, 75, "Graph (25%)"),
        (pdf.margin_x + 365, 75, "Overall"),
        (pdf.margin_x + 440, 75, "Alert Status"),
    ]

    def draw_sim_header():
        pdf.set_fill_color(0.91, 0.93, 0.97)
        pdf.rect(pdf.margin_x, pdf.y - 16, pdf.page_w - 2 * pdf.margin_x, 20, fill=True, stroke=False)
        for x_pos, _, title in sim_cols:
            pdf.draw_text(title, x_pos + 4, pdf.y - 12, font="/F1", size=8, r=0.2, g=0.25, b=0.35)
        pdf.y -= 22

    draw_sim_header()

    if not similarities:
        pdf.draw_text("No pairwise similarity data available in current report.", sim_cols[0][0] + 4, pdf.y - 12, font="/F2", size=8.5, r=0.5, g=0.5, b=0.5)
        pdf.y -= 20

    for pair in similarities:
        p_sim = pdf.page_num
        pdf.check_space(22)
        if pdf.page_num != p_sim:
            draw_sim_header()

        pair_str = f"{pair.get('file1')} vs {pair.get('file2')}"
        tok = f"{pair.get('token_similarity', 0.0)}%"
        tree = f"{pair.get('tree_similarity', 0.0)}%"
        graph = f"{pair.get('graph_similarity', 0.0)}%"
        ov = f"{pair.get('overall_similarity', 0.0)}%"
        stat = pair.get("status", "")
        is_alert = pair.get("is_alert", False)

        if is_alert:
            pdf.set_fill_color(1.0, 0.95, 0.95)
        else:
            pdf.set_fill_color(0.98, 0.99, 1.0)

        pdf.rect(pdf.margin_x, pdf.y - 14, pdf.page_w - 2 * pdf.margin_x, 18, fill=True, stroke=False)
        pdf.set_stroke_color(0.92, 0.93, 0.96)
        pdf.line(pdf.margin_x, pdf.y - 14, pdf.page_w - 2 * pdf.margin_x, pdf.y - 14)

        name_col = (0.85, 0.15, 0.15) if is_alert else (0.1, 0.15, 0.25)
        pdf.draw_text(pair_str, sim_cols[0][0] + 4, pdf.y - 10, font="/F4", size=8, r=name_col[0], g=name_col[1], b=name_col[2])
        pdf.draw_text(tok, sim_cols[1][0] + 4, pdf.y - 10, font="/F3", size=8, r=0.2, g=0.3, b=0.5)
        pdf.draw_text(tree, sim_cols[2][0] + 4, pdf.y - 10, font="/F3", size=8, r=0.3, g=0.2, b=0.6)
        pdf.draw_text(graph, sim_cols[3][0] + 4, pdf.y - 10, font="/F3", size=8, r=0.4, g=0.2, b=0.7)

        ov_col = (0.85, 0.15, 0.15) if is_alert else (0.05, 0.55, 0.45)
        pdf.draw_text(ov, sim_cols[4][0] + 4, pdf.y - 10, font="/F1", size=8.5, r=ov_col[0], g=ov_col[1], b=ov_col[2])

        stat_col = (0.85, 0.15, 0.15) if is_alert else (0.4, 0.45, 0.55)
        pdf.draw_text(stat, sim_cols[5][0] + 4, pdf.y - 10, font="/F1" if is_alert else "/F2", size=7.5, r=stat_col[0], g=stat_col[1], b=stat_col[2])

        pdf.y -= 18

    # 5. Disclaimer Box
    pdf.check_space(55)
    pdf.y -= 10
    pdf.set_fill_color(0.99, 0.98, 0.95)
    pdf.set_stroke_color(0.9, 0.75, 0.4)
    pdf.set_line_width(1)
    pdf.rect(pdf.margin_x, pdf.y - 36, pdf.page_w - 2 * pdf.margin_x, 40, fill=True, stroke=True)

    pdf.draw_text("ACADEMIC & METHODOLOGICAL DISCLAIMER:", pdf.margin_x + 12, pdf.y - 12, font="/F1", size=8, r=0.6, g=0.4, b=0.1)
    pdf.draw_text("Structural similarity metrics are mathematical indicators of token multiset, scope-nesting, and sequential transition likeness.", pdf.margin_x + 12, pdf.y - 22, font="/F2", size=7.5, r=0.45, g=0.35, b=0.2)
    pdf.draw_text("Similarity scores do NOT independently prove plagiarism or academic dishonesty. Manual instructor review is mandatory.", pdf.margin_x + 12, pdf.y - 32, font="/F5", size=7.5, r=0.45, g=0.35, b=0.2)

    return pdf.build()
