import argparse
import re
from pathlib import Path
import fitz




def find_first_existing_font(candidates):
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def resolve_default_fonts():
    windows_fonts = Path(r"C:\Windows\Fonts")
    bold_candidates = [
        windows_fonts / "arialbd.ttf",
        windows_fonts / "tahomabd.ttf",
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    viet_candidates = [
        windows_fonts / "arialbd.ttf",
        windows_fonts / "arial.ttf",
        windows_fonts / "tahoma.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    font_bold = find_first_existing_font(bold_candidates)
    font_viet = find_first_existing_font(viet_candidates)
    if not font_bold:
        raise FileNotFoundError("Khong tim thay font in dam phu hop.")
    if not font_viet:
        raise FileNotFoundError("Khong tim thay font ho tro tieng Viet phu hop.")
    return font_bold, font_viet


def update_pdf(input_pdf, output_pdf, font_bold):
    doc = fitz.open(str(input_pdf))
    try:
        if doc.page_count == 0:
            raise ValueError("File PDF khong co trang nao.")

        white = (1, 1, 1)
        black = (0, 0, 0)

        for page in doc:
            # 1) Tìm t?t c? "SL:" và ch? x? lý khi s? lu?ng >= 2
            instances = page.search_for("SL:")

            for rect in instances:
                # M? r?ng rect sang ph?i d? d?c s? phía sau "SL:"
                extended_rect = fitz.Rect(rect.x0, rect.y0, rect.x1 + 30, rect.y1)
                snippet = page.get_text("text", clip=extended_rect).strip()

                match = re.search(r"SL:\s*(\d+)", snippet)
                if not match:
                    continue

                quantity = int(match.group(1))
                if quantity < 2:
                    continue  # SL: 1 ? b? qua, gi? nguyên

                full_text = f"SL: {quantity}"
                full_rect = fitz.Rect(rect.x0, rect.y0, rect.x1 + 30, rect.y1)

                page.draw_rect(full_rect, color=white, fill=white)  # xóa ch? cu
                tw = fitz.TextWriter(page.rect)
                tw.append(
                    (full_rect.x0, full_rect.y1),
                    full_text,
                    font=fitz.Font(fontfile=font_bold),
                    fontsize=11,
                )
                tw.write_text(page, color=black)

            # 3) Tìm "Combo" ? in d?m + g?ch chân (không dè ch? khác)
            combo_instances = page.search_for("Combo")
            for rect in combo_instances:
                combo_rect = fitz.Rect(rect)
                # Xóa ch? cu dúng vùng g?c
                page.draw_rect(combo_rect, color=white, fill=white)

                # Vi?t l?i "Combo" bold, fontsize v?a khít ô g?c
                bold_font = fitz.Font(fontfile=font_bold)
                fit_size = combo_rect.height * 0.85
                tw2 = fitz.TextWriter(page.rect)
                tw2.append(
                    (combo_rect.x0, combo_rect.y1 - 1),
                    "Combo",
                    font=bold_font,
                    fontsize=fit_size,
                )
                tw2.write_text(page, color=black)

                # G?ch chân d? n?i b?t khi in den tr?ng
                page.draw_line(
                    fitz.Point(combo_rect.x0, combo_rect.y1 + 1),
                    fitz.Point(combo_rect.x1, combo_rect.y1 + 1),
                    color=black, width=1.0,
                )

        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_pdf))
    finally:
        doc.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Edit Shopee SPX shipping label")
    parser.add_argument("input_pdf", nargs="?", help="Input PDF path")
    parser.add_argument("output_pdf", nargs="?", help="Output PDF path")
    parser.add_argument("--font-bold", dest="font_bold", help="Bold font file path")
    parser.add_argument("--font-viet", dest="font_viet", help="Vietnamese-capable font file path")
    return parser.parse_args()


def main():
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    input_pdf  = Path(args.input_pdf)  if args.input_pdf  else script_dir / "test.pdf"
    output_pdf = Path(args.output_pdf) if args.output_pdf else script_dir / "label_updated.pdf"

    if not input_pdf.exists():
        raise FileNotFoundError(f"Khong tim thay file input: {input_pdf}")

    default_bold, default_viet = resolve_default_fonts()
    font_bold = args.font_bold or default_bold

    update_pdf(input_pdf, output_pdf, font_bold=font_bold)
    print(f"Da luu: {output_pdf}")


if __name__ == "__main__":
    main()