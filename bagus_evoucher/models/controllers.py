from odoo import http
from odoo.http import request, route
import base64
import io


class SSEVoucherController(http.Controller):

    @route(['/bagus_evoucher/pdf_download/<int:attachment_id>'], type='http', auth='public')
    def download_pdf(self, attachment_id, **kw):
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)
        if not attachment:
            return request.not_found()

        file_content = base64.b64decode(attachment.datas)
        pdf_http_response = http.send_file(
            io.BytesIO(file_content),
            filename=attachment.name,
            as_attachment=True,
            mimetype=attachment.mimetype
        )
        return pdf_http_response

