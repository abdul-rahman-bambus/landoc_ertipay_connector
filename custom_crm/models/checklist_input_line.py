from odoo import fields, models, api, _

from odoo.exceptions import (
    UserError,
)


class ChecklistInputLine(models.Model):
    _name = 'checklist.input.line'
    _description = 'Checklist Input Line'
    _rec_name = "client_type_name"

    checklist_id = fields.Many2one(comodel_name="checklist.input", index=True, ondelete='cascade', string="Checklist ")
    name = fields.Char(string="Checklist")
    description_code = fields.Char(string="Description Code", compute="_compute_description_code")
    is_data_required = fields.Boolean(string="Data Field")
    is_attachment_required = fields.Boolean(string="Attachment")
    data_field = fields.Char(string="Data")
    aadhaar_front_attachment = fields.Binary(copy=False)
    aadhaar_front_file_name = fields.Char()
    aadhaar_back_attachment = fields.Binary(copy=False)
    aadhaar_back_file_name = fields.Char()
    attachments = fields.Binary(copy=False)
    file_name = fields.Char()
    order_sequence = fields.Integer(string="Order Sequence", default=1)
    is_seller_minor = fields.Boolean(default=False)
    is_buyer_minor = fields.Boolean(default=False)
    is_buyer_representative = fields.Boolean(default=False)
    is_seller_representative = fields.Boolean(default=False)
    client_type = fields.Selection(selection=[('buyer', 'Buyer'), ('seller', 'Seller'), ('witness', 'Witness'), ('minor_guardian', 'Minor/Guardian'), ('representative', 'Representative')], string="Client Type",
                                      copy=False, index=True)
    client_type_name = fields.Char(string="Content")

    contact_name = fields.Char()
    title = fields.Many2one(comodel_name="res.partner.title")
    # Address fields
    street = fields.Char('Street', readonly=False, store=True)
    street2 = fields.Char('Street2', readonly=False, store=True)
    zip = fields.Char('Zip', change_default=True, readonly=False, store=True)
    city_id = fields.Many2one("res.city", string="City ", readonly=False,
                              store=True)
    city = fields.Char(string='City', related="city_id.name", readonly=True)
    state_id = fields.Many2one(
        "res.country.state", string='State', readonly=False, store=True,
        domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one(
        'res.country', string='Country', readonly=False, store=True)

    mobile = fields.Char(default="+91 ", string="Whatsapp No ", required=True)
    relation = fields.Selection(selection=[('w/o', 'W/o'), ('s/o', 'S/o'), ('d/o', 'D/o'), ('h/o', 'H/o'), ('c/o', 'C/o')])
    aadhaar_no = fields.Char(string="Aadhaar No.")
    to_whom = fields.Char(string="To Whom")
    company_id = fields.Many2one(comodel_name='res.company',index=True)

    @api.depends('checklist_id')
    def _compute_description_code(self):
        for data in self:
            description_code = data.name.replace(" ", "_") if data.name else data.name
            data.description_code = description_code.lower() if description_code else False

    @api.onchange('order_sequence')
    def order_sequence_onchange_method(self):
        if self.order_sequence:
            if self.client_type == 'buyer':
                self.client_type_name = f"Buyer {self.order_sequence}"
            if self.client_type == 'seller':
                self.client_type_name = f"Seller {self.order_sequence}"
            if self.client_type == 'witness':
                self.client_type_name = f"Witness {self.order_sequence}"


    def action_checklist_form(self):
        def_country_id = self.env['res.country'].search([('code', '=', 'IN')],limit=1)
        checklist_action = self.env['ir.actions.actions']._for_xml_id('custom_crm.content_checklists_wiz_act_window')
        checklist_action['target'] = "new"
        checklist_action['context'] = {'default_checklist_line_id': self.id,
                                       'default_contact_name': self.contact_name,
                                       # 'default_company_id': self.company_id.id,
                                       'default_title': self.title.id,
                                       'default_mobile': self.mobile,
                                       'default_aadhaar_no': self.aadhaar_no,
                                       'default_to_whom': self.to_whom,
                                       'default_relation': self.relation,
                                       # 'default_file_name': self.file_name,
                                       # 'default_attachments': self.attachments,
                                       'default_aadhaar_front_file_name': self.aadhaar_front_file_name,
                                       'default_aadhaar_front_attachment': self.aadhaar_front_attachment,
                                       'default_aadhaar_back_file_name': self.aadhaar_back_file_name,
                                       'default_aadhaar_back_attachment': self.aadhaar_back_attachment,
                                       'default_street': self.street,
                                       'default_street2': self.street2,
                                       'default_zip': self.zip,
                                       'default_city_id': self.city_id.id,
                                       'default_state_id': self.state_id.id,
                                       'default_country_id': self.country_id.id if self.country_id else def_country_id.id,
                                       }
        return checklist_action


class ServiceChecklistLine(models.Model):
    _name = 'service.checklist.line'
    _description = 'Checklist Service Line'

    checklist_id = fields.Many2one(comodel_name="checklist.input", string="Checklist ")
    name = fields.Char(string="Checklist")
    description_code = fields.Char(string="Description Code", compute="_compute_description_code")
    is_data_required = fields.Boolean(string="Data Field")
    is_attachment_required = fields.Boolean(string="Attachment")
    data_field = fields.Char(string="Data")
    attachments = fields.Binary(copy=False)
    file_name = fields.Char()
    company_id = fields.Many2one(comodel_name='res.company', index=True)
    bot_status = fields.Selection([
        ('pending', 'Pending'),
        ('uploaded', 'Uploaded'),
        ('approved', 'Approved'),
        ('correction_required', 'Correction Required'),
        ('correction_uploaded', 'Correction Uploaded'),
        ('rejected', 'Rejected'),
    ], string='Bot Status', default='pending', copy=False)

    correction_reason = fields.Text(string='Correction Reason')
    correction_requested_at = fields.Datetime(string='Correction Requested At', copy=False)
    correction_uploaded_at = fields.Datetime(string='Correction Uploaded At', copy=False)
    approved_at = fields.Datetime(string='Approved At', copy=False)

    attachment_filename = fields.Char(string='Filename')
    attachment_mimetype = fields.Char(string='Mimetype')

    def action_approve_document(self):
        for line in self:
            line.write({
                'bot_status': 'approved',
                'approved_at': fields.Datetime.now(),
                'correction_reason': False,
            })

            # if line.checklist_id and line.checklist_id.lead_id:
            #     line.checklist_id.lead_id.message_post(
            #         body=_("Checklist document approved: %s") % (line.name or '')
            #     )

        return True

    def action_request_correction(self):
        for line in self:
            if not line.correction_reason:
                raise UserError(
                    _("Please enter correction reason for '%s' before requesting correction.")
                    % (line.name or '')
                )

            checklist = line.checklist_id
            if not checklist:
                raise UserError(_("Checklist is missing."))

            lead = checklist.lead_id
            if not lead:
                raise UserError(_("Lead is missing for this checklist."))

            correction_items = [{
                "name": line.name or "",
                "description_code": line.description_code or "",
                "reason": line.correction_reason or "Please upload the correct document.",
                "is_data_required": line.is_data_required,
                "is_attachment_required": line.is_attachment_required,
            }]

            line.write({
                'bot_status': 'correction_required',
                'correction_requested_at': fields.Datetime.now(),
            })

            checklist._send_document_correction_to_n8n(correction_items)

            lead.message_post(
                body=_(
                    "Correction requested for checklist document: %s<br/>"
                    "Reason: %s"
                ) % (
                    line.name or '',
                    line.correction_reason or ''
                )
            )

        return True

    def action_reject_document(self):
        for line in self:
            line.write({
                'bot_status': 'rejected',
            })

            if line.checklist_id and line.checklist_id.lead_id:
                line.checklist_id.lead_id.message_post(
                    body=_("Checklist document rejected: %s") % (line.name or '')
                )

        return True

    def action_preview_attachment(self):
        self.ensure_one()

        if not self.attachments:
            raise UserError(_("No attachment found for this checklist item."))

        filename = self.file_name or self.name or 'document'

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/attachments/%s?download=false' % (
                self._name,
                self.id,
                filename
            ),
            'target': 'new',
        }


    @api.depends('checklist_id')
    def _compute_description_code(self):
        for data in self:
            description_code = data.name.replace(" ", "_") if data.name else data.name
            data.description_code = description_code.lower() if description_code else False


class PropertyChecklistLine(models.Model):
    _name = 'property.checklist.line'
    _description = 'Checklist Property Line'

    checklist_id = fields.Many2one(comodel_name="checklist.input", string="Checklist ")
    name = fields.Char(string="Checklist")
    description_code = fields.Char(string="Description Code", compute="_compute_description_code")
    is_data_required = fields.Boolean(string="Data Field")
    is_attachment_required = fields.Boolean(string="Attachment")
    data_field = fields.Char(string="Data")
    attachments = fields.Binary(copy=False)
    file_name = fields.Char()
    company_id = fields.Many2one(comodel_name='res.company',index=True)

    @api.depends('checklist_id')
    def _compute_description_code(self):
        for data in self:
            description_code = data.name.replace(" ", "_") if data.name else data.name
            data.description_code = description_code.lower() if description_code else False
