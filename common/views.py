from rest_framework.views import APIView
from rest_framework.response import Response
from .models import PrinterSetting

class PrinterSettingView(APIView):
    def get(self, request):
        setting = PrinterSetting.load()
        return Response({
            'printer_name': setting.printer_name,
            'paper_width_mm': setting.paper_width_mm,
            'paper_height_mm': setting.paper_height_mm,
            'dpi': setting.dpi,
            'layout_config': setting.layout_config,
        })

    def put(self, request):
        setting = PrinterSetting.load()
        setting.printer_name = request.data.get('printer_name', setting.printer_name)
        setting.paper_width_mm = int(request.data.get('paper_width_mm', setting.paper_width_mm))
        setting.paper_height_mm = int(request.data.get('paper_height_mm', setting.paper_height_mm))
        setting.dpi = int(request.data.get('dpi', setting.dpi))
        
        layout_config = request.data.get('layout_config')
        if layout_config:
            setting.layout_config = layout_config
            
        setting.save()
        return Response({'message': 'Printer settings updated successfully'})
