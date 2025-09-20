from django.contrib import admin

from .models import EventProposal, ExpenseDetail, IncomeDetail

admin.site.register(EventProposal)
admin.site.register(IncomeDetail)
admin.site.register(ExpenseDetail)
