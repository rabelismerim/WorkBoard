from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.core.validators import validate_email
from .auth_security import throttle, RateLimited
from .account_views import rate_response
from .models import RecoveryEmail
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.http import require_http_methods
import json
@ensure_csrf_cookie
@csrf_protect
@require_http_methods(['GET', 'POST', 'DELETE'])
def session(request):
    if request.method == 'DELETE':
        logout(request)
        return JsonResponse({'user': None})
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if not isinstance(data, dict):
                raise ValueError()
            username, password = data.get('username', ''), data.get('password', '')
            if not isinstance(username, str) or not isinstance(password, str):
                raise ValueError()
            throttle(request,'session',username)
            if data.get('register'):
                if not username.strip() or len(username) > 150:
                    return JsonResponse({'detail': 'Informe um usuário válido.'}, status=400)
                email=data.get('email','')
                if not isinstance(email,str):raise ValueError()
                email=email.strip().lower()
                if email:
                    validate_email(email)
                    if get_user_model().objects.filter(email__iexact=email).exists():raise ValueError()
                with transaction.atomic():
                    user = get_user_model()(username=username,email=email)
                    user.full_clean(exclude=['password'])
                    validate_password(password, user)
                    user.set_password(password)
                    user.save()
                    if email:RecoveryEmail.objects.create(user=user,email=email)
            else:
                user = authenticate(request, username=username, password=password)
                if user is None:
                    return JsonResponse({'detail': 'Usuário ou senha inválidos.'}, status=400)
            login(request, user)
        except RateLimited:return rate_response()
        except (ValueError, ValidationError, IntegrityError) as exc:
            return JsonResponse({'detail': ' '.join(exc.messages) if isinstance(exc, ValidationError) else 'Dados inválidos ou usuário já cadastrado.'}, status=400)
    return JsonResponse({'user': {'id': request.user.id, 'username': request.user.username} if request.user.is_authenticated else None})
