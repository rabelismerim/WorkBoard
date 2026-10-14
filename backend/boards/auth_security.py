import hashlib
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import AuthThrottle

class RateLimited(Exception):
    pass

def throttle(request, scope, identity=''):
    now=timezone.now()
    # Trust only the deployment proxy's dedicated real-IP header when explicitly enabled.
    ip=request.META.get('HTTP_X_REAL_IP') if getattr(settings,'AUTH_TRUST_PROXY_IP',False) else request.META.get('REMOTE_ADDR','unknown')
    limit=settings.AUTH_RATE_LIMIT
    keys=[(f'{scope}:ip:{ip}',limit*3)]
    if identity:keys.append((f'{scope}:identity:{identity.casefold().strip()}',limit))
    with transaction.atomic():
        for value,maximum in keys:
            key=hashlib.sha256(f'{settings.SECRET_KEY}:{value}'.encode()).hexdigest()
            row,_=AuthThrottle.objects.get_or_create(key=key,defaults={'window_start':now})
            row=AuthThrottle.objects.select_for_update().get(pk=row.pk)
            if now-row.window_start>=timedelta(seconds=settings.AUTH_RATE_WINDOW):
                row.window_start=now;row.attempts=0
            if row.attempts>=maximum:raise RateLimited()
            row.attempts+=1
            row.save(update_fields=['window_start','attempts'])
