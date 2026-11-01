from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import bp
from app.auth.forms import RegistrationForm, LoginForm
from app.extensions import db
from app.models.user import User


def _redirect_by_role(user: User):
    """Перенаправить пользователя в его кабинет по роли или на ?next=."""
    destinations = {
        'client': 'client.dashboard',
        'master': 'master.dashboard',
        'admin':  'admin.dashboard',
    }
    next_url = request.args.get('next')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(url_for(destinations.get(user.role, 'auth.login')))


@bp.get('/register')
@bp.post('/register')
def register():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role='client',
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Регистрация прошла успешно. Войдите в систему.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@bp.get('/login')
@bp.post('/login')
def login():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неверный email или пароль.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user)
        return _redirect_by_role(user)

    return render_template('auth/login.html', form=form)


@bp.get('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('auth.login'))
