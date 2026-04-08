from rest_framework import viewsets
from .models import Posto
from .serializers import PostoSerializer

# Create your views here.

class PostoViewSet(viewsets.ModelViewSet):
    queryset = Posto.objects.all()
    serializer_class = PostoSerializer