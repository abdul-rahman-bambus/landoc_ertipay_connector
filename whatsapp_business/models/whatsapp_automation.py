from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

def get_rule_dicts(env, model_name):
    """Fetch active automation rules for a given model as plain dicts."""
    rules = env['template.whatsapp'].sudo().search([
        ('model_id.model', '=', model_name),
        ('active', '=', True)
    ])
    rules.read(['trigger_field_ids', 'trg_selection_field_id'])
    return [
        {
            'id': rule.id,
            'field_name': rule.trigger_field_ids.name or '',
            'selection_value': rule.trg_selection_field_id.value or '',
        }
        for rule in rules
    ]

def trigger_automation(env, record, vals, model_name):
    """Trigger automation rules for a record and vals."""
    for rule in get_rule_dicts(env, model_name):
        try:
            template = env['template.whatsapp'].browse(rule['id'])
            # Check if the field is being set in vals (write/create)
            if rule['field_name'] and rule['field_name'] in vals and vals[rule['field_name']] == rule['selection_value']:
                template._run_action(record)
            # Fallback: check the record's field value (for create)
            elif rule['field_name'] and hasattr(record, rule['field_name']) and getattr(record, rule['field_name']) == rule['selection_value']:
                template._run_action(record)
        except Exception as e:
            _logger.warning("Automation rule %s failed: %s", rule['id'], e)

def patch_model(model_class, model_name):
    """Monkey-patch write/create for automation, only once per model."""
    if getattr(model_class, '_custom_automation_patched', False):
        return
    model_class._custom_automation_patched = True

    orig_write = model_class.write
    orig_create = model_class.create

    def write_with_trigger(self, vals):
        res = orig_write(self, vals)
        for rec in self:
            trigger_automation(self.env, rec, vals, model_name)
        return res

    def create_with_trigger(self, vals_list):
        records = orig_create(self, vals_list)
        vals_iter = vals_list if isinstance(vals_list, list) else [vals_list]
        for record, vals in zip(records, vals_iter):
            trigger_automation(self.env, record, vals, model_name)
        return records

    model_class.write = write_with_trigger
    model_class.create = create_with_trigger

class WhatsappAutomation(models.AbstractModel):
    _name = 'whatsapp.automation.hook'
    _description = 'Custom Automation Hook'

    @api.model
    def _register_hook(self):
        self.update_registry()
        return super()._register_hook()

    @api.model
    def update_registry(self):
        """Patch all models referenced by active automation rules."""
        rules = self.env['template.whatsapp'].sudo().search([])
        patched = set()
        for rule in rules:
            model_name = rule.model_id.model
            if model_name and model_name not in patched:
                try:
                    model = self.env[model_name]
                    patch_model(model.__class__, model_name)
                    patched.add(model_name)
                except Exception as e:
                    _logger.error("Failed to patch model %s: %s", model_name, e)
