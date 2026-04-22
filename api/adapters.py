from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        
        email = data.get('email')
        
        if email:
            base_username = email.split('@')[0]
            username = base_username
            contador = 1
            
            User = user.__class__
            
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{contador}"
                contador += 1
                
            user.username = username
            
        return user