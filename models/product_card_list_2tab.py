
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)
class ProductCardList(models.Model):
    _name = 'product_card_list.2tab'
    _description = 'Danh sách sản phẩm'
    name =  fields.Char(default='Danh sách sản phẩm')
    custom_view_field = fields.Boolean(string="Custom View")

    