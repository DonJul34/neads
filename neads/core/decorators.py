from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from functools import wraps


def role_required(allowed_roles):
    """
    Décorateur pour limiter l'accès aux vues en fonction du rôle de l'utilisateur.
    
    Exemple d'utilisation:
    @role_required(['admin', 'consultant'])
    def some_view(request):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Vérifier si l'utilisateur est authentifié
            if not request.user.is_authenticated:
                return redirect('login')
            
            # Vérifier si l'utilisateur a un rôle autorisé
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            # Accès refusé
            return HttpResponseForbidden("Vous n'avez pas les autorisations nécessaires pour accéder à cette page.")
            
        return _wrapped_view
    return decorator 