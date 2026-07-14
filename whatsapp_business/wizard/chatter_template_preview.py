from odoo import api, fields, models, _
from bs4 import BeautifulSoup
from odoo.osv import expression
from odoo.exceptions import ValidationError, UserError
import requests
from odoo.addons.phone_validation.tools import phone_validation


class ChatterPreview(models.TransientModel):
    _name = 'chatter.preview'
    _description = 'Chatter template'

    @api.model
    def _selection_target_model(self):
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([])]

    selected_template_ids = fields.Many2many(comodel_name="template.whatsapp", compute="_compute_selected_template")
    model = fields.Char(string='Model')
    active_id = fields.Integer(string='Active Id')
    template_id = fields.Many2one(comodel_name="template.whatsapp", string="Templates",
                                  domain="[('id', 'in', selected_template_ids)]")
    preview_whatsapp = fields.Html(
        compute="_compute_preview_message",
        string="Message Preview")
    current_record = fields.Reference(
        string='Record',
        compute='_compute_resource_ref',
        compute_sudo=False, readonly=False,
        selection='_selection_target_model',
        store=True
    )

    ##############################
    # Default get function
    ###############################

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        context = self.env.context
        res.update({
            'model': context.get('active_model'),
            'active_id': context.get('active_id'),
        })
        return res

    ##############################
    # Compute functions
    ###############################

    @api.depends('model', 'active_id')
    def _compute_selected_template(self):
        for preview in self:
            model_template = self.env['template.whatsapp'].search(
                [('model', '=', self.model), ('state', '=', 'approved')])
            preview.selected_template_ids = model_template if model_template else False

    @api.depends('template_id')
    def _compute_resource_ref(self):
        for preview in self:
            if preview.template_id:
                model = self.model
                res = self.env[model].browse(self.active_id)
                preview.current_record = f'{model},{res.id}' if res else False
            else:
                preview.current_record = False

    @api.depends('template_id', 'current_record')
    def _compute_preview_message(self):
        for record in self:
            if record.template_id:
                record.preview_whatsapp = record.template_id._get_preview_message(self.current_record)
            else:
                record.preview_whatsapp = None

    ##############################
    # Compose message functions
    ###############################

    def send_whatsapp_message(self):
        """
        Send WhatsApp message using the selected template and log the result.
        """
        message_log = self.env['whatsapp.message.info']
        if not self.template_id:
            return
        formatted_number = self._validate_mobile_format()
        try:
            PHONE_NUMBER_ID = self.template_id.account_id.phone_number_id
            headers = self.template_id._get_headers()
            components = []

            # Prepare body parameters
            body_parameter = [
                {"type": "text", "text": ("{" + f"object.{body.variable_field}" + "}").format(object=self.current_record)}
                for body in self.template_id.variables_lines
            ]

            # Header components for media types
            header_type = self.template_id.header_type
            if header_type in ('image', 'video', 'document', 'location'):
                header_component = self._prepare_header_component(header_type)
                if header_component:
                    components.append(header_component)

            # Body component
            if self.template_id.body:
                components.append({
                    "type": "body",
                    "parameters": body_parameter,
                })

            # Build payload
            payload = {
                "messaging_product": "whatsapp",
                "to": formatted_number,
                "type": "template",
                "template": {
                    "name": self.template_id.meta_template_name,
                    "language": {"code": "en_US"},
                    "components": components
                }
            }

            url = f"{PHONE_NUMBER_ID}/messages"
            response = self.env['whatsapp.api.services'].send_request(url, payload, headers, message_loging=True)

            # Handle response and log message
            if response and response.get('messages') and response.get('contacts'):
                formated_no_id = ''
                for contact in response.get('contacts'):
                    formated_no_id = contact.get('wa_id')

                for res in response.get('messages'):
                    if res.get('message_status') == "accepted":
                        message_mail_id = self.current_record.message_post(body=self.preview_whatsapp,attachment_ids=self.template_id.file_data_attachments.ids if self.template_id.file_data_attachments else False)

                        message_log.create({
                            'mobile_number': formatted_number,
                            'formated_mobile_number': formated_no_id,
                            'template_id': self.template_id.id,
                            'account_id': self.template_id.account_id.id,
                            'message_id': res.get('id'),
                            'mail_message_id': message_mail_id.id,
                            'message_body': self.template_id.body.replace('\n', ''),
                            'state': 'sent',
                        })
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'success',
                                'message': _("Message send successfull !"),
                            }
                        }
            # If failed
            message_log.create({
                'mobile_number': formatted_number,
                'template_id': self.template_id.id,
                'account_id': self.template_id.account_id.id,
                'message_body': self.template_id.body.replace('\n', ''),
                'state': 'error',
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _("Message Failed!"),
                }
            }
        except requests.exceptions.RequestException:
            raise UserError(_("Failed to connect to WhatsApp Business API: Please check API Log."))

    ##############################
    # Helper functions
    ###############################

    def _validate_mobile_format(self, force_format="INTERNATIONAL",):
        """Validate mobile number."""
        try:
            phone_field_number = self.current_record
            field_path = self.template_id.phone_field
            if field_path:
                for attr in field_path.split('.'):
                    phone_field_number = getattr(phone_field_number, attr, False)
                    if not phone_field_number:
                        break
            country = self.env.user.partner_id.country_id if self.env.user.partner_id else False
            formatted_number = phone_validation.phone_format(
                phone_field_number,
                country.code,
                country.phone_code,
                force_format=force_format if force_format != "WHATSAPP" else "E164",
                raise_exception=True,
            )
            return formatted_number
        except Exception as e:
            raise UserError(_("Invalid recipient mobile number."))

    def _prepare_header_component(self, header_type):
        """
        Prepare the header component for the WhatsApp message based on the header type.
        """
        if header_type == 'image':
            return {
                "type": "header",
                "parameters": [{
                    "type": "image",
                    "image": {
                        'id': self.template_id._upload_message_document(self.template_id.header_attachment_ids),
                    }
                }]
            }
        elif header_type == 'video':
            return {
                "type": "header",
                "parameters": [{
                    "type": "video",
                    "video": {
                        'id': self.template_id._upload_message_document(self.template_id.header_attachment_ids),
                    }
                }]
            }
        elif header_type == 'document':
            attachment = False
            if self.template_id.report_id:
                record = self.current_record
                if not record:
                    raise ValidationError(
                        _("There is no record for preparing demo pdf in model %(model)s",
                          model=self.template_id.model_id.name))
                attachment = self.template_id._generate_attachment_from_report(record)
            else:
                attachment = self.template_id.header_attachment_ids
            if not attachment:
                raise ValidationError("Header Document is missing")
            return {
                "type": "header",
                "parameters": [{
                    "type": "document",
                    "document": {
                        'id': self.template_id._upload_message_document(attachment),
                        'filename': attachment.name
                    }
                }]
            }
        elif header_type == 'location':
            latitude = "{" + f"object.{self.template_id.location_latitude_field}" + "}"
            longitude = "{" + f"object.{self.template_id.location_longitude_field}" + "}"
            name = "{" + f"object.{self.template_id.location_name_field}" + "}"
            address = "{" + f"object.{self.template_id.location_address_field}" + "}"
            if latitude and longitude and name and address:
                return {
                    "type": "header",
                    "parameters": [{
                        "type": "location",
                        "location": {
                            "latitude": latitude.format(object=self.current_record),
                            "longitude": longitude.format(object=self.current_record),
                            "name": name.format(object=self.current_record),
                            "address": address.format(object=self.current_record)
                        }
                    }]
                }
        return None
