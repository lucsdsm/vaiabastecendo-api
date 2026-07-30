from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.auth import GoogleLogin, UserProfileView
from .views.fuel_types import FuelTypeViewSet
from .views.price_updates import PriceUpdateViewSet
from .views.reactions import ReactionViewSet
from .views.stations import StationViewSet

router = DefaultRouter()

router.register(r'stations', StationViewSet, basename='station')
router.register(r'fuel-types', FuelTypeViewSet, basename='fuel-type')
router.register(r'reactions', ReactionViewSet, basename='reaction')
router.register(r'price-updates', PriceUpdateViewSet, basename='price-update')

urlpatterns = [
	path('', include(router.urls)),
	path('auth/google/', GoogleLogin.as_view(), name='google-login'),
	path('profile/', UserProfileView.as_view(), name='user-profile'),
]