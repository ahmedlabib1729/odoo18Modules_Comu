# -*- coding: utf-8 -*-

from odoo import http, fields
from odoo.http import request
import json
import logging
from datetime import datetime
import base64

_logger = logging.getLogger(__name__)


class CharityRegistrationController(http.Controller):

    @http.route('/registration', type='http', auth='public', website=True)
    def registration_home(self, **kwargs):
        """الصفحة الرئيسية للتسجيل - عرض المقرات"""
        headquarters = request.env['charity.headquarters'].sudo().search([
            ('is_active', '=', True),
            ('active', '=', True)
        ])

        values = {
            'headquarters': headquarters,
            'page_title': 'التسجيل في الأنشطة'
        }
        return request.render('charity_clubs.registration_headquarters', values)

    @http.route('/registration/headquarters/<int:headquarters_id>', type='http', auth='public', website=True)
    def registration_departments(self, headquarters_id, **kwargs):
        """عرض أقسام المقر المحدد"""
        headquarters = request.env['charity.headquarters'].sudo().browse(headquarters_id)
        if not headquarters.exists() or not headquarters.is_active:
            return request.redirect('/registration')

        departments = request.env['charity.departments'].sudo().search([
            ('headquarters_id', '=', headquarters_id),
            ('is_active', '=', True),
            ('active', '=', True)
        ])

        values = {
            'headquarters': headquarters,
            'departments': departments,
            'page_title': f'أقسام {headquarters.name}'
        }
        return request.render('charity_clubs.registration_departments', values)

    @http.route('/registration/ladies/<int:department_id>', type='http', auth='public', website=True)
    def ladies_registration_form(self, department_id, **kwargs):
        """فورم تسجيل السيدات"""
        department = request.env['charity.departments'].sudo().browse(department_id)
        if not department.exists() or department.type != 'ladies':
            return request.redirect('/registration')

        # البرامج المتاحة
        programs = request.env['charity.ladies.program'].sudo().search([
            ('department_id', '=', department_id),
            ('is_active', '=', True),
            ('active', '=', True)
        ])

        values = {
            'department': department,
            'headquarters': department.headquarters_id,
            'programs': programs,
            'countries': request.env['res.country'].sudo().search([]),
            'page_title': f'التسجيل في {department.name}'
        }
        return request.render('charity_clubs.ladies_registration_form', values)

    @http.route('/registration/clubs/<int:department_id>', type='http', auth='public', website=True)
    def clubs_list(self, department_id, **kwargs):
        """عرض النوادي في القسم"""
        department = request.env['charity.departments'].sudo().browse(department_id)
        if not department.exists() or department.type != 'clubs':
            return request.redirect('/registration')

        clubs = request.env['charity.clubs'].sudo().search([
            ('department_id', '=', department_id),
            ('is_active', '=', True),
            ('active', '=', True)
        ])

        values = {
            'department': department,
            'headquarters': department.headquarters_id,
            'clubs': clubs,
            'page_title': f'نوادي {department.name}'
        }
        return request.render('charity_clubs.registration_clubs', values)

    @http.route('/registration/club/<int:club_id>', type='http', auth='public', website=True)
    def club_registration_form(self, club_id, **kwargs):
        """فورم تسجيل النوادي"""
        club = request.env['charity.clubs'].sudo().browse(club_id)
        if not club.exists() or not club.is_active:
            return request.redirect('/registration')

        # الترمات المتاحة
        today = fields.Date.today()
        terms = request.env['charity.club.terms'].sudo().search([
            ('club_id', '=', club_id),
            ('is_active', '=', True),
            ('date_to', '>=', today)
        ])

        values = {
            'club': club,
            'department': club.department_id,
            'headquarters': club.department_id.headquarters_id,
            'terms': terms,
            'countries': request.env['res.country'].sudo().search([]),
            'page_title': f'التسجيل في {club.name}'
        }
        return request.render('charity_clubs.club_registration_form', values)

    @http.route('/registration/submit/ladies', type='json', auth='public', website=True, csrf=False)
    def submit_ladies_registration(self, **post):
        """معالجة تسجيل السيدات مع البحث التلقائي عن العضوة"""
        try:
            _logger.info(f"Received ladies registration data: {post}")

            # التحقق من البيانات المطلوبة
            required_fields = ['department_id', 'full_name', 'mobile', 'whatsapp',
                               'birth_date', 'email', 'booking_type']

            for field in required_fields:
                if not post.get(field):
                    _logger.error(f"Missing required field: {field}")
                    return {'success': False, 'error': f'الحقل {field} مطلوب'}

            # التحقق من الملفات المطلوبة
            required_files = ['id_card_file', 'passport_file', 'residence_file']
            for file_field in required_files:
                if not post.get(file_field):
                    file_names = {
                        'id_card_file': 'صورة الهوية',
                        'passport_file': 'صورة جواز السفر',
                        'residence_file': 'صورة الإقامة'
                    }
                    _logger.error(f"Missing required file: {file_field}")
                    return {'success': False, 'error': f'يجب رفع {file_names.get(file_field, file_field)}'}

            # البحث عن عضوة موجودة بناءً على رقم الموبايل
            mobile = post.get('mobile')
            whatsapp = post.get('whatsapp')
            department_id = int(post.get('department_id'))

            existing_member = request.env['charity.member.profile'].sudo().search([
                '|',
                ('mobile', '=', mobile),
                ('whatsapp', '=', whatsapp)
            ], limit=1)

            # إذا وُجدت عضوة، نتحقق من اشتراكاتها النشطة
            active_subscription = False
            subscription_message = None

            if existing_member:
                _logger.info(f"Found existing member: {existing_member.full_name} - {existing_member.member_number}")

                # البحث عن اشتراك نشط في نفس القسم
                active_subscription = request.env['charity.member.subscription'].sudo().search([
                    ('member_id', '=', existing_member.id),
                    ('department_id', '=', department_id),
                    ('state', '=', 'active')
                ], limit=1)

                if active_subscription:
                    subscription_message = {
                        'has_active_subscription': True,
                        'subscription_number': active_subscription.subscription_number,
                        'end_date': active_subscription.end_date.strftime('%Y-%m-%d'),
                        'days_remaining': active_subscription.days_remaining,
                        'programs': [{'name': p.name, 'schedule': p.schedule} for p in active_subscription.program_ids]
                    }
                    _logger.info(f"Member has active subscription until {active_subscription.end_date}")

            # إعداد بيانات الحجز
            booking_vals = {
                'headquarters_id': int(post.get('headquarters_id')),
                'department_id': department_id,
                'full_name': post.get('full_name'),
                'mobile': post.get('mobile'),
                'whatsapp': post.get('whatsapp'),
                'birth_date': post.get('birth_date'),
                'email': post.get('email'),
                'state': 'draft'
            }

            # إذا وُجدت عضوة، نغير نوع الحجز إلى existing
            if existing_member:
                booking_vals['booking_type'] = 'existing'
                booking_vals['member_id'] = existing_member.id
            else:
                booking_vals['booking_type'] = 'new'

            # إضافة الملفات
            if post.get('id_card_file'):
                booking_vals['id_card_file'] = base64.b64decode(post.get('id_card_file'))
                booking_vals['id_card_filename'] = post.get('id_card_file_name', 'id_card.pdf')

            if post.get('passport_file'):
                booking_vals['passport_file'] = base64.b64decode(post.get('passport_file'))
                booking_vals['passport_filename'] = post.get('passport_file_name', 'passport.pdf')

            if post.get('residence_file'):
                booking_vals['residence_file'] = base64.b64decode(post.get('residence_file'))
                booking_vals['residence_filename'] = post.get('residence_file_name', 'residence.pdf')

            # إضافة البرامج إذا تم اختيارها
            if post.get('program_ids'):
                program_ids = json.loads(post.get('program_ids'))
                booking_vals['program_ids'] = [(6, 0, program_ids)]

            # إنشاء الحجز
            _logger.info(f"Creating booking with values: {booking_vals}")
            booking = request.env['charity.booking.registrations'].sudo().create(booking_vals)
            _logger.info(f"Booking created with ID: {booking.id}")

            # تأكيد الحجز تلقائياً
            try:
                booking.action_confirm()
                _logger.info(f"Booking confirmed successfully")

                # إذا تم إنشاء فاتورة، نحصل على معلوماتها
                if booking.invoice_id:
                    _logger.info(f"Invoice created with ID: {booking.invoice_id.id}")
                    invoice_data = {
                        'invoice_id': booking.invoice_id.id,
                        'invoice_name': booking.invoice_id.name,
                        'amount': booking.invoice_id.amount_total,
                        'access_token': booking.invoice_id._portal_ensure_token()
                    }

                    return {
                        'success': True,
                        'message': 'تم التسجيل بنجاح',
                        'booking_id': booking.id,
                        'has_invoice': True,
                        'invoice': invoice_data,
                        'member_found': bool(existing_member),
                        'member_name': existing_member.full_name if existing_member else None,
                        'active_subscription': subscription_message
                    }
            except Exception as e:
                _logger.error(f"Error confirming booking: {str(e)}")
                # إذا فشل التأكيد، نرجع نجاح التسجيل فقط
                pass

            return {
                'success': True,
                'message': 'تم التسجيل بنجاح',
                'booking_id': booking.id,
                'has_invoice': False,
                'member_found': bool(existing_member),
                'member_name': existing_member.full_name if existing_member else None,
                'active_subscription': subscription_message
            }

        except Exception as e:
            _logger.error(f"Error in ladies registration: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/registration/invoice/<int:invoice_id>/<string:access_token>', type='http', auth='public',
                website=True)
    @http.route('/registration/invoice/<int:invoice_id>/<string:access_token>', type='http', auth='public',
                website=True)
    def show_invoice(self, invoice_id, access_token, **kwargs):
        """عرض صفحة الفاتورة للدفع"""
        try:
            invoice = request.env['account.move'].sudo().search([
                ('id', '=', invoice_id),
                ('access_token', '=', access_token)
            ], limit=1)

            if not invoice:
                return request.redirect('/registration')

            # التحقق من حالة الدفع
            if invoice.payment_state == 'paid':
                booking = request.env['charity.booking.registrations'].sudo().search([
                    ('invoice_id', '=', invoice.id)
                ], limit=1)
                if booking:
                    return request.redirect(f'/registration/success/ladies/{booking.id}')

            # الحصول على طرق الدفع المتاحة
            payment_providers = request.env['payment.provider'].sudo().search([
                ('state', 'in', ['enabled', 'test']),
                ('is_published', '=', True),
                ('company_id', '=', invoice.company_id.id),
            ])

            if not payment_providers:
                payment_providers = request.env['payment.provider'].sudo().search([
                    ('state', 'in', ['enabled', 'test']),
                ])
                _logger.warning(
                    f"No providers found with company filter, trying without: {len(payment_providers)} found")

            # إنشاء payment transaction إذا لم يكن موجود
            existing_tx = request.env['payment.transaction'].sudo().search([
                ('invoice_ids', 'in', invoice.id),
                ('state', 'not in', ['done', 'cancel', 'error'])
            ], limit=1)

            values = {
                'invoice': invoice,
                'page_title': f'الفاتورة {invoice.name}',
                'access_token': access_token,
                'payment_providers': payment_providers,
                'existing_transaction': existing_tx,
                'partner': invoice.partner_id,
                'amount': invoice.amount_residual,
                'currency': invoice.currency_id,
            }

            return request.render('charity_clubs.invoice_payment_page', values)

        except Exception as e:
            _logger.error(f"Error showing invoice: {str(e)}")
            return request.redirect('/registration')

    @http.route('/registration/payment/transaction/<int:invoice_id>/<string:access_token>',
                type='json', auth='public', website=True, csrf=False)
    def create_payment_transaction(self, invoice_id, access_token, provider_id, **kwargs):
        """إنشاء معاملة دفع"""
        try:
            invoice = request.env['account.move'].sudo().search([
                ('id', '=', invoice_id),
                ('access_token', '=', access_token)
            ], limit=1)

            if not invoice:
                return {'success': False, 'error': 'الفاتورة غير موجودة'}

            provider = request.env['payment.provider'].sudo().browse(int(provider_id))
            if not provider.exists() or provider.state != 'enabled':
                return {'success': False, 'error': 'طريقة الدفع غير متاحة'}

            # إنشاء معاملة الدفع
            tx_values = {
                'provider_id': provider.id,
                'amount': invoice.amount_residual,
                'currency_id': invoice.currency_id.id,
                'partner_id': invoice.partner_id.id,
                'invoice_ids': [(6, 0, [invoice.id])],
                'reference': f'{invoice.name}-{fields.Datetime.now().strftime("%Y%m%d%H%M%S")}',
            }

            transaction = request.env['payment.transaction'].sudo().create(tx_values)

            # الحصول على رابط الدفع
            payment_link = transaction._get_processing_values()

            return {
                'success': True,
                'transaction_id': transaction.id,
                'payment_link': payment_link.get('payment_link_url', '#'),
                'provider_type': provider.code,
            }

        except Exception as e:
            _logger.error(f"Error creating payment transaction: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/registration/payment/status/<int:transaction_id>',
                type='json', auth='public', website=True, csrf=False)
    def check_payment_status(self, transaction_id, **kwargs):
        """التحقق من حالة الدفع"""
        try:
            transaction = request.env['payment.transaction'].sudo().browse(transaction_id)
            if not transaction.exists():
                return {'success': False, 'error': 'المعاملة غير موجودة'}

            # التحقق من حالة المعاملة
            if transaction.state == 'done':
                # البحث عن الحجز المرتبط
                booking = request.env['charity.booking.registrations'].sudo().search([
                    ('invoice_id', 'in', transaction.invoice_ids.ids)
                ], limit=1)

                return {
                    'success': True,
                    'state': 'done',
                    'message': 'تم الدفع بنجاح',
                    'redirect_url': f'/registration/success/ladies/{booking.id}' if booking else '/registration'
                }
            elif transaction.state == 'pending':
                return {
                    'success': True,
                    'state': 'pending',
                    'message': 'في انتظار تأكيد الدفع'
                }
            elif transaction.state in ['cancel', 'error']:
                return {
                    'success': False,
                    'state': transaction.state,
                    'message': transaction.state_message or 'فشلت عملية الدفع'
                }
            else:
                return {
                    'success': True,
                    'state': 'processing',
                    'message': 'جاري معالجة الدفع...'
                }

        except Exception as e:
            _logger.error(f"Error checking payment status: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/registration/process-payment', type='json', auth='public', website=True, csrf=False)
    def process_payment(self, **post):
        """معالجة الدفع (نموذج مبسط)"""
        try:
            invoice_id = post.get('invoice_id')
            payment_method = post.get('payment_method')

            if not invoice_id or not payment_method:
                return {'success': False, 'error': 'بيانات غير كاملة'}

            invoice = request.env['account.move'].sudo().browse(int(invoice_id))
            if not invoice.exists():
                return {'success': False, 'error': 'الفاتورة غير موجودة'}

            # هنا يمكن إضافة معالجة الدفع الفعلية مع بوابة الدفع
            # للتجربة، سنضع الفاتورة كمدفوعة
            if payment_method == 'test':
                # إنشاء دفعة تجريبية
                payment_vals = {
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': invoice.partner_id.id,
                    'amount': invoice.amount_total,
                    'date': fields.Date.today(),
                    'journal_id': request.env['account.journal'].sudo().search([
                        ('type', 'in', ['bank', 'cash'])
                    ], limit=1).id,
                    'payment_method_line_id': request.env['account.payment.method.line'].sudo().search([
                        ('payment_method_id.payment_type', '=', 'inbound')
                    ], limit=1).id,
                }

                payment = request.env['account.payment'].sudo().create(payment_vals)
                payment.action_post()

                # ربط الدفعة بالفاتورة
                invoice.js_assign_outstanding_line(payment.line_ids.id)

                # البحث عن الحجز المرتبط
                booking = request.env['charity.booking.registrations'].sudo().search([
                    ('invoice_id', '=', invoice.id)
                ], limit=1)

                return {
                    'success': True,
                    'message': 'تم الدفع بنجاح',
                    'redirect_url': f'/registration/success/ladies/{booking.id}' if booking else '/registration'
                }

            return {'success': False, 'error': 'طريقة دفع غير مدعومة'}

        except Exception as e:
            _logger.error(f"Error processing payment: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/registration/submit/club', type='json', auth='public', website=True, csrf=False)
    def submit_club_registration(self, **post):
        """معالجة تسجيل النوادي"""
        try:
            # التحقق من البيانات المطلوبة
            required_fields = ['headquarters_id', 'department_id', 'club_id', 'term_id',
                               'full_name', 'birth_date', 'gender', 'nationality',
                               'id_number', 'student_grade', 'mother_name', 'mother_mobile',
                               'father_name', 'father_mobile']

            for field in required_fields:
                if not post.get(field):
                    return {'success': False, 'error': f'الحقل {field} مطلوب'}

            # إنشاء التسجيل
            registration_vals = {
                'headquarters_id': int(post.get('headquarters_id')),
                'department_id': int(post.get('department_id')),
                'club_id': int(post.get('club_id')),
                'term_id': int(post.get('term_id')),
                'registration_type': 'new',
                'full_name': post.get('full_name'),
                'birth_date': post.get('birth_date'),
                'gender': post.get('gender'),
                'nationality': int(post.get('nationality')),
                'id_type': post.get('id_type', 'emirates_id'),
                'id_number': post.get('id_number'),
                'student_grade': post.get('student_grade'),
                'mother_name': post.get('mother_name'),
                'mother_mobile': post.get('mother_mobile'),
                'father_name': post.get('father_name'),
                'father_mobile': post.get('father_mobile'),
                'mother_whatsapp': post.get('mother_whatsapp', ''),
                'email': post.get('email', ''),
                'arabic_education_type': post.get('arabic_education_type'),
                'previous_roayati_member': post.get('previous_roayati_member') == 'true',
                'previous_arabic_club': post.get('previous_arabic_club') == 'true',
                'previous_qaida_noorania': post.get('previous_qaida_noorania') == 'true',
                'quran_memorization': post.get('quran_memorization', ''),
                'has_health_requirements': post.get('has_health_requirements') == 'true',
                'health_requirements': post.get('health_requirements', ''),
                'photo_consent': post.get('photo_consent') == 'true',
                'state': 'draft'
            }

            registration = request.env['charity.club.registrations'].sudo().create(registration_vals)

            return {
                'success': True,
                'message': 'تم التسجيل بنجاح',
                'registration_id': registration.id
            }

        except Exception as e:
            _logger.error(f"Error in club registration: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/registration/success/<string:type>/<int:record_id>', type='http', auth='public', website=True)
    def registration_success(self, type, record_id, **kwargs):
        """صفحة النجاح بعد التسجيل"""
        if type == 'ladies':
            record = request.env['charity.booking.registrations'].sudo().browse(record_id)
            record_name = 'حجز'
        else:
            record = request.env['charity.club.registrations'].sudo().browse(record_id)
            record_name = 'تسجيل'

        if not record.exists():
            return request.redirect('/registration')

        values = {
            'record': record,
            'record_type': type,
            'record_name': record_name,
            'page_title': 'تم التسجيل بنجاح'
        }
        return request.render('charity_clubs.registration_success', values)