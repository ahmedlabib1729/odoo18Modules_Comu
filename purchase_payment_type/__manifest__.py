{
    'name': 'Purchase Invoice Payment Type',
    'version': '18.0.1.0.0',
    'summary': 'Add payment type field (Cash/Bank) on vendor bills only',
    'category': 'Accounting',
    'author': 'Your Company',
    'depends': ['account'],
    'data': [
        'views/account_move_inherit_views.xml',
    ],
    'installable': True,
    'application': False,
}
