from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)
class StockCardLine(models.Model):
    _name = 'stock.card.line'
    _description = 'Chi tiết thẻ'
    _order = 'id asc'

    stock_card_id = fields.Many2one('stock.card.form', string='Phiếu cấp thẻ', required=True, ondelete='cascade')
    card_code = fields.Char(string='Mã thẻ', required=True)
    description = fields.Text(string='Mô tả')
    is_done = fields.Boolean(string='Đã Hoàn Thành')