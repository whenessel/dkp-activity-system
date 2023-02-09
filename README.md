# DKP Activity System

# Сборка и запуск

### Сборка
```shell
docker build -f compose/Dockerfile -t dkp .

```

##### Стандартная команда запуска: runserver 0.0.0.0:8000
>Полный писок команд можно получить [HERE](#Help) 

#### Запуск web
Создать файл .env

```shell
docker create --env-file=.env --publish 0.0.0.0:8000:8000 --name=dkp-web --restart=always -t dkp
docker start dkp-web

# для применения миграций
docker exec -it dkp-web python manage.py migrate --no-input

# Для создания суперпользователя
docker exec -it dkp-web python manage.py createsuperuser --username admin

```

#### Запуск без "_.env_" файла
Возможно указать все необходимые переменные через параметры при создании контейнера

```shell
docker create -e DATABASE_URL=sqlite:///../dkp.sqlite3 \
-e EVE_TOKEN=<TOKEN_HERE> \
-e EVE_PERMISSIONS=8 \
--name=dkp-eve --restart=always -t dkp run_evebot

docker start dkp-eve

# для применения миграций (если требуется)
docker exec -it dkp-eve python manage.py migrate --no-input

```


#### Запуск EveBot
Создать файл .env
```shell
docker create --env-file=.env --name=dkp-eve --restart=always -t dkp run_evebot
docker start dkp-eve

# для применения миграций (если требуется)
docker exec -it dkp-eve python manage.py migrate --no-input

```

#### Остановка контейнеров

```shell
docker stop dkp-eve
docker stop dkp-web

```

# Docker Compose

Собрать свежую версию и запустить

```shell
docker compose build

# Для получения с реестра образов
docker compose pull

docker compose up -d

# Миграции
docker exec -it dkp-eve python manage.py migrate --no-input

# Остановка
docker compose down
```


# Help
Полный список команд _Django Framework_

```shell
docker run -it --rm dkp help

```
или в том же самом контейнере

```shell
docker exec -it dkp-web python manage.py help

```

| Команда         | Описание                                                                   |
|-----------------|----------------------------------------------------------------------------|
| migrate         | Применить новые миграции в БД                                              |
| run_evebot      | Запустить EveBot - отвечает за собития внутри игры                         |
| runserver       | Запускает django web server                                                |
| createsuperuser | Создает супер пользователя для доступа к панели администрирования          |
| changepassword  | Изменить пароль для пользователя                                           |
| loaddata        | Загрузить первичные данные в БД ( если требуется )                         |
| collectstatic   | Сбор статик файлов (картинки и тд) в директорию веб сервера (не требуется) |



# Вспомогательные команды

Сохранить фикстуры
```shell
docker exec -it dkp-eve python manage.py dumpdata auth --indent 4 -o fixtures/auth.json
docker exec -it dkp-eve python manage.py dumpdata activity --indent 4 -o fixtures/activity.json

```

Загрузка при инициализации системы

```shell
docker exec -it dkp-eve python manage.py loaddata auth
docker exec -it dkp-eve python manage.py activity

```


### HACKS

С подключением к БД из другой сети

```shell
# Create
docker create --env-file=.env --name=dkp-eve --restart=always --link db_postgres_1:db_postgres_1 --net db_default -t dkp run_evebot


```