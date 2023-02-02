from system.env import env


CACHES = {'default': env.cache('CACHE_URL', default='locmemcache://')}
