from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class T4tekStockPickingType(models.Model):
    _name = 't4tek.stock.picking.type'
    _description = 'Loại phiếu'
    _order = 'create_date desc'
    
    stock_picking_type_id = fields.Many2one('stock.picking.type', string='Loại phiếu kho')
    name = fields.Char(string='Tên', required=True)