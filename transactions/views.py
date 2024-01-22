from typing import Any
from django.db.models.query import QuerySet
from django.forms.models import BaseModelForm
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import CreateView,ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Transaction
from .forms import DepositForm,WithdrawForm,LoanRequestForm
from .constants import DEPOSIT,WITHDRAWAL,LOAN,LOAN_PAID
from django.contrib import messages
from datetime import datetime
from django.db import Sum
from django.shortcuts import get_object_or_404,redirect
from django.views import View
# Create your views here.
# ei view ke inheret kore amara deposit,withdraw,load request er kaj korbo
class TransactionCreateMixin(LoginRequiredMixin,CreateView):
    template_name= ''
    model = Transaction
    title = ''
    success_url = ''
    
    def get_form_kwargs(self) :
       kwargs = super().get_form_kwargs()
       kwargs.update({
           'account': self.request.user.account,
           
       })
       return kwargs
    
    def get_context_data(self, **kwargs: Any) :
        context=  super().get_context_data(**kwargs)
        return context.update(
           { 'title' : self.title
            
            }
        )
        
class DepositMoneyView(TransactionCreateMixin):
    form = DepositForm
    title = 'Deposit'
    
    def get_initial(self)  :
        initial ={'transaction_type':DEPOSIT}
        return initial
    
    def form_valid(self, form) :
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account 
        account.balance += amount  #user er kase ase 500tk
        account.save(
            
            update_fields =['balance']
        )
        messages.success(self.request,f"{amount} $ was deposited to your account successfully")
        return super().form_valid()
    
    
class WithdrawMoneyView(TransactionCreateMixin):
    form = WithdrawForm
    title = 'Withdraw Money'
    
    def get_initial(self)  :
        initial ={'transaction_type':WITHDRAWAL}
        return initial
    
    def form_valid(self, form) :
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account 
        account.balance -= amount  #withdraw korle tk kome jaabe
        account.save(
            
            update_fields =['balance']
        )
        messages.success(self.request,f"Successfully withdrawn {amount} $ from you account")
        return super().form_valid()
    
    
class LoanRequestView(TransactionCreateMixin):
    form = LoanRequestForm
    title = 'Request For Loan'
    
    def get_initial(self)  :
        initial ={'transaction_type':LOAN}
        return initial
    
    def form_valid(self, form) :
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(account = self.request.user.account,transaction_type =3 ,loan_approve =True ).count()
        if current_loan_count >= 3:
            return HttpResponse("You have crossed your Loan Request Limit")
        messages.success(self.request,f"Loan request for  {amount} $ has been successfully sent to admin")
        return super().form_valid()
    
    
class TransactionReportView(LoginRequiredMixin,ListView):
    # jodi user kono type filter na kore taile tar total transaction report dekhabo
    template_name = ""
    model =Transaction
    balance = 0 
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account = self.request.user.account             
            
        )
        
        start_date_str = self.request.GET('start_date')
        end_date_str = self.request.GET('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str,"%Y-%M-%d").date()
            end_date = datetime.strptime(end_date_str,"%Y-%M-%d").date()

            queryset = queryset.filter(timestamp_date_gte = start_date,timestamp_date_lte = end_date)
            self.balance = Transaction.objects.filter(timestamp_date_gte = start_date,timestamp_date_lte = end_date).aggregate(Sum('amount'))['amount__sum']
        
        else:
            self.balance = self.request.user.account.balance
            
        return queryset.distinct()
    
    def get_context_data(self, **kwargs: Any) :
        context=  super().get_context_data(**kwargs)
        return context.update(
           { 'account' : self.request.user.account
            
            }
        )
        return context
    

class PayLoanView(LoginRequiredMixin,View):
    def get(self,request,loan_id):
        loan = get_object_or_404(Transaction,id = loan_id)
        if loan.loan_approve: #ekjon user loan pay korte parbe tokhnoi jkn tar loan approve hobe
            user_account = loan.account
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount 
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.transaction_type = LOAN_PAID
                loan.save()
                return redirect()
            else:
                messages.error(self.request,f"Loan amount is greater than available balance")
                return redirect()
            
    
class LoanListView(LoginRequiredMixin,ListView):
    model =Transaction
    template_name =''
    context_object_name ='loans'
    
    def get_queryset(self):
        user_account = self.request.user.account
        queryset = Transaction.objects.filter(account =user_account,transaction_type = LOAN)
        return queryset
    