from odoo import fields, models, api, _
from markupsafe import Markup
from odoo.exceptions import (
    UserError,
    ValidationError,
)


class CrmChecklistTracking(models.Model):
    _name = 'crm.checklist.tracking'
    _description = 'Crm Checklist Tracking'
    _rec_name = "sequence"

    lead_id = fields.Many2one(comodel_name="crm.lead", readonly=True)
    sequence = fields.Integer(string="Step", default=1, required=True, copy=False, readonly=False)
    comments = fields.Text()
    workflow_line_id = fields.Many2one(comodel_name="workflow.line")
    landoc_stage = fields.Char(string="Landoc Stage", readonly=True)
    # attachment_file = fields.Binary()
    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        domain=lambda self: [('res_model', '=', self._name)],
        string="Attachments"
    )
    file_name = fields.Char()
    department_id = fields.Many2one(comodel_name="crm.team", readonly=True, string="Department")
    assigned_to_id = fields.Many2one(comodel_name="res.users", string="Assigned To")
    dept_members_ids = fields.Many2many('res.users', string='Members', compute='_compute_department_members_ids')
    stage_id = fields.Many2one(comodel_name="crm.stage", readonly=True, string="Stage")
    active_step = fields.Boolean()
    department_status = fields.Selection([('to_do', 'To Do'), ('in_progress', 'In Progress'), ('done', 'Done')], default='to_do', required=True, string="Status")

    timer_start = fields.Datetime()
    timer_pause = fields.Datetime()
    is_timer_running = fields.Boolean()
    remaining_hours = fields.Float("Remaining Hours", readonly=True)
    estimated_time = fields.Float(related="workflow_line_id.estimated_time", string="Estimated Time")
    time_difference = fields.Float(string="Time Difference", compute="_compute_time_difference")
    difference_status = fields.Selection(selection=[('overdue', "Overdue"), ('normal', "Normal"), ('beforehand', "Beforehand")], compute="_compute_difference_status", string="Time Status", copy=False, index=True)


    display_timer_start_primary = fields.Boolean(compute='_compute_display_timer_buttons')
    display_timer_stop = fields.Boolean(compute='_compute_display_timer_buttons')
    display_timer_pause = fields.Boolean(compute='_compute_display_timer_buttons')
    display_timer_resume = fields.Boolean(compute='_compute_display_timer_buttons')
    company_id = fields.Many2one(comodel_name='res.company',index=True)


    ############
    # Compute
    ###########

    @api.depends('sequence', 'department_id', 'landoc_stage')
    def _compute_display_name(self):
        for rec in self:
            if rec.sequence or rec.department_id or rec.landoc_stage:
                rec.display_name = f"[{rec.sequence}] - {rec.department_id.name} - {rec.landoc_stage}"
            else:
                rec.display_name = rec.sequence

    @api.depends('lead_id')
    def _compute_department_members_ids(self):
        for member in self:
            if member.department_id:
                members_list = member.department_id.member_ids.ids
                if member.department_id.user_id:
                    members_list.append(member.department_id.user_id.id)
                member.dept_members_ids = members_list
            else:
                member.dept_members_ids = []


    ############
    # ORM
    ###########
    def unlink(self):
        """
        Inherited write function.
        Preventing an active step record's deletion.
        """
        for record in self:
            if record.active_step:
                raise ValidationError(_("You can not delete current checklist."))
        return super().unlink()

    ##################
    # Timer Functions
    ##################
    @api.depends('remaining_hours', 'estimated_time', 'difference_status')
    def _compute_difference_status(self):
        for record in self:
            if record.estimated_time is not None and record.remaining_hours is not None:
                time_difference = record.estimated_time - record.remaining_hours
                if time_difference < 0:
                    record.difference_status = 'overdue'
                elif time_difference == 0:
                    record.difference_status = 'normal'
                else:
                    record.difference_status = 'beforehand'
            else:
                record.difference_status = 'normal'

    @api.depends('remaining_hours', 'estimated_time')
    def _compute_time_difference(self):
        for record in self:
            if record.estimated_time is not None and record.remaining_hours is not None:
                record.time_difference = abs(record.estimated_time - record.remaining_hours)
            else:
                record.time_difference = False

    def action_timer_start(self):

        if not self.timer_start:
            self.write({'timer_start': fields.Datetime.now()})
            self.lead_id.write({'timer_start': fields.Datetime.now()})


    def action_timer_stop(self):
        if not self.timer_start:
            return False
        minutes_spent = self._get_minutes_spent()
        self.write({'timer_start': False, 'timer_pause': False})
        self.remaining_hours += minutes_spent
        self.lead_id.write({'timer_start': False, 'timer_pause': False, 'remaining_hours':  self.remaining_hours})
        return minutes_spent

    def _get_minutes_spent(self):
        start_time = self.timer_start
        stop_time = fields.Datetime.now()
        # timer was either running or paused
        if self.timer_pause:
            start_time += (stop_time - self.timer_pause)
        # return (stop_time - start_time).total_seconds() / 60  # convert to minute if needed.
        return round((stop_time - start_time).total_seconds() / 3600, 2)  # convert to hours.


    def action_timer_pause(self):
        self.write({'timer_pause': fields.Datetime.now()})
        self.lead_id.write({'timer_pause': fields.Datetime.now()})


    def action_timer_resume(self):
        if self.timer_start and self.timer_pause:
            new_start = self.timer_start + (fields.Datetime.now() - self.timer_pause)
            self.write({'timer_start': new_start, 'timer_pause': False})
            self.lead_id.write({'timer_start': new_start, 'timer_pause': False})


    @api.depends('timer_start', 'timer_pause')
    def _compute_display_timer_buttons(self):
        for record in self:
            start_p, stop, pause, resume = True, True, True, True
            if record.timer_start:
                start_p = False
                stop = True
            if record.timer_pause:
                pause = False
            else:
                resume = False
            if not record.timer_start:
                stop = False
                pause = False

            record.update({
                'display_timer_start_primary': start_p,
                'display_timer_stop': stop,
                'display_timer_pause': pause,
                'display_timer_resume': resume,
            })

    ##########
    # Action
    ##########
    def action_set_status_done(self):
        checklist_tracking_line = self.lead_id.checklist_tracking_line

        for checklist in checklist_tracking_line:
            checklist.active_step = False
            if checklist.id == self.id:
                checklist.active_step = True
                checklist.department_status = 'done'

        active_step = checklist_tracking_line.filtered(lambda l: l.active_step)

        if checklist_tracking_line and len(active_step) == 0:
            raise UserError(_("One step should be active."))
        if checklist_tracking_line and len(active_step) > 1:
            raise UserError(_("Only one step can be active at a time."))
        if active_step and active_step.landoc_stage != self.lead_id.landoc_stage:
            self.lead_id.landoc_stage = active_step.landoc_stage
        if active_step and active_step.department_id.id != self.lead_id.team_id.id:
            self.lead_id.team_id = active_step.department_id.id
        if active_step and active_step.assigned_to_id.id != self.lead_id.assigned_to_id.id:
            self.lead_id.assigned_to_id = active_step.assigned_to_id.id

        if self.lead_id.team_id.id != active_step.department_id.id or self.lead_id.assigned_to_id.id != active_step.assigned_to_id.id:
            crm_kanban_action = self.env['ir.actions.actions']._for_xml_id('crm.crm_lead_action_pipeline')
            crm_kanban_action['target'] = 'main'
            return crm_kanban_action







