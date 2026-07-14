# -*- coding: utf-8 -*-

import urllib.parse

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LandocServiceAvailability(models.Model):
    _name = 'landoc.service.availability'
    _description = 'LANDOC Service Availability'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'available_date asc, id asc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True
    )

    service_category_id = fields.Many2one(comodel_name="product.category", domain="[('is_service','=',True)]",
                                          tracking=1, string="Category of Service")
    service_id = fields.Many2one(comodel_name="service.type",
                                 domain="[('service_category_id','=',service_category_id)]", tracking=1,
                                 string="Service")
    service_ids = fields.Many2many(comodel_name="service.type",
                                 domain="[('service_category_id','=',service_category_id)]", tracking=1,
                                 string="Service")

    service_code = fields.Char(
        string='Service Code',
        tracking=True,
        help='Example: muslim_marriage, hindu_marriage, ec_process'
    )

    service_name = fields.Char(
        string='Service Name',
        tracking=True,
        help='Example: Muslim Marriage Registration'
    )

    available_date = fields.Date(
        string='Available Date',
        required=True,
        tracking=True
    )

    month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Month', compute='_compute_month_year', store=True)

    year = fields.Char(
        string='Year',
        compute='_compute_month_year',
        store=True
    )

    location = fields.Char(
        string='Location',
        tracking=True,
        help='Optional. Example: Registrar Office, Erode'
    )

    notes = fields.Text(
        string='Notes'
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        index=True
    )

    booking_count = fields.Integer(
        string='Bookings',
        compute='_compute_booking_count'
    )

    @api.onchange('service_category_id')
    def onchange_service_category_id(self):
        self.service_id = False

    @api.onchange('service_id')
    def onchange_service_id(self):
        self.service_name = self.service_id.name
        service_code = self.service_id.name.replace(" ", "_") if self.service_id.name else self.service_id.name
        self.service_code = service_code.lower() if service_code else False

    @api.depends('service_name', 'available_date')
    def _compute_name(self):
        for rec in self:
            if rec.service_name and rec.available_date:
                rec.name = '%s - %s' % (rec.service_name, rec.available_date.strftime('%d/%m/%Y'))
            elif rec.service_name:
                rec.name = rec.service_name
            else:
                rec.name = 'Service Availability'

    @api.depends('available_date')
    def _compute_month_year(self):
        for rec in self:
            if rec.available_date:
                rec.month = rec.available_date.strftime('%m')
                rec.year = rec.available_date.strftime('%Y')
            else:
                rec.month = False
                rec.year = False

    def _compute_booking_count(self):
        Booking = self.env['landoc.service.booking'].sudo()

        for rec in self:
            if not rec.available_date or not rec.service_code:
                rec.booking_count = 0
                continue

            domain = [
                ('service_code', '=', rec.service_code),
                ('selected_date', '=', rec.available_date),
                ('status', 'in', ['selected', 'confirmed']),
                ('active', '=', True),
            ]

            if rec.location:
                domain.append(('location', '=', rec.location))

            rec.booking_count = Booking.search_count(domain)

    @api.constrains('available_date')
    def _check_available_date(self):
        today = fields.Date.context_today(self)

        for rec in self:
            if rec.available_date and rec.available_date < today:
                raise UserError(_('Available date cannot be a past date.'))

    _sql_constraints = [
        (
            'service_date_location_unique',
            'unique(service_code, available_date, location, company_id)',
            'This available date already exists for this service and location.'
        )
    ]


class LandocServiceBooking(models.Model):
    _name = 'landoc.service.booking'
    _description = 'LANDOC Service Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'selected_date desc, id desc'

    name = fields.Char(
        string='Booking Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        tracking=True
    )

    lead_id = fields.Many2one(
        'crm.lead',
        string='Lead',
        required=True,
        tracking=True,
        ondelete='cascade'
    )

    service_category_id = fields.Many2one(comodel_name="product.category", domain="[('is_service','=',True)]",
                                          tracking=1, string="Category of Service")
    service_id = fields.Many2one(comodel_name="service.type",
                                 domain="[('service_category_id','=',service_category_id)]", tracking=1,
                                 string="Service")

    request_number = fields.Char(
        string='Request Number',
        related='lead_id.name',
        store=True,
        readonly=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='lead_id.partner_id',
        store=True,
        readonly=True
    )

    customer_name = fields.Char(
        string='Customer Name',
        compute='_compute_customer_details',
        store=True
    )

    customer_mobile = fields.Char(
        string='Customer Mobile',
        compute='_compute_customer_details',
        store=True
    )

    service_code = fields.Char(
        string='Service Code',
        tracking=True
    )

    service_name = fields.Char(
        string='Service Name',
        tracking=True
    )

    selected_date = fields.Date(
        string='Selected Date',
        required=True,
        tracking=True
    )

    location = fields.Char(
        string='Location',
        tracking=True
    )

    status = fields.Selection([
        ('selected', 'Selected'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ], string='Status', default='selected', tracking=True)

    source = fields.Selection([
        ('bot', 'Bot'),
        ('backend', 'Backend'),
        ('manual', 'Manual'),
    ], string='Source', default='bot', tracking=True)

    bot_customer_id = fields.Char(
        string='Bot Customer ID'
    )

    bot_channel = fields.Char(
        string='Bot Channel',
        default='chat'
    )

    bot_session_id = fields.Char(
        string='Bot Session ID'
    )

    google_calendar_link = fields.Char(
        string='Google Calendar Link',
        compute='_compute_google_calendar_link',
        store=True
    )

    notes = fields.Text(
        string='Notes'
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        index=True
    )

    responsible_user_id = fields.Many2one(
        'res.users', readonly=True,
        string='External User',
    )

    @api.onchange('lead_id')
    def onchange_lead_id(self):
        self.service_category_id = self.lead_id.service_category_id.id
        self.service_id = self.lead_id.service_id.id

    @api.onchange('service_id')
    def onchange_service_id(self):
        self.service_name = self.service_id.name
        service_code = self.service_id.name.replace(" ", "_") if self.service_id.name else self.service_id.name
        self.service_code = service_code.lower() if service_code else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'landoc.service.booking'
                ) or 'New'

        records = super().create(vals_list)

        for booking in records:
            booking.message_post(
                body=_(
                    'Service booking created.<br/>'
                    '<b>Selected Date:</b> %s<br/>'
                    '<b>Service:</b> %s<br/>'
                    '<b>Location:</b> %s'
                ) % (
                    booking.selected_date.strftime('%d/%m/%Y') if booking.selected_date else '',
                    booking.service_name or booking.service_code or '',
                    booking.location or ''
                )
            )

        return records

    @api.depends(
        'lead_id',
        'lead_id.partner_id',
        'lead_id.contact_name',
        'lead_id.phone',
        'lead_id.mobile'
    )
    def _compute_customer_details(self):
        for rec in self:
            lead = rec.lead_id
            partner = lead.partner_id if lead else False

            if lead:
                rec.customer_name = (
                    partner.name
                    or lead.contact_name
                    or lead.partner_name
                    or lead.name
                    or ''
                )

                rec.customer_mobile = (
                    lead.mobile
                    or lead.phone
                    or partner.mobile
                    or partner.phone
                    or ''
                )
            else:
                rec.customer_name = ''
                rec.customer_mobile = ''

    @api.depends('selected_date', 'service_name', 'service_code', 'location')
    def _compute_google_calendar_link(self):
        for rec in self:
            rec.google_calendar_link = ''

            if not rec.selected_date:
                continue

            title = rec.service_name or rec.service_code or 'LANDOC Service Appointment'
            location = rec.location or ''
            details = 'LANDOC service appointment date confirmed.'

            # All-day Google Calendar event format: YYYYMMDD/YYYYMMDD+1
            start_date = rec.selected_date.strftime('%Y%m%d')
            end_date = fields.Date.add(rec.selected_date, days=1).strftime('%Y%m%d')

            params = {
                'action': 'TEMPLATE',
                'text': title,
                'dates': '%s/%s' % (start_date, end_date),
                'details': details,
                'location': location,
            }

            rec.google_calendar_link = 'https://calendar.google.com/calendar/render?' + urllib.parse.urlencode(params)

    @api.constrains('selected_date')
    def _check_selected_date(self):
        today = fields.Date.context_today(self)

        for rec in self:
            if rec.selected_date and rec.selected_date < today:
                raise UserError(_('Selected booking date cannot be a past date.'))

    @api.constrains('lead_id', 'status')
    def _check_single_active_booking_per_lead(self):
        for rec in self:
            if rec.status in ['selected', 'confirmed']:
                existing = self.search([
                    ('id', '!=', rec.id),
                    ('lead_id', '=', rec.lead_id.id),
                    ('status', 'in', ['selected', 'confirmed']),
                    ('active', '=', True),
                ], limit=1)

                if existing:
                    raise UserError(
                        _('This lead already has an active booking: %s') % existing.name
                    )

    def action_confirm_booking(self):
        for rec in self:
            rec.status = 'confirmed'
            rec.message_post(body=_('Service booking confirmed.'))
        return True

    def action_cancel_booking(self):
        for rec in self:
            rec.status = 'cancelled'
            rec.message_post(body=_('Service booking cancelled.'))
        return True

    def action_complete_booking(self):
        for rec in self:
            rec.status = 'completed'
            rec.message_post(body=_('Service booking completed.'))
        return True

    def action_reset_to_selected(self):
        for rec in self:
            rec.status = 'selected'
            rec.message_post(body=_('Service booking reset to selected.'))
        return True