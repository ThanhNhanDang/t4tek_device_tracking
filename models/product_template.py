import logging

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    product_type_id = fields.Many2one('product.type', string='Loại sản phẩm')