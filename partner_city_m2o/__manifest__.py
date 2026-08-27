{
    "name": "Partner City Many2one",
    "version": "1.0.0",
    "summary": "Use a Many2one field for City on Contacts (res.partner)",
    "description": """
        Provides a structured city master and replaces free-text city entry with
        a Many2one selection on contacts and companies. Country, state, city,
        and ZIP values are synchronized, and Indian city master data is loaded
        during installation.
    """,
    "category": "Contacts",
    "author": "Bambus Technologies",
    "depends": ["base", "custom_landoc"],
    "data": [
        "security/ir.model.access.csv",
        "data/india_city.xml",
        "views/res_partner_view.xml"
    ],
    #"post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3"
}
