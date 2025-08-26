
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)
class StockReceiptCard(models.Model):
    _name = 'stock.receipt.card'
    _description = 'Thẻ Cấp'

    name = fields.Char(
        string='Mã Thẻ',
        required=True,
        readonly=True,
        help="Mã định danh duy nhất của thẻ RFID"
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial Number',
        help="Lot/Serial number liên kết với RFID tag"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        readonly=True
    )
    receipt_id = fields.Many2one(
        'stock.receipt',
        string='Phiếu Nhập',
        required=True,
        ondelete='cascade'
    )
    quantity = fields.Integer(string='Số Lượng', default=1)  # Thêm trường quantity
    picking_id = fields.Many2one(  
        'stock.picking',
        string='Phiếu Kho',
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Kho Đích',
        required=True,
        domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]",
        related='receipt_id.location_id',
    )
    is_used = fields.Boolean(
        string='Đã Sử Dụng',
        default=False,
        help="Chỉ ra thẻ đã được sử dụng trong một phiếu kho hay chưa"
    )
    
    status = fields.Selection(
        [('input', 'Nhập Kho'), ('output', 'Xuất Kho')],    
        string='Trạng Thái',
        default='input',
        help="Trạng thái của thẻ, có thể là 'Nhập Kho' hoặc 'Xuất Kho'"
    )
    state = fields.Selection(
        [('in', 'Đã Vào'), ('out', 'Đã Ra')],
        default='in',
    )
    create_date = fields.Datetime(
        string='Ngày Nhập', default=fields.Datetime.now, readonly=True, copy=False
    )
    
    product_id = fields.Many2one(
        'product.template',
        string='Sản Phẩm',
        readonly=True,
        related='receipt_id.product_id',
    )
    
  
    def action_export_cards(self):
        """Open popup to scan RFID tags for stock issuance from selected cards"""
        if not self:
            raise UserError("Vui lòng chọn ít nhất một sản phẩm để xuất kho!")
         # Create stock.picking
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not picking_type:
            raise UserError("Không tìm thấy loại phiếu xuất kho!")
        product_quantities = {}
        for card in self:
            if card.status == 'output':
                raise UserError(f"Sản phẩm {card.name} đã được xuất kho!")
            product = self.env['product.product'].search([('product_tmpl_id', '=', card.product_id.id)], limit=1)
            if not product:
                raise UserError(f"Không tìm thấy biến thể sản phẩm cho {card.product_id.name}!")
            if product.id not in product_quantities:
                product_quantities[product.id] = {
                    'quantity': 0,
                }
            product_quantities[product.id]['quantity'] += card.quantity

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.mapped('location_id')[0].id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'state': 'draft',
            'is_device_tracking':True,  # Đánh dấu là phiếu xuất kho thiết bị
        })

        # Create stock.move
        for product_id, data in product_quantities.items():
            self.env['stock.move'].create({
                'picking_id': picking.id,
                'product_id': product_id,
                'product_uom_qty': data['quantity'],
                'product_uom': self.env['product.product'].browse(product_id).uom_id.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'name': f"Xuất kho: {self.env['product.product'].browse(product_id).name}"
            })
            
        """Xử lý phiếu kho: xác nhận"""
        picking.action_confirm()
        picking.action_assign()
        picking.button_validate()
        self.write({
            'status': 'output',
            'picking_id': picking.id,
            'location_id': picking_type.default_location_dest_id.id
        })
        
    def action_export_cards_v3(self, picking=None):
        """Open popup to scan RFID tags for stock issuance from selected cards"""
        if not self:
            raise UserError("Vui lòng chọn ít nhất một sản phẩm để xuất kho!")
        
        # product_quantities = {}
        product_quantities = []
        
        for card in self:
            # Kiểm tra trạng thái card
            if card.status == 'output':
                return f"Sản phẩm {card.name} đã được xuất kho!"
                
            # Tìm product variant
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', card.product_id.id)
            ], limit=1)
            
            if not product:
                return f"Không tìm thấy biến thể sản phẩm cho {card.product_id.name}!"
            # Tìm stock lot tương ứng
            lot = self.env['stock.lot'].search([
                ('name', '=', card.name),
            ], limit=1)
                
            product_quantities.append({'product_id': product.id, 'product_name':product.name, 'product_uom': product.uom_id.id, 'lot_id': lot.id if lot else None})

        
        # Kiểm tra picking có tồn tại
        if not picking:
            raise UserError("Không tìm thấy phiếu kho để xuất!")
        
        # Tạo stock.move cho từng sản phẩm
        try:
            move_vals_list = []
            for product in product_quantities:
                move_vals = {
                    'picking_id': picking.id,
                    'product_id': product.get('product_id'),
                    'product_uom_qty': 1,
                    'product_uom': product.get('product_uom'),
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'name': product.get('product_name'),
                    'lot_id': product.get('lot_id'),  # Gán lot_id nếu có
                    'lot_ids':[product.get('lot_id')]
                }
                
                move_vals_list.append((0, 0, move_vals))

            
            # Tạo tất cả stock.move cùng lúc
            picking.move_ids_without_package  =  [(5, 0, 0)]  # Xóa tất cả dòng hiện có trước khi thêm mới
            picking.move_ids_without_package = move_vals_list
            # Xử lý phiếu kho: xác nhận và phân bổ
            if picking.state == 'draft':
                picking.action_confirm()
            
            if picking.state == 'confirmed':
                picking.action_assign()
            
            # Cập nhật trạng thái cards
            self.write({
                'picking_id': picking.id,
                'location_id': picking.location_dest_id.id,
            })
            return "1"
            
        except Exception as e:
            raise UserError(f"Lỗi khi tạo stock move: {str(e)}")
    
    def action_import_cards_v3(self, picking=None):
        """Open popup to scan RFID tags for stock issuance from selected cards"""
        """Open popup to scan RFID tags for stock issuance from selected cards"""
        if not self:
            raise UserError("Vui lòng chọn ít nhất một sản phẩm để nhập kho!")
        
        # product_quantities = {}
        product_quantities = []
        
        for card in self:
            # Kiểm tra trạng thái card
            if card.status == 'input':
                return f"Sản phẩm {card.name} đã được nhập kho!"
                
            # Tìm product variant
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', card.product_id.id)
            ], limit=1)
            
            if not product:
                return f"Không tìm thấy biến thể sản phẩm cho {card.product_id.name}!"
            # Tìm stock lot tương ứng
            lot = self.env['stock.lot'].search([
                ('name', '=', card.name),
            ], limit=1)
                
            product_quantities.append({'product_id': product.id, 'product_name':product.name, 'product_uom': product.uom_id.id, 'lot_id': lot.id if lot else None})
        
        # Kiểm tra picking có tồn tại
        if not picking:
            raise UserError("Không tìm thấy phiếu kho để nhập!")

        # Tạo stock.move cho từng sản phẩm
        try:
            move_vals_list = []
            for product in product_quantities:
                _logger.info(product)
                
                move_vals = {
                    'picking_id': picking.id,
                    'product_id': product.get('product_id'),
                    'product_uom_qty': 1,
                    'product_uom': product.get('product_uom'),
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'name': product.get('product_name'),
                    'lot_id': product.get('lot_id'),  # Gán lot_id nếu có
                    'lot_ids':[product.get('lot_id')]
            
                }
                move_vals_list.append((0, 0, move_vals))

            # Tạo tất cả stock.move cùng lúc
            picking.move_ids_without_package  =  [(5, 0, 0)]  # Xóa tất cả dòng hiện có trước khi thêm mới
            picking.move_ids_without_package = move_vals_list
            # Xử lý phiếu kho: xác nhận và phân bổ
            
            # Xử lý phiếu kho: xác nhận và phân bổ
            if picking.state == 'draft':
                picking.action_confirm()
            
            if picking.state == 'confirmed':
                picking.action_assign()
            
            # Cập nhật trạng thái cards
            self.write({
            'picking_id': picking.id,
            'location_id': picking.location_dest_id.id
        })
            return "1"
            
            
        except Exception as e:
            raise UserError(f"Lỗi khi tạo stock move: {str(e)}")
    
    def action_export_cards_v2(self, picking=None, lot_ids=None):
        """Open popup to scan RFID tags for stock issuance from selected cards"""
        if not self:
            raise UserError("Vui lòng chọn ít nhất một sản phẩm để xuất kho!")
        
        product_quantities = {}
        
        for card in self:
            # Kiểm tra trạng thái card
            if card.status == 'output':
                return f"Sản phẩm {card.name} đã được xuất kho!"
                
            # Tìm product variant
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', card.product_id.id)
            ], limit=1)
            
            if not product:
                return f"Không tìm thấy biến thể sản phẩm cho {card.product_id.name}!"
                
            # Tích lũy số lượng theo sản phẩm
            if product.id not in product_quantities:
                product_quantities[product.id] = {
                    'quantity': 0,
                    'product': product,
                }
            product_quantities[product.id]['quantity'] += card.quantity

        
        # Kiểm tra picking có tồn tại
        if not picking:
            raise UserError("Không tìm thấy phiếu kho để xuất!")
        
        # Tạo stock.move cho từng sản phẩm
        try:
            move_vals_list = []
            for product_id, data in product_quantities.items():
                move_vals = {
                    'picking_id': picking.id,
                    'product_id': product_id,
                    'product_uom_qty': data['quantity'],
                    'product_uom': data['product'].uom_id.id,
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'name': data['product'].name,
                }
                
                # Thêm lot_ids nếu có và không rỗng
                if lot_ids:
                    # Lọc bỏ các lot_id None hoặc False
                    valid_lot_ids = [lot_id for lot_id in lot_ids if lot_id]
                    if valid_lot_ids:
                        move_vals['lot_ids'] = [(6, 0, valid_lot_ids)]
                
                move_vals_list.append(move_vals)
            
            # Tạo tất cả stock.move cùng lúc
            moves = self.env['stock.move'].create(move_vals_list)
            
            # Xử lý phiếu kho: xác nhận và phân bổ
            if picking.state == 'draft':
                picking.action_confirm()
            
            if picking.state == 'confirmed':
                picking.action_assign()
            
            # Cập nhật trạng thái cards
            self.write({
                'status': 'output',
                'picking_id': picking.id,
                'location_id': picking.location_dest_id.id,
            })
            
            
        except Exception as e:
            raise UserError(f"Lỗi khi tạo stock move: {str(e)}")
        
        
    def action_import_cards_v2(self, picking=None, lot_ids=None):
        """Open popup to scan RFID tags for stock issuance from selected cards"""
        if not self:
            raise UserError("Vui lòng chọn ít nhất một sản phẩm để xuất kho!")
        
        product_quantities = {}
        
        for card in self:
            # Kiểm tra trạng thái card
            if card.status == 'input':
                return f"Sản phẩm {card.name} đã được nhập kho!"
                
            # Tìm product variant
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', card.product_id.id)
            ], limit=1)
            
            if not product:
                return f"Không tìm thấy biến thể sản phẩm cho {card.product_id.name}!"
                
            # Tích lũy số lượng theo sản phẩm
            if product.id not in product_quantities:
                product_quantities[product.id] = {
                    'quantity': 0,
                    'product': product,
                }
            product_quantities[product.id]['quantity'] += card.quantity

        
        # Kiểm tra picking có tồn tại
        if not picking:
            raise UserError("Không tìm thấy phiếu kho để xuất!")
        
        # Tạo stock.move cho từng sản phẩm
        try:
            move_vals_list = []
            for product_id, data in product_quantities.items():
                move_vals = {
                    'picking_id': picking.id,
                    'product_id': product_id,
                    'product_uom_qty': data['quantity'],
                    'product_uom': data['product'].uom_id.id,
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'name': data['product'].name,
                }
                
                # Thêm lot_ids nếu có và không rỗng
                if lot_ids:
                    # Lọc bỏ các lot_id None hoặc False
                    valid_lot_ids = [lot_id for lot_id in lot_ids if lot_id]
                    if valid_lot_ids:
                        move_vals['lot_ids'] = [(6, 0, valid_lot_ids)]
                
                move_vals_list.append(move_vals)
            
            # Tạo tất cả stock.move cùng lúc
            moves = self.env['stock.move'].create(move_vals_list)
            
            # Xử lý phiếu kho: xác nhận và phân bổ
            if picking.state == 'draft':
                picking.action_confirm()
            
            if picking.state == 'confirmed':
                picking.action_assign()
            
            # Cập nhật trạng thái cards
            self.write({
            'status': 'input',
            'picking_id': picking.id,
            'location_id': picking.location_dest_id.id
        })
            
            
        except Exception as e:
            raise UserError(f"Lỗi khi tạo stock move: {str(e)}")
    
        
    def action_import_cards(self):
        """Xử lý nhập kho từ các thẻ liên quan đến phiếu nhập"""
        product_quantities = {}
        location_id = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('company_id', '=', self.company_id.id)
        ], limit=1) 
        if not location_id:
            raise ValidationError("Không tìm thấy kho đích phù hợp!")
        for card in self:
            _logger.info(f"Processing card: {card.name}, Status: {card.status}, Quantity: {card.quantity}")
            # Tổng hợp số lượng theo product_id từ card_ids
            if card.status == 'input':
                raise UserError(f"Sản phẩm {card.name} đã được nhập kho!")
            product = self.env['product.product'].search([('product_tmpl_id', '=', card.product_id.id)], limit=1)
            if not product:
                raise UserError(f"Không tìm thấy biến thể sản phẩm cho {card.product_id.name}!")
            if product.id not in product_quantities:
                product_quantities[product.id] = {
                    'quantity': 0,
                }
            product_quantities[product.id]['quantity'] += card.quantity
           
        
        # Tạo stock.picking cho nhập kho
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not picking_type:
            raise UserError("Không tìm thấy loại phiếu nhập kho!")
       
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': picking_type.default_location_src_id.id,  # Nguồn: thường là supplier
            'location_dest_id': location_id.id,  # Đích: kho nội bộ
            'state': 'draft',
            'is_device_tracking':True,  # Đánh dấu là phiếu xuất kho thiết bị
        })
        
        # Tạo stock.move cho từng sản phẩm
        for product_id, data in product_quantities.items():
            self.env['stock.move'].create({
                'picking_id': picking.id,
                'product_id': product_id,
                'product_uom_qty': data['quantity'],
                'product_uom': self.env['product.product'].browse(product_id).uom_id.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'name': f"Nhập kho: {self.env['product.product'].browse(product_id).name}"
            })
        # Xác nhận phiếu kho
        picking.action_confirm()
        picking.action_assign()
        picking.button_validate()
        # Cập nhật trạng thái và picking_id cho các thẻ
        self.write({
            'status': 'input',
            'picking_id': picking.id,
            'location_id': location_id.id
        })
        
    def action_inventory_history(self):
        return {'type': 'ir.actions.act_window',
                'res_model': 'stock.move.line',
                'view_mode': 'list,form',
                'views': [(False,'list'),(False,'form')],
                'domain': [('lot_id', '=', self.lot_id.id if self.lot_id else -1)],}