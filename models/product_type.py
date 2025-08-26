from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class ProductType(models.Model):
    _name = 'product.type'
    _description = 'Loại sản phẩm'
    _order = 'name asc'
    name = fields.Char(string='Tên loại sản phẩm', required=True)
    description = fields.Text(string='Mô tả')