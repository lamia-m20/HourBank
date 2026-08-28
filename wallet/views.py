from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import HourWallet


@login_required(login_url='accounts:login')
def wallet_detail(request):
    wallet, _ = HourWallet.objects.get_or_create(user=request.user)
    return render(request, 'wallet-templates/wallet.html', {
        'wallet': wallet, 'transactions': wallet.transactions.all()[:30],
    })
