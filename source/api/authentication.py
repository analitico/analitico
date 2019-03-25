from django.utils.translation import ugettext_lazy as _
from rest_framework.authentication import BaseAuthentication, get_authorization_header, exceptions
from api.models.token import Token


class BearerAuthentication(BaseAuthentication):
    """
    Simple token based authentication.
    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string "Bearer ".  For example:
    Authorization: Bearer 401f7ac837da42b97f613d789819ff93537bee6a
    """

    keyword = "Bearer"
    model = Token

    def get_model(self):
        if self.model is not None:
            return self.model
        return Token

    def authenticate(self, request):

        # see if token passed as ?token=tok_xxx
        token = request.query_params.get("token")

        # check for token in authorization headers
        if not token:
            auth = get_authorization_header(request).split()
            if not auth or auth[0].lower() != self.keyword.lower().encode():
                return None

            if len(auth) == 1:
                msg = _("Invalid token header. No credentials provided.")
                raise exceptions.AuthenticationFailed(msg)
            elif len(auth) > 2:
                msg = _("Invalid token header. Token string should not contain spaces.")
                raise exceptions.AuthenticationFailed(msg)
            try:
                token = auth[1].decode()
            except UnicodeError:
                msg = _("Invalid token header. Token string should not contain invalid characters.")
                raise exceptions.AuthenticationFailed(msg)
        return self.authenticate_credentials(token)

    def authenticate_credentials(self, key):
        try:
            # pylint: disable=no-member
            token = Token.objects.select_related("user").get(pk=key)
        except Token.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid token."))

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed(_("User inactive or deleted."))

        return (token.user, token)

    def authenticate_header(self, request):
        return self.keyword
