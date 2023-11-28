from odoo import fields, models, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    

    use_evoucher = fields.Boolean(string='Use eVoucher')
    type_evoucher = fields.Selection([
        ('evoucher', 'eVoucher'),
        ('biaya_harian', 'Biaya Harian'),
        ('all', 'All')
    ], string='Type eVoucher')
    evoucher_view = fields.Selection([
        ('own_voucher', 'Own Voucher'),
        ('all_voucher', 'All Voucher')
    ], string='eVoucher View')
    evoucher_amount_type = fields.Selection([
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('all', 'All')
    ], string='eVoucher Amount Type')
    approval_evoucher = fields.Boolean(string='Approval eVoucher')
