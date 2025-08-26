from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class StockCardForm(models.Model):
    _name = 'stock.card.form'
    _description = 'Phiếu cấp thẻ'
    _order = 'create_date desc'

    name = fields.Char(string='Tên phiếu',  store=True, default="Phiếu cấp thẻ")
    card_quantity = fields.Integer(string='Số lượng thẻ', required=True, default=1)
    product_type_id = fields.Many2one('product.type', string='Loại sản phẩm', required=True)
    card_line_ids = fields.One2many('stock.card.line', 'stock_card_id', string='Danh sách thẻ')
    is_loading = fields.Boolean("Loading", default=False)
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('done', 'Hoàn Thành'),
        ('cancelled', 'Đã Hủy')
    ], string='Trạng Thái', default='draft')
    
    def action_generate_cards(self):
        self.is_loading = True
        if self.env.context.get('uuid_client', False):
            self.env['bus.bus'].sudo()._sendone(
                self.env.context.get('uuid_client', False),
                self.env.context.get('uuid_client', False),
                {
                    "type":"generate_cards",
                    "id":self.id,
                    "model": self._name,
                    'quantity': self.card_quantity,
                    'receipt_name': self.name,
                    'no_open_popup': True,
                }
            )
    def action_cancer_scan(self):
        self.is_loading = False
        if self.env.context.get('uuid_client', False):
            self.env['bus.bus'].sudo()._sendone(
                self.env.context.get('uuid_client', False),
                self.env.context.get('uuid_client', False),
                {
                    "type":"cancel_scan",
                    'no_open_popup': True,
                }
            )
    def action_confirm(self):
        if not self.card_line_ids  or  len(self.card_line_ids) != self.card_quantity:
            raise UserWarning(f"Số lượng thẻ cấp không khớp với số lượng yêu cầu!, {len(self.card_line_ids)}/{self.card_quantity}")
        self.write({
            'is_loading':False,
            'state':'done',
        })
        self.card_line_ids.is_done = True
        self.env['stock.lot'].create([{ 
            'name': tag.card_code,
            'company_id': self.env.company.id,
        } for tag in self.card_line_ids])
    
    def callback_generate_cards(self, tags):
        # Xóa các thẻ cũ
        self.card_line_ids.unlink()
        # Tạo bản ghi stock.card.line cho mỗi thẻ
        self.env['stock.card.line'].create([
            {
                'stock_card_id': self.id,
                'card_code': tag['Tid'],
                'description': f'Thẻ {tag["Tid"]}'
            } for tag in tags
        ])
        return "1"
        
    