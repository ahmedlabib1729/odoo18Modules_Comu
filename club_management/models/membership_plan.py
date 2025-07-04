from odoo import models, fields
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

class MembershipPlan(models.Model):
    _name = 'membership.plan'
    _description = 'Membership Plan'
    _order = 'sequence, name'

    sequence = fields.Char(
        string='Plan Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('membership.plan')
    )
    name = fields.Char(string='Plan Name', required=True)
    sport_type_id = fields.Many2one('sports.type', string='Sport Type')

    duration_months = fields.Integer(
        string='Duration (Months)',
        required=True,
        help='Length of the membership in months'
    )
    price = fields.Monetary(string='Price', required=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id,
        readonly=True
    )
    features = fields.Text(string='Features',
        help='Describe what this plan includes')
    auto_renew = fields.Boolean(
        string='Auto Renew',
        help='Automatically renew membership before expiry'
    )
    active = fields.Boolean(string='Active', default=True)