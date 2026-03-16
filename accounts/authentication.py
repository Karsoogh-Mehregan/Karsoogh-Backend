from typing import Optional
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication, AuthUser
from rest_framework_simplejwt.tokens import Token


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request: Request) -> Optional[tuple[AuthUser, Token]]:
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return None
        
        validated_token = self.get_validated_token(raw_token)

        return self.get_user(validated_token), validated_token
        
