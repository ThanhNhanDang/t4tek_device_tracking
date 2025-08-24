from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class StockReceipt(models.Model):
    _name = 'stock.receipt'
    _description = 'Phiếu Ghi Nhận'
    _order = 'create_date desc'

    name = fields.Char(
        string='Số Phiếu',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )
    
    create_date = fields.Datetime(
        string='Ngày Nhập', default=fields.Datetime.now, readonly=True, copy=False
    )
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã Xác Nhận'),
        ('done', 'Hoàn Thành'),
        ('cancelled', 'Đã Hủy')
    ], string='Trạng Thái', default='draft')
    
    product_id = fields.Many2one(
        'product.template',
        string='Sản Phẩm',
        required=True,
        domain="[('type', 'in', ['product', 'consu'])]"
    )
    
    quantity = fields.Integer(
        string='Số Lượng',
        required=True,
        default=1
    )
    
    card_count = fields.Integer(
        string='Số Thẻ Cấp',
        compute='_compute_card_count',
        store=True,
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        readonly=True
    )
    
    location_id = fields.Many2one(
        'stock.location',
        string='Kho Đích',
        domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]"
    )
    
    card_ids = fields.One2many(
        'stock.receipt.card',
        'receipt_id',
        string='Danh Sách Thẻ',
        readonly=True,
    )
    
    picking_id = fields.Many2one(
        'stock.picking',
        string='Phiếu Kho',
        readonly=True,
    )
    
    @api.model
    def _create_sequence_if_not_exists(self):
        """Tạo sequence nếu chưa tồn tại"""
        sequence = self.env['ir.sequence'].search(
            [('code', '=', 'stock.receipt')], limit=1)
        if not sequence:
            sequence = self.env['ir.sequence'].create({
                'name': 'Stock Receipt Sequence',
                'code': 'stock.receipt',
                'prefix': 'STCK/',
                'padding': 4,
                'number_increment': 1,
                'number_next': 1,
                'active': True,
            })
        return sequence
    
    @api.depends('quantity')
    def _compute_card_count(self):
        for record in self:
            record.card_count = record.quantity

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            self._create_sequence_if_not_exists()
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.receipt') or 'New'
        return super().create(vals)

    def action_confirm(self):
        """Xác nhận phiếu nhập"""
        if not self.product_id or not self.quantity:
            raise ValidationError("Phiếu nhập phải có sản phẩm và số lượng!")
        
        # Create stock.picking
        picking = self._create_stock_picking()
        self.picking_id = picking.id
        
        # Generate cards
        
        self.state = 'confirmed'
        return self.action_receipt()
        # self._process_stock_picking()
    def action_receipt(self):
        """Xử lý phiếu nhập kho"""
        if not self.picking_id:
            raise ValidationError("Phiếu kho không được để trống!")
        
        # Generate RFID cards
        return {
            'type': 'ir.actions.act_window',
            'name': 'Phiếu nhận hàng',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'context': {'is_oper': True},   
            'res_id': self.picking_id.id,
        }
    def action_generate_cards(self):
        if self.env.context.get('uuid_client', False):
            self.env['bus.bus'].sudo()._sendone(
                self.env.context.get('uuid_client', False),
                'notification',
                {
                    "type":"generate_cards",
                    "id":self.id,
                    "model": self._name,
                    'quantity': self.quantity,
                    'receipt_name': self.name,
                }
            )
    
    def callback_generate_cards(self, tags):
        """Callback for generating RFID cards"""
        if not tags or len(tags) != self.quantity:
            return f"Số lượng thẻ cấp không khớp với số lượng yêu cầu!, {len(tags)}/{self.quantity}" 
        for tag in tags:
            exitRecord = self.env['stock.receipt.card'].search([
                ('name', '=', tag['Tid']),
            ], limit=1)
            if exitRecord:
                return f"Thẻ {tag['Tid']} đã tồn tại!"
        
        # Get product variant
        product_variant = self.product_id.product_variant_ids[0] if self.product_id.product_variant_ids else False
        if not product_variant:
            return f"Không tìm thấy biến thể sản phẩm cho {self.product_id.name}"
        card_records = []
        move_lines = []
        lots_ids = []
        for tag in tags:
            # Tạo thẻ RFID
            # Tạo stock.quant cho từng thẻ RFID
            lot_id = self._create_stock_quant_and_return_lot_id(product_variant, tag['Tid'])
            card_vals = {
                'name': tag['Tid'],
                'receipt_id': self.id,
                'lot_id' : lot_id,
                'location_id': self.location_id.id,
            }
            card_records.append((0, 0, card_vals))
            lots_ids.append((4, lot_id))  # Thêm lot_id vào danh sách lots_ids
            
           
        move_vals = {
                'name': f'{self.name} - {self.product_id.name} - {tag["Tid"]}',
                'product_id': product_variant.id,
                'product_uom_qty': self.quantity,
                'product_uom': product_variant.uom_id.id,
                'location_id': self.env.ref('stock.stock_location_suppliers').id,
                'location_dest_id': self.location_id.id,
                'company_id': self.company_id.id,
                'picking_id': self.picking_id.id,
                'lot_ids': lots_ids
            }
        move_lines.append((0, 0, move_vals))
        # Cập nhật card_ids và move_ids_without_package
        self.card_ids = card_records
        self.picking_id.move_ids_without_package = move_lines

        # Process stock picking after generating cards
        self._process_stock_picking()
        return "1"
    
    def _create_stock_quant_and_return_lot_id(self, product_variant, rfid_tag):
        """Tạo stock.quant cho từng thẻ RFID"""
        try:
            # Tạo lot/serial number cho RFID tag
            lot_vals = {
                'name': rfid_tag,
                'product_id': product_variant.id,
                'company_id': self.company_id.id,
            }
            lot = self.env['stock.lot'].create(lot_vals)
            
            # # Tạo stock.quant mới
            # quant_vals = {
            #     'product_id': product_variant.id,
            #     'location_id': self.location_id.id,
            #     'quantity': 1,  # Mỗi thẻ RFID = 1 sản phẩm
            #     'lot_id': lot.id,
            #     'company_id': self.company_id.id,
            # }
            # quant = self.env['stock.quant'].create(quant_vals)
            # _logger.info(f"Created new quant for RFID {rfid_tag}: {quant.id}")
            return lot.id
                
        except Exception as e:
            _logger.error(f"Error creating stock.quant for RFID {rfid_tag}: {str(e)}")
            raise ValidationError(f"Lỗi tạo stock.quant cho thẻ {rfid_tag}: {str(e)}")
    
    def _create_stock_picking(self):
        """Tạo phiếu kho (stock.picking)"""
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id.company_id', '=', self.company_id.id),
        ], limit=1)
        if not picking_type:
            raise ValidationError("Không tìm thấy loại phiếu kho nhập phù hợp!")
        
        # product_variant = self.product_id.product_variant_ids[0] if self.product_id.product_variant_ids else False
        # if not product_variant:
        #     raise ValidationError(f"Không tìm thấy biến thể sản phẩm cho {self.product_id.name}")
        self.location_id = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('company_id', '=', self.company_id.id)
        ], limit=1) 
        if not self.location_id:
            raise ValidationError("Không tìm thấy kho đích phù hợp!")
        picking_vals = {
            'is_device_tracking':True,  # Đánh dấu là phiếu xuất kho thiết bị
            'name': self.env['ir.sequence'].next_by_code('stock.picking') or '/',
            'picking_type_id': picking_type.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.location_id.id,
            'origin': self.name,
            'stock_receipt_id': self.id,
            'partner_id': self.env.user.partner_id.id,
            'company_id': self.company_id.id,
            'state': 'draft',
            # 'move_ids_without_package': [(0, 0, {
            #     'name': f'{self.name} - {self.product_id.name}',
            #     'product_id': product_variant.id,
            #     'product_uom_qty': self.quantity,
            #     'product_uom': product_variant.uom_id.id,
            #     'location_id': self.env.ref('stock.stock_location_suppliers').id,
            #     'location_dest_id': self.location_id.id,
            #     'company_id': self.company_id.id,
            # })],
        }
        
        return self.env['stock.picking'].create(picking_vals)

    def _process_stock_picking(self):
        """Xử lý phiếu kho: xác nhận và hoàn thành"""
        if self.picking_id:
            self.picking_id.action_confirm()
            self.picking_id.action_assign()
            # self.picking_id.button_validate()
            self.state = 'done'
    
    def action_cancel(self):
        """Hủy phiếu nhập"""
        self.state = 'cancelled'
    
    def action_draft(self):
        """Đưa về trạng thái nháp"""
        self.state = 'draft'