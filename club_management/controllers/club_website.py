# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class ClubWebsite(http.Controller):
    @http.route(['/club/register'], type='http', auth='public', website=True)
    def club_register(self, **kwargs):
        countries = request.env['res.country'].sudo().search([])
        sports = request.env['sports.type'].sudo().search([('active', '=', True)])
        return request.render('club_management.register_template', {
            'countries': countries,
            'sports': sports,
            'error': kwargs.get('error', False)
        })

    @http.route(['/club/register/submit'], type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def club_register_submit(self, **post):
        _logger.info("Form submitted with data: %s", post)

        # التحقق من وجود البيانات الإلزامية
        required_fields = ['name', 'email', 'identity_no', 'nationality_id', 'date_of_birth']
        for field in required_fields:
            if not post.get(field):
                return self.club_register(error=f"Field {field} is required.")

        # ** المشكلة الرئيسية هنا **
        # التعامل مع اختيار الألعاب المتعددة بشكل صحيح
        # عند استخدام checkboxes، يمكن أن تأتي القيم بأشكال مختلفة:
        # 1. قيمة واحدة: sport_type_ids = '1'
        # 2. قيم متعددة كقائمة: sport_type_ids = ['1', '2']
        # 3. قيم متعددة كسلسلة من القيم: sport_type_ids = '1,2'
        sport_type_ids = post.get('sport_type_ids')
        sport_ids = []

        _logger.info("Raw sport_type_ids: %s, Type: %s", sport_type_ids, type(sport_type_ids))

        # إذا كانت قيمة واحدة (string)
        if sport_type_ids and isinstance(sport_type_ids, str):
            # تحقق مما إذا كانت القيمة تحتوي على فواصل (قد تكون مجموعة قيم)
            if ',' in sport_type_ids:
                sport_ids = [int(x.strip()) for x in sport_type_ids.split(',') if x.strip().isdigit()]
            else:
                # قيمة واحدة فقط
                if sport_type_ids.isdigit():
                    sport_ids = [int(sport_type_ids)]

        # إذا كانت قائمة
        elif sport_type_ids and isinstance(sport_type_ids, list):
            # تحويل كل قيمة إلى عدد صحيح
            sport_ids = [int(x) for x in sport_type_ids if str(x).isdigit()]

        _logger.info("Processed sport_ids: %s", sport_ids)

        if not sport_ids:
            return self.club_register(error="Please select at least one sport.")

        try:
            # التحقق من وجود رقم الهوية مسبقًا
            identity_no = post.get('identity_no')
            existing_member = request.env['club.member'].sudo().search([('identity_no', '=', identity_no)], limit=1)

            if existing_member:
                error_message = f"Member with Passport/ID number '{identity_no}' is already registered with name '{existing_member.name}'. Please use a different ID or contact support if you believe this is an error."
                return self.club_register(error=error_message)

            # تخزين البيانات في الجلسة
            session_data = {
                'name': post.get('name'),
                'email': post.get('email'),
                'identity_no': identity_no,
                'sport_type_ids': sport_ids,  # القائمة المعالجة من الألعاب
                'nationality_id': int(post.get('nationality_id')),
                'date_of_birth': post.get('date_of_birth'),
            }

            _logger.info("Saving to session: %s", session_data)
            request.session['registration_data'] = session_data

            # إعادة توجيه المستخدم إلى صفحة اختيار خطط العضوية
            return request.redirect('/club/register/plans')

        except Exception as e:
            _logger.error("Error processing registration: %s", str(e), exc_info=True)
            return self.club_register(error=f"An error occurred: {str(e)}")

    @http.route(['/club/register/plans'], type='http', auth='public', website=True)
    def club_register_plans(self, **kwargs):
        # استرجاع بيانات التسجيل من الجلسة
        registration_data = request.session.get('registration_data')
        if not registration_data:
            return request.redirect('/club/register')

        # جلب بيانات الألعاب المختارة
        sport_ids = registration_data.get('sport_type_ids', [])
        _logger.info("Sport IDs from session: %s", sport_ids)

        if not sport_ids:
            return request.redirect('/club/register')

        sports = request.env['sports.type'].sudo().browse(sport_ids)
        _logger.info("Found sports: %s", sports.mapped('name'))

        # جلب خطط العضوية المتاحة لكل لعبة
        plans_by_sport = {}

        for sport in sports:
            sport_plans = request.env['membership.plan'].sudo().search([
                ('sport_type_id', '=', sport.id),
                ('active', '=', True)
            ])
            _logger.info("Sport %s (ID: %s) has %s plans: %s",
                         sport.name, sport.id, len(sport_plans),
                         ', '.join([p.name for p in sport_plans]))
            plans_by_sport[sport.id] = sport_plans

        _logger.info("Final plans_by_sport keys: %s", list(plans_by_sport.keys()))

        return request.render('club_management.plans_template', {
            'sports': sports,
            'plans_by_sport': plans_by_sport,
            'error': kwargs.get('error', False)
        })

    @http.route(['/club/register/plans/submit'], type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def club_register_plans_submit(self, **post):
        _logger.info("Plans form submitted with data: %s", post)

        # استرجاع بيانات التسجيل من الجلسة
        registration_data = request.session.get('registration_data')
        if not registration_data:
            return request.redirect('/club/register')

        # التحقق من اختيار خطط العضوية - نفس المعالجة كما في الألعاب
        plan_ids_raw = post.get('plan_ids')
        plan_ids = []

        _logger.info("Raw plan_ids: %s, Type: %s", plan_ids_raw, type(plan_ids_raw))

        if plan_ids_raw and isinstance(plan_ids_raw, str):
            if ',' in plan_ids_raw:
                plan_ids = [int(x.strip()) for x in plan_ids_raw.split(',') if x.strip().isdigit()]
            else:
                if plan_ids_raw.isdigit():
                    plan_ids = [int(plan_ids_raw)]
        elif plan_ids_raw and isinstance(plan_ids_raw, list):
            plan_ids = [int(x) for x in plan_ids_raw if str(x).isdigit()]

        _logger.info("Processed plan_ids: %s", plan_ids)

        if not plan_ids:
            return self.club_register_plans(error="Please select at least one membership plan.")

        try:
            # إنشاء العضو الجديد
            member_data = {
                'name': registration_data.get('name'),
                'email': registration_data.get('email'),
                'identity_no': registration_data.get('identity_no'),
                'sport_type_ids': [(6, 0, registration_data.get('sport_type_ids', []))],
                'membership_plan_ids': [(6, 0, plan_ids)],
                'nationality_id': registration_data.get('nationality_id'),
                'date_of_birth': registration_data.get('date_of_birth'),
                'state': 'draft',
            }

            _logger.info("Creating member with data: %s", member_data)

            member = request.env['club.member'].sudo().create(member_data)
            _logger.info("Member created with ID: %s", member.id)

            # مسح بيانات الجلسة بعد إنشاء العضو بنجاح
            request.session.pop('registration_data', None)

            return request.render('club_management.thanks_template', {
                'member': member
            })

        except Exception as e:
            _logger.error("Error creating member: %s", str(e), exc_info=True)
            return self.club_register_plans(error=f"An error occurred: {str(e)}")