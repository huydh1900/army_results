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

    'depends': ['base', 'hr'],

    # always loaded
    'data': [
        "security/ir.model.access.csv",
        "security/training_result_security.xml",
        'data/training_category_data.xml',
        'wizard/print_word_wizard.xml',
        'views/hr_department_views.xml',
        'views/training_mission.xml',
        'views/training_mission_result.xml',
        'views/training_content_template.xml',
        'views/training_lesson.xml',
        'views/training_section_view.xml',
        'views/hr_employee_views.xml',
        'wizard/modify_reason_wizard.xml',
        'views/training_phase_views.xml',
        'views/training_plan.xml',
        'views/ir_attachment_view.xml',
        'views/training_course_view.xml',
        'views/training_subject.xml',
        'views/menu_view.xml',
    ],

    "assets": {
        "web.assets_backend": [
            "army_results_manager/static/src/components/**/*.js",
            "army_results_manager/static/src/components/**/*.xml",
            "army_results_manager/static/src/components/**/*.css",
        ],
    },
}
