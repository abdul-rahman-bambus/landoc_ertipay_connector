import hmac
import json
import logging
import time

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ErtipayController(http.Controller):

    @http.route('/payment/ertipay/redirect', type='http', auth='public', website=True, csrf=False)
    def ertipay_redirect(self, **kwargs):
        reference = kwargs.get('reference')
        intent_link = kwargs.get('intent_link')
        if not intent_link and reference:
            tx = request.env['payment.transaction'].sudo().search([
                ('reference', '=', reference),
                ('provider_code', '=', 'ertipay'),
            ], limit=1)
            intent_link = tx.ertipay_intent_link
        return request.render('payment_ertipay.redirect_to_upi', {
            'intent_link': intent_link,
            'reference': reference,
        })

    @http.route('/payment/ertipay/return', type='http', auth='public', website=True, csrf=False)
    def ertipay_return(self, **kwargs):
        reference = kwargs.get('txnRefId') or kwargs.get('reference')
        if reference:
            tx = request.env['payment.transaction'].sudo().search([('reference', '=', reference), ('provider_code', '=', 'ertipay')], limit=1)
            if tx and tx.state not in ('done', 'cancel', 'error'):
                try:
                    status_data = tx._ertipay_fetch_status()
                    data = status_data.get('data', status_data)
                    tx._process_notification_data(data)
                except Exception:
                    _logger.exception('Unable to refresh Ertipay transaction status for %s', reference)
        return request.redirect('/payment/status')

    @http.route('/payment/ertipay/callback', type='json', auth='public', csrf=False, methods=['POST'])
    def ertipay_callback(self):
        payload = request.get_json_data() or {}
        provider = request.env['payment.provider'].sudo().search([('code', '=', 'ertipay'), ('state', '!=', 'disabled')], limit=1)
        if not provider:
            _logger.warning('Received Ertipay callback but no enabled Ertipay provider exists.')
            return {'success': False, 'message': 'Provider not configured'}

        signature = request.httprequest.headers.get('x-erti-signature') or request.httprequest.headers.get('X-ERTI-SIGNATURE')
        timestamp = request.httprequest.headers.get('x-erti-timestamp') or request.httprequest.headers.get('X-ERTI-TIMESTAMP')
        encrypted_data = payload.get('data') or payload.get('encryptedData')
        if not signature or not timestamp or not encrypted_data:
            return {'success': False, 'message': 'Missing Ertipay callback security fields'}

        try:
            if abs(int(time.time() * 1000) - int(timestamp)) > 5 * 60 * 1000:
                return {'success': False, 'message': 'Expired callback timestamp'}
        except ValueError:
            return {'success': False, 'message': 'Invalid callback timestamp'}

        data_to_verify = json.dumps(encrypted_data, separators=(',', ':')) + timestamp
        expected = hmac.new(
            provider.ertipay_encryption_key.strip().encode('utf-8'),
            data_to_verify.encode('utf-8'),
            'sha256',
        ).hexdigest()
        if not hmac.compare_digest(signature.lower(), expected.lower()):
            return {'success': False, 'message': 'Invalid callback signature'}

        notification_data = provider._ertipay_decrypt(encrypted_data)
        data = notification_data.get('data', notification_data)
        tx = request.env['payment.transaction'].sudo()._get_tx_from_notification_data('ertipay', data)
        tx._process_notification_data(data)
        return {'success': True}
