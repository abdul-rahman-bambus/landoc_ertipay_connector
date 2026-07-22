import json
import logging
import secrets
import subprocess
from datetime import timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('ertipay', 'Ertipay')], ondelete={'ertipay': 'set default'})

    ertipay_merchant_id = fields.Char(string='Merchant ID', groups='base.group_system')
    ertipay_email = fields.Char(string='Pay-In Email', groups='base.group_system')
    ertipay_api_secret = fields.Char(string='Pay-In API Secret', groups='base.group_system')
    ertipay_encryption_key = fields.Char(
        string='Pay-In Encryption Key',
        groups='base.group_system',
        help='32-character hexadecimal AES-128 key shared by Ertipay.',
    )
    ertipay_vpa = fields.Char(string='Merchant VPA', groups='base.group_system')
    ertipay_channel_type = fields.Selection(
        [('MOB', 'Mobile Intent'), ('WEB', 'Web')],
        string='Channel Type',
        default='MOB',
        required_if_provider='ertipay',
    )
    ertipay_init_mode = fields.Selection(
        [('04', 'Intent'), ('01', 'Dynamic QR')],
        string='Initiation Mode',
        default='04',
        required_if_provider='ertipay',
    )
    ertipay_token = fields.Char(string='Cached Bearer Token', groups='base.group_system', copy=False)
    ertipay_token_expiry = fields.Datetime(string='Token Expiry', groups='base.group_system', copy=False)

    @api.constrains('ertipay_encryption_key')
    def _check_ertipay_encryption_key(self):
        for provider in self.filtered(lambda p: p.code == 'ertipay' and p.ertipay_encryption_key):
            key = provider.ertipay_encryption_key.strip()
            if len(key) != 32:
                raise ValidationError(_('The Ertipay encryption key must be a 32-character hexadecimal AES-128 key.'))
            try:
                bytes.fromhex(key)
            except ValueError as error:
                raise ValidationError(_('The Ertipay encryption key must contain only hexadecimal characters.')) from error

    def _get_default_payment_method_codes(self):
        self.ensure_one()
        if self.code != 'ertipay':
            return super()._get_default_payment_method_codes()
        return {'upi'}

    def _ertipay_get_base_url(self):
        self.ensure_one()
        return 'https://payin.ertipay.com/prod' if self.state == 'enabled' else 'https://payin.ertipay.com/uat'

    def _ertipay_headers(self, authenticated=True):
        self.ensure_one()
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'merchantid': self.ertipay_merchant_id or '',
            'MerchantId': self.ertipay_merchant_id or '',
        }
        if authenticated:
            headers['Authorization'] = 'Bearer %s' % self._ertipay_get_token()
        return headers

    def _ertipay_validate_configuration(self):
        self.ensure_one()
        missing = []
        for field_name, label in [
            ('ertipay_merchant_id', _('Merchant ID')),
            ('ertipay_email', _('Pay-In Email')),
            ('ertipay_api_secret', _('Pay-In API Secret')),
            ('ertipay_encryption_key', _('Pay-In Encryption Key')),
            ('ertipay_vpa', _('Merchant VPA')),
        ]:
            if not self[field_name]:
                missing.append(label)
        if missing:
            raise UserError(_('Please configure the following Ertipay fields: %s') % ', '.join(missing))

    def _ertipay_get_token(self):
        self.ensure_one()
        self._ertipay_validate_configuration()
        refresh_at = fields.Datetime.now() + timedelta(minutes=5)
        if self.ertipay_token and self.ertipay_token_expiry and self.ertipay_token_expiry > refresh_at:
            return self.ertipay_token

        endpoint = '%s/token' % self._ertipay_get_base_url()
        payload = {
            'email': self.ertipay_email,
            'apiPayinApiSecret': self.ertipay_api_secret,
        }
        response = requests.post(endpoint, headers=self._ertipay_headers(authenticated=False), json=payload, timeout=30)
        response.raise_for_status()
        body = response.json()
        if not body.get('success') or not body.get('data', {}).get('token'):
            raise UserError(_('Ertipay token generation failed: %s') % (body.get('message') or body))

        data = body['data']
        expires_in = int(data.get('expiresInSeconds') or 3600)
        self.sudo().write({
            'ertipay_token': data['token'],
            'ertipay_token_expiry': fields.Datetime.now() + timedelta(seconds=max(expires_in - 60, 60)),
        })
        return data['token']

    def _ertipay_run_openssl(self, payload, key_hex, iv_hex, decrypt=False):
        command = ['openssl', 'enc', '-aes-128-cbc', '-K', key_hex, '-iv', iv_hex]
        if decrypt:
            command.insert(2, '-d')
        try:
            result = subprocess.run(command, input=payload, capture_output=True, check=True)
        except FileNotFoundError as error:
            raise UserError(_('OpenSSL is required on the Odoo server to process Ertipay encrypted payloads.')) from error
        except subprocess.CalledProcessError as error:
            _logger.exception('OpenSSL failed while processing Ertipay payload: %s', error.stderr.decode('utf-8', errors='ignore'))
            raise UserError(_('Unable to process the Ertipay encrypted payload.')) from error
        return result.stdout

    def _ertipay_encrypt(self, payload):
        self.ensure_one()
        raw_payload = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
        key = bytes.fromhex(self.ertipay_encryption_key.strip())
        iv = secrets.token_bytes(16)
        encrypted = self._ertipay_run_openssl(raw_payload.encode('utf-8'), key.hex(), iv.hex(), decrypt=False)
        return '%s:%s' % (iv.hex(), encrypted.hex())

    def _ertipay_decrypt(self, encrypted_data):
        self.ensure_one()
        try:
            iv_hex, encrypted_hex = encrypted_data.split(':', 1)
        except ValueError as error:
            raise UserError(_('Ertipay returned encrypted data in an invalid format.')) from error
        key = bytes.fromhex(self.ertipay_encryption_key.strip())
        decrypted = self._ertipay_run_openssl(bytes.fromhex(encrypted_hex), key.hex(), iv_hex, decrypt=True)
        return json.loads(decrypted.decode('utf-8'))
