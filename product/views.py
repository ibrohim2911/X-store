from django.shortcuts import render
from rest_framework import viewsets
from .models import Products, Variant, Size, SizeScale
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, filters
from django.db import transaction
import time
import random
from .serializers import ProductSerializer, VariantSerializer, SizeSerializer, SizeScaleSerializer
from rest_framework.permissions import IsAuthenticated
from common.permissions import IsRoleAuthorized

from rest_framework.pagination import PageNumberPagination

class LargeResultsSetPagination(PageNumberPagination):
    page_size = 500
    page_size_query_param = 'page_size'
    max_page_size = 1000

class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsRoleAuthorized]
    queryset = Products.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(barcode=search) | Q(name__icontains=search)
            ).distinct()
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        if not instance.barcode:
            instance.barcode = str(instance.id)
            instance.save()

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def createwithvariants(self, request, pk=None):
        name = request.data.get('name')
        img = request.data.get('img')
        barcode = request.data.get('barcode')
        variants_data = request.data.get('variants', [])
        
        if isinstance(variants_data, str):
            import json
            try:
                variants_data = json.loads(variants_data)
            except ValueError as e:
                from django.db import transaction
                transaction.set_rollback(True)
                return Response({"error": f"Invalid JSON in variants: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
                
        product = Products.objects.create(name=name, img=img, barcode=barcode)
        
        # If barcode is empty, auto-acquire the generated ID
        if not product.barcode:
            product.barcode = str(product.id)
            product.save()
            
        for variant_data in variants_data:
            size_id = variant_data.get('size')
            size_obj = None
            
            # Safely get Size, it could be an ID (UUID) or a Name string
            import uuid
            try:
                uuid.UUID(str(size_id))
                size_obj = Size.objects.filter(id=size_id).first()
            except ValueError:
                pass
            
            # If not found by ID, try by name
            if not size_obj:
                size_obj = Size.objects.filter(name=size_id).first()
                
            if not size_obj:
                from django.db import transaction
                transaction.set_rollback(True)
                return Response({"error": f"Size not found for size identifier: {size_id}"}, status=status.HTTP_400_BAD_REQUEST)

            sticker_price = variant_data.get('sticker_price', 0)
            
            # Use frontend's SKU or generate a safe unique SKU
            sku = variant_data.get('sku')
            if not sku:
                rnd = random.randint(1000, 9999)
                sku = f"{product.name[:3]}-{size_obj.name[:3]}-{rnd}".upper().replace(" ", "")
                
            # Ensure uniqueness
            while Variant.objects.filter(sku=sku).exists():
                sku = f"{sku}-{random.randint(10, 99)}"

            variant = Variant.objects.create(
                product=product,
                sku=sku,
                size_scale_id=variant_data.get('size_scale'),
                cost_price=variant_data.get('cost_price', 0),
                sticker_price=sticker_price,
                quantity=variant_data.get('quantity', 0)
            )
            if size_obj:
                variant.size.set([size_obj.id])
            
        serializer = self.get_serializer(product)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def print_barcode(self, request):
        try:
            name = str(request.data.get('name') or 'X-STORE')
            price = str(request.data.get('price') or '0')
            barcode_val = str(request.data.get('barcode') or '')
            
            try:
                price_int = int(float(price))
                price_str = f"{price_int:,}".replace(',', ' ') + " UZS"
            except:
                price_str = f"{price} UZS"
                
            if not barcode_val or len(barcode_val.strip()) == 0:
                barcode_val = "000000000000"

            copies = int(request.data.get('copies', 1))

            from common.models import PrinterSetting
            settings = PrinterSetting.load()
            printer_name = settings.printer_name or 'Xprinter XP-365B'
            layout = settings.layout_config or {}

            import win32print
            import win32ui
            import win32con
            from PIL import Image, ImageDraw, ImageFont, ImageWin
            import barcode

            # Generate Barcode binary string manually
            code128 = barcode.get_barcode_class('code128')
            bc = code128(barcode_val)
            binary_string = "".join(bc.build())

            hDC = win32ui.CreateDC()
            hDC.CreatePrinterDC(printer_name)
            
            # DPI adjustment based on settings
            dpi = settings.dpi or 203
            width = int((settings.paper_width_mm / 25.4) * dpi)
            height = int((settings.paper_height_mm / 25.4) * dpi)
            
            if width <= 0 or height <= 0:
                width, height = 320, 240

            img = Image.new('RGB', (width, height), color=(255, 255, 255))
            d = ImageDraw.Draw(img)

            def get_font(size_pct):
                try:
                    return ImageFont.truetype("arial.ttf", int(height * (size_pct / 100.0)))
                except:
                    return ImageFont.load_default()

            # Product Name
            cfg = layout.get('product_name', {})
            if cfg.get('visible', True):
                x = int(width * (cfg.get('x', 50) / 100.0))
                y = int(height * (cfg.get('y', 15) / 100.0))
                font = get_font(cfg.get('fontSize', 14))
                
                display_name = name
                if len(display_name) > 30:
                    display_name = display_name[:27] + "..."
                if len(display_name) > 15:
                    split_idx = display_name.rfind(' ', 0, 16)
                    if split_idx <= 0: split_idx = 15
                    d.text((x, y - (height*0.06)), display_name[:split_idx].strip(), fill=(0,0,0), font=font, anchor="mm")
                    d.text((x, y + (height*0.06)), display_name[split_idx:].strip(), fill=(0,0,0), font=font, anchor="mm")
                else:
                    d.text((x, y), display_name, fill=(0,0,0), font=font, anchor="mm")

            # Barcode
            cfg = layout.get('barcode', {})
            if cfg.get('visible', True):
                x = int(width * (cfg.get('x', 50) / 100.0))
                y = int(height * (cfg.get('y', 50) / 100.0))
                bw_pct = cfg.get('width', 80) / 100.0
                bh_pct = cfg.get('height', 30) / 100.0
                
                target_w = int(width * bw_pct)
                target_h = int(height * bh_pct)
                
                module_width_px = max(1, int(target_w / len(binary_string)))
                module_width_px = min(module_width_px, 3) 
                barcode_w = len(binary_string) * module_width_px
                
                paste_x = x - (barcode_w // 2)
                paste_y = y - (target_h // 2)
                
                for i, bit in enumerate(binary_string):
                    if bit == '1':
                        x0 = paste_x + i * module_width_px
                        y0 = paste_y
                        x1 = x0 + module_width_px - 1
                        y1 = paste_y + target_h
                        d.rectangle([x0, y0, x1, y1], fill=(0,0,0))
                
                # Barcode Text
                font_bc = get_font(cfg.get('fontSize', 10))
                d.text((x, paste_y + target_h + int(height * 0.05)), barcode_val, fill=(0,0,0), font=font_bc, anchor="mm")

            # Price
            cfg = layout.get('price', {})
            if cfg.get('visible', True):
                x = int(width * (cfg.get('x', 50) / 100.0))
                y = int(height * (cfg.get('y', 85) / 100.0))
                font = get_font(cfg.get('fontSize', 16))
                d.text((x, y), price_str, fill=(0,0,0), font=font, anchor="mm")

            hDC.StartDoc("Barcode Print")
            dib = ImageWin.Dib(img)
            
            # Ensure it fits within the printer's configured page size
            horz_res = hDC.GetDeviceCaps(win32con.HORZRES)
            vert_res = hDC.GetDeviceCaps(win32con.VERTRES)
            
            scale_w = horz_res / width if horz_res < width else 1.0
            scale_h = vert_res / height if vert_res < height else 1.0
            scale = min(scale_w, scale_h)
            
            dest_w = int(width * scale)
            dest_h = int(height * scale)
            
            for _ in range(copies):
                hDC.StartPage()
                dib.draw(hDC.GetHandleOutput(), (0, 0, dest_w, dest_h))
                hDC.EndPage()
            hDC.EndDoc()
            hDC.DeleteDC()

            return Response({'status': 'success'}, status=200)
        except Exception as e:
            import traceback
            return Response({'error': str(e), 'traceback': traceback.format_exc()}, status=500)
class VariantViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsRoleAuthorized]
    queryset = Variant.objects.all().order_by('-id')
    serializer_class = VariantSerializer
    pagination_class = LargeResultsSetPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(product__barcode=search) | 
                Q(sku=search) | 
                Q(product__name__icontains=search) | 
                Q(size__name__icontains=search)
            ).distinct()
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class SizeScaleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsRoleAuthorized]
    queryset = SizeScale.objects.all()
    serializer_class = SizeScaleSerializer
    pagination_class = None
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class SizeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsRoleAuthorized]
    queryset = Size.objects.all()
    serializer_class = SizeSerializer
    pagination_class = None
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)