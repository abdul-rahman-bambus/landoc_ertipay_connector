import json
import logging
import secrets
import subprocess
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('ertipay', 'Ertipay')], ondelete={'ertipay': 'set default'})
    is_trn_charges_applied = fields.Boolean(default=False, string='Transaction Charges Applied')
    trn_percentage = fields.Float(string='Transaction Percentage')
    trn_tax_percentage = fields.Float(string='Transaction Tax Percentage')
    ertipay_merchant_id = fields.Char(string='Merchant ID', groups='base.group_system')
    ertipay_email = fields.Char(string='Pay-In Email', groups='base.group_system')
    ertipay_api_secret = fields.Char(string='Pay-In API Secret', groups='base.group_system')
    ertipay_encryption_key = fields.Char(
        string='Pay-In Encryption Key',
        groups='base.group_system',
        help='32-character hexadecimal AES-128 key shared by Ertipay.',
    )
    ertipay_base_url = fields.Char(
        string='API Base URL',
        default='https://payin.ertipay.com',
        required_if_provider='ertipay',
        groups='base.group_system',
        help='Base Ertipay API host. The connector appends /uat in test mode and /prod in enabled mode.',
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
    ertipay_debug_logging = fields.Boolean(
        string='Enable API Debug Logs',
        groups='base.group_system',
        help='Log Ertipay API endpoints, payloads, and responses in the Odoo server log. API secrets are masked, while tokens are shown for server-side testing.',
    )

    def _calculate_total_payable(self, sale_id, is_partial):
        """Return the checkout charge breakdown for a sale order.

        This method is called from the public payment-method template, so invalid
        or missing request parameters must produce no breakdown rather than an
        access error. The payment transaction performs the authoritative charge
        calculation again and stores a snapshot before contacting Ertipay.
        """
        self.ensure_one()
        if self.code != 'ertipay' or not self.is_trn_charges_applied or not sale_id:
            return {}
        try:
            sale_order = self.env['sale.order'].browse(int(sale_id)).exists()
        except (TypeError, ValueError):
            return {}
        if not sale_order:
            return {}

        if isinstance(is_partial, str):
            is_partial = is_partial.lower() in ('1', 'true', 'yes')
        elif is_partial is None:
            is_partial = bool(sale_order.require_payment)

        amount = (
            sale_order._get_prepayment_required_amount()
            if is_partial
            else sale_order.amount_total
        )
        values = {
            key: float(value)
            for key, value in self._ertipay_calculate_charges(amount).items()
        }
        values['currency'] = sale_order.currency_id
        return values

    def _ertipay_calculate_charges(self, amount):
        """Calculate commission without changing the Landoc invoice amount."""
        self.ensure_one()
        amount = Decimal(str(amount or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if self.is_trn_charges_applied:
            fee_percentage = Decimal(str(self.trn_percentage or 0))
            gst_percentage = Decimal(str(self.trn_tax_percentage or 0))
        else:
            fee_percentage = gst_percentage = Decimal('0')
        transaction_fee = (amount * fee_percentage / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP,
        )
        gst = (transaction_fee * gst_percentage / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP,
        )
        return {
            'amount': amount,
            'fee_percentage': fee_percentage,
            'gst_percentage': gst_percentage,
            'transaction_fee': transaction_fee,
            'gst': gst,
            'total': amount + transaction_fee + gst,
        }

    @api.constrains('trn_percentage', 'trn_tax_percentage')
    def _check_ertipay_charge_percentages(self):
        for provider in self:
            if provider.trn_percentage < 0 or provider.trn_tax_percentage < 0:
                raise ValidationError(_('Ertipay transaction and tax percentages cannot be negative.'))

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
        return {'ertipay_upi'}

    def _get_redirect_form_view(self, is_validation=False):
        self.ensure_one()
        if self.code != 'ertipay':
            return super()._get_redirect_form_view(is_validation=is_validation)
        return self.env.ref('payment_ertipay.redirect_form')

    def _ertipay_get_base_url(self):
        self.ensure_one()
        base_url = (self.ertipay_base_url or 'https://payin.ertipay.com').rstrip('/')
        environment_path = 'prod' if self.state == 'enabled' else 'uat'
        if base_url.endswith('/uat') or base_url.endswith('/prod'):
            base_url = base_url.rsplit('/', 1)[0]
        return '%s/%s' % (base_url, environment_path)

    def _ertipay_mask_sensitive(self, value):
        if not value:
            return value
        value = str(value)
        if len(value) <= 8:
            return '****'
        return '%s****%s' % (value[:4], value[-4:])

    def _ertipay_sanitized_payload(self, payload):
        if isinstance(payload, dict):
            sanitized = {}
            for key, value in payload.items():
                if key.lower() in {
                    'apipayinapisecret',
                    'authorization',
                    'token',
                    'jwttoken',
                    'accesstoken',
                    'bearertoken',
                } and value:
                    sanitized[key] = self._ertipay_mask_sensitive(value)
                else:
                    sanitized[key] = self._ertipay_sanitized_payload(value)
            return sanitized
        if isinstance(payload, list):
            return [self._ertipay_sanitized_payload(item) for item in payload]
        return payload

    def _ertipay_log_api(self, message, *args):
        self.ensure_one()
        _logger.warning('[Ertipay] ' + message, *args)

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
            ('ertipay_base_url', _('API Base URL')),
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
            self._ertipay_log_api(
                'Using cached bearer token expiring at %s: %s',
                self.ertipay_token_expiry,
                self._ertipay_mask_sensitive(self.ertipay_token),
            )
            return self.ertipay_token

        endpoint = '%s/token' % self._ertipay_get_base_url()
        payload = {
            'email': self.ertipay_email,
            'apiPayinApiSecret': self.ertipay_api_secret,
        }
        self._ertipay_log_api('Token request endpoint: %s', endpoint)
        self._ertipay_log_api('Token request payload: %s', self._ertipay_sanitized_payload(payload))
        try:
            response = requests.post(endpoint, headers=self._ertipay_headers(authenticated=False), json=payload, timeout=30)
        except requests.exceptions.RequestException as error:
            _logger.exception('[Ertipay] Token request failed before receiving a response from %s', endpoint)
            raise UserError(_('Ertipay token request failed before receiving a response: %s') % error) from error
        self._ertipay_log_api('Token response status: %s', response.status_code)
        response.raise_for_status()
        body = response.json()
        self._ertipay_log_api('Token response body: %s', self._ertipay_sanitized_payload(body))
        if not body.get('success'):
            raise UserError(_('Ertipay token generation failed: %s') % (body.get('message') or body))

        data = body.get('data') or {}
        encrypted_data = data.get('encryptedData')
        if encrypted_data:
            decrypted_body = self._ertipay_decrypt(encrypted_data)
            self._ertipay_log_api('Token decrypted response body: %s', self._ertipay_sanitized_payload(decrypted_body))
            data = decrypted_body.get('data') or decrypted_body

        token = data.get('token') or data.get('jwtToken') or data.get('accessToken') or data.get('bearerToken')
        if not token:
            raise UserError(_('Ertipay token generation did not return a bearer token: %s') % self._ertipay_sanitized_payload(data))

        expires_in = int(data.get('expiresInSeconds') or data.get('expiresIn') or 3600)
        self.sudo().write({
            'ertipay_token': token,
            'ertipay_token_expiry': fields.Datetime.now() + timedelta(seconds=max(expires_in - 60, 60)),
        })
        return token

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
