# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class LandocServiceAppointmentController(http.Controller):

    def _json_response(self, payload, status=200):
        return request.make_response(
            json.dumps(payload, default=str),
            headers=[
                ('Content-Type', 'application/json')
            ],
            status=status
        )

    def _get_request_json(self):
        try:
            return json.loads(request.httprequest.data.decode('utf-8') or '{}')
        except Exception:
            return {}

    def _format_date_display(self, date_value):
        if not date_value:
            return ''

        if isinstance(date_value, str):
            try:
                date_obj = fields.Date.from_string(date_value)
            except Exception:
                return date_value
        else:
            date_obj = date_value

        return date_obj.strftime('%d/%m/%Y')

    @http.route(
        '/api/v1/service/available-dates',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False
    )
    def get_service_available_dates(self, **kwargs):
        """
        GET /api/v1/service/available-dates?lead_id=232&service_code=muslim_marriage&limit=8

        Returns available dates from landoc.service.availability.
        """
        try:
            lead_id = kwargs.get('lead_id')
            service_code = kwargs.get('service_code')
            limit = int(kwargs.get('limit') or 8)

            if not service_code and lead_id:
                lead = request.env['crm.lead'].sudo().browse(int(lead_id))
                if lead.exists():
                    service_code = (
                        getattr(lead, 'service_code', False)
                        or getattr(lead, 'selected_service_option', False)
                        or ''
                    )

            if not service_code:
                return self._json_response({
                    'success': False,
                    'message': 'service_code is required.',
                    'available_dates': []
                }, status=400)

            today = fields.Date.context_today(request.env['landoc.service.availability'])

            domain = [
                ('service_ids.code', '=', service_code),
                ('available_date', '>=', today),
                ('active', '=', True),
            ]

            availability_records = request.env['landoc.service.availability'].sudo().search(
                domain,
                order='available_date asc',
                limit=limit
            )

            available_dates = []

            for index, rec in enumerate(availability_records, start=1):
                available_dates.append({
                    'option': index,
                    'availability_id': rec.id,
                    'date': fields.Date.to_string(rec.available_date),
                    'available_date': fields.Date.to_string(rec.available_date),
                    'display_date': self._format_date_display(rec.available_date),
                    'month': rec.month or '',
                    'year': rec.year or '',
                    'service_code': rec.service_code or '',
                    'service_name': rec.service_name or '',
                    'location': rec.location or '',
                    'booking_count': rec.booking_count or 0,
                })

            return self._json_response({
                'success': True,
                'service_code': service_code,
                'count': len(available_dates),
                'available_dates': available_dates
            })

        except Exception as e:
            _logger.exception('LANDOC: Failed to get service available dates')
            return self._json_response({
                'success': False,
                'message': str(e),
                'available_dates': []
            }, status=500)

    @http.route(
        '/api/v1/service/select-date',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def select_service_date(self, **kwargs):
        """
        POST /api/v1/service/select-date

        Body:
        {
          "lead_id": 232,
          "request_number": "L00236",
          "service_code": "muslim_marriage",
          "service_name": "Muslim Marriage Registration",
          "selected_date": "2026-07-14",
          "location": "Registrar Office, Erode",
          "bot_customer_id": "...",
          "bot_channel": "chat",
          "bot_session_id": "..."
        }
        """
        try:
            body = self._get_request_json()

            lead_id = body.get('lead_id')
            request_number = body.get('request_number')
            service_code = body.get('service_code')
            service_name = body.get('service_name')
            selected_date = body.get('selected_date')
            location = body.get('location') or ''
            bot_customer_id = body.get('bot_customer_id') or ''
            bot_channel = body.get('bot_channel') or 'chat'
            bot_session_id = body.get('bot_session_id') or bot_customer_id

            if not lead_id and request_number:
                lead = request.env['crm.lead'].sudo().search([
                    ('name', '=', request_number)
                ], limit=1)
            elif lead_id:
                lead = request.env['crm.lead'].sudo().browse(int(lead_id))
            else:
                lead = request.env['crm.lead'].sudo()

            if not lead or not lead.exists():
                return self._json_response({
                    'success': False,
                    'message': 'Lead not found.'
                }, status=404)

            if not service_code:
                service_code = (
                    getattr(lead, 'service_code', False)
                    or getattr(lead, 'selected_service_option', False)
                    or ''
                )

            if not service_name:
                service_name = (
                    getattr(lead, 'service_name', False)
                    or getattr(lead, 'selected_service_option_label', False)
                    or service_code
                    or 'LANDOC Service'
                )

            if not selected_date:
                return self._json_response({
                    'success': False,
                    'message': 'selected_date is required.'
                }, status=400)

            selected_date_obj = fields.Date.from_string(selected_date)

            availability = request.env['landoc.service.availability'].sudo().search([
                ('service_ids.code', '=', service_code),
                ('available_date', '=', selected_date_obj),
                ('active', '=', True),
            ], limit=1)

            if not availability:
                return self._json_response({
                    'success': False,
                    'message': 'Selected date is not available for this service.'
                }, status=400)

            if not location:
                location = availability.location or ''

            existing_booking = request.env['landoc.service.booking'].sudo().search([
                ('lead_id', '=', lead.id),
                ('status', 'in', ['selected', 'confirmed']),
                ('active', '=', True),
            ], limit=1)
            params = request.env['ir.config_parameter'].sudo()

            responsible_user_id = int(params.get_param('custom_landoc.responsible_user_id') or 0) or False
            responsible_user = request.env['res.users'].sudo().browse(responsible_user_id) if responsible_user_id else False

            responsible_mobile_no = ''
            if responsible_user and responsible_user.exists() and responsible_user.partner_id:
                responsible_mobile_no = (
                    responsible_user.partner_id.mobile
                    or responsible_user.partner_id.phone
                    or ''
                )

            booking_vals = {
                'lead_id': lead.id,
                'service_category_id': lead.service_category_id.id if lead.service_category_id else False,
                'service_id': lead.service_id.id if lead.service_id else False,
                'service_code': service_code,
                'service_name': service_name or availability.service_name,
                'selected_date': selected_date_obj,
                'responsible_user_id': responsible_user_id or False,
                #'responsible_mobile_no': responsible_mobile_no,
                'location': lead.sro_id.name if lead.sro_id else (location or availability.location or ''),
                'source': 'bot',
                'bot_customer_id': bot_customer_id,
                'bot_channel': bot_channel,
                'bot_session_id': bot_session_id,
                'status': 'selected',
            }

            if existing_booking:
                existing_booking.sudo().write(booking_vals)
                booking = existing_booking
                action_message = 'updated'
            else:
                booking = request.env['landoc.service.booking'].sudo().create(booking_vals)
                action_message = 'created'

            lead.message_post(
                body=(
                    'Service appointment date %s by bot.<br/>'
                    '<b>Selected Date:</b> %s<br/>'
                    '<b>Service:</b> %s<br/>'
                    '<b>Location:</b> %s<br/>'
                    '<b>Responsible Person:</b> %s<br/>'
                    '<b>Responsible Mobile:</b> %s<br/>'
                    '<b>Booking:</b> %s'
                ) % (
                    action_message,
                    self._format_date_display(booking.selected_date),
                    booking.service_name or booking.service_code or '',
                    booking.lead_id.sro_id.name or '',
                    booking.responsible_user_id.id or '',
                    responsible_mobile_no or responsible_mobile_no or '',
                    booking.name or ''
                )
            )

            return self._json_response({
                'success': True,
                'message': 'Selected date saved successfully.',
                'booking_id': booking.id,
                'booking_reference': booking.name,
                'lead_id': booking.lead_id.id,
                'request_number': booking.lead_id.name or '',
                'service_code': booking.service_code or '',
                'service_name': booking.service_name or '',
                'responsible_user_name': booking.responsible_user_id.name or '',
                'responsible_mobile_no': responsible_mobile_no or '',
                'selected_date': fields.Date.to_string(booking.selected_date),
                'display_date': self._format_date_display(booking.selected_date),
                'location': booking.lead_id.sro_id.name or '',
                'google_calendar_link': booking.google_calendar_link or '',
                'status': booking.status,
            })

        except Exception as e:
            _logger.exception('LANDOC: Failed to save selected service date')
            return self._json_response({
                'success': False,
                'message': str(e)
            }, status=500)