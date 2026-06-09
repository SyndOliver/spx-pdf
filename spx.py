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

            # Lấy toàn bộ text của page để kiểm tra tổng số lượng sản phẩm
            page_text = page.get_text("text")
            qty_match = re.search(r"Tổng SL sản phẩm:\s*(\d+)", page_text)
            if qty_match:
                total_qty = int(qty_match.group(1))
                if total_qty < 4:
                    lines = ["Quay video", "khi mở hàng"]
                    bold_font = fitz.Font(fontfile=font_bold)
                    target_fontsize = 30
                    
                    # Căn giữa trong cột bên trái (x từ 11.3 đến 210.0)
                    col_left = 11.3
                    col_right = 210.0
                    col_width = col_right - col_left
                    
                    line_widths = [bold_font.text_length(line, fontsize=target_fontsize) for line in lines]
                    line_xs = [col_left + (col_width - w) / 2.0 for w in line_widths]
                    
                    # Tọa độ y cho 2 dòng
                    write_y1 = 253.0
                    write_y2 = 277.0
                    
                    # Tính toán khung hộp xung quanh cả 2 dòng
                    min_x = min(line_xs) - 6
                    max_x = max(x + w for x, w in zip(line_xs, line_widths)) + 6
                    
                    box_rect = fitz.Rect(
                        min_x,
                        write_y1 - target_fontsize - 2,
                        max_x,
                        write_y2 + 4
                    )
                    page.draw_rect(box_rect, color=black, width=1.2)
                    
                    # Ghi 2 dòng chữ
                    tw_warn = fitz.TextWriter(page.rect)
                    tw_warn.append(
                        (line_xs[0], write_y1),
                        lines[0],
                        font=bold_font,
                        fontsize=target_fontsize,
                    )
                    tw_warn.append(
                        (line_xs[1], write_y2),
                        lines[1],
                        font=bold_font,
                        fontsize=target_fontsize,
                    )
                    tw_warn.write_text(page, color=black)


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

            # 2b) Xử lý trường hợp "SL:" bị tách thành "S" + "L:" do xuống dòng
            for idx, w in enumerate(all_words):
                if w[4].strip() != "S":
                    continue
                if idx + 1 >= len(all_words):
                    continue
                nw = all_words[idx + 1]
                nw_text = nw[4].strip()

                # Trường hợp 1: word tiếp theo là "L:" và số nằm ở word sau nữa
                # Trường hợp 2: word tiếp theo là "L:N" (dính liền số)
                quantity = None
                qty_word = None  # word chứa số lượng

                if nw_text == "L:" and idx + 2 < len(all_words):
                    qty_w = all_words[idx + 2]
                    if qty_w[4].strip().isdigit():
                        quantity = int(qty_w[4].strip())
                        qty_word = qty_w
                elif nw_text.startswith("L:"):
                    num_part = nw_text[2:].strip()
                    if num_part.isdigit():
                        quantity = int(num_part)
                        qty_word = nw  # số nằm chung word "L:2"

                if quantity is None or quantity < 2:
                    continue

                # Kiểm tra đây có phải là SL sản phẩm hay không
                # (bỏ qua "Tổng SL sản phẩm" ở dòng header)
                s_word = w
                # Nếu "S" nằm trong dòng "Tổng SL sản phẩm:" thì bỏ qua
                skip = False
                if idx >= 1:
                    prev_text = all_words[idx - 1][4].strip()
                    if prev_text in ("Tổng", "tổng"):
                        skip = True
                if skip:
                    continue

                full_text = f"SL: {quantity}"
                bold_font_sl = fitz.Font(fontfile=font_bold)
                target_fontsize = 11
                text_w_val = bold_font_sl.text_length(full_text, fontsize=target_fontsize)

                # Xóa word "S"
                s_erase = fitz.Rect(s_word[0], s_word[1],
                                    min(s_word[2] + 2, max_right_x), s_word[3])
                page.draw_rect(s_erase, color=white, fill=white)

                # Xóa word "L:" (hoặc "L:N")
                l_erase = fitz.Rect(nw[0], nw[1], nw[2] + 2, nw[3])
                page.draw_rect(l_erase, color=white, fill=white)

                # Xóa word số lượng nếu nó là word riêng biệt
                if qty_word is not None and qty_word is not nw:
                    q_erase = fitz.Rect(qty_word[0], qty_word[1],
                                        qty_word[2] + 2, qty_word[3])
                    page.draw_rect(q_erase, color=white, fill=white)

                # Ghi "SL: N" bold ở dòng "L:" (dòng dưới, có nhiều chỗ hơn)
                write_x = nw[0]
                write_y = nw[3]
                avail_w = max_right_x - write_x
                if text_w_val > avail_w and avail_w > 0:
                    target_fontsize *= avail_w / text_w_val

                tw = fitz.TextWriter(page.rect)
                tw.append(
                    (write_x, write_y),
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



                # Vẽ khung hình chữ nhật xung quanh chữ Combo thay vì gạch chân
                border_rect = fitz.Rect(
                    combo_rect.x0 - 2,
                    combo_rect.y0 - 1,
                    min(combo_rect.x0 + text_w + 2, max_right_x),
                    combo_rect.y1 + 1
                )
                page.draw_rect(border_rect, color=black, width=1.0)




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