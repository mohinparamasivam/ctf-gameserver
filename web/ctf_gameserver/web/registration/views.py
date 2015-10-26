from django.db import transaction
from django.shortcuts import render, redirect
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.contrib.auth import logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required

from . import forms
from .models import Team
from .util import email_token_generator

User = get_user_model()    # pylint: disable=invalid-name


@transaction.atomic
def register(request):

    if request.method == 'POST':
        user_form = forms.UserForm(request.POST, prefix='user')
        team_form = forms.TeamForm(request.POST, prefix='team')

        # pylint: disable=no-member
        if user_form.is_valid() and team_form.is_valid():
            user = user_form.save()
            team_form.save(user)
            user_form.send_confirmation_mail(request)

            messages.success(request, _('Successful registration! A confirmation mail has been sent to your '
                                        'formal email adress. Please open the link inside that email in '
                                        'order to complete your sign-up.'))

            # TODO
            return redirect('/')
    else:
        user_form = forms.UserForm(prefix='user')
        team_form = forms.TeamForm(prefix='team')

    return render(request, 'register.html', {'user_form': user_form, 'team_form': team_form})


@login_required
@transaction.atomic
def edit_team(request):

    try:
        team = request.user.team
    except Team.DoesNotExist:
        team = None

    if request.method == 'POST':
        user_form = forms.UserForm(request.POST, prefix='user', instance=request.user)
        team_form = forms.TeamForm(request.POST, prefix='team', instance=team)

        # pylint: disable=no-member
        if user_form.is_valid() and team_form.is_valid():
            user = user_form.save()
            team_form.save(user)

            if 'password' in user_form.changed_data:
                # Keep the current session active although all sessions are invalidated on password change
                update_session_auth_hash(request, user)

            if 'email' in user_form.changed_data:
                user_form.send_confirmation_mail(request)
                logout(request)

                messages.warning(request, _('A confirmation mail has been sent to your new formal email '
                                            'adress. Please visit the link inside that email. Until then, '
                                            'your team has been deactivated and you have been logged out.'))

            # TODO
            return redirect('/')
    else:
        user_form = forms.UserForm(prefix='user', instance=request.user)
        team_form = forms.TeamForm(prefix='team', instance=team)

    return render(request, 'edit_team.html', {'user_form': user_form, 'team_form': team_form})


@transaction.atomic
def confirm_email(request):

    try:
        user_pk = request.GET['user']
        token = request.GET['token']
    except KeyError:
        messages.error(request, _('Missing parameters, email address could not be confirmed.'))
        return render(request, '400.html', status=400)

    error_message = _('Invalid user or token, email address could not be confirmed.')

    # pylint: disable=protected-access
    try:
        user = User._default_manager.get(pk=user_pk)
    except User.DoesNotExist:
        messages.error(request, error_message)
        return render(request, '400.html', status=400)

    if email_token_generator.check_token(user, token):    # pylint: disable=no-member
        User._default_manager.filter(pk=user_pk).update(is_active=True)
        messages.success(request, _('Email address confirmed. Your registration is now complete.'))
    else:
        messages.error(request, error_message)
        return render(request, '400.html', status=400)

    # TODO
    return redirect('/')