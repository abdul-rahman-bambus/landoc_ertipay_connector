import logging
import re

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    ertipay_txn_id = fields.Char(string='Ertipay Transaction ID', readonly=True, copy=False)
    ertipay_intent_link = fields.Char(string='Ertipay UPI Intent Link', readonly=True, copy=False)

    def _get_specific_processing_values(self, processing_values):
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'ertipay':
            return res
        self.ensure_one()
        _logger.warning('[Ertipay] Building processing values for transaction %s with values: %s', self.reference, processing_values)
        if not self.ertipay_intent_link:
            self._ertipay_create_upi_payment()
        return {
            **res,
            'api_url': '/payment/ertipay/redirect',
            'intent_link': self.ertipay_intent_link,
            'reference': self.reference,
        }

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'ertipay':
            return res
        self.ensure_one()
        _logger.warning('[Ertipay] Building rendering values for transaction %s with values: %s', self.reference, processing_values)
        if not self.ertipay_intent_link:
            self._ertipay_create_upi_payment()
        return {
            **res,
            'api_url': '/payment/ertipay/redirect',
            'intent_link': self.ertipay_intent_link,
            'reference': self.reference,
        }

    def _ertipay_get_txn_ref_id(self):
        self.ensure_one()
        return re.sub(r'[^A-Za-z0-9]', '', self.reference or '')

    def _ertipay_create_upi_payment(self):
        self.ensure_one()
        provider = self.provider_id
        base_url = self.get_base_url()
        txn_ref_id = self._ertipay_get_txn_ref_id()
        provider._ertipay_log_api('Creating UPI payment for transaction %s with Ertipay txnRefId %s and amount %s', self.reference, txn_ref_id, self.amount)
        payload = {
            'type': provider.ertipay_channel_type or 'MOB',
            'vpa': provider.ertipay_vpa,
            'initMode': provider.ertipay_init_mode or '04',
            'txnRefId': txn_ref_id,
            'txnAmt': '%.2f' % self.amount,
            'txnRemarks': txn_ref_id,
            'refUrl': '%s/payment/ertipay/return' % base_url.rstrip('/'),
        }
        provider._ertipay_log_api('UPI plain request payload before encryption: %s', payload)
        encrypted_payload = provider._ertipay_encrypt(payload)
        request_payload = {'data': encrypted_payload}
        endpoint = '%s/upi' % provider._ertipay_get_base_url()
        provider._ertipay_log_api('UPI request endpoint: %s', endpoint)
        provider._ertipay_log_api('UPI encrypted request payload: %s', request_payload)
        try:
            response = requests.post(endpoint, headers=provider._ertipay_headers(), json=request_payload, timeout=30)
        except requests.exceptions.RequestException as error:
            _logger.exception('[Ertipay] UPI request failed before receiving a response from %s', endpoint)
            raise UserError(_('Ertipay UPI request failed before receiving a response: %s') % error) from error
        provider._ertipay_log_api('UPI response status: %s', response.status_code)
        response.raise_for_status()
        body = response.json()
        provider._ertipay_log_api('UPI response body: %s', body)
        if not body.get('success'):
            raise UserError(_('Ertipay UPI payment creation failed: %s') % (body.get('message') or body))

        encrypted_data = body.get('data', {}).get('encryptedData')
        if not encrypted_data:
            raise UserError(_('Ertipay did not return encrypted payment data.'))
        plain_response = provider._ertipay_decrypt(encrypted_data)
        payment_data = plain_response.get('data', {})
        self.write({
            'provider_reference': payment_data.get('txnId') or self.provider_reference,
            'ertipay_txn_id': payment_data.get('txnId'),
            'ertipay_intent_link': payment_data.get('intentLink') or payment_data.get('qrUrl'),
        })
        if not self.ertipay_intent_link:
            raise UserError(_('Ertipay did not return a UPI intent link or QR URL.'))
        self._set_pending()

    def _ertipay_fetch_status(self):
        self.ensure_one()
        provider = self.provider_id
        txn_ref_id = self._ertipay_get_txn_ref_id()
        endpoint = '%s/status/%s' % (provider._ertipay_get_base_url(), txn_ref_id)
        provider._ertipay_log_api('Status request endpoint: %s', endpoint)
        try:
            response = requests.get(endpoint, headers=provider._ertipay_headers(), timeout=30)
        except requests.exceptions.RequestException as error:
            _logger.exception('[Ertipay] Status request failed before receiving a response from %s', endpoint)
            raise UserError(_('Ertipay status request failed before receiving a response: %s') % error) from error
        provider._ertipay_log_api('Status response status: %s', response.status_code)
        response.raise_for_status()
        body = response.json()
        provider._ertipay_log_api('Status response body: %s', body)
        encrypted_data = body.get('data', {}).get('encryptedData')
        if encrypted_data:
            return provider._ertipay_decrypt(encrypted_data)
        return body

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'ertipay' or len(tx) == 1:
            return tx
        reference = notification_data.get('txnRefId') or notification_data.get('reference')
        if not reference:
            raise ValidationError(_('Ertipay notification does not contain a transaction reference.'))
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'ertipay')])
        if not tx:
            tx = self.search([('provider_code', '=', 'ertipay')]).filtered(
                lambda transaction: transaction._ertipay_get_txn_ref_id() == reference
            )
        if not tx:
            raise ValidationError(_('No Ertipay transaction found for reference %s.') % reference)
        return tx

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != 'ertipay':
            return
        status = notification_data.get('status') or notification_data.get('orgStatus')
        provider_reference = notification_data.get('txnId') or notification_data.get('rrn') or self.provider_reference
        if provider_reference:
            self.provider_reference = provider_reference
        if status == 'S':
            self._set_done()
        elif status == 'D':
            self._set_pending(state_message=_('Ertipay returned deemed success; waiting for final confirmation.'))
        elif status == 'F':
            self._set_error(_('Ertipay reported payment failure.'))
        else:
            self._set_pending(state_message=_('Waiting for Ertipay payment confirmation.'))
