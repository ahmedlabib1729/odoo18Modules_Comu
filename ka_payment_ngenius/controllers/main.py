import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class NGeniusController(http.Controller):
    _process_url = '/ngenius/payment/process'
    _redirect_url = '/ngenius/payment/redirect'

    @http.route(_process_url, type='http', auth="public", csrf=False)
    def paymob_process_callback(self, **kw):
        data = kw or request.httprequest.json
        _logger.info(f'ngenius webhook {data} {kw}')
        request.env['payment.transaction'].sudo()._handle_notification_data('ngenius', data)

    @http.route(_redirect_url, type='http', auth="public", csrf=False)
    def paymob_process_callback(self, ref):
        _logger.info(f'ngenius redirect {ref}')
        request.env['payment.transaction'].sudo()._ngenius_process_tx(ref)
        return request.redirect('/payment/status')
