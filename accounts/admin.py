from django.contrib import admin
from .models import City, OtpRequest, Province, School, User

# Register your models here.
admin.site.register(Province)
admin.site.register(City)
admin.site.register(School)
admin.site.register(User)
admin.site.register(OtpRequest)
