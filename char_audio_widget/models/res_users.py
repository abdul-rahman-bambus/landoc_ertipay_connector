from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    voice_to_text_lang_id = fields.Many2one("res.trans.lang","Voice Translation Language")
    browser_config = fields.Selection(selection=[('chrome','Chrome'),('other','Other Browser')],
                                      help="Chrome browser works faster\nOther browsers may take time to recognise!")

    def get_voice_language(self):
        """Returns selected language to JS function"""

        user = self.env.user
        language = user.voice_to_text_lang_id.code
        return language
    
    def get_browser(self):
        """Returns Browser to JS function"""

        browser = self.env.user.browser_config
        return browser