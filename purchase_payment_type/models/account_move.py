from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    payment_type = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank'),
    ], string="Payment Type")
