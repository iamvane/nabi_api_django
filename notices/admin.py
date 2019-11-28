from django.contrib import admin

from .models import Offer


class OfferAdmin(admin.ModelAdmin):
    list_display = ('name', 'show_at', 'hide_at')


admin.site.register(Offer, OfferAdmin)
