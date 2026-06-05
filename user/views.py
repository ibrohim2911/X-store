from rest_framework import viewsets
from rest_framework.views import APIView, Response
from rest_framework import permissions, status
from django.contrib.auth import authenticate, login, logout
from .models import User
from .serializers import UserSerializer
from common.permissions import IsRoleAuthorized

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsRoleAuthorized]
    queryset = User.objects.all()
    serializer_class = UserSerializer

class LoginView(APIView):
    # This view must be accessible to unauthenticated users
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')

        user = authenticate(request, username=phone_number, password=password)

        if user is not None:
            login(request, user) # This creates the session cookie
            return Response({"detail": "Successfully logged in."}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
class LogoutView(APIView):
    # This view must be accessible to authenticated users
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request) # This deletes the session cookie
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)