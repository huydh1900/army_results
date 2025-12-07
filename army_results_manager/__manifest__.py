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

    'version': '0.1',

    'depends': ['auth_signup', 'web', 'base', 'hr', 'web_unsplash', 'web_widget_video'],
    # always loaded
    'data': [
        "security/training_result_security.xml",
        "security/training_day_security.xml",
        "security/training_plan_security.xml",
        "security/training_mission_security.xml",
        "security/training_day_comment_security.xml",
        "security/training_course_security.xml",
        "security/ir.model.access.csv",
        'views/remove_odoo_title.xml',
        'data/training_category_data.xml',
        'data/training_subject_data.xml',
        'wizard/print_word_wizard.xml',
        'wizard/approved_wizard.xml',
        'wizard/preview_report_pdf_wizard.xml',
        'views/ir_attachment_views.xml',
        'views/webclient_templates.xml',
        'views/support_contact_views.xml',
        'views/training_location_views.xml',
        'views/camera_video_views.xml',
        'views/training_day_comment_views.xml',
        'views/res_users_views.xml',
        'views/training_day_views.xml',
        'views/auth_totp_templates.xml',
        'views/res_config_settings.xml',
        'views/hr_department_views.xml',
        'views/ir_cron.xml',
        'views/training_mission_views.xml',
        'views/training_result_views.xml',
        'views/hr_employee_views.xml',
        'wizard/modify_reason_wizard.xml',
        'views/training_plan_views.xml',
        'views/training_course_views.xml',
        'views/training_subject_views.xml',
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
            "army_results_manager/static/lib/chart/chart.umd.min.js",
            "army_results_manager/static/lib/vgcaplugin/vgcaplugin.js",
            "army_results_manager/static/src/components/**/*.xml",
            "army_results_manager/static/src/components/**/*.js",
            "army_results_manager/static/src/xml/*.xml",
            "army_results_manager/static/src/js/*.js",
            "army_results_manager/static/src/css/*.css",
        ],
    },

}
