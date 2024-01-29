[![image](https://img.shields.io/github/v/release/whenessel/dkp-activity-system?logo=GitHub)](https://github.com/whenessel/dkp-activity-system/releases)
[![image](https://img.shields.io/docker/v/whenessel/dkp-activity-system?logo=docker)](https://hub.docker.com/repository/docker/whenessel/dkp-activity-system/general)
# DKP Activity System

## Запуск контейнера с ботом
> Рекомендуется только для опытных пользователей
> Файл .env должен содержать все необходимые переменные среды
```Bash
docker run --env-file ./.env --rm -it whenessel/dkp-activity-system:latest runbot
```


## Подготовка для запуска с помощью **docker compose**

В директории сервера требуется создать 2 файла:
- docker-compose.yml (пример [docker-compose.yml](resources/docker-compose.yml.template))
- docker-compose.env (пример [docker-compose.env](resources/docker-compose.env.template))

Заменить или вписать все необходимые параметры.

> Для запуска и подключения к внешнему серверу БД (PostgreSQL) 
> скачивать [docker-compose.yml](resources/docker-compose-ext-db.yml.template)


## Запуск с помощью **docker compose**
> Если старая версия docker compose, то использовать команду 'docker-compose'

```Bash
docker compose -f docker-compose.yml --env-file docker-compose.env up -d 

```


### HACKS

С подключением к БД из другой сети

```shell
# Create
docker create --env-file=.env --name=evebot --restart=always --link db_postgres_1:db_postgres_1 --net db_default -t whenessel/dkp-activity-system:latest runbot
docker start evebot


```
