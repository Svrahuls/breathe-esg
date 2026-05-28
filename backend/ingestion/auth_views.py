from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        if not username or not password:
            return Response({"error": "Username aur password required hain."}, status=400)
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({"error": "Galat username ya password."}, status=401)
        if not user.is_active:
            return Response({"error": "Account disabled hai."}, status=403)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "user": {"id": user.id, "username": user.username,
                     "email": user.email, "is_staff": user.is_staff},
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
        except Exception:
            pass
        return Response({"detail": "Logged out."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        return Response({"id": u.id, "username": u.username,
                         "email": u.email, "is_staff": u.is_staff})