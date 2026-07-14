{
    'name': 'Custom CRM',
    'version': '18.0',
    'category': 'Sales',
    'active': True,
    'summary': 'CRM Customization',
    'author': 'Bambus Technologies LLP',
    'sequence': '1',
    'website': 'https://bambustechnologies.in/',
    'depends': [
        'base', 'sale', 'crm', 'stock', 'partner_city_m2o', 'sale_management', 'hr_expense', 'account', 'custom_landoc', 'sales_team',
    ],
    'external_dependencies': {
        'python': ['phonenumbers'],
    },
    'data': [
        # ---------- security ----------------#
        'security/crm_security.xml',
        'security/ir.model.access.csv',
        # ---------- data ----------------#
        'data/account_analytic_data.xml',
        'data/ir_sequence_common.xml',
        # ---------- views ----------------#
        'views/checklist_input.xml',
        'views/hr_expense.xml',
        'views/hr_employee.xml',
        'views/account_move_views.xml',
        'views/res_partner.xml',
        'views/sale_order_view.xml',
        # ---------- wizard ----------------#
        'wizard/checklist_tracking.xml',
        'wizard/department_transfer.xml',
        'wizard/content_checklists_from_wiz.xml',
        'wizard/crm_lead_to_opportunity_views.xml',
        'wizard/legal_service_process.xml',

        # - crm_lead view having wizard action id.
        'views/crm_lead.xml',
    ],
    'description': """
    """,
    'demo_xml': [],
    'license': 'OPL-1',
    "images": ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
