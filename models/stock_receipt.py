from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
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
        default='Phiếu Nhập Kho Lần Đầu'
    )
    
    create_date = fields.Datetime(
        string='Ngày Nhập', default=fields.Datetime.now, readonly=True, copy=False
    )
    
    state = fields.Selection([
        ('draft', 'Nháp'),
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
        copy=False,
    )
    
    picking_id = fields.Many2one(
        'stock.picking',
        string='Phiếu Kho',
        readonly=True,
    )
    
    def cleanup_old_receipts_cron(self):
        """
        Chạy định kỳ để dọn dẹp các phiếu cũ (sử dụng cron job)
        """
        from datetime import datetime, timedelta
        
        # Xóa các phiếu 'old' cũ hơn 2 giờ
        time_limit = datetime.now() - timedelta(hours=2)
        _logger.info("=========================Running cleanup_old_receipts_cron=========================")
        old_receipts = self.sudo().search([
            ('state', '!=', 'done'),
            ('create_date', '<', time_limit)
        ])
        
        if old_receipts:
            _logger.info(f"Cleaning up {len(old_receipts)} old receipts")
            old_receipts.unlink()
    
    
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
        
        # if vals.get('name', 'New') == 'New':
        #     self._create_sequence_if_not_exists()
        #     vals['name'] = self.env['ir.sequence'].next_by_code('stock.receipt') or 'New'
        return super().create(vals)

    def action_print(self):
        if self.picking_id:
            if self.picking_id.state not in ['assigned','done']:
                raise ValidationError("Chưa thể in lúc này!")
            else: 
                if self.quantity != len(self.card_ids):
                    raise ValidationError("Số lượng thẻ cấp không khớp với số lượng yêu cầu!")
                return self.picking_id.do_print_picking()
        else: 
            raise ValidationError("Chưa thể in lúc này!")
        return
    
    def action_confirm(self):
        """Xác nhận phiếu nhập"""
        if self.quantity != len(self.card_ids):
            raise ValidationError("Số lượng thẻ cấp không khớp với số lượng yêu cầu!")

        # Create stock.picking
        # picking = self._create_stock_picking()
        # self.picking_id = picking.id
        
        # Generate cards
        if self.picking_id:
            if self.picking_id.state not in ['assigned','done']:
                raise ValidationError("Chưa thể xác nhận lúc này!")
            else: 
                product_variant = self.product_id.product_variant_ids[0] if self.product_id.product_variant_ids else False
                count =0
                for card_id in self.card_ids:
                    if not card_id.lot_id:
                        lot_id = self._create_stock_quant_and_return_lot_id(product_variant, card_id.name)
                        card_id.lot_id = lot_id
                        self.picking_id.move_ids_without_package[count].write({
                            'lot_id': lot_id,
                            'lot_ids': [lot_id]
                        })
                        count += 1
                return self._process_stock_picking()
        else: 
            raise ValidationError("Chưa thể xác nhận lúc này!")
        # return self.action_receipt()
       
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
        _logger.info(self.env.context.get('uuid_client', False))
        if self.env.context.get('uuid_client', False):
            self.env['bus.bus'].sudo()._sendone(
                self.env.context.get('uuid_client', False),
                self.env.context.get('uuid_client', False),
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
                ('name', '=', tag['Tid']), ('is_used', '=', True)
            ], limit=1)
            if exitRecord:
                return f"Thẻ {tag['Tid']} đã tồn tại!"
        if  not self.picking_id:
            # Create stock.picking if not exists
            picking = self._create_stock_picking()
            self.picking_id = picking.id
        # Get product variant
        product_variant = self.product_id.product_variant_ids[0] if self.product_id.product_variant_ids else False
        if not product_variant:
            return f"Không tìm thấy biến thể sản phẩm cho {self.product_id.name}"
        card_records = []
        move_lines = []
        for tag in tags:
            # Tạo thẻ RFID
            # Tạo stock.quant cho từng thẻ RFID
            card_vals = {
                'name': tag['Tid'],
                'receipt_id': self.id,
                'location_id': self.location_id.id,
            }
            card_records.append((0, 0, card_vals))
            move_vals = {
                    'name': f'{self.name} - {self.product_id.name} - {tag["Tid"]}',
                    'product_id': product_variant.id,
                    'product_uom_qty': 1,
                    'product_uom': product_variant.uom_id.id,
                    'location_id': self.env.ref('stock.stock_location_suppliers').id,
                    'location_dest_id': self.location_id.id,
                    'company_id': self.company_id.id,
                    'picking_id': self.picking_id.id,
                }
            # _logger.info(f"Creating move line for RFID {tag['Tid']}: {move_vals}")
            move_lines.append((0, 0, move_vals))
        # Cập nhật card_ids và move_ids_without_package
        self.card_ids = [(5, 0, 0)]  # Xóa tất cả thẻ hiện có trước khi thêm mới
        self.card_ids = card_records
        self.picking_id.move_ids_without_package  =  [(5, 0, 0)]  # Xóa tất cả dòng hiện có trước khi thêm mới
        self.picking_id.move_ids_without_package = move_lines
        self.picking_id.action_confirm()
        self.picking_id.action_assign()
        # Process stock picking after generating cards
        return "1"
    
    def _create_stock_quant_and_return_lot_id(self, product_variant, rfid_tag):
        """Tạo stock.quant cho từng thẻ RFID"""
        try:
            # Tạo lot/serial number cho RFID tag
            lots = self.env['stock.lot'].search([('name', '=', rfid_tag), ('product_id','=',product_variant.id)], limit=1)
            move = self.env['stock.move'].search([('lot_id', '=', rfid_tag), ('product_id','=',product_variant.id)], limit=1)
            if move:
                move.unlink()
            if lots: 
                lots.unlink()
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
            return self.picking_id.button_validate()
    
    def action_cancel(self):
        """Hủy phiếu nhập"""
        self.state = 'cancelled'
    
    def action_draft(self):
        """Đưa về trạng thái nháp"""
        self.state = 'draft'