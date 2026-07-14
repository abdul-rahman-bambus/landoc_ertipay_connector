from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import re
import html
import base64
from odoo.tools.safe_eval import safe_eval
from odoo.addons.phone_validation.tools import phone_validation

_logger = logging.getLogger(__name__)


class WhatsAppTemplate(models.Model):
    _name = 'template.whatsapp'
    _inherit = ['mail.thread']
    _description = 'WhatsApp Message'

    # ----------------------------------------
    # Fields
    # ----------------------------------------
    name = fields.Char(string='Name', required=True, tracking=True)
    model_id = fields.Many2one('ir.model', string='Model', ondelete='cascade', required=True)
    active = fields.Boolean(default=True, help="When unchecked, the rule is hidden and will not be executed.")
    model = fields.Char(string='Related Document Model', related='model_id.model', precompute=True, store=True, readonly=True)
    account_id = fields.Many2one('whatsapp.account.details', string='Account')
    state = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending'), ('submitted', 'Waiting'), ('in_appeal', 'In Appeal'),
        ('approved', 'Approved'), ('paused', 'Paused'), ('disabled', 'Disabled'), ('rejected', 'Rejected'),
        ('pending_deletion', 'Pending Deletion'), ('deleted', 'Deleted'), ('limit_exceeded', 'Limit Exceeded')],
        string='State', default='draft', required=True, tracking=True)
    meta_template_state = fields.Char(readonly=True)
    # Location fields
    location_latitude = fields.Char(string="Latitude Sample Value")
    location_latitude_field = fields.Char(string="Location Latitude Field")
    location_longitude = fields.Char(string="Longitude Sample Value")
    location_longitude_field = fields.Char(string="Location Longitude Field")
    location_name = fields.Char(string="Name Sample Value")
    location_name_field = fields.Char(string="Location Name Field")
    location_address = fields.Char(string="Address Sample Value")
    location_address_field = fields.Char(string="Location Address Field")
    # Meta fields
    meta_template_name = fields.Char(string="Meta Template Name", readonly=True, copy=False, tracking=True)
    phone_field = fields.Char(string="Phone Field", tracking=True)
    media_json = fields.Text(copy=False)
    media_id = fields.Char(copy=False)
    media_url = fields.Char(copy=False)
    meta_template_id = fields.Char(string="Meta template ID", copy=False)
    is_update_template = fields.Boolean(string="Update Template", copy=False)
    category_type = fields.Selection([
        ('authentication', 'Authentication'),
        ('marketing', 'Marketing'),
        ('utility', 'Utility')],
        string="Category", default='utility', required=True, tracking=True,
        help="Authentication - One-time passwords that your customers use to authenticate a transaction or login.\n"
             "Marketing - Promotions or information about your business, products or services. Or any message that isn't utility or authentication.\n"
             "Utility - Messages about a specific transaction, account, order or customer request.")
    footer_text = fields.Char(string="Footer Message")
    body = fields.Text(string="Body content")
    header_type = fields.Selection([
        ('none', 'None'), ('text', 'Text'), ('image', 'Image'),
        ('video', 'Video'), ('document', 'Document'), ('location', 'Location')],
        string="Header Type", default='none', tracking=True)
    header_text = fields.Char(string="Template Header Text", size=60)
    header_attachment_ids = fields.Many2many('ir.attachment', string="Template Static Header", copy=False)
    file_data_attachments = fields.Many2one('ir.attachment', string="File data attachments", copy=False)
    report_id = fields.Many2one(
        comodel_name='ir.actions.report', string="Report",
        compute="_compute_report_id", readonly=False, store=True, copy=False,
        domain="[('model', '=', model)]")
    lang_id = fields.Many2one("res.lang")
    is_url = fields.Boolean(string="Website")
    url_name = fields.Char("Text")
    url_link = fields.Char("Url")
    is_phone_number = fields.Boolean(string="Call")
    phone_name = fields.Char("Text ")
    phone_no = fields.Char("Phone No:")
    is_quick = fields.Boolean(string="Quick Reply")
    quick_name = fields.Char("Text  ")
    trigger = fields.Selection(
        [('on_state_set', "State is set to")], string='Trigger', readonly=False, store=True)
    trigger_field_ids = fields.Many2one('ir.model.fields', string='Trigger Fields',
                                        compute='_compute_trigger_field_ids', store=True)
    trg_selection_field_id = fields.Many2one(
        'ir.model.fields.selection', string='Trigger Field',
        domain="[('field_id', '=', trigger_field_ids)]", readonly=False, store=True,
        help="Some triggers need a reference to a selection field. This field is used to store it.")
    variables_lines = fields.One2many('whatsapp.variable', 'template_id', compute="_compute_variable_line",
                                      precompute=True, readonly=False, store=True, copy=False)

    # ----------------------------------------
    # Compute Methods
    # ----------------------------------------

    @api.depends('body')
    def _compute_variable_line(self):
        """Extract variables from body and sync with variables_lines."""
        for line in self:
            matches = set(re.findall(r"\{\{\d+\}\}", line.body or ""))
            existing_vars = {v.name: v.id for v in line.variables_lines}
            to_remove = [(2, var_id) for var_name, var_id in existing_vars.items() if var_name not in matches]
            to_add = []
            for match in matches:
                if match not in existing_vars:
                    sequence = int(re.search(r'\d+', match).group())
                    to_add.append((0, 0, {'name': match, 'sequence': sequence}))
            line.variables_lines = to_remove + to_add

    @api.model
    @api.depends('model_id', 'trigger')
    def _compute_trigger_field_ids(self):
        """Compute trigger field ids for selection fields."""
        for automation in self:
            if automation.trigger == 'on_state_set':
                domain = [('model_id', '=', automation.model_id.id),
                          ('ttype', '=', 'selection'),
                          ('name', 'in', ['state', 'x_studio_state'])]
                automation.trigger_field_ids = self.env['ir.model.fields'].search(domain, limit=1)
            else:
                automation.trigger_field_ids = False

    @api.depends('model')
    def _compute_report_id(self):
        """Reset report if model changes to avoid ill defined reports."""
        to_reset = self.filtered(lambda tpl: tpl.report_id.model != tpl.model)
        if to_reset:
            to_reset.report_id = False

    # ----------------------------------------
    # Onchange Methods
    # ----------------------------------------

    @api.onchange('trigger')
    def trigger_onchange_method(self):
        """Reset trigger fields when trigger is unset."""
        if not self.trigger:
            self.trigger_field_ids = False
            self.trg_selection_field_id = False

    @api.onchange('model_id')
    def model_onchange(self):
        """Reset trigger when model changes."""
        self.trigger = False

    # ----------------------------------------
    # CRUD & Registry Operations
    # ----------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Create record and update registry, validate button exclusivity and variables."""
        records = super().create(vals_list)
        self.env['whatsapp.automation.hook'].sudo().update_registry()
        records._validate_buttons()
        records._validate_variables()
        # records._validate_mobile_format()
        return records

    def write(self, vals):
        """Write record and update registry, validate button exclusivity and variables."""
        res = super().write(vals)
        self.env['whatsapp.automation.hook'].sudo().update_registry()
        self._validate_buttons()
        self._validate_variables()
        # self._validate_mobile_format()
        return res

    def unlink(self):
        """Delete only if in draft or deleted state, update registry."""
        for record in self:
            if record.state not in ['draft', 'deleted']:
                raise ValidationError("Template not in draft or delete state: can't delete the template.")
        res = super().unlink()
        self.env['whatsapp.automation.hook'].sudo().update_registry()
        return res

    # ----------------------------------------
    # Validation Helpers
    # ----------------------------------------

    def _validate_buttons(self):
        """Ensure only one button type is set."""
        for record in self:
            if record.is_url and record.is_phone_number and record.is_quick:
                raise ValidationError("Can't pass Url, Phone, Quick reply buttons to the template at same time.")
            if (record.is_quick and record.is_phone_number) or (record.is_url and record.is_quick) or (record.is_url and record.is_phone_number):
                raise ValidationError("Can't pass multiple buttons to the template at same time.")

    def _validate_variables(self):
        """Ensure all variables have temp_value and variable_field."""
        for template in self:
            for record in template.variables_lines:
                if (record.name and not record.temp_value) or not record.variable_field:
                    raise ValidationError("Variable Temporary Value or Variable Field should not be null.")

    def _validate_mobile_format(self, force_format="INTERNATIONAL",):
        """Validate mobile number."""
        try:
            country = self.env.user.partner_id.country_id if self.env.user.partner_id else False
            formatted_number = phone_validation.phone_format(
                self.phone_no,
                country.code,
                country.phone_code,
                force_format=force_format if force_format != "WHATSAPP" else "E164",
                raise_exception=True,
            )
            return formatted_number
        except Exception as e:
            raise UserError(_("Invalid mobile number."))

    # ----------------------------------------
    # Action Execution
    # ----------------------------------------

    def _run_action(self, record):
        """Execute automation code for sending messages."""
        for instance in self:
            message_instance = instance.env['chatter.preview']
            _logger.info("Executing action code for template %s and record %s", instance.id, record.id)
            message_vals = message_instance.create({
                'selected_template_ids': instance.id,
                'template_id': instance.id,
                'current_record': record,
                'model': instance.model,
                'active_id': record.id,
            })
            if message_vals.template_id.state == "approved":
                confirmation = message_vals.send_whatsapp_message()
                return confirmation

    # ----------------------------------------
    # WhatsApp API Integration
    # ----------------------------------------

    def _generate_attachment_from_report(self, record=False):
        """Create attachment from report if relevant."""
        if record and self.header_type == 'document' and self.report_id:
            report_content, report_format = self.report_id._render_qweb_pdf(self.report_id, record.id)
            report_name = (safe_eval(self.report_id.print_report_name, {'object': record}) if self.report_id.print_report_name else self.display_name) + '.' + report_format
            return self.env['ir.attachment'].create({
                'name': report_name,
                'raw': report_content,
                'mimetype': 'application/pdf',
            })
        return self.env['ir.attachment']

    def button_submit_template(self):
        """Register template to WhatsApp Business Account."""
        self.ensure_one()
        if not self.category_type:
            raise ValidationError(_("Template category is missing"))
        attachment = False
        if self.header_type in ('image', 'video', 'document'):
            if self.header_type == 'document' and self.report_id:
                record = self.env[self.model].search([], limit=1)
                if not record:
                    raise ValidationError(_("There is no record for preparing demo pdf in model %(model)s", model=self.model_id.name))
                attachment = self._generate_attachment_from_report(record)
            else:
                attachment = self.header_attachment_ids
            if not attachment:
                raise ValidationError("Header Document is missing")
        file_handle = False
        if attachment:
            try:
                file_handle = self._upload_demo_document(attachment)
            except Exception as e:
                raise UserError(str(e))
        return self._get_template_head_component(file_handle)

    def _upload_demo_document(self, attachment):
        """Upload demo document to WhatsApp and return file handle."""
        WHATSAPP_ACCOUNT_ID = self.account_id.account_app_id
        params = {
            'file_length': attachment.file_size,
            'file_type': attachment.mimetype,
            'access_token': self.account_id.access_token,
        }
        _logger.info("Open template sample document upload session with file size %s Bites of mimetype %s on account %s [%s]",
            attachment.file_size, attachment.mimetype, self.account_id.name, self.account_id.id)
        uploads_session_response = self.env['whatsapp.api.services'].send_request(f"{WHATSAPP_ACCOUNT_ID}/uploads", params=params)
        upload_session_id = uploads_session_response.get('id')
        if not upload_session_id:
            raise UserError(_("Document upload session open failed, please retry after sometime."))
        headers = self._get_headers(OAuth=True)
        headers.update({'file_offset': '0'})
        file_data = base64.b64decode(attachment.raw) if isinstance(attachment.raw, str) else attachment.raw
        upload_file_response = self.env['whatsapp.api.services'].send_request(f"{upload_session_id}", params=params,
                                                                              headers={'file_offset': '0'},
                                                                              data=file_data)
        file_handle = upload_file_response.get('h')
        self.media_url = file_handle
        if not file_handle:
            raise UserError(_("Document upload failed, please retry after sometime."))
        return file_handle

    def _upload_message_document(self, attachment):
        """Upload message document for template registration."""
        phone_number_id = self.account_id.phone_number_id
        access_token = self.account_id.access_token
        self.file_data_attachments = attachment if self.file_data_attachments != attachment else self.file_data_attachments
        file_data = base64.b64decode(attachment.raw) if isinstance(attachment.raw, str) else attachment.raw
        files = [('file', (attachment.name, file_data, attachment.mimetype))]
        params = {'access_token': access_token, 'messaging_product': 'whatsapp'}
        _logger.info("Open template sample document upload session with file size %s Bites of mimetype %s on account %s [%s]",
            attachment.file_size, attachment.mimetype, self.account_id.name, self.account_id.id)
        uploads_meida = self.env['whatsapp.api.services'].send_request(f"{phone_number_id}/media", params=params, files=files)
        upload_session_id = uploads_meida.get('id')
        if not upload_session_id:
            raise UserError(_("File uploading failed, please retry after sometime."))
        _logger.info("File uploading successful using account %s [%s]", self.account_id.name, self.account_id.id)
        self.media_id = upload_session_id
        return upload_session_id

    def _get_headers(self, token=False, OAuth=False):
        """Return appropriate headers for WhatsApp API requests."""
        if token:
            return {"Authorization": f"Bearer {self.account_id.access_token}"}
        if OAuth:
            return {"Authorization": f"OAuth {self.account_id.access_token}"}
        return {"Authorization": f"Bearer {self.account_id.access_token}", "Content-Type": "application/json"}

    def _get_template_head_component(self, file_handle=False):
        """Return header component according to header type for template registration to WhatsApp."""
        if self.header_type == 'none':
            return None
        head_component = {'type': 'HEADER', 'format': self.header_type.upper()}
        if self.header_type == 'text' and self.header_text:
            head_component['text'] = self.header_text
        if self.header_type in ['image', 'video', 'document']:
            head_component['example'] = {'header_handle': file_handle}
        return head_component

    def generate_template_json(self, template_name, condition, language="en_US", comp_dict=False):
        """Generate WhatsApp template JSON payload."""
        components = []
        if condition in ('text', 'image', 'video', 'document', 'location'):
            media_component = self.button_submit_template()
            components.append(media_component)
        if self.body:
            body_dict = {"type": "BODY", "text": self.body}
            if self.variables_lines:
                body_dict["example"] = {"body_text": [self.variables_lines.mapped('temp_value')]}
            components.append(body_dict)
        if self.footer_text:
            components.append({"type": "FOOTER", "text": self.footer_text})
        if self.is_url or self.is_quick or self.is_phone_number:
            button_list = []
            if self.is_quick:
                button_list.append({"type": "QUICK_REPLY", "text": self.quick_name})
            if self.is_url:
                button_list.append({"type": "URL", "text": self.url_name, "url": self.url_link})
            if self.is_phone_number:
                button_list.append({"type": "PHONE_NUMBER", "text": self.phone_name, "phone_number": self.phone_no})
            components.append({"type": "BUTTONS", "buttons": button_list})
        if comp_dict:
            return components
        payload = {
            "name": template_name.lower().replace(" ", "_"),
            "language": language,
            "category": self.category_type.upper(),
            "components": components
        }
        return payload

    # ----------------------------------------
    # Meta Template Management
    # ----------------------------------------

    def button_meta_validation(self):
        """Validate and submit template to WhatsApp."""
        self._validate_variables()
        WHATSAPP_BUSINESS_ACCOUNT_ID = self.account_id.whatsapp_app_id
        url = f"{WHATSAPP_BUSINESS_ACCOUNT_ID}/message_templates"
        headers = self._get_headers()
        payload = self.generate_template_json(self.name, self.header_type)
        response = self.env['whatsapp.api.services'].send_request(url, payload, headers)
        if response.get('status'):
            self.meta_template_name = self.name.lower().replace(" ", "_")
            self.state = 'submitted'
            self.meta_template_id = response.get('id')
            self.is_update_template = True

    def button_update_template(self):
        """Update WhatsApp template if allowed."""
        components = self.generate_template_json(self.name, self.header_type, comp_dict=True)
        post_body = {"components": components}
        access_token = self.account_id.access_token
        business_account_id = self.account_id.whatsapp_app_id
        template_name = self.meta_template_name
        url = f"{business_account_id}/message_templates?name={template_name}&limit=8"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = self.env['whatsapp.api.services'].get_request(url, headers)

        if not response:
            return

        for template in response.get('data', []):
            if template.get('name') != self.meta_template_name:
                continue

            status = template.get('status', '').lower()
            category = template.get('category', '').lower()

            if status not in ['approved', 'rejected', 'paused']:
                raise UserError(_("Only templates with an APPROVED, REJECTED, or PAUSED status can be edited."))

            # Category unchanged
            if self.category_type == category:
                update_response = self.env['whatsapp.api.services'].send_request(
                    f"{template.get('id')}", post_body, headers
                )
                if update_response.get('success'):
                    self.state = 'submitted'
                return

            # Category changed
            if status == 'approved':
                raise UserError(_("You cannot edit the category of an approved template."))

            post_body["category"] = self.category_type.upper()
            update_response = self.env['whatsapp.api.services'].send_request(
                f"{template.get('id')}", post_body, headers
            )
            if update_response.get('success'):
                self.state = 'submitted'
            return

    def button_delete_template(self):
        """Delete WhatsApp template via API and update state."""
        ACCESS_TOKEN = self.account_id.access_token
        WHATSAPP_BUSINESS_ACCOUNT_ID = self.account_id.whatsapp_app_id
        TEMPLATE_NAME = self.meta_template_name
        url = f"{WHATSAPP_BUSINESS_ACCOUNT_ID}/message_templates"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        response = self.env['whatsapp.api.services'].get_request(f'{url}?name={TEMPLATE_NAME}&limit=3', headers)
        if response:
            for template in response.get('data'):
                if template.get('name') == self.meta_template_name:
                    update_response = self.env['whatsapp.api.services'].delete_request(
                        f"{url}?hsm_id={template.get('id')}&name={TEMPLATE_NAME}", headers)
                    if update_response.get('success'):
                        self.active = False
                        self.state = 'deleted'
                        self.meta_template_name = False
                        self.meta_template_id = False
                        self.media_id = False
                        self.is_update_template = False

    def button_reset_to_draft(self):
        """Reset template state to draft."""
        for tmpl in self:
            tmpl.write({'state': 'draft'})

    def button_set_to_submitted(self):
        """Reset template state to submit."""
        for tmpl in self:
            tmpl.write({'state': 'submitted'})

    # ----------------------------------------
    # Cron & Status Update
    # ----------------------------------------

    def meta_temp_status_update(self):
        """Update template status from WhatsApp API."""
        accounts = self.env['template.whatsapp'].search([])
        for account in accounts:
            if account.meta_template_name and account.state != 'draft' and account.active:
                WHATSAPP_BUSINESS_ACCOUNT_ID = account.account_id.whatsapp_app_id
                TEMPLATE_NAME = account.meta_template_name
                if not account.account_id.access_token or not account.account_id.whatsapp_app_id:
                    raise UserError(_("Access Token and WhatsApp Business App ID must be set to test the connection."))
                url = f"{WHATSAPP_BUSINESS_ACCOUNT_ID}/message_templates?name={TEMPLATE_NAME}"
                headers = account._get_headers(token=True)
                response = self.env['whatsapp.api.services'].get_request(url, headers)
                if response.get('data'):
                    for status in response.get('data'):
                        if account.state != status.get('status').lower():
                            account.state = status.get('status').lower()
                            account.meta_template_state = status.get('status').upper()
                        if account.category_type != status.get('category').lower():
                            account.category_type = status.get('category').lower()

    # ----------------------------------------
    # Preview & Formatting
    # ----------------------------------------

    def _get_preview_message(self, instance):
        """Render WhatsApp message preview."""
        for record in self:
            preview_whatsapp = self.env['ir.qweb']._render('whatsapp_business.template_wh_message_preview', {
                'template_id': record,
                'header_type': record.header_type,
                'body': self._get_formatted_body(instance),
                'footer_text': record.footer_text,
            })
            return preview_whatsapp or None

    def text_to_html(self, text):
        """Escape and convert text to HTML."""
        return html.escape(text).replace('\n', '<br/>')

    def _get_formatted_body(self, instance):
        """Format body with variables for preview."""
        body = self.text_to_html(self.body)
        for var in self.variables_lines:
            if var.name and var.variable_field:
                body = body.replace(var.name, "{" + f"object.{var.variable_field}" + "}")
        if not instance:
            return body
        return body.format(object=instance)
