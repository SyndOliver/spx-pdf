import os
import logging
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from spx import update_pdf, resolve_default_fonts

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Load font một lần khi khởi động ─────────────────────
FONT_BOLD, _ = resolve_default_fonts()


# ── /start ───────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Xin chào! Gửi file PDF nhãn vận chuyển SPX cho tôi.\n"
        "Tôi sẽ xử lý (in đậm SL ≥ 2, Combo) rồi trả lại file đã chỉnh."
    )


# ── Xử lý file PDF ──────────────────────────────────────
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document

    # Kiểm tra có phải PDF không
    if doc.mime_type != "application/pdf":
        await update.message.reply_text("⚠️ Vui lòng gửi file PDF.")
        return

    await update.message.reply_text("⏳ Đang xử lý...")

    try:
        # Tải file về thư mục tạm
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.pdf"
            output_path = Path(tmpdir) / "output.pdf"

            tg_file = await doc.get_file()
            await tg_file.download_to_drive(str(input_path))

            # Xử lý PDF
            update_pdf(input_path, output_path, font_bold=FONT_BOLD)

            # Gửi lại file đã chỉnh sửa
            original_name = doc.file_name or "label.pdf"
            output_name = original_name.rsplit(".", 1)[0] + "_updated.pdf"

            await update.message.reply_document(
                document=open(output_path, "rb"),
                filename=output_name,
                caption="✅ Đã xử lý xong!",
            )

    except Exception as e:
        logger.exception("Lỗi khi xử lý PDF")
        await update.message.reply_text(f"❌ Lỗi: {e}")


# ── Main ─────────────────────────────────────────────────
def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(
            "Chưa set TELEGRAM_BOT_TOKEN.\n"
            "Chạy: export TELEGRAM_BOT_TOKEN='your-token-here'"
        )

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    logger.info("🤖 Bot đang chạy...")
    app.run_polling()


if __name__ == "__main__":
    main()
