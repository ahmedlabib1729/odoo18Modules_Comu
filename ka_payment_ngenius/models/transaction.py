import logging
import json
import requests
from urllib.parse import urlparse, urljoin, parse_qsl
from odoo import api, models, _
from odoo.exceptions import ValidationError
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class TransactionNGenius(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _get_tx_from_notification_data(self, provider, data):
        tx = super()._get_tx_from_notification_data(provider, data)
        if provider != 'ngenius':
            return tx
        reference = data.get('order', {}).get('reference')
        if not reference:
            raise ValidationError(_("No reference found"))
        tx = self.search([('provider_reference', '=', reference)])
        if not tx:
            raise ValidationError(_("No transaction found matching reference %s.", reference))
        return tx

    def _get_ngenius_order_url(self):
        return urljoin(self.provider_id._get_ngenius_api_url(),
                      f'/transactions/outlets/{self.provider_id.ngenius_reference}/orders')

    def _get_specific_rendering_values(self, processing_values):
        if self.provider_code == 'ngenius':
            order_data = self._create_ngenius_order()
            if self.provider_code == 'ngenius':
                pay_url = order_data.get('_links', {}).get('payment', {}).get('href')
                return {
                    'api_url': pay_url,
                    **dict(parse_qsl(urlparse(pay_url).query))
                }
        return super()._get_specific_rendering_values(processing_values)


    def _process_notification_data(self, data):
        super()._process_notification_data(data)
        if self.provider_code != 'ngenius':
            return
        _logger.info('process data %s' % data)
        tx_state = data.get('transaction', {}).get('state')
        if tx_state == 'CAPTURED':
            self._set_done()
        else:
            _logger.error("received data with invalid payment status")
            self._set_error(f"ngenius: Error with reference {data.get('order', {}).get('reference')}")

    @api.model
    def _ngenius_process_tx(self, ref):
        # this simulates the webhook
        tx = self.search([('provider_reference', '=', ref)])
        if not tx:
            raise ValidationError(_("No reference found"))
        tx._process_notification_data({
            'order': {
                'reference': ref,
            },
            'transaction': {
                'state': 'CAPTURED',
            }
        })

    # ngenius payment flow
    def _create_ngenius_order(self):
        headers = {
            'content-type': 'application/vnd.ni-payment.v2+json',
            'Accept': 'application/vnd.ni-payment.v2+json',
            'Authorization': f'Bearer {self.provider_id.get_ngenius_token_response()}',
        }
        converted_amount = payment_utils.to_minor_currency_units(self.amount, self.currency_id)
        first_name = self.partner_id.display_name.split(' ')[0]
        try:
            last_name = self.partner_id.display_name.split(' ')[1]
        except IndexError:
            last_name = first_name
        order_url = self._get_ngenius_order_url()
        order_payload = {
            "action": "SALE",
            "amount": {
                "currencyCode" : self.currency_id.name,
                "value" : converted_amount
            },
            "emailAddress": self.partner_id.email,
            "merchantOrderReference": self.reference.replace('/','-'),
            "merchantAttributes": {
                "redirectUrl": urljoin(self.provider_id.get_base_url(), '/ngenius/payment/redirect'),
                "cancelUrl": urljoin(self.provider_id.get_base_url(), '/ngenius/payment/redirect'),
                "showPayerName": True,
            },
            "billingAddress": {
                "firstName": first_name,
                "lastName": last_name,
            }
        }
        try:
            order_response = requests.post(order_url, data=json.dumps(order_payload), headers=headers)
            _logger.info(f"url {order_url} data {order_payload} headers {headers} resp {order_response.status_code} {order_response.text}")
        except requests.ConnectionError as e:
            _logger.error(e, exc_info=True)
            raise ValidationError(_(f"Connection Error {e}"))
        if order_response.status_code == requests.codes.created:
            self.provider_reference = order_response.json().get('reference')
            return order_response.json()
        else:
            _logger.error(order_response.text)
            raise ValidationError(_(f"An error occurred when creating ngenius order {order_response.text}"))
