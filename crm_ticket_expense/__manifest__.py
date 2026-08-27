{
    'name': 'CRM Ticket Expenses',
    'version': '18.0.1.0.0',
    'category': 'CRM',
    'summary': 'Link employee expenses to CRM Leads (Tickets)',
    'description': """
        Links employee expenses to Landoc CRM tickets and provides a guided
        financial workflow for confirming quotations, creating customer
        invoices, registering receipts, creating and paying vendor bills, and
        monitoring ticket collections, costs, and financial status.
    """,
    'depends': ['base', 'crm', 'account', 'hr_expense', 'custom_crm'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
        'views/hr_expense_views.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}
