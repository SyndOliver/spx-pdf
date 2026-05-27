import fitz
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

doc = fitz.open('label_updated.pdf')
# Count all overlaps
overlap_count = 0
for i, page in enumerate(doc):
    qr_rect = None
    imgs = page.get_images(full=True)
    for img in imgs:
        xref = img[0]
        rects = page.get_image_rects(xref)
        for r in rects:
            w, h = r.width, r.height
            if 0.7 < w/h < 1.3 and w > 30:
                qr_rect = r
                break
    if not qr_rect:
        continue
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            bbox = line["bbox"]
            if bbox[0] < 200 and bbox[2] > qr_rect.x0 and bbox[1] < qr_rect.y1 and bbox[3] > qr_rect.y0:
                text = "".join([span["text"] for span in line["spans"]])
                overlap_count += 1
                if "SL" in text or "Quay" in text or "video" in text or "hàng" in text:
                    print(f'\n  OVERLAP on page {i}: "{text}" @ x:{bbox[0]:.1f}-{bbox[2]:.1f}')

print(f'\nTotal overlaps: {overlap_count}')
print(f'Total images in doc: {sum(len(p.get_images(full=True)) for p in doc)}')
doc.close()
