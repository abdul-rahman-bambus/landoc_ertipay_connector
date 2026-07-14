{
    'name': 'Custom Landoc',
    'version': '18.0',
    'category': 'Sales',
    'active': True,
    'summary': 'Landoc Customization',
    'author': 'Bambus Technologies LLP',
    'sequence': '1',
    'website': 'https://bambustechnologies.in/',
    'depends': [
        'base', 'sale', 'sale_crm', 'hr', 'crm', 'sale_management', 'product', 'contacts', 'account', 'hr_expense', 'purchase',
    ],
    'data': [
        # ---------- security ----------------#
        'security/landoc_security.xml',
        'security/ir.model.access.csv',
        # ---------- data ----------------#
        'data/ir_sequence_common.xml',
        'data/department_data.xml',
        # ---------- views ----------------#
        'views/menu_items.xml',
        'views/checklist_master.xml',
        'views/product_category.xml',
        'views/workflow_master.xml',
        'views/services.xml',
        'views/city_and_zone.xml',
        'views/sro_view.xml',
        'views/res_religion.xml',
        'views/property_type.xml',
        'views/res_company.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_view.xml',
        'views/landoc_fees_view.xml',
        'views/landoc_service_appointment_view.xml'
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
