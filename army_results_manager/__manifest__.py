# -*- coding: utf-8 -*-
{
    'name': "Army Results Manager",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['web', 'base', 'hr', 'web_unsplash'],

    "assets": {
        "web.assets_backend": [
            "army_results_manager/static/src/components/**/*.js",
            "army_results_manager/static/src/components/**/*.xml",
            "army_results_manager/static/src/components/**/*.css",
        ],
    },
    # always loaded
    'data': [
        "security/training_result_security.xml",
        "security/ir.model.access.csv",
        'views/remove_odoo_title.xml',
        'data/training_category_data.xml',
        'data/training_subject_data.xml',
        'wizard/print_word_wizard.xml',
        'views/hr_department_views.xml',
        'views/training_mission.xml',
        'views/training_month.xml',
        'views/training_mission_line.xml',
        'views/training_result.xml',
        'views/hr_employee_views.xml',
        'wizard/modify_reason_wizard.xml',
        'views/training_plan.xml',
        'views/training_course_view.xml',
        'views/training_subject.xml',
        'views/menu_view.xml',
    ],

}
