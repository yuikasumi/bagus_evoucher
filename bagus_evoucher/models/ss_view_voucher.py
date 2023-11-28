from odoo import api, fields, models
from odoo.exceptions import ValidationError
import fitz  # PyMuPDF
import base64
import requests

class VoucherViewerWizard(models.TransientModel):
    _name = 'voucher.viewer.wizard'
    _description = 'Voucher Viewer Wizard'

    name = fields.Char(string='Voucher Name')
    image_content = fields.Binary(string='Image Content', readonly=True)
    is_voucher_valid = fields.Boolean(string='Is Voucher Valid', default=False, readonly=True)
    def convert_pdf_to_image(self, pdf_url):
        # Ambil PDF dari URL
        response = requests.get(pdf_url)
        if response.status_code != 200:
            return []

        # Buka PDF
        pdf_stream = fitz.open(stream=response.content, filetype="pdf")
        images = []
        for page in pdf_stream:
            # Tentukan DPI yang lebih tinggi untuk gambar yang lebih jelas
            zoom_x = 1.5  # horizontal zoom
            zoom_y = 1.5  # vertical zoom
            mat = fitz.Matrix(zoom_x, zoom_y)  # zoom factor 2 in each dimension
            pix = page.get_pixmap(matrix=mat)  # render page to an image
            img_data = pix.tobytes("png")
            images.append(img_data)
        pdf_stream.close()
        return images

    
    def action_view_voucher(self):
        self.ensure_one()
        voucher = self.env['ss.evoucher'].search([('name', '=', self.name), ('link_pdf', '!=', '#'), ('status', '=', 'confirmed')], limit=1)
        if voucher:
            images = self.convert_pdf_to_image(voucher.link_pdf)
            if images:
                self.image_content = base64.b64encode(images[0])  # Mengambil gambar pertama
                self.is_voucher_valid = True
            else:
                self.is_voucher_valid = False
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'voucher.viewer.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
            }
        else:
            self.is_voucher_valid = False
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Warning',
                    'message': 'No valid voucher found or PDF link is not set.',
                    'sticky': False,
                }
            }

    def action_approve_voucher(self):
        self.ensure_one()
        voucher = self.env['ss.evoucher'].search([('name', '=', self.name)], limit=1)
        if voucher and voucher.link_pdf != '#':
            voucher.write({'status': 'done', 'approval': self.env.user.id})
            # Kosongkan field name dan image_content setelah voucher disetujui
            self.write({'name': '', 'image_content': False, 'is_voucher_valid': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'voucher.viewer.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'flags': {'form': {'action_buttons': True}}
        }

    def action_reject_voucher(self):
        self.ensure_one()
        voucher = self.env['ss.evoucher'].search([('name', '=', self.name)], limit=1)
        if voucher and voucher.link_pdf != '#':
            voucher.write({'status': 'cancel', 'approval': self.env.user.id})
            # Kosongkan field name dan image_content setelah voucher ditolak
            self.write({'name': '', 'image_content': False, 'is_voucher_valid': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'voucher.viewer.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'flags': {'form': {'action_buttons': True}}
        }