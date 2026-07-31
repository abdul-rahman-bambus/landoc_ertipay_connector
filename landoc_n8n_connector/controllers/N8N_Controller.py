# controllers/main.py

import json
import logging
from datetime import datetime, date

from odoo import http, fields
from odoo.http import request, Response
from odoo.exceptions import UserError
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class CRMWebhookController(http.Controller):

    # --------------------------------------------------
    # Utility / Helper Methods
    # --------------------------------------------------

    def _build_response(self, success, status=200, message=None, **kwargs):
        """Helper to standardize JSON responses."""
        response_data = {'success': success}
        if message:
            response_data['message'] = message
        response_data.update(kwargs)

        return Response(
            json.dumps(response_data),
            status=status,
            content_type='application/json'
        )

    def _authenticate(self):
        """
        Validates the Bearer token. 
        Returns an error Response if invalid, or None if successful.
        """
        auth_header = request.httprequest.headers.get('Authorization')

        if not auth_header:
            return self._build_response(False, status=401, message='Authorization header missing')

        if not auth_header.startswith('Bearer '):
            return self._build_response(False, status=401, message='Invalid authorization format')

        incoming_token = auth_header.replace('Bearer ', '').strip()
        saved_token = request.env['ir.config_parameter'].sudo().get_param('landoc_n8n_webhook.api_token')

        if incoming_token != saved_token:
            return self._build_response(False, status=401, message='Invalid token')

        return None

    def _parse_date(self, value):
        if not value:
            return False

        value = str(value).strip()

        for date_format in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, date_format).date()
            except ValueError:
                pass

        raise ValueError(f"Invalid date format: {value}")

    # --------------------------------------------------
    # Routes
    # --------------------------------------------------

    @http.route(
        '/api/v1/crm/lead',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def create_lead(self, **kwargs):
        try:
            # 1. Authenticate
            auth_error = self._authenticate()
            if auth_error:
                return auth_error

            # 2. Parse Payload
            payload = json.loads(request.httprequest.data.decode('utf-8'))
            _logger.info("CRM Webhook Payload : %s", payload)

            # 3. Handle specific service categories
            lead = request.env['crm.lead']
            additional_res = {}
            if payload.get('service_category') == "Marriage Registration":
                lead, additional_res = self._marriage_registration(payload)

            # 4. Handle Not Interested feedback
            not_interested_details = payload.get('not_interested_details', {})
            if not_interested_details.get('not_interested'):
                reason = not_interested_details.get('not_interested_reason', '')
                _logger.info("NOT Interested Reason : %s", reason)

                message = f"""
                    <p><strong>❌ Client declined to proceed with our services.</strong></p>
                    <ul class='mb-0'>
                        <li><strong>Reason:</strong> {reason}</li>
                    </ul>
                """
                lead.message_post(body=Markup(message), message_type='comment')

                return self._build_response(
                    success=True,
                    message='Thank you for sharing your feedback. Our team will review the details and contact you if any suitable option is available.'
                )

            # 5. Success Response
            request_number = lead.name or ""
            bot_details = payload.get('bot_details', {}) or {}
            success_msg = f'We appreciate you using LANDOC.\n     Your service request number is "{request_number}".     \nPlease save this number for future reference. Our team will contact you for the next steps.'
            return self._build_response(success=True, lead_id=lead.id, request_number=request_number,
                                        **additional_res,
                                        bot_customer_id=(
                                                payload.get('bot_customer_id')
                                                or bot_details.get('bot_customer_id')
                                                or ''
                                        ),
                                        bot_channel=(
                                                payload.get('bot_channel')
                                                or bot_details.get('bot_channel')
                                                or 'chat'
                                        ),
                                        bot_session_id=(
                                                payload.get('bot_session_id')
                                                or bot_details.get('bot_session_id')
                                                or payload.get('bot_customer_id')
                                                or ''
                                        ),
                                        bot_current_stage=(
                                                payload.get('bot_current_stage')
                                                or bot_details.get('bot_current_stage')
                                                or ''
                                        ),
                                        bot_active_service=(
                                                payload.get('bot_active_service')
                                                or bot_details.get('bot_active_service')
                                                or 'marriage_registration'
                                        ),
                                        bot_workflow_source=(
                                                payload.get('bot_workflow_source')
                                                or bot_details.get('bot_workflow_source')
                                                or 'n8n_landoc_marriage_bot'
                                        ),
                                        bot_callback_reference=(
                                                payload.get('bot_callback_reference')
                                                or bot_details.get('bot_callback_reference')
                                                or ''
                                        ),
                                        message=success_msg)

        except Exception as e:
            _logger.exception("CRM Webhook Error")
            return self._build_response(False, status=500, message=str(e))

    def _marriage_registration(self, payload):
        """
        Marriage registration with Landoc
        params: payload
        return: crm.lead record
        """
        marriage_details = payload.get('marriage_details', {}) or {}
        groom = payload.get('groom_details', {}) or {}
        bride = payload.get('bride_details', {}) or {}
        selected_service_option = marriage_details.get('selected_service_option')
        raw_number = payload.get('customer_mobile')
        customer_mobile = f"+91 {raw_number[:5]} {raw_number[5:]}"

        # Bot details can come as flat fields or inside bot_details
        bot_details = payload.get('bot_details', {}) or {}

        bot_customer_id = (
                payload.get('bot_customer_id')
                or bot_details.get('bot_customer_id')
                or ''
        )
        bot_channel = (
                payload.get('bot_channel')
                or bot_details.get('bot_channel')
                or 'chat'
        )
        bot_session_id = (
                payload.get('bot_session_id')
                or bot_details.get('bot_session_id')
                or bot_customer_id
                or ''
        )
        bot_current_stage = (
                payload.get('bot_current_stage')
                or bot_details.get('bot_current_stage')
                or ''
        )
        bot_active_service = (
                payload.get('bot_active_service')
                or bot_details.get('bot_active_service')
                or 'marriage_registration'
        )
        bot_workflow_source = (
                payload.get('bot_workflow_source')
                or bot_details.get('bot_workflow_source')
                or 'n8n_landoc_marriage_bot'
        )
        bot_callback_reference = (
                payload.get('bot_callback_reference')
                or bot_details.get('bot_callback_reference')
                or ''
        )

        Env = request.env

        service = Env['service.type'].sudo().search(
            [('code', '=', selected_service_option)],
            limit=1
        )

        if not service:
            raise UserError(
                "No service type found for selected_service_option: %s"
                % selected_service_option
            )

        workflow = Env['workflow.master'].sudo().search(
            [('category_id', '=', service.service_category_id.id)],
            limit=1
        )

        contact = Env['res.partner'].sudo().search(
            [('mobile', 'ilike', customer_mobile)],
            limit=1
        )

        source = Env['utm.source'].sudo().search(
            [('name', 'ilike', 'Odoo Chatbot')],
            limit=1
        )

        params = Env['ir.config_parameter'].sudo()

        bot_user_id = int(params.get_param('custom_landoc.bot_user_id') or 2)
        team_id = int(params.get_param('custom_landoc.department_id') or 11)

        create_dict = {
            'type': 'lead',
            'source_id': source.id if source else False,

            'service_category_id': service.service_category_id.id,
            'service_id': service.id,
            'workflow_master_id': workflow.id if workflow else False,

            'user_id': bot_user_id,
            'assigned_to_id': bot_user_id,
            'team_id': team_id,

            'mobile': customer_mobile,
            'description': payload.get('notes'),

            'date_of_marriage': self._parse_date(
                marriage_details.get('marriage_date')
            ),
            'bride_is_nri': bride.get('bride_is_nri'),
            'groom_is_nri': groom.get('groom_is_nri'),
            'marriage_place': marriage_details.get('marriage_place'),
            'service_cost': marriage_details.get('service_cost'),
            'marriage_registration_place_option': marriage_details.get('registration_place_option'),


            # Bot session mapping fields
            # These fields must exist in crm.lead
            'bot_customer_id': bot_customer_id,
            'bot_channel': bot_channel,
            'bot_session_id': bot_session_id,
            'bot_current_stage': bot_current_stage,
            'bot_active_service': bot_active_service,
            'bot_workflow_source': bot_workflow_source,
            'bot_callback_reference': bot_callback_reference,
        }

        # Customer details extended
        if contact:
            create_dict.update({
                'new_or_existing_customer': 'existing_customer',
                'partner_id': contact.id
            })
        else:
            create_dict.update({
                'new_or_existing_customer': 'new_customer',
                'contact_name': payload.get('customer_name')
            })

        _logger.info("Marriage Registration Payload : %s", payload)
        _logger.info("Creation Dict : %s", create_dict)

        # 1 . Lead Creation
        lead = Env['crm.lead'].sudo().create(create_dict)
        additional_res = {}
        try:
            # 2 . Converting to Opportunity
            lead_2_opportunity = Env['crm.lead2opportunity.partner'].with_context(
                active_model='crm.lead',
                active_ids=[lead.id],
                active_id=lead.id,
            ).sudo().create({})
            lead_2_opportunity.sudo().action_apply()

            # 1 . Sale Creation
            if lead.partner_id:
                quotation_context = lead._prepare_opportunity_quotation_context()
                sale = Env['sale.order'].sudo().with_context(quotation_context).create({})
                base_url = Env['ir.config_parameter'].sudo().get_param('web.base.url')
                additional_res.update({"quotation_id": sale.id,
                                       "quotation_number": sale.name,
                                       "quotation_amount": sale.amount_total,
                                       "quotation_preview_url": f"{base_url}{sale.get_portal_url()}",
                                       "payment_status": "pending", })
        except Exception as e:
            _logger.exception(e)

        # Log details in chatter

        message = f"""
            <b>Groom Details</b><br/>
            Name: {groom.get('groom_name', '')}<br/>
            DOB: {groom.get('groom_dob', '')}<br/>
            Age: {groom.get('groom_age', '')}<br/>
            Address: {groom.get('groom_address', '')}<br/>
            Religion: {groom.get('groom_religion', '')}<br/>
            Is Groom NRI?: {groom.get('groom_is_nri', '')}<br/><br/>

            <b>Bride Details</b><br/>
            Name: {bride.get('bride_name', '')}<br/>
            DOB: {bride.get('bride_dob', '')}<br/>
            Age: {bride.get('bride_age', '')}<br/>
            Address: {bride.get('bride_address', '')}<br/>
            Religion: {bride.get('bride_religion', '')}<br/>
            Is Bride NRI?: {bride.get('bride_is_nri', '')}<br/><br/>

            <b>Marriage Details</b><br/>
            Marriage Date: {marriage_details.get('marriage_date', '')}<br/>
            Marriage Place: {marriage_details.get('marriage_place', '')}<br/>
            Marriage Registration Place Label: {marriage_details.get('registration_place_label', '')}<br/><br/>

            <b>Landoc Details:</b><br/>
            Requested Service: {marriage_details.get('selected_service_option_label', '')}<br/>
            Service Option Code: {marriage_details.get('selected_service_option', '')}<br/>
            Quotation Value: {marriage_details.get('service_cost', '')}<br/><br/>

            <b>Bot Session Details:</b><br/>
            Bot Customer ID: {bot_customer_id}<br/>
            Bot Channel: {bot_channel}<br/>
            Bot Session ID: {bot_session_id}<br/>
            Bot Current Stage: {bot_current_stage}<br/>
            Bot Active Service: {bot_active_service}<br/>
            Bot Workflow Source: {bot_workflow_source}<br/>
            Bot Callback Reference: {bot_callback_reference}<br/>
        """

        lead.message_post(
            body=Markup(message),
            message_type='comment'
        )

        return lead, additional_res

    @http.route(
        '/api/v1/crm/lead/checklist/upload',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def lead_checklist_upload(self, **kwargs):
        """Upload checklist attachment from n8n.
        """

        try:
            # ---------------------------------------------------------
            # Authenticate
            # ---------------------------------------------------------
            auth_error = self._authenticate()
            if auth_error:
                return auth_error

            # ---------------------------------------------------------
            # Parse Payload
            # ---------------------------------------------------------
            payload = json.loads(request.httprequest.data.decode('utf-8'))
            _logger.info("Checklist Upload Payload : %s", payload)

            env = request.env

            lead_id = payload.get('lead_id')
            request_number = payload.get('request_number')
            service_code = payload.get('service_code')
            description_code = payload.get('description_code')
            bot_customer_id = payload.get('bot_customer_id')
            attachment = payload.get('attachment') or {}
            attachment_data = attachment.get('data')
            filename = attachment.get('filename')
            mimetype = attachment.get('mimetype')

            # ---------------------------------------------------------
            # Lead Validation
            # ---------------------------------------------------------
            lead = env['crm.lead'].sudo().search([
                ('id', '=', lead_id),
                ('name', '=', request_number)
            ], limit=1)

            if not lead:
                return self._build_response(
                    False,
                    status=404,
                    message="Lead not found."
                )

            # ---------------------------------------------------------
            # Checklist Validation
            # ---------------------------------------------------------
            checklist = lead.checklist_input_ids

            if not checklist:
                return self._build_response(
                    False,
                    status=404,
                    message="Checklist not generated for this lead."
                )

            # ---------------------------------------------------------
            # Checklist Line Validation
            # ---------------------------------------------------------
            checklist_line = checklist.service_checklist_line.filtered(
                lambda line: line.description_code == description_code
            )
            if not checklist_line:
                return self._build_response(
                    False,
                    status=404,
                    message="Checklist item not found.",
                    response={
                        "description_code": description_code
                    }
                )

            if not attachment_data:
                return self._build_response(
                    False,
                    status=400,
                    message="Attachment data is required.",
                    response={
                        "description_code": description_code
                    }
                )

            # ---------------------------------------------------------
            # Save Attachment
            # ---------------------------------------------------------
            write_vals = {
                'attachments': attachment_data,
            }

            if 'attachment_filename' in checklist_line._fields:
                write_vals['attachment_filename'] = filename

            if 'file_name' in checklist_line._fields:
                write_vals['file_name'] = filename

            if 'attachment_mimetype' in checklist_line._fields:
                write_vals['attachment_mimetype'] = mimetype

            if 'bot_status' in checklist_line._fields:
                if checklist_line.bot_status == 'correction_required':
                    write_vals.update({
                        'bot_status': 'correction_uploaded',
                    })

                    if 'correction_uploaded_at' in checklist_line._fields:
                        write_vals['correction_uploaded_at'] = fields.Datetime.now()
                else:
                    write_vals.update({
                        'bot_status': 'uploaded',
                    })

            checklist_line.write(write_vals)

            # ---------------------------------------------------------
            # Success Response
            # ---------------------------------------------------------
            return self._build_response(
                True,
                status=200,
                message="Checklist attachment uploaded successfully.",
                response={
                    "lead_id": lead.id,
                    "request_number": lead.name,
                    "description_code": checklist_line.description_code,
                    "uploaded": True,
                    'service_code': service_code,
                    'bot_customer_id': bot_customer_id
                }
            )

        except Exception as e:

            _logger.exception("Checklist Upload Error")

            return self._build_response(
                False,
                status=500,
                message="Unexpected server error.",
                response={
                    "error": str(e)
                }
            )

    @http.route(
        '/api/v1/crm/lead/status',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False
    )
    def get_lead_status(self, **kwargs):

        auth_error = self._authenticate()
        if auth_error:
            return auth_error

        reference = kwargs.get('reference')
        lead = request.env['crm.lead'].sudo().search([('name', '=', reference)], limit=1)

        if not lead.exists():
            return self._build_response(False, status=404, message='Lead not found')

        return self._build_response(
            success=True,
            lead_id=lead.id,
            lead_name=lead.name,
            stage=lead.stage_id.name,
            customer_name=lead.contact_name or lead.partner_id.name,
            mobile=lead.mobile,
        )

    @http.route(
    '/api/v1/crm/checklist/code',
    type='http',
    auth='public',
    methods=['GET'],
    csrf=False
    )
    def get_checklist_code(self, **kwargs):

        auth_error = self._authenticate()
        if auth_error:
            return auth_error

        service_code = kwargs.get('service_code')
        lead_id = kwargs.get('lead_id') or kwargs.get('record_id')

        if not service_code:
            return self._build_response(
                False,
                status=400,
                message='service_code is required'
            )

        service = request.env['service.type'].sudo().search(
            [('code', '=', service_code)],
            limit=1
        )

        if not service.exists():
            return self._build_response(
                False,
                status=404,
                message='Service not found'
            )

        checklist_master = request.env['checklist.data'].sudo().search(
            [('service_id', '=', service.id)],
            limit=1
        )

        if not checklist_master:
            return self._build_response(
                False,
                status=404,
                message='Checklist not found for this service'
            )

        lead = False
        bride_is_nri = False
        groom_is_nri = False

        if lead_id:
            try:
                lead_id = int(lead_id)
            except Exception:
                lead_id = False

            if lead_id:
                lead = request.env['crm.lead'].sudo().browse(lead_id)
                if not lead.exists():
                    lead = False

        if lead:
            bride_is_nri_value = str(getattr(lead, 'bride_is_nri', '') or '').lower()
            groom_is_nri_value = str(getattr(lead, 'groom_is_nri', '') or '').lower()

            bride_is_nri = bride_is_nri_value in ['yes', 'true', '1']
            groom_is_nri = groom_is_nri_value in ['yes', 'true', '1']

        description_code_list = []

        for checklist in checklist_master.checklist_data_ids:
            code = checklist.description_code

            # Bride passport should be returned only if bride is NRI
            if code == 'bride_passport' and not bride_is_nri:
                continue

            # Groom passport should be returned only if groom is NRI
            if code == 'groom_passport' and not groom_is_nri:
                continue

            description_code_list.append({
                'name': checklist.name,
                'code': checklist.description_code,
                'is_data_required': checklist.is_data_required,
                'is_attachment_required': checklist.is_attachment_required,
            })

        _logger.info(
            "Checklist Document List for service %s lead %s bride_nri=%s groom_nri=%s : %s",
            service_code,
            lead_id,
            bride_is_nri,
            groom_is_nri,
            description_code_list
        )

        return self._build_response(
            success=True,
            response=description_code_list
        )
        
    @http.route(
        '/api/v1/landoc/service-fee/calculate',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def calculate_landoc_service_fee(self, **kwargs):
        try:
            try:
                data = request.get_json_data() or {}
            except Exception:
                data = {}

            service_code = data.get('service_code')
            marriage_age_days = int(data.get('marriage_age_days') or 0)

            if not service_code:
                return {
                    "success": False,
                    "message": "service_code is required"
                }

            service = request.env['service.type'].sudo().search([
                ('code', '=', service_code)
            ], limit=1)

            if not service:
                return {
                    "success": False,
                    "message": "Service not found",
                    "service_code": service_code
                }

            landoc_fee = request.env['landoc.fees'].sudo().search([
                ('service_id', '=', service.id)
            ], limit=1)

            if not landoc_fee:
                return {
                    "success": False,
                    "message": "LANDOC fee configuration not found",
                    "service_code": service_code,
                    "service_name": service.name
                }

            fee_lines = landoc_fee.customer_fees_line

            if not fee_lines:
                return {
                    "success": False,
                    "message": "Customer fee line not configured",
                    "service_code": service_code,
                    "service_name": service.name,
                }

            # ----------------------------------------------------------
            # Calculate Late Fee
            # ----------------------------------------------------------
            late_fee = 0.0

            if marriage_age_days > 150:
                late_fee = float(
                    getattr(service, 'fees_above_one_hundred_fifty', 0.0)
                    or getattr(service, 'fees_above_150', 0.0)
                    or 0.0
                )

            fee_breakup = []
            grand_total = 0.0

            for index, line in enumerate(fee_lines):

                if line.rate <= 0:
                    continue

                label = (
                    line.product_id.display_name
                    if line.product_id
                    else getattr(line, 'name', 'LANDOC Service Fee')
                )

                # ----------------------------------------------------------
                # Apply late fee only once (first fee line)
                # ----------------------------------------------------------
                price = float(line.rate)

                additional_rate = 0.0
                if index == 0 and late_fee:
                    price += late_fee
                    additional_rate = late_fee

                taxes = line.tax_ids.compute_all(
                    price,
                    currency=line.currency_id,
                    quantity=1.0,
                )

                untaxed_amount = taxes['total_excluded']
                total_amount = taxes['total_included']
                tax_amount = total_amount - untaxed_amount

                sgst = 0.0
                cgst = 0.0
                igst = 0.0
                tax_percentage = 0.0

                for tax in taxes['taxes']:
                    tax_rec = request.env['account.tax'].browse(tax['id'])

                    tax_percentage += tax_rec.amount

                    if 'SGST' in tax_rec.name.upper():
                        sgst += tax['amount']

                    elif 'CGST' in tax_rec.name.upper():
                        cgst += tax['amount']

                    elif 'IGST' in tax_rec.name.upper():
                        igst += tax['amount']

                grand_total += total_amount

                fee_breakup.append({
                    "label": label,
                    "is_tax_applied": bool(line.tax_ids),
                    "tax_percentage": tax_percentage,
                    "untaxed_amount": round(untaxed_amount, 2),
                    "additional_rate": round(additional_rate, 2),
                    "tax_amount": round(tax_amount, 2),
                    "total_amount": round(total_amount, 2),
                    "sgst": round(sgst, 2),
                    "cgst": round(cgst, 2),
                    "igst": round(igst, 2),
                })

            return {
                "success": True,
                "service_code": service.code,
                "service_name": service.name,
                "currency": "INR",
                "late_fee": round(late_fee, 2),
                "total_amount": round(grand_total, 2),
                "fee_breakup": fee_breakup,
            }
        except Exception as e:
            _logger.exception("LANDOC: Failed to calculate service fee")
            return {
                "success": False,
                "message": str(e)
            }



    @http.route(
        '/api/v1/crm/remaining/payment',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False
    )
    def get_remaining_payment_status(self, **kwargs):
        auth_error = self._authenticate()
        if auth_error:
            return auth_error

        try:
            lead_id = int(kwargs.get("lead_id"))
        except (TypeError, ValueError):
            return self._build_response(
                False,
                status=400,
                message="Invalid or missing lead_id"
            )

        lead = request.env["crm.lead"].sudo().browse(lead_id)

        if not lead.exists():
            return self._build_response(
                False,
                status=404,
                message="Lead not found"
            )


        sale_order = request.env["sale.order"].sudo().search(
            [
                ("opportunity_id", "=", lead.id),
                ("state", "in", ["sale", "done"]),
            ],
            order="id desc",
            limit=1,
        )

        if not sale_order:
            return self._build_response(
                False,
                status=404,
                message="No confirmed sale order found."
            )

        base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url")


        remaining_to_invoice = sale_order.amount_total - sale_order.amount_invoiced

        if remaining_to_invoice > 0:

            draft_invoice = sale_order.invoice_ids.filtered(
                lambda inv: inv.state == "draft"
            )


            if not draft_invoice:
                try:
                    wizard = (
                        request.env["sale.advance.payment.inv"]
                        .sudo()
                        .with_context(
                            active_model="sale.order",
                            active_ids=sale_order.ids,
                        )
                        .create({
                            "advance_payment_method": "fixed",
                            "fixed_amount": remaining_to_invoice,
                        })
                    )

                    wizard.create_invoices()

                    draft_invoice = sale_order.invoice_ids.filtered(
                        lambda inv: inv.state == "draft"
                    ).sorted("id", reverse=True)[:1]

                    if draft_invoice:
                        draft_invoice.action_post()

                    invoice = draft_invoice

                    return self._build_response(
                        True,
                        message="Payment pending.",
                        data={
                            "payment_status": "pending",
                            "remaining_amount": remaining_to_invoice,
                            "payment_url": (
                                f"{base_url}{invoice.get_portal_url()}"
                                if invoice else ""
                            ),
                        },
                    )
                except Exception as e:
                    return self._build_response(
                        False,
                        status=400,
                        message="Error occurred while processing invoice."
                    )


        posted_invoices = sale_order.invoice_ids

        total_due = sum(posted_invoices.mapped("amount_residual"))

        if total_due == 0:
            return self._build_response(
                True,
                message="Payment completed.",
                data={
                    "payment_status": "paid",
                    "remaining_amount": 0,
                },
            )

        due_invoices = posted_invoices.filtered(
            lambda inv: inv.amount_residual > 0
        ).sorted("id", reverse=True)

        if len(due_invoices) == 1:
            # invoice = due_invoices[0]

            return self._build_response(
                True,
                message="Partially paid.",
                data={
                    "payment_status": "pending",
                    "remaining_amount": due_invoices.amount_residual,
                    "payment_url": (
                        f"{base_url}{due_invoices.get_portal_url()}"
                    ),
                },
            )

        return self._build_response(
            True,
            message="Multiple invoices pending. Kindly contact with Landoc",
            data={
                "payment_status": "processing",
                "remaining_amount": total_due,
            },
        )

    def _get_marriage_services(self, bride, groom, marriage_date):
        service_ids = request.env['service.type'].sudo().search([
            ('service_type', '=', 'marriage_registration')
        ])

        services = {
            religion: service_ids.filtered(lambda s: s.religion == religion)
            for religion in (
                'special',
                'christian',
                'muslim',
                'hindu',
                'tamilnadu',
                'hindu_tn_marriage_both',
            )
        }

        cutoff_date = date(2009, 11, 23)

        marriage_type = bride if bride == groom else 'other'

        if marriage_type == 'christian':
            return services['christian']

        if marriage_type == 'other':
            return services['special']

        if marriage_type == 'muslim':
            return (
                services['muslim']
                if marriage_date and marriage_date > cutoff_date
                else services['special']
            )

        if marriage_type == 'hindu':
            if marriage_date and marriage_date > cutoff_date:
                return (
                        services['hindu']
                        | services['tamilnadu']
                        | services['hindu_tn_marriage_both']
                )
            return services['hindu']

        return request.env['service.type'].sudo()

    @http.route(
        '/api/v1/crm/marriage/registration/options',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False
    )
    def get_marriage_registraion_options(self, **kwargs):
        auth_error = self._authenticate()
        if auth_error:
            return auth_error

        try:
            bride_religion = kwargs.get('bride_religion')
            groom_religion = kwargs.get('groom_religion')
            marriage_date = self._parse_date(kwargs.get('marriage_date'))

            services = self._get_marriage_services(
                bride_religion,
                groom_religion,
                marriage_date
            )

            options = (
                {
                    'marriage_place': 'Place where the marriage was solemnized'
                }
                if marriage_date and marriage_date < date(2020, 9, 15)
                else {
                    'bride_residence': 'Residence of the Bride',
                    'groom_residence': 'Residence of the Groom',
                    'marriage_place': 'Place where the marriage was solemnized',
                }
            )

            response = {
                'services': [
                    {
                        'service_id': service.id,
                        'service_name': service.name,
                    }
                    for service in services
                ],
                'options': options,
                'bride_religion': bride_religion,
                'groom_religion': groom_religion,
                'marriage_date': kwargs.get('marriage_date'),
            }

            return self._build_response(
                True,
                message="Marriage Registration Options.",
                data=response,
            )

        except (TypeError, ValueError):
            return self._build_response(
                False,
                status=400,
                message="Invalid or missing bride religion, groom religion or marriage date.",
            )



        
