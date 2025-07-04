# club_member.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class ClubMember(models.Model):
    _name = 'club.member'
    _description = 'Club Member'
    _rec_name = 'reference'

    reference = fields.Char(string='Member Ref', required=True, copy=False, readonly=True,
                            default=lambda self: self.env['ir.sequence'].next_by_code('club.member'))
    name = fields.Char(string='Name', required=True)
    email = fields.Char(string='Email')
    identity_no = fields.Char(string='Passport/ID No', copy=False, help="Member's passport or national ID number")

    # علاقة مع الألعاب
    sport_type_ids = fields.Many2many('sports.type', string='Sports')

    # علاقة مع خطط العضوية
    membership_plan_ids = fields.Many2many('membership.plan', string='Membership Plans')

    nationality_id = fields.Many2one('res.country', string='Nationality')
    date_of_birth = fields.Date(string='Date of Birth')
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    join_date = fields.Date(string='Join Date', default=fields.Date.today)
    expiry_date = fields.Date(string='Expiry Date', compute='_compute_expiry_date', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status')

    @api.depends('membership_plan_ids', 'join_date')
    def _compute_expiry_date(self):
        """حساب تاريخ انتهاء العضوية بناء على خطط العضوية المختارة"""
        for member in self:
            if member.membership_plan_ids and member.join_date:
                # نستخدم أطول مدة عضوية
                max_months = max(member.membership_plan_ids.mapped('duration_months'), default=0)
                member.expiry_date = member.join_date + relativedelta(months=max_months) if max_months else False
            else:
                member.expiry_date = False

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.date_of_birth:
                # تحقق من صحة البيانات أولاً
                if isinstance(rec.date_of_birth, fields.Date):
                    birth_date = rec.date_of_birth
                else:
                    try:
                        birth_date = fields.Date.from_string(rec.date_of_birth)
                    except Exception:
                        rec.age = 0
                        continue

                # حساب الفرق بين التاريخ الحالي وتاريخ الميلاد
                delta = relativedelta(today, birth_date)
                rec.age = delta.years
            else:
                rec.age = 0

    @api.constrains('identity_no')
    def _check_identity_no_unique(self):
        for record in self:
            if record.identity_no:
                duplicate = self.search([
                    ('identity_no', '=', record.identity_no),
                    ('id', '!=', record.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(_("The Passport/ID number %s is already registered for member %s.") %
                                          (record.identity_no, duplicate.name))

    _sql_constraints = [
        ('identity_no_unique', 'unique(identity_no)', 'The Passport/ID number must be unique!')
    ]

    # إضافة محقق لحساب العمر عند تغيير التاريخ
    @api.onchange('date_of_birth')
    def _onchange_birth_date(self):
        if self.date_of_birth:
            today = fields.Date.context_today(self)
            try:
                birth_date = fields.Date.from_string(self.date_of_birth)
                delta = relativedelta(today, birth_date)
                self.age = delta.years
            except Exception:
                self.age = 0

    def action_confirm(self):
        for rec in self:
            if not rec.membership_plan_ids:
                raise ValidationError(_("Cannot activate membership: No membership plans selected."))
            rec.state = 'active'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_set_to_draft(self):
        for rec in self:
            rec.state = 'draft'

    # يمكن إضافة وظيفة للتحقق من انتهاء العضوية بشكل دوري
    @api.model
    def _cron_check_expired_memberships(self):
        today = fields.Date.today()
        expired_members = self.search([
            ('state', '=', 'active'),
            ('expiry_date', '<', today)
        ])
        if expired_members:
            expired_members.write({'state': 'expired'})