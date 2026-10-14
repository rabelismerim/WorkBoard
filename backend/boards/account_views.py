import json
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.mail import send_mail
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from .models import RecoveryEmail
from .auth_security import throttle, RateLimited

def payload(request):
    data=json.loads(request.body)
    if not isinstance(data,dict) or not all(isinstance(v,str) for v in data.values()):raise ValueError()
    return data

def rate_response():
    response=JsonResponse({'detail':'Muitas tentativas. Aguarde alguns minutos e tente novamente.'},status=429)
    response['Retry-After']=str(settings.AUTH_RATE_WINDOW)
    return response

@ensure_csrf_cookie
@csrf_protect
@require_http_methods(['GET','POST'])
def account(request):
    if not request.user.is_authenticated:return JsonResponse({'detail':'Entre na sua conta.'},status=403)
    if request.method=='POST':
        try:
            data=payload(request)
            throttle(request,'account',request.user.username)
            if authenticate(request,username=request.user.username,password=data.get('password','')) is None:
                return JsonResponse({'detail':'Senha atual inválida.'},status=400)
            email=data.get('email','').strip().lower()
            validate_email(email)
            with transaction.atomic():
                if get_user_model().objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists():raise ValueError()
                RecoveryEmail.objects.update_or_create(user=request.user,defaults={'email':email})
                request.user.email=email
                request.user.save(update_fields=['email'])
        except RateLimited:return rate_response()
        except (ValueError,ValidationError,IntegrityError):return JsonResponse({'detail':'E-mail inválido ou indisponível.'},status=400)
    return JsonResponse({'username':request.user.username,'email':request.user.email})

@ensure_csrf_cookie
@csrf_protect
@require_http_methods(['POST'])
def recovery(request):
    try:
        data=payload(request)
        email=data.get('email','').strip().lower()
        throttle(request,'recovery',email)
        validate_email(email)
    except RateLimited:return rate_response()
    except (ValueError,ValidationError):return JsonResponse({'detail':'Informe um e-mail válido.'},status=400)
    entry=RecoveryEmail.objects.select_related('user').filter(email=email,user__is_active=True).first()
    if entry and entry.user.has_usable_password():
        user=entry.user
        uid=urlsafe_base64_encode(force_bytes(user.pk))
        token=default_token_generator.make_token(user)
        link=f'{settings.PUBLIC_URL}/?reset_uid={uid}&reset_token={token}'
        send_mail('Recuperação de senha — WorkBoard',f'Para definir uma nova senha, abra:\n{link}\n\nO link expira em uma hora e só pode ser usado uma vez. Se você não solicitou, ignore esta mensagem.',settings.DEFAULT_FROM_EMAIL,[email])
    return JsonResponse({'detail':'Se o e-mail estiver cadastrado, você receberá as instruções de recuperação.'})

@ensure_csrf_cookie
@csrf_protect
@require_http_methods(['POST'])
def reset_password(request):
    try:
        data=payload(request)
        throttle(request,'reset',data.get('uid',''))
        pk=force_str(urlsafe_base64_decode(data.get('uid','')))
        with transaction.atomic():
            user=get_user_model().objects.select_for_update().filter(pk=pk,is_active=True).first()
            if not user or not default_token_generator.check_token(user,data.get('token','')):
                return JsonResponse({'detail':'Link inválido ou expirado. Solicite uma nova recuperação.'},status=400)
            password=data.get('password','')
            validate_password(password,user)
            user.set_password(password)
            user.save(update_fields=['password'])
    except RateLimited:return rate_response()
    except (ValueError,TypeError,OverflowError,ValidationError) as exc:
        return JsonResponse({'detail':' '.join(exc.messages) if isinstance(exc,ValidationError) else 'Dados inválidos.'},status=400)
    # Django session authentication hashes invalidate existing sessions automatically.
    return JsonResponse({'detail':'Senha atualizada. Entre com a nova senha.'})
