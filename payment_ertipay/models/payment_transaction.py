import logging
import re

import requests
from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    ertipay_txn_id = fields.Char(string='Ertipay Transaction ID', readonly=True, copy=False)
    ertipay_txn_ref_id = fields.Char(string='Ertipay Transaction Reference', readonly=True, copy=False)
    ertipay_intent_link = fields.Char(string='Ertipay UPI Intent Link', readonly=True, copy=False)

    # Extended fields for transaction fee, gst on trn fee.
    ertipay_transaction_fee = fields.Monetary(
        string="Transaction Fee",
        currency_field="currency_id",
        readonly=True,
        copy=False,
    )

    ertipay_gst = fields.Monetary(
        string="GST",
        currency_field="currency_id",
        readonly=True,
        copy=False,
    )

    ertipay_total_paid = fields.Monetary(
        string="Requested Gateway Total",
        currency_field="currency_id",
        readonly=True,
        copy=False,
    )
    ertipay_fee_percentage = fields.Float(string='Commission %', readonly=True, copy=False)
    ertipay_gst_percentage = fields.Float(string='Commission GST %', readonly=True, copy=False)
    ertipay_received_amount = fields.Monetary(
        string='Gateway Confirmed Total', currency_field='currency_id', readonly=True, copy=False,
    )
    ertipay_amount_mismatch = fields.Boolean(string='Gateway Amount Mismatch', readonly=True, copy=False)
    ertipay_session_id = fields.Char(readonly=True, copy=False)
    ertipay_payment_reference = fields.Char(readonly=True, copy=False)
    ertipay_raw_response = fields.Json(readonly=True, copy=False)

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
        total = self._calculate_gateway_charges()
        # Freeze the exact values sent to Ertipay. Provider percentages may be
        # changed later and must never rewrite the historical audit trail.
        self.write({
            'ertipay_txn_ref_id': txn_ref_id,
            'ertipay_transaction_fee': float(total['transaction_fee']),
            'ertipay_gst': float(total['gst']),
            'ertipay_total_paid': float(total['total']),
            'ertipay_fee_percentage': float(total['fee_percentage']),
            'ertipay_gst_percentage': float(total['gst_percentage']),
        })
        provider._ertipay_log_api('Creating UPI payment for transaction %s with Ertipay txnRefId %s and amount %s', self.reference, txn_ref_id, total["total"])
        payload = {
            'type': provider.ertipay_channel_type or 'MOB',
            'vpa': provider.ertipay_vpa,
            'initMode': provider.ertipay_init_mode or '04',
            'txnRefId': txn_ref_id,
            'txnAmt': '%.2f' % total["total"],
            # Ertipay rejects digits and punctuation in this field.
            'txnRemarks': 'Payment',
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

        response_data = body.get('data')
        encrypted_data = (
            response_data.get('encryptedData') or response_data.get('data')
            if isinstance(response_data, dict)
            else response_data
        )
        if not encrypted_data:
            raise UserError(_('Ertipay did not return encrypted payment data.'))
        plain_response = provider._ertipay_decrypt(encrypted_data)
        provider._ertipay_log_api('UPI decrypted response body: %s', plain_response)
        payment_data = plain_response.get('data') or plain_response
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
        response_data = body.get('data')
        encrypted_data = (
            response_data.get('encryptedData') or response_data.get('data')
            if isinstance(response_data, dict)
            else response_data
        )
        if encrypted_data:
            plain_response = provider._ertipay_decrypt(encrypted_data)
            provider._ertipay_log_api('Status decrypted response body: %s', plain_response)
            return plain_response
        return body

    def action_ertipay_fetch_status(self):
        """Manually fetch, decrypt, log, and process the Ertipay status."""
        self.ensure_one()
        if self.provider_code != 'ertipay':
            raise UserError(_('Manual Ertipay status fetching is only available for Ertipay transactions.'))

        status_response = self._ertipay_fetch_status()
        notification_data = status_response.get('data', status_response)
        if not isinstance(notification_data, dict):
            raise UserError(_('Ertipay returned an invalid status response.'))

        self.provider_id._ertipay_log_api(
            'Manually fetched plain status response for %s: %s',
            self.reference,
            self.provider_id._ertipay_sanitized_payload(notification_data),
        )
        self._process_notification_data(notification_data)
        status = notification_data.get('status') or notification_data.get('orgStatus') or _('Unknown')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Ertipay Status Refreshed'),
                'message': _('Ertipay returned status %s. The transaction is now %s.') % (
                    status,
                    self.state,
                ),
                'type': 'success' if self.state == 'done' else 'warning',
                'sticky': self.state != 'done',
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'ertipay' or len(tx) == 1:
            return tx
        reference = notification_data.get('txnRefId') or notification_data.get('reference')
        if not reference:
            raise ValidationError(_('Ertipay notification does not contain a transaction reference.'))
        tx = self.search([
            ('provider_code', '=', 'ertipay'),
            '|',
            ('reference', '=', reference),
            ('ertipay_txn_ref_id', '=', reference),
        ])
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
        self.ensure_one()
        self._process_ertipay_payment(notification_data)

    def _process_ertipay_payment(self, notification_data):
        """Handle Ertipay payment completion."""

        status = str(
            notification_data.get('status') or notification_data.get('orgStatus') or ''
        ).upper()

        provider_reference = (
                notification_data.get('txnId')
                or notification_data.get('rrn')
                or self.provider_reference
        )

        if provider_reference:
            self.provider_reference = provider_reference

        self._save_ertipay_payment_details(notification_data)

        if status == 'S' and not self.ertipay_amount_mismatch:
            self._set_done()
            self._update_invoice_ertipay_information()

        elif status == 'S':
            self._set_pending(
                state_message=_('Ertipay confirmed success, but the returned amount does not match the requested gateway total.'),
            )

        elif status == 'D':
            self._set_pending(
                state_message=_(
                    'Ertipay returned deemed success; waiting for final confirmation.'
                )
            )

        elif status == 'F':
            self._set_pending(
                state_message=_('Ertipay reported payment failure; retained as pending for reconciliation.'),
            )

        else:
            self._set_pending(
                state_message=_(
                    'Waiting for Ertipay payment confirmation.'
                )
            )

    def _calculate_gateway_charges(self):
        """Calculate Ertipay transaction fee, GST, and total payable."""

        self.ensure_one()

        return self.provider_id._ertipay_calculate_charges(self.amount)

    def _save_ertipay_payment_details(self, notification_data):
        self.ensure_one()

        received_amount = self._ertipay_get_received_amount(notification_data)
        currency = self.currency_id
        mismatch = self.ertipay_amount_mismatch
        if received_amount is not None:
            mismatch = not currency.is_zero(received_amount - self.ertipay_total_paid)
        values = {
            'ertipay_raw_response': notification_data,
            'ertipay_amount_mismatch': mismatch,
        }
        session_id = notification_data.get('sessionId')
        payment_reference = notification_data.get('txnId') or notification_data.get('rrn')
        if session_id:
            values['ertipay_session_id'] = session_id
        if payment_reference:
            values['ertipay_payment_reference'] = payment_reference
        if received_amount is not None:
            values['ertipay_received_amount'] = received_amount
        self.write(values)
        self.provider_id._ertipay_log_api(
            'Reconciliation for %s: Landoc amount=%s, requested gateway total=%s, '
            'gateway confirmed total=%s, mismatch=%s',
            self.reference, self.amount, self.ertipay_total_paid, received_amount, mismatch,
        )

    def _ertipay_get_received_amount(self, notification_data):
        """Extract Ertipay's confirmed total while accepting documented aliases."""
        for key in ('txnAmt', 'amount', 'totalAmount', 'total', 'paidAmount'):
            value = notification_data.get(key)
            if value not in (None, ''):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    self.provider_id._ertipay_log_api(
                        'Ignoring invalid callback amount %r from field %s.', value, key,
                    )
                    return None
        return None

    def _update_invoice_ertipay_information(self):
        """Copy Ertipay information to generated invoice."""

        self.ensure_one()

        invoices = self.invoice_ids.filtered(
            lambda inv: inv.state != 'cancel'
        )

        if not invoices:
            return

        values = {
            'payment_transaction_id': self.id,
            'ertipay_transaction_fee':
                self.ertipay_transaction_fee,

            'ertipay_gst':
                self.ertipay_gst,

            'ertipay_total_paid':
                self.ertipay_total_paid,

            'ertipay_received_amount':
                self.ertipay_received_amount,

            'ertipay_amount_mismatch':
                self.ertipay_amount_mismatch,

            'ertipay_session_id':
                self.ertipay_session_id,
            'ertipay_payment_reference': self.ertipay_payment_reference,
        }

        invoices.write(values)
