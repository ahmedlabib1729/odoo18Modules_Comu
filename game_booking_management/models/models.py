# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class Game(models.Model):
    _name = 'game.game'
    _description = 'الألعاب'
    _rec_name = 'name'

    name = fields.Char(string='اسم اللعبة', required=True)
    description = fields.Text(string='وصف اللعبة')
    active = fields.Boolean(string='نشط', default=True)
    schedule_ids = fields.One2many('game.schedule', 'game_id', string='مواعيد اللعبة')

    @api.depends('name')
    def _compute_display_name(self):
        for game in self:
            game.display_name = game.name


class GameSchedule(models.Model):
    _name = 'game.schedule'
    _description = 'مواعيد الألعاب'
    _rec_name = 'display_name'

    game_id = fields.Many2one('game.game', string='اللعبة', required=True, ondelete='cascade')
    date = fields.Date(string='التاريخ', required=True)
    time = fields.Float(string='الوقت', required=True)
    max_players = fields.Integer(string='العدد الأقصى للاعبين', required=True, default=5)
    booking_ids = fields.One2many('game.booking', 'schedule_id', string='الحجوزات')
    current_players = fields.Integer(string='عدد اللاعبين الحالي', compute='_compute_current_players', store=True)
    available_slots = fields.Integer(string='الأماكن المتاحة', compute='_compute_available_slots', store=True)
    display_name = fields.Char(string='الاسم', compute='_compute_display_name')

    @api.depends('booking_ids', 'booking_ids.state', 'booking_ids.players_count')
    def _compute_current_players(self):
        for schedule in self:
            total_players = 0
            for booking in schedule.booking_ids:
                if booking.state == 'confirmed':
                    total_players += booking.players_count
            schedule.current_players = total_players

    @api.depends('max_players', 'current_players')
    def _compute_available_slots(self):
        for schedule in self:
            schedule.available_slots = schedule.max_players - schedule.current_players

    @api.depends('game_id', 'date', 'time')
    def _compute_display_name(self):
        for schedule in self:
            time_str = '{:02d}:{:02d}'.format(int(schedule.time), int((schedule.time % 1) * 60))
            schedule.display_name = f"{schedule.game_id.name} - {schedule.date} - {time_str}"

    @api.constrains('max_players')
    def _check_max_players(self):
        for schedule in self:
            if schedule.max_players <= 0:
                raise ValidationError('عدد اللاعبين الأقصى يجب أن يكون أكبر من صفر')
            if schedule.current_players > schedule.max_players:
                raise ValidationError('عدد اللاعبين الحالي أكبر من العدد الأقصى المسموح')


class GameBooking(models.Model):
    _name = 'game.booking'
    _description = 'حجوزات الألعاب'
    _rec_name = 'player_name'

    player_name = fields.Char(string='اسم اللاعب', required=True)
    mobile = fields.Char(string='رقم الجوال', required=True)
    players_count = fields.Integer(string='عدد المشاركين', required=True, default=1)
    children_names = fields.Text(string='أسماء الأبناء المشاركين')
    schedule_id = fields.Many2one('game.schedule', string='موعد اللعبة', required=True)
    game_id = fields.Many2one('game.game', string='اللعبة', related='schedule_id.game_id', store=True)
    booking_date = fields.Datetime(string='تاريخ الحجز', default=fields.Datetime.now)
    state = fields.Selection([
        ('confirmed', 'مؤكد'),
        ('cancelled', 'ملغي')
    ], string='الحالة', default='confirmed')

    @api.constrains('mobile')
    def _check_mobile(self):
        for booking in self:
            # التحقق من أن الرقم يبدأ بـ +966
            if not booking.mobile.startswith('+966'):
                raise ValidationError('رقم الجوال يجب أن يبدأ بـ +966')

            # التحقق من صحة تنسيق الرقم
            # +966 متبوعة بـ 9 أرقام (رقم جوال سعودي)
            pattern = r'^\+966[0-9]{9}$'
            if not re.match(pattern, booking.mobile):
                raise ValidationError('رقم الجوال غير صحيح. يجب أن يكون بالصيغة: +966XXXXXXXXX')

    @api.constrains('players_count')
    def _check_players_count(self):
        for booking in self:
            if booking.players_count < 1:
                raise ValidationError('عدد المشاركين يجب أن يكون 1 على الأقل')
            if booking.players_count > 3:
                raise ValidationError('عذراً، الحد الأقصى للمشاركين هو 3 أشخاص إذا أردت الاشتارك بأكثر من لاعب يرجى التواصل على الرقم التالى بالوتس أب 00966590610836')

    @api.constrains('schedule_id', 'players_count')
    def _check_schedule_capacity(self):
        for booking in self:
            if booking.state == 'confirmed':
                # حساب إجمالي اللاعبين المحجوزين
                total_booked = sum(
                    b.players_count for b in self.search([
                        ('schedule_id', '=', booking.schedule_id.id),
                        ('state', '=', 'confirmed'),
                        ('id', '!=', booking.id)
                    ])
                )

                # التحقق من توفر أماكن كافية
                if total_booked + booking.players_count > booking.schedule_id.max_players:
                    available = booking.schedule_id.max_players - total_booked
                    raise ValidationError(
                        f'عذراً، لا توجد أماكن كافية. '
                        f'المتاح فقط {available} أماكن.'
                    )

    @api.model
    def create(self, vals):
        # التحقق من السعة قبل إنشاء الحجز
        if 'schedule_id' in vals and vals.get('state', 'confirmed') == 'confirmed':
            schedule = self.env['game.schedule'].browse(vals['schedule_id'])
            players_count = vals.get('players_count', 1)

            # حساب إجمالي اللاعبين المحجوزين
            total_booked = sum(
                b.players_count for b in self.search([
                    ('schedule_id', '=', vals['schedule_id']),
                    ('state', '=', 'confirmed')
                ])
            )

            if total_booked + players_count > schedule.max_players:
                available = schedule.max_players - total_booked
                raise ValidationError(
                    f'عذراً، لا توجد أماكن كافية. '
                    f'المتاح فقط {available} أماكن.'
                )

        return super(GameBooking, self).create(vals)