# -*- coding: utf-8 -*-
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




def _find_qr_rect(page):
    """Tìm vị trí mã QR (hình vuông lớn nhất) trên trang."""
    imgs = page.get_images(full=True)
    for img in imgs:
        xref = img[0]
        rects = page.get_image_rects(xref)
        for r in rects:
            w, h = r.width, r.height
            if 0.7 < w / h < 1.3 and w > 30:
                return r
    return None


def update_pdf(input_pdf, output_pdf, font_bold):

    doc = fitz.open(str(input_pdf))

    try:

        if doc.page_count == 0:

            raise ValueError("File PDF khong co trang nao.")



        white = (1, 1, 1)

        black = (0, 0, 0)



        for page in doc:

            # Tìm QR rect để biết giới hạn bên phải
            qr_rect = _find_qr_rect(page)
            # Giới hạn x bên phải: không được vượt qua QR (trừ margin 3pt)
            max_right_x = (qr_rect.x0 - 3) if qr_rect else page.rect.width

            # 1) Tìm tất cả "SL:" và chỉ xử lý khi số lượng >= 2

            instances = page.search_for("SL:")



            # Lấy toàn bộ words của page một lần để tìm đúng vị trí
            all_words = page.get_text("words")

            for rect in instances:

                line_h = rect.height

                # Tìm đúng word "SL:" theo tọa độ (khớp với kết quả search_for)
                sl_idx = None
                for i, w in enumerate(all_words):
                    if w[4].strip() in ("SL:", "SL") and abs(w[0] - rect.x0) < 5 and abs(w[1] - rect.y0) < 5:
                        sl_idx = i
                        break

                if sl_idx is None or sl_idx + 1 >= len(all_words):
                    continue

                # Word liền sau "SL:" chính là số lượng (cùng dòng hoặc xuống dòng)
                next_w = all_words[sl_idx + 1]
                if not next_w[4].strip().isdigit():
                    continue

                quantity = int(next_w[4].strip())
                if quantity < 2:
                    continue  # SL: 1 -> bo qua, giu nguyen

                full_text = f"SL: {quantity}"
                bold_font_sl = fitz.Font(fontfile=font_bold)
                target_fontsize = 11
                text_w = bold_font_sl.text_length(full_text, fontsize=target_fontsize)

                # Kiểm tra số nằm ở dòng khác hay cùng dòng
                number_on_next_line = next_w[1] > rect.y1 - 2

                if number_on_next_line:
                    # Số bị xuống dòng → xóa "SL:" ở dòng cũ + số ở dòng dưới
                    # Ghi "SL: N" bold ở dòng dưới (x=next_w[0]) nơi có nhiều chỗ
                    sl_erase = fitz.Rect(rect.x0, rect.y0,
                                         min(rect.x1 + 2, max_right_x), rect.y1)
                    page.draw_rect(sl_erase, color=white, fill=white)
                    page.draw_rect(fitz.Rect(next_w[0], next_w[1], next_w[2], next_w[3]),
                                   color=white, fill=white)

                    # Viết "SL: N" bold ở vị trí dòng dưới (nhiều chỗ hơn)
                    write_x = next_w[0]
                    write_y = next_w[3]
                    # Đảm bảo text không tràn QR ngay cả ở dòng dưới
                    avail_w = max_right_x - write_x
                    if text_w > avail_w and avail_w > 0:
                        target_fontsize *= avail_w / text_w
                    tw = fitz.TextWriter(page.rect)
                    tw.append(
                        (write_x, write_y),
                        full_text,
                        font=bold_font_sl,
                        fontsize=target_fontsize,
                    )
                    tw.write_text(page, color=black)
                else:
                    # Số cùng dòng → xóa vùng SL: + số, ghi lại tại chỗ
                    # Adaptive fontsize nếu không đủ chỗ trước QR
                    avail_w = max_right_x - rect.x0
                    if text_w > avail_w and avail_w > 0:
                        target_fontsize *= avail_w / text_w
                        text_w = avail_w

                    erase_right = min(rect.x0 + max(rect.width, text_w + 2), max_right_x)
                    sl_erase = fitz.Rect(rect.x0, rect.y0, erase_right, rect.y1)
                    page.draw_rect(sl_erase, color=white, fill=white)

                    tw = fitz.TextWriter(page.rect)
                    tw.append(
                        (sl_erase.x0, sl_erase.y1),
                        full_text,
                        font=bold_font_sl,
                        fontsize=target_fontsize,
                    )
                    tw.write_text(page, color=black)



            # 3) Tìm "Combo" → in đậm + gạch chân (không đè chữ khác)

            combo_instances = page.search_for("Combo")

            for rect in combo_instances:

                combo_rect = fitz.Rect(rect)

                # Tính font size lớn hơn, nhưng giới hạn chiều rộng để không tràn
                bold_font = fitz.Font(fontfile=font_bold)
                target_size = combo_rect.height * 1.05
                text_w = bold_font.text_length("Combo", fontsize=target_size)

                # Không cho phép text rộng hơn 1.3x ô gốc (tránh đè chữ/QR bên cạnh)
                max_w = combo_rect.width * 1.3
                # Thêm: giới hạn bên phải không vượt QR
                available_w = max_right_x - combo_rect.x0
                max_w = min(max_w, available_w)
                if text_w > max_w:
                    target_size *= max_w / text_w
                    text_w = max_w

                fit_size = target_size

                # Xóa vùng vừa đủ cho text mới
                erase_rect = fitz.Rect(
                    combo_rect.x0, combo_rect.y0,
                    combo_rect.x0 + text_w + 1, combo_rect.y1
                )
                page.draw_rect(erase_rect, color=white, fill=white)

                tw2 = fitz.TextWriter(page.rect)

                tw2.append(

                    (combo_rect.x0, combo_rect.y1 - 1),

                    "Combo",

                    font=bold_font,

                    fontsize=fit_size,

                )

                tw2.write_text(page, color=black)



                # Gạch chân theo đúng chiều rộng text mới
                page.draw_line(

                    fitz.Point(combo_rect.x0, combo_rect.y1 + 1),

                    fitz.Point(combo_rect.x0 + text_w, combo_rect.y1 + 1),

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