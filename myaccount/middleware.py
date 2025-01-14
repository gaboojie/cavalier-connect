from django.shortcuts import redirect

class RestrictAdminMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated or request.path.startswith('/admin/'):
            return self.get_response(request)

        if request.user.is_staff:
            return redirect('/admin/')

        return self.get_response(request)