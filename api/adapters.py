from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Gera username único a partir do e-mail no fluxo social login."""

    def populate_user(self, request, sociallogin, data):
        """Evita colisão de username adicionando sufixo incremental."""
        user = super().populate_user(request, sociallogin, data)

        email = data.get('email')

        if email:
            base_username = email.split('@')[0]
            username = base_username
            counter = 1

            user_model = user.__class__

            while user_model.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            user.username = username

        return user