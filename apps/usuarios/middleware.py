from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class CambioClaveObligatorioMiddleware:
    """Mientras `primer_ingreso` sea True, solo se permite cambiar la clave o cerrar sesión.

    Se aplica a todas las rutas, así que escribir otra URL a mano tampoco evita el cambio.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, 'user', None)
        if usuario is not None and usuario.is_authenticated and usuario.primer_ingreso:
            permitidas = {reverse('usuarios:cambiar_clave'), reverse('usuarios:logout')}
            if request.path not in permitidas and not request.path.startswith('/' + settings.STATIC_URL.lstrip('/')):
                return redirect('usuarios:cambiar_clave')
        return self.get_response(request)
