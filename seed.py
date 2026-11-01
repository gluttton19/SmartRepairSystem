"""
Наполнение базы данных тестовыми данными.
Повторный запуск безопасен — дубликаты не создаются.
"""
import os
import random
from datetime import date, timedelta
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.car import Car
from app.models.master import Master, MasterSkill
from app.models.service import Service
from app.models.request import Request, RequestStatus
from app.models.status_history import RequestStatusHistory
from app.models.notification import Notification
from app.services.status_service import record_status_change

app = create_app()

# ---------------------------------------------------------------------------
# Справочные данные
# ---------------------------------------------------------------------------

SERVICES = [
    ('Замена масла',              'Замена моторного масла и масляного фильтра',   1_500),
    ('Диагностика',               'Компьютерная диагностика всех систем',          800),
    ('Шиномонтаж',                'Замена и балансировка шин',                     600),
    ('Замена тормозных колодок',  'Замена передних или задних тормозных колодок', 2_200),
    ('Ремонт подвески',           'Диагностика и ремонт элементов подвески',      4_500),
]

MASTERS = [
    ('master_ivanov',  'master1@example.test',  'Техническое обслуживание'),
    ('master_petrov',  'master2@example.test',  'Кузовной ремонт'),
    ('master_sidorov', 'master3@example.test', 'Электрика и диагностика'),
]

# Какие услуги умеет каждый мастер (по индексу в SERVICES)
MASTER_SKILLS = {
    'master_ivanov':  [0, 1, 2, 3],   # Замена масла, Диагностика, Шиномонтаж, Тормоза
    'master_petrov':  [2, 3, 4],       # Шиномонтаж, Тормоза, Подвеска
    'master_sidorov': [1, 0, 4],       # Диагностика, Замена масла, Подвеска
}

CLIENTS = [
    ('client_kozlov',    'client1@example.test'),
    ('client_novikova',  'client2@example.test'),
    ('client_morozov',   'client3@example.test'),
    ('client_volkov',    'client4@example.test'),
    ('client_lebedeva',  'client5@example.test'),
]

CARS_DATA = [
    # (owner_username, brand, model, year, reg_number, vin)
    ('client_kozlov',   'Toyota',    'Camry',   2019, 'TEST-REG-001', None),
    ('client_kozlov',   'Ford',      'Focus',   2017, 'TEST-REG-002', None),
    ('client_novikova', 'BMW',       'X5',      2021, 'TEST-REG-003', None),
    ('client_novikova', 'Kia',       'Rio',     2018, 'TEST-REG-004', None),
    ('client_morozov',  'Lada',      'Vesta',   2022, 'TEST-REG-005', None),
    ('client_morozov',  'Hyundai',   'Solaris', 2020, 'TEST-REG-006', None),
    ('client_volkov',   'Volkswagen','Polo',    2016, 'TEST-REG-007', None),
    ('client_volkov',   'Skoda',     'Octavia', 2020, 'TEST-REG-008', None),
    ('client_volkov',   'Nissan',    'Qashqai', 2018, 'TEST-REG-009', None),
    ('client_lebedeva', 'Renault',   'Logan',   2015, 'TEST-REG-010', None),
    ('client_lebedeva', 'Mazda',     'CX-5',    2021, 'TEST-REG-011', None),
]

# Последовательности статусов для разных сценариев заявок
STATUS_CHAINS = [
    [RequestStatus.CREATED],
    [RequestStatus.CREATED, RequestStatus.CONFIRMED],
    [RequestStatus.CREATED, RequestStatus.CONFIRMED, RequestStatus.IN_WORK],
    [RequestStatus.CREATED, RequestStatus.CONFIRMED, RequestStatus.IN_WORK,
     RequestStatus.WAITING],
    [RequestStatus.CREATED, RequestStatus.CONFIRMED, RequestStatus.IN_WORK,
     RequestStatus.READY],
    [RequestStatus.CREATED, RequestStatus.CONFIRMED, RequestStatus.IN_WORK,
     RequestStatus.READY, RequestStatus.DONE],
    [RequestStatus.CREATED, RequestStatus.CANCELLED],
]

DEFAULT_PASSWORD = os.environ.get('AUTOSERVICE_DEMO_PASSWORD')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f'  {msg}')


def get_or_create_user(username: str, email: str, role: str) -> tuple[User, bool]:
    user = User.query.filter_by(email=email).first()
    if user:
        return user, False
    user = User(username=username, email=email, role=role)
    user.set_password(DEFAULT_PASSWORD)
    db.session.add(user)
    db.session.flush()
    return user, True


def seed_admin() -> User:
    print('\n[Администратор]')
    user, created = get_or_create_user('admin', 'admin@example.test', 'admin')
    log(f'{"Создан" if created else "Существует"}: admin  /  admin@example.test')
    return user


def seed_services() -> dict[str, Service]:
    print('\n[Услуги]')
    result = {}
    for name, desc, price in SERVICES:
        svc = Service.query.filter_by(name=name).first()
        if svc:
            log(f'Существует: {name}')
        else:
            svc = Service(name=name, description=desc, price=price)
            db.session.add(svc)
            db.session.flush()
            log(f'Создана:    {name}  ({price} ₽)')
        result[name] = svc
    return result


def seed_masters(services: dict[str, Service]) -> dict[str, Master]:
    print('\n[Мастера]')
    service_list = [services[n] for n, _, _ in SERVICES]
    result = {}
    for username, email, spec in MASTERS:
        user, u_created = get_or_create_user(username, email, 'master')
        master = Master.query.filter_by(user_id=user.id).first()
        if master:
            log(f'Существует: {username}  ({spec})')
        else:
            master = Master(user_id=user.id, specialization=spec, is_available=True)
            db.session.add(master)
            db.session.flush()
            skill_names = []
            for svc_idx in MASTER_SKILLS[username]:
                svc = service_list[svc_idx]
                exists = MasterSkill.query.filter_by(
                    master_id=master.id, service_id=svc.id
                ).first()
                if not exists:
                    db.session.add(MasterSkill(master_id=master.id, service_id=svc.id))
                skill_names.append(svc.name)
            log(f'Создан:     {username}  ({spec})  навыки: {", ".join(skill_names)}')
        result[username] = master
    return result


def seed_clients() -> dict[str, User]:
    print('\n[Клиенты]')
    result = {}
    for username, email in CLIENTS:
        user, created = get_or_create_user(username, email, 'client')
        log(f'{"Создан" if created else "Существует"}: {username}')
        result[username] = user
    return result


def seed_cars(clients: dict[str, User]) -> dict[str, list[Car]]:
    print('\n[Автомобили]')
    result: dict[str, list[Car]] = {u: [] for u in clients}
    for owner_name, brand, model, year, reg, vin in CARS_DATA:
        owner = clients[owner_name]
        car = Car.query.filter_by(registration_number=reg).first()
        if car:
            log(f'Существует: {brand} {model} ({reg})')
        else:
            car = Car(
                owner_id=owner.id, brand=brand, model=model,
                year=year, registration_number=reg, vin=vin,
            )
            db.session.add(car)
            db.session.flush()
            log(f'Создан:     {brand} {model} ({year})  рег.{reg}  владелец:{owner_name}')
        result[owner_name].append(car)
    return result


def seed_requests(
    clients: dict[str, User],
    cars_by_owner: dict[str, list[Car]],
    services: dict[str, Service],
    masters: dict[str, Master],
) -> None:
    print('\n[Заявки]')

    if Request.query.count() >= 20:
        log('Заявки уже существуют (≥20), пропуск.')
        return

    service_list = list(services.values())
    master_list  = list(masters.values())
    today        = date.today()

    requests_created = 0
    for owner_name, owner_user in clients.items():
        owner_cars = cars_by_owner.get(owner_name, [])
        if not owner_cars:
            continue

        # Каждый клиент получает 4 заявки
        for i in range(4):
            car     = random.choice(owner_cars)
            svc     = random.choice(service_list)
            master  = random.choice(master_list)
            chain   = random.choice(STATUS_CHAINS)
            pref_dt = today + timedelta(days=random.randint(-30, 30))

            req = Request(
                car_id=car.id,
                service_id=svc.id,
                master_id=master.id,
                preferred_date=pref_dt,
                description=f'Тестовая заявка #{requests_created + 1}',
                status=RequestStatus.CREATED,
            )
            db.session.add(req)
            db.session.flush()

            # Прогоняем цепочку статусов
            prev_status = None
            for status in chain:
                entry = RequestStatusHistory(
                    request_id=req.id,
                    old_status=prev_status,
                    new_status=status,
                    changed_by_id=owner_user.id if status == RequestStatus.CREATED else master.user_id,
                    comment='Создана клиентом' if status == RequestStatus.CREATED else None,
                )
                db.session.add(entry)
                req.status = status
                prev_status = status

            requests_created += 1
            log(f'Заявка #{req.id}: {owner_name} / {car.brand} {car.model} / {svc.name} / статус: {req.status.value}')

    # Дополняем до 20 если не хватает
    if requests_created < 20:
        extra = 20 - requests_created
        all_cars   = [c for lst in cars_by_owner.values() for c in lst]
        owner_map  = {c.id: uname for uname, lst in cars_by_owner.items() for c in lst}
        for _ in range(extra):
            car    = random.choice(all_cars)
            svc    = random.choice(service_list)
            master = random.choice(master_list)
            chain  = random.choice(STATUS_CHAINS)
            pref_dt = today + timedelta(days=random.randint(-30, 30))
            owner_user = clients[owner_map[car.id]]

            req = Request(
                car_id=car.id, service_id=svc.id, master_id=master.id,
                preferred_date=pref_dt, description=f'Доп. заявка',
                status=RequestStatus.CREATED,
            )
            db.session.add(req)
            db.session.flush()

            prev_status = None
            for status in chain:
                db.session.add(RequestStatusHistory(
                    request_id=req.id, old_status=prev_status, new_status=status,
                    changed_by_id=owner_user.id if status == RequestStatus.CREATED else master.user_id,
                ))
                req.status = status
                prev_status = status

            requests_created += 1
            log(f'Заявка #{req.id}: (доп) {car.brand} {car.model} / статус: {req.status.value}')


def seed_notifications(clients: dict[str, User]) -> None:
    print('\n[Уведомления]')
    if Notification.query.count() > 0:
        log('Уведомления уже существуют, пропуск.')
        return

    messages = [
        'Ваша заявка принята в обработку.',
        'Мастер приступил к работе.',
        'Ваш автомобиль готов к выдаче.',
        'Не забудьте забрать автомобиль — он ждёт вас!',
    ]
    count = 0
    for username, user in clients.items():
        for msg in random.sample(messages, k=random.randint(1, 3)):
            db.session.add(Notification(user_id=user.id, message=msg))
            count += 1
    log(f'Создано уведомлений: {count}')


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    if not DEFAULT_PASSWORD:
        raise SystemExit('Set AUTOSERVICE_DEMO_PASSWORD before running seed.py.')
    with app.app_context():
        print('=' * 60)
        print('SEED: наполнение базы данных тестовыми данными')
        print('=' * 60)

        seed_admin()
        services = seed_services()
        masters  = seed_masters(services)
        clients  = seed_clients()
        cars     = seed_cars(clients)

        db.session.flush()
        seed_requests(clients, cars, services, masters)
        seed_notifications(clients)

        db.session.commit()

        print('\n' + '=' * 60)
        print('ИТОГ:')
        from app.models.user import User
        from app.models.request import Request
        from app.models.notification import Notification
        print(f'  Пользователей:   {User.query.count()}')
        print(f'  Услуг:           {Service.query.count()}')
        print(f'  Мастеров:        {Master.query.count()}')
        print(f'  Автомобилей:     {Car.query.count()}')
        print(f'  Заявок:          {Request.query.count()}')
        print(f'  Уведомлений:     {Notification.query.count()}')
        print('=' * 60)
        print('Готово. Demo password comes from AUTOSERVICE_DEMO_PASSWORD.')


if __name__ == '__main__':
    run()
