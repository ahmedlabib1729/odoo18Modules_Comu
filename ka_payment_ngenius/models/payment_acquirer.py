import logging
import requests
from urllib.parse import urljoin
from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class NGeniusAcquirer(models.Model):
    _inherit = 'payment.provider'

    ngenius_api_key = fields.Char(string='API Key', required_if_provider='ngenius')
    ngenius_reference = fields.Char(string='Reference', required_if_provider='ngenius')
    code = fields.Selection(selection_add=[
        ('ngenius', 'ngenius')
    ], ondelete={'ngenius': 'set default'})

    def _get_ngenius_api_url(self):
        if self.state == 'enabled':
            return 'https://api-gateway.ngenius-payments.com'
        return 'https://api-gateway.sandbox.ngenius-payments.com'

    def get_ngenius_token_response(self, response=False):
        token_url = urljoin(self._get_ngenius_api_url(), '/identity/auth/access-token')
        headers = {
            'content-type': 'application/vnd.ni-identity.v1+json',
            'Authorization': f'Basic {self.ngenius_api_key}',
        }
        try:
            token_response = requests.post(token_url, headers=headers)
            _logger.info(f"url {token_url} headers {headers} resp {token_response.status_code} {token_response.text}")
        except requests.exceptions.RequestException as e:
            _logger.error(e, exc_info=True)
            raise UserError(e)
        if response:
            return token_response
        try:
            token = token_response.json().get('access_token')
            return token
        except:
            raise UserError(_("Can not get token, Please contact administrator"))

    def test_ngenius_connection(self):
        token_response = self.get_ngenius_token_response(response=True)
        if token_response.status_code == requests.codes.ok and token_response.json().get('access_token'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'info',
                    'message': _("Successful Connection"),
                }
            }
        else:
            raise UserError(_("an error occurred http code: %s message: %s", token_response.status_code, token_response.text))

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'ngenius':
            return default_codes
        return [
            'ngenius',
        ]
