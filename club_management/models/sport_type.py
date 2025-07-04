from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class SportType(models.Model):
    _name = 'sports.type'
    _description = 'Sports Type'

    name = fields.Char(string='Sport Name', required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)

    # علاقة عكسية لعرض خطط العضوية المرتبطة باللعبة
    membership_plan_ids = fields.One2many('membership.plan', 'sport_type_id', string='Membership Plans')
    membership_plan_count = fields.Integer(compute='_compute_membership_plan_count', string='Plans Count')

    @api.depends('membership_plan_ids')
    def _compute_membership_plan_count(self):
        for sport in self:
            sport.membership_plan_count = len(sport.membership_plan_ids)