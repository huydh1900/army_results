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

    # always loaded
    'data': [
        "security/training_result_security.xml",
        "security/ir.model.access.csv",
        'views/remove_odoo_title.xml',
        'data/training_category_data.xml',
        'data/training_subject_data.xml',
        'wizard/print_word_wizard.xml',
        'views/webclient_templates.xml',
        'views/training_day_line_view.xml',
        'views/auth_totp_templates.xml',
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
        'views/camera_device_views.xml',
        'views/menu_view.xml',
        'views/data_collect_views.xml',
        'data/ir_cron_data.xml',
    ],

    "assets": {
        'web.assets_frontend': [
            'army_results_manager/static/src/css/login.css',
        ],
        "web.assets_backend": [
            "army_results_manager/static/src/components/**/*.scss",
            "army_results_manager/static/lib/chart/chart.umd.min.js",
            "army_results_manager/static/src/components/**/*.js",
            "army_results_manager/static/src/components/**/*.xml",
            "army_results_manager/static/src/xml/*.xml",
            "army_results_manager/static/src/js/*.js",
            "army_results_manager/static/src/css/*.css",
        ],
    },

}
