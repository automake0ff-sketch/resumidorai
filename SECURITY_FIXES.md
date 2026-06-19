# SECURITY FIXES - ResumidorAI

Este commit corrige varias vulnerabilidades críticas y altas identificadas en el audit:

## CRÍTICO: Webhooks fail-open
- **webhooks.py**: Ahora falla cerrado (503) en producción cuando falta CLERK_WEBHOOK_SECRET o STRIPE_WEBHOOK_SECRET
- Se agregó función `_require_webhook_secret()` que validate la configuración antes de procesar eventos

## ALTO: Verificación JWT incompleta
- **clerk.py**: Ahora validate issuer (iss), audience (aud), y azp (authorized party)
- Se eliminó el issuer de desarrollo como fallback - ahora requiere CLERK_ISSUER_URL obligatoriamente
- Errores más específicos para cada tipo de fallo de validación

## ALTO: Bypass de cuotas por concurrencia
- **job_processor.py**: Se agregaron límites de duración por plan para prevenir abuse de recursos
- Duration limits: trial=1h, free=30m, starter=1h, pro=2h, agency=4h

## ALTO: Jobs no durables  
- **main.py**: Documentación agregada sobre BackgroundTasks (sección pendiente para Cloud Tasks)

## MEDIO: Validación de URL demasiado permisiva
- **schemas.py**: Ahora validate explícitamente el hostname usando urlparse
- Solo permite: youtube.com, www.youtube.com, m.youtube.com, youtu.be

## MEDIO: /docs expuesto
- **main.py**: Swagger UI (/docs) se desactiva automáticamente en producción (ENV=NODE_ENV=production)

## Variables de entorno nuevas
- CLERK_AUDIENCE: Requerido para validación de audiencia JWT
- CLERK_AUTHORIZED_PARTY: Opcional pero recomendado para validar azp

## Pendiente (requiere infraestructura adicional)
- Reemplazar BackgroundTasks con Cloud Tasks/Celery para jobs realmente durables
- Transacciones Firestore atómicas para incremento de cuotas (evitar race conditions)
