from . import models

# from odoo import SUPERUSER_ID
# from odoo.api import Environment

# def post_init_hook(cr, registry):
#     """
#     Migrate existing text 'city' values on partners into res.city records and link city_id.
#     """
#     env = Environment(cr, SUPERUSER_ID, {})
#     Partner = env["res.partner"].with_context(active_test=False)
#     City = env["res.city"]
#     partners = Partner.search([("city", "!=", False), ("city_id", "=", False)])
#     for p in partners:
#         domain = [("name", "=", p.city)]
#         if p.state_id:
#             domain.append(("state_id", "=", p.state_id.id))
#         if p.country_id:
#             domain.append(("country_id", "=", p.country_id.id))
#         city = City.search(domain, limit=1)
#         if not city:
#             vals = {"name": p.city}
#             if p.state_id:
#                 vals["state_id"] = p.state_id.id
#             if p.country_id:
#                 vals["country_id"] = p.country_id.id
#             city = City.create(vals)
#         p.city_id = city.id
