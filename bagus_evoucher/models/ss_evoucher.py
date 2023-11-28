from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
import base64
import random
import string
import requests
import pytz


class SSEVoucher(models.Model):
    _name = 'ss.evoucher'
    _description = 'SS EVoucher'

    # Fungsi untuk generate nama default voucher berdasarkan login user ditambah string acak
    def _default_name(self):
        user_name = self.env.user.login[:4].upper()
        random_string = ''.join(random.choices(string.ascii_uppercase, k=4))
        return user_name + random_string


    name = fields.Char(string='Name', readonly=True, default=_default_name)
    type = fields.Selection([('evoucher', 'eVoucher'), ('biaya_harian', 'Biaya_Harian')], string='Type', required=True)
    date = fields.Date(string='Date', default=lambda self: fields.Date.context_today(self))
    total = fields.Float(string='Total', compute='_compute_total')
    license_plate = fields.Char(string='No Police')
    status = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancelled')], default='draft', string='Status')
    user_id = fields.Many2one('res.users', string='User', readonly=True, default=lambda self: self.env.user)
    driver = fields.Many2one('res.users', string='Driver')
    line_ids_evoucher = fields.One2many('ss.evoucher.line', 'evoucher_id', string='Lines eVoucher')
    line_ids_biaya_harian = fields.One2many('ss.evoucher.line', 'evoucher_id', string='Lines Biaya Harian')
    link_pdf = fields.Char(string="PDF Link", readonly=True, default="#")  # Field baru untuk link PDF
    date_print = fields.Char(string="Date Print", readonly=True)  # Field baru untuk link PDF
    information = fields.Text(string="Information")  # Field baru untuk link PDF
    revision = fields.Integer(string='Revision', default=0, readonly=True)
    approval = fields.Many2one('res.users', string='Approval', readonly=True)

    @api.model
    def _get_division_selection(self):
        department_model = self.env['hr.department']
        departments = department_model.search([])
        # Gunakan str(dept.id) sebagai kunci
        return [(str(dept.id), dept.name) for dept in departments]

    division = fields.Selection(selection='_get_division_selection', string='Division')
    division_name = fields.Char(string='Division Name', compute='_compute_division_name', store=False)

    @api.depends('division')
    def _compute_division_name(self):
        for record in self:
            if record.division:
                department_id = int(record.division)  # Mengonversi kembali ke integer
                department = self.env['hr.department'].browse(department_id)
                record.division_name = department.name if department else ''
            else:
                record.division_name = ''

    @api.depends('line_ids_biaya_harian.subtotal', 'line_ids_evoucher.subtotal')
    def _compute_total(self):
        for record in self:
            # Inisialisasi total dengan 0
            record.total = 0.0

            # Jika tipe adalah evoucher, hitung total dari line_ids_evoucher saja
            if record.type == 'evoucher':
                record.total = sum(line.subtotal for line in record.line_ids_evoucher)

            # Jika tipe adalah biaya_harian, hitung total dari line_ids_biaya_harian saja
            elif record.type == 'biaya_harian':
                record.total = sum(line.subtotal for line in record.line_ids_biaya_harian)



    # Fungsi untuk mengubah status eVoucher menjadi confirmed
    def action_confirm(self):
        self.write({'status': 'confirmed'})# Fungsi untuk mengubah status eVoucher menjadi confirmed

    def action_done(self):
        self.write({'status': 'done'})

    def action_cancel(self):
        self.write({'status': 'cancel'})

    def action_reprint(self):
        # Meningkatkan nilai 'revision' dengan 1
        self.revision += 1
        # Memanggil fungsi cetak
        self.action_print_now()

    # Fungsi untuk mencetak eVoucher
    def action_print_now(self):
        timezone_gmt7 = pytz.timezone('Asia/Jakarta')  # 'Asia/Jakarta' is in the GMT+7 timezone
        current_datetime_gmt7 = datetime.now(timezone_gmt7)
        formatted_datetime = current_datetime_gmt7.strftime("%d/%m/%Y %H:%M:%S")
        self.date_print = formatted_datetime
        # Membuat laporan PDF
        report = self.env.ref('bagus_evoucher.report_ss_evoucher')
        pdf_content, content_type = report._render([self.id])  # Mengupdate baris ini
        # Menyimpan PDF ke binary field atau ke penyimpanan lain
        pdf_name = "E-Voucher %s.pdf" % (self.name)
        attachment = self.env['ir.attachment'].create({
            'name': pdf_name,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name, 
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        # Membuat link untuk mengunduh PDF
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        pdf_link = "%s/bagus_evoucher/pdf_download/%s" % (base_url, attachment.id)
        # Mengupdate field link_pdf dengan link yang baru
        self.link_pdf = pdf_link
        
        #self.write({'status': 'printed'})
        self.send_post_request()

        # message = "Berhasil mengirim ke Printer, silahkan ambil di Ruangan Sales"

        # # Mengembalikan aksi untuk memicu popup pesan konfirmasi
        # return {
        #     'type': 'ir.actions.client',
        #     'tag': 'display_notification',
        #     'params': {
        #         'title': 'Sukses',
        #         'message': message,
        #         'sticky': True,  # True jika Anda ingin pesan tetap ada sampai ditutup pengguna
        #     }
        # }
        
        self.send_post_request()

        # Mengembalikan aksi untuk refresh halaman tanpa popup
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def send_post_request(self):
        url = "https://script.google.com/macros/s/AKfycbz2S0KgZgi-snqWVQuzjUzIP9Xu9NNDgKCpwvftJnYdeXpPaeU-jdcVnCNtU88ZZtAmxA/exec"
        data = {
            "apikey": "1111",
            "doc_url": self.link_pdf,
            "name": "{}.pdf".format(self.name),
            "size": "size",  # Adjust this as needed
            "date_doc": self.date.strftime("%Y-%m-%d") if self.date else "",  # Convert date to string
            "downloaded": 0,
            "print": 0,
            "print_date": self.date_print if self.date_print else ""
        }
        response = requests.post(url, json=data)
        return response

    # Override method write
    def write(self, vals):
        # Cek jika field 'type' ada dalam vals dan ingin diubah
        if 'type' in vals:
            for record in self:
                # Cek apakah line_ids memiliki data
                if record.line_ids_evoucher or record.line_ids_biaya_harian:
                    raise ValidationError(_("Tidak dapat merubah type jika memiliki data details."))
        return super(SSEVoucher, self).write(vals)

class SSEVoucherLine(models.Model):
    _name = 'ss.evoucher.line'
    _description = 'SS EVoucher Line'

    evoucher_id = fields.Many2one('ss.evoucher', string='EVoucher')
    salesman_id = fields.Many2one('res.users', string='Salesman')
    item = fields.Char(string='Item')
    service_id = fields.Many2one('ss.evoucher.line.services', string='Service')  # Replace 'service.model' with your service model
    visit_id = fields.Many2one('ss.evoucher.line.visit', string='Visit')  # Replace 'visit.model' with your visit model
    qty = fields.Integer(string='Qty',default="")
    price = fields.Float(string='Price',default="")
    subtotal = fields.Float(compute='_compute_subtotal', string='Subtotal')
    amount_type = fields.Selection([
        ('credit', 'Credit'),
        ('debit', 'Debit')
    ], string='Amount Type')
    @api.depends('qty', 'price')
    def _compute_subtotal(self):
        for record in self:
            record.subtotal = record.qty * record.price

    @api.constrains('qty', 'price')
    def _check_qty_price(self):
        for record in self:
            if record.qty < 1 or record.price < 1:
                raise ValidationError(_("Qty dan Harga harus lebih dari Nol (0)"))

class SSEVoucherLineVisit(models.Model):
    _name = 'ss.evoucher.line.visit'
    _description = 'SS EVoucher Market Visit'

    name = fields.Char(string='Market Location')

class SSEVoucherLineServices(models.Model):
    _name = 'ss.evoucher.line.services'
    _description = 'SS EVoucher Services'

    name = fields.Char(string='Service Name')
