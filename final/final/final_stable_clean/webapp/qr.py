from __future__ import annotations

import io

import qrcode
from fastapi import Response


def qrcode_png_response(data: str) -> Response:
    img = qrcode.make(data, box_size=8, border=2)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")
