from django.shortcuts import render
from rest_framework import viewsets
from .models import Products, Variant, Size, SizeScale
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, filters
from .serializers import ProductSerializer, VariantSerializer, SizeSerializer, SizeScaleSerializer
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Products.objects.all()
    serializer_class = ProductSerializer
    
    def perform_update(self, serializer):
        instance = serializer.save()
        if not instance.barcode:
            instance.barcode = str(instance.id)
            instance.save()

    @action(detail=False, methods=['post'])
    def createwithvariants(self, request, pk=None):
        name = request.data.get('name')
        img = request.data.get('img')
        barcode = request.data.get('barcode')
        variants_data = request.data.get('variants', [])
        
        if isinstance(variants_data, str):
            import json
            try:
                variants_data = json.loads(variants_data)
            except ValueError:
                variants_data = []
                
        product = Products.objects.create(name=name, img=img, barcode=barcode)
        
        # If barcode is empty, auto-acquire the generated ID
        if not product.barcode:
            product.barcode = str(product.id)
            product.save()
            
        for variant_data in variants_data:
            size_id = variant_data.get('size')
            size_obj = Size.objects.get(id=size_id)
            sticker_price = variant_data.get('sticker_price')
            
            # Generate custom SKU: {ProductName}-{SizeName}-{Price}
            sku = f"{product.name}-{size_obj.name}-{sticker_price}"

            variant = Variant.objects.create(
                product=product,
                sku=sku,
                size_scale_id=variant_data.get('size_scale'),
                cost_price=variant_data.get('cost_price'),
                sticker_price=sticker_price,
                quantity=variant_data.get('quantity')
            )
            if size_id:
                variant.size.set([size_id])
            
        serializer = self.get_serializer(product)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def print_barcode(self, request):
        try:
            name = str(request.data.get('name') or 'X-STORE')
            price = str(request.data.get('price') or '0')
            barcode_val = str(request.data.get('barcode') or '')
            price = int(float(price))  # Convert to integer for cleaner display
            # Prevent empty barcode crash
            if not barcode_val or len(barcode_val.strip()) == 0:
                barcode_val = "000000000000"

            copies = int(request.data.get('copies', 1))
            printer_name = str(request.data.get('printer_name', 'Xprinter XP-365B'))

            import win32print
            import win32ui
            from PIL import Image, ImageDraw, ImageFont, ImageWin
            import barcode

            # Generate Barcode class
            code128 = barcode.get_barcode_class('code128')
            bc = code128(barcode_val)

            # Create DC once
            hDC = win32ui.CreateDC()
            hDC.CreatePrinterDC(printer_name)
            
            printer_size = hDC.GetDeviceCaps(110), hDC.GetDeviceCaps(111) # HORZRES, VERTRES
            width, height = printer_size[0], printer_size[1]
            
            if width <= 0 or height <= 0:
                width, height = 320, 240
                
            # Dynamically load fonts based on paper height
            try:
                font_large = ImageFont.truetype("arial.ttf", int(height * 0.14))
                font_medium = ImageFont.truetype("arial.ttf", int(height * 0.10))
                font_small = ImageFont.truetype("arial.ttf", int(height * 0.08))
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()

            img = Image.new('RGB', (width, height), color=(255, 255, 255))
            d = ImageDraw.Draw(img)

            # Texts (Product name at top)
            display_name = name
            if len(display_name) > 30:
                display_name = display_name[:27] + "..."
            
            if len(display_name) > 15:
                split_idx = display_name.rfind(' ', 0, 16)
                if split_idx <= 0:
                    split_idx = 15
                
                line1 = display_name[:split_idx].strip()
                line2 = display_name[split_idx:].strip()
                d.text((width/2, int(height * 0.09)), line1, fill=(0,0,0), font=font_large, anchor="mm")
                d.text((width/2, int(height * 0.23)), line2, fill=(0,0,0), font=font_large, anchor="mm")
            else:
                d.text((width/2, int(height * 0.15)), display_name, fill=(0,0,0), font=font_large, anchor="mm")
            
            # Barcode Image
            target_w = int(width * 0.90)
            # Make barcode not so tall
            target_h = int(height * 0.20)

            # Get pure binary representation of the barcode
            binary_string = "".join(bc.build())
            
            # Calculate the exact integer pixel width per module to prevent fractional distortion
            module_width_px = max(1, int(target_w / len(binary_string)))
            # Cap the maximum thickness of lines so scanners don't fail on very short codes
            module_width_px = min(module_width_px, 3) 
            
            barcode_w = len(binary_string) * module_width_px
            
            paste_x = (width - barcode_w) // 2
            # Start barcode below product name
            paste_y = int(height * 0.35)
            
            # Draw barcode manually
            for i, bit in enumerate(binary_string):
                if bit == '1':
                    x0 = paste_x + i * module_width_px
                    y0 = paste_y
                    x1 = x0 + module_width_px - 1
                    y1 = paste_y + target_h
                    d.rectangle([x0, y0, x1, y1], fill=(0,0,0))

            # Readable Barcode Text (font medium)
            text_y = paste_y + target_h + int(height * 0.05)
            d.text((width/2, text_y), barcode_val, fill=(0,0,0), font=font_medium, anchor="mm")
            
            # Price (font large) at the bottom
            price_y = text_y + int(height * 0.20)
            d.text((width/2, price_y), f"{price} UZS", fill=(0,0,0), font=font_large, anchor="mm")

            dib = ImageWin.Dib(img)

            hDC.StartDoc("Barcode Print")
            
            # Print copies continuously as pages of a single document
            for _ in range(copies):
                hDC.StartPage()
                dib.draw(hDC.GetHandleOutput(), (0, 0, width, height))
                hDC.EndPage()

            hDC.EndDoc()
            hDC.DeleteDC()

            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            return Response({'error': str(e), 'traceback': traceback.format_exc()}, status=status.HTTP_400_BAD_REQUEST)
class VariantViewSet(viewsets.ModelViewSet):
    queryset = Variant.objects.all()
    serializer_class = VariantSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['product__name', 'sku', 'product__barcode', 'size__name']
class SizeViewSet(viewsets.ModelViewSet):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer
class SizeScaleViewSet(viewsets.ModelViewSet):
    queryset = SizeScale.objects.all()
    serializer_class = SizeScaleSerializer