# -*- coding: utf-8 -*-
# from odoo import http


# class ArmyResultsManager(http.Controller):
#     @http.route('/army_results_manager/army_results_manager', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/army_results_manager/army_results_manager/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('army_results_manager.listing', {
#             'root': '/army_results_manager/army_results_manager',
#             'objects': http.request.env['army_results_manager.army_results_manager'].search([]),
#         })

#     @http.route('/army_results_manager/army_results_manager/objects/<model("army_results_manager.army_results_manager"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('army_results_manager.object', {
#             'object': obj
#         })
